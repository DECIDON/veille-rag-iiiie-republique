#!/usr/bin/env python3
"""Adaptateur : export brut « compte-rendu BnF » → contrat d'entrée de l'atelier.

Format source (un fichier = un compte-rendu exporté, tableau d'interventions) :

    {"orateur": "M. Regaud", "role": "l'un des secrétaires",
     "contenu": "… OCR brut …", "résumé": "…", "position": [29, 30, …],
     "canvasId": "…/f1/canvas"}

Le champ ``canvasId`` porte un folio (``/fN/``). Son interprétation dépend de
l'export : ici le folio **est le numéro de page** du Journal officiel
(``--page-canvas``), et l'export ne couvre **qu'une séance** — on force alors le
numéro de séance avec ``--seance N`` (``--segments canvas`` reste disponible
pour les exports qui mélangent plusieurs comptes-rendus en une séance par canvas).

Mapping appliqué à chaque enregistrement :

    orateur (+role)   → orateur : {"nom", "role", "groupe": null}   (civilés « M. » retirées du nom)
    contenu           → text_brut      (aucun nettoyage : c'est le contrat, leçon 0001)
    position          → page_jo        (première page du segment ; --offset-page si calage connu)
    canvasId          → page_jo quand --page-canvas (le folio /fN/ EST le numéro de page)
    résumé            → résumé         (conservé tel quel, champ optionnel du contrat)
    —                 → id, date, chambre, session, seance  (fournis par les options)

Fichiers sources : sous ``data/corpus/brut/`` uniquement — le chargeur de
l'atelier lit ``data/corpus/*.json`` au premier niveau et refuserait un fichier
brut sans ``id``. Sortie : ``data/corpus/{stem}.converti.json`` (tableau de
toutes les interventions du fichier, une ligne par intervention).

Usage (depuis docs/ateliers/axe1-pipeline) :

    mv mes_exports.json data/corpus/brut/
    uv run python outils/adaptateur_debats.py --chambre senat --date 1922-11-28 \
        --seance 2 --page-canvas
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

ATELIER = Path(__file__).resolve().parent.parent
CORPUS = ATELIER / "data" / "corpus"
BRUT = CORPUS / "brut"

_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
# Civilés d'interpellation en tête du nom observé : « M. », « MM. », « Mme. »…
_CIVILITE = re.compile(r"^(?:MM\.\s?|M{1,2}e\.\s?|Mmes?\s+|Mlles?\s+|M\.\s*)+", re.IGNORECASE)
_FOLIO = re.compile(r"/f(\d+)/")


def folio(canvas_id: str) -> int:
    """N° de folio porté par le canvasId (« …/f12/canvas ») ; 0 si absent."""
    m = _FOLIO.search(canvas_id or "")
    return int(m.group(1)) if m else 0


def segmenter(enregistrements: list[dict]) -> list[list[dict]]:
    """Un compte-rendu par canvasId, dans l'ordre de première apparition."""
    par_canvas: dict[int, list[dict]] = {}
    for e in enregistrements:
        par_canvas.setdefault(folio(e.get("canvasId", "")), []).append(e)
    return [par_canvas[k] for k in sorted(par_canvas)]


def nom_observé(enreg: dict, garder_civilites: bool) -> str:
    nom = str(enreg.get("orateur") or "").strip()
    if garder_civilites:
        return nom
    return _CIVILITE.sub("", nom).strip() or nom


def convertir_segment(
    segment: list[dict], numero_seance: int, options: argparse.Namespace
) -> list[dict]:
    interventions = []
    for rang, e in enumerate(segment, start=1):
        if options.page_canvas:
            page = folio(e.get("canvasId", ""))
            if not page:
                raise ValueError(
                    f"--page-canvas : pas de folio /fN/ dans le canvasId de "
                    f"{str(e.get('contenu', ''))[:80]!r}"
                )
        else:
            position = e.get("position") or []
            if not position:
                raise ValueError(
                    f"intervention sans « position » (citation de page impossible) : "
                    f"{str(e.get('contenu', ''))[:80]!r}"
                )
            page = min(position) + options.offset_page
        enreg = {
            "id": f"{options.chambre}-{options.date}-s{numero_seance:03d}-i{rang:03d}",
            "date": options.date,
            "chambre": options.chambre,
            "session": options.session,
            "seance": str(numero_seance),
            "orateur": {
                "nom": nom_observé(e, options.garder_civilites),
                "role": e.get("role"),
                "groupe": None,
            },
            "text_brut": e["contenu"],
            "page_jo": page,
        }
        if e.get("résumé"):
            enreg["résumé"] = e["résumé"]
        interventions.append(enreg)
    return interventions


def proposer_alias(convertis: list[dict]) -> list[dict]:
    """Graphies qui ne diffèrent que par la casse/ponctuation une fois les
    civilés retirées : à basculer dans alias_orateurs.json, pas ici."""
    par_cle: dict[str, set[str]] = {}
    for enreg in convertis:
        nom = enreg["orateur"]["nom"]
        sans_accents = unicodedata.normalize("NFD", nom.casefold()) \
            .encode("ascii", "ignore").decode()
        cle = re.sub(r"[^a-z0-9]+", "", sans_accents)
        par_cle.setdefault(cle, set()).add(nom)
    propositions = []
    for noms in par_cle.values():
        if len(noms) > 1:
            canonique = max(noms, key=len)  # la graphie la plus complète sert de cible
            propositions.append({"nom canonique": canonique,
                                 "variantes": sorted(noms - {canonique})})
    return propositions


def traiter(chemin: Path, options: argparse.Namespace) -> tuple[list[dict], list[list[dict]]]:
    donnees = json.loads(chemin.read_text(encoding="utf-8"))
    if isinstance(donnees, dict):
        donnees = [donnees]
    if not isinstance(donnees, list):
        raise ValueError(f"{chemin} : tableau d'interventions attendu")
    if options.seance:                     # tout le fichier = une seule séance, numérotée N
        conversions = [donnees]
        premier = options.seance
    else:
        conversions = segmenter(donnees) if options.segments == "canvas" else [donnees]
        premier = 1
    convertis = []
    for numero, segment in enumerate(conversions, start=premier):
        convertis.extend(convertir_segment(segment, numero, options))
    return convertis, conversions


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        epilog="Mapping et conventions : voir l'en-tête de ce script.",
    )
    p.add_argument("entrees", nargs="*", type=Path,
                   help="fichiers bruts (défaut : tous les *.json de data/corpus/brut/)")
    p.add_argument("--chambre", required=True, choices=("chambre", "senat"),
                   help="valeur stable de la facette « chambre » pour ce lot")
    p.add_argument("--date", required=True, metavar="AAAA-MM-JJ",
                   help="date des séances du lot (un export = une séance : "
                        "sinon relancer par export, la date est une métadonnée, pas une devinette)")
    p.add_argument("--session", default=None,
                   help="facette « session » (défaut : l'année de --date)")
    p.add_argument("--offset-page", type=int, default=0,
                   help="décalage à ajouter à « position » pour obtenir la page JO imprimée")
    p.add_argument("--segments", choices=("canvas", "aucun"), default="canvas",
                   help="« canvas » (défaut) : une séance par canvasId ; « aucun » : tout le fichier = 1 séance")
    p.add_argument("--seance", type=int, default=None, metavar="N",
                   help="tout le fichier = la séance N unique (prime sur --segments)")
    p.add_argument("--page-canvas", action="store_true",
                   help="le folio /fN/ du canvasId est le numéro de page du Journal officiel")
    p.add_argument("--garder-civilites", action="store_true",
                   help="ne pas retirer « M. », « Mme »… des noms d'orateurs")
    p.add_argument("--force", action="store_true", help="écraser une sortie existante")
    p.add_argument("--sortie", type=Path, default=CORPUS,
                   help=f"dossier de sortie (défaut : {CORPUS})")
    options = p.parse_args(argv)
    options.session = options.session or options.date[:4]

    if not _DATE.fullmatch(options.date):
        p.error("« --date » attendu au format AAAA-MM-JJ")

    entrees = options.entrees
    if not entrees:
        entrees = sorted(BRUT.glob("*.json"))
        if not entrees:
            print(f"aucun fichier brut dans {BRUT}/ — déposer vos exports là (jamais dans data/corpus/)",
                  file=sys.stderr)
            return 1
    for chemin in entrees:
        if chemin.resolve().parent == CORPUS.resolve():
            print(f"{chemin} : un fichier brut ne doit pas rester dans data/corpus/ — "
                  f"le chargeur le lirait et rejeterait l'absence d'« id ». Déplacez-le dans brut/.",
                  file=sys.stderr)
            return 1

    echec = 0
    for chemin in entrees:
        try:
            convertis, conversions = traiter(chemin, options)
        except (ValueError, KeyError, json.JSONDecodeError) as e:
            print(f"{chemin} : {e}", file=sys.stderr)
            echec = 1
            continue
        destination = options.sortie / f"{chemin.stem}.converti.json"
        if destination.exists() and not options.force:
            print(f"{destination} existe déjà — relancer avec --force", file=sys.stderr)
            echec = 1
            continue
        destination.write_text(
            json.dumps(convertis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        seances = ", ".join(
            f"s{n:03d} ({len(c)} int.)"
            for n, c in enumerate(conversions, start=options.seance or 1)
        )
        print(f"{chemin.name} → {destination.name} : {len(convertis)} interventions, {len(conversions)} séance(s) — {seances}")
        for proposition in proposer_alias(convertis):
            print(f"  alias à envisager : {json.dumps(proposition, ensure_ascii=False)}")
    if not echec:
        print("ensuite : make test && make smoke   (l'étape 1 valide le contrat de chaque enregistrement)")
    return echec


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
