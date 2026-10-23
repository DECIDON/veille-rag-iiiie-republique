"""Étape 1 — normalisation du corpus (leçon 0001).

Le corpus d'entrée est un JSON canonique *par intervention* (contrat décrit
dans ``data/corpus/README.md``). Cette étape ne corrige rien du ``text_brut``
— il reste inchangé pour la recherche lexicale et la citation verbatim — et
produit en plus un ``text_normalise`` obtenu par règles : unification des
espaces, des apostrophes et des guillemets, rejointoiement des césures OCR,
décomposition Unicode NFKD,Whitespace aplati. Les noms d'orateurs sont
unifiés par le dictionnaire d'alias ``alias_orateurs.json`` ; le nom canonique
devient une métadonnée filtrable, jamais une correction du texte.

Aucune dépendance tierce : ce module doit pouvoir être testé partout.
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

CHAMPS_REQUIS = (
    "id", "date", "chambre", "session", "seance", "orateur", "text_brut", "page_jo",
)

_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
# Césure OCR : un mot coupé par un trait d'union en fin de ligne.
_CESURE = re.compile(r"([A-Za-zÀ-ÿà-ÿ])-[ \t\r]*\n[ \t]*(?=[A-Za-zÀ-ÿà-ÿ])")
# Variantes d'apostrophe et d'accent aigu utilisé comme apostrophe.
_APOSTROPHES = re.compile(r"[\u2018\u2019\u201a\u02b9\u02ba\u02bb\u02bc\u02be\u2032\u00b4]")


def normaliser_texte(texte: str) -> str:
    """Applique les règles de normalisation documentées à un texte OCR brut."""
    t = texte
    # 1. Unifier toutes les variantes d'espace (insécables, fines, étroites).
    for espace in ("\u00a0", "\u202f", "\u200a", "\u2009", "\u2008", "\u2007", "\u2006",
                   "\u2005", "\u2004", "\u2003", "\u2002", "\u2000"):
        t = t.replace(espace, " ")
    # 2. Supprimer les traits d'union mous, artefacts d'import Word/OCR.
    t = t.replace("\u00ad", "")
    # 3. Rejoindre les mots coupés par césure : « insti-\ntution » → « institution ».
    t = _CESURE.sub(r"\1", t)
    # 4. Unifier toutes les apostrophes sur l'apostrophe ASCII.
    t = _APOSTROPHES.sub("'", t)
    # 5. Unifier les guillemets : les français « … » perdent leurs espaces
    #    intérieures, les typographiques deviennent des guillemets droits.
    t = re.sub(r"\u00ab[ \u00a0]*", '"', t)
    t = re.sub(r"[ \u00a0]*\u00bb", '"', t)
    t = t.replace("\u201c", '"').replace("\u201d", '"')
    # 6. Décomposition NFKD (forme stable et comparable, ligatures et espaces
    #    de compatibilité repliées) puis recomposition NFC : les accents restent
    #    sous forme précomposée, lisible et comparable en Python comme en JSON.
    t = unicodedata.normalize("NFKD", t)
    t = unicodedata.normalize("NFC", t)
    # 7. Whitespace : un seul espace horizontal, saut de ligne normalisé,
    #    paragraphes séparés par une ligne vide.
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r" ?\n ?", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def cle_alias(nom: str) -> str:
    """Clé de comparaison de deux noms : minuscules, sans accents, sans apostrophe."""
    n = normaliser_texte(nom).replace("'", "")
    n = unicodedata.normalize("NFD", n.lower())
    n = "".join(c for c in n if not unicodedata.combining(c))
    n = re.sub(r"[^a-z0-9]+", "-", n)
    return n.strip("-")


def charger_alias(chemin: Path) -> dict[str, str]:
    """Lit ``{"nom canonique": ["variantes", …]}`` et retourne ``{clé: canonique}``."""
    chemin = Path(chemin)
    if not chemin.exists():
        return {}
    table_brute = json.loads(chemin.read_text(encoding="utf-8"))
    table: dict[str, str] = {}
    for canonique, variantes in table_brute.items():
        for variante in [canonique, *(variantes or [])]:
            table[cle_alias(variante)] = canonique
    return table


def charger_corpus(dossier: Path) -> list[dict]:
    """Charge toutes les interventions d'un dossier (``.json`` tableaux ou objets,
    et ``.jsonl`` un enregistrement par ligne). Refuse les identifiants dupliqués."""
    dossier = Path(dossier)
    enregistrements: list[dict] = []
    for chemin in sorted(dossier.glob("*.json")):
        if chemin.name == "alias_orateurs.json":
            continue
        contenu = chemin.read_text(encoding="utf-8").strip()
        if not contenu:
            continue
        données = json.loads(contenu)
        if isinstance(données, list):
            enregistrements.extend(données)
        elif isinstance(données, dict):
            enregistrements.append(données)
        else:
            raise ValueError(f"{chemin.name} : le JSON racine doit être un tableau ou un objet")
    for chemin in sorted(dossier.glob("*.jsonl")):
        for ligne in chemin.read_text(encoding="utf-8").splitlines():
            if ligne.strip():
                enregistrements.append(json.loads(ligne))
    vus: set[str] = set()
    for enreg in enregistrements:
        identifiant = enreg.get("id")
        if identifiant in vus:
            raise ValueError(f"identifiant dupliqué dans le corpus : {identifiant}")
        vus.add(identifiant)
    return enregistrements


def valider(enreg: dict) -> None:
    """Vérifie le contrat d'entrée ; lève ``ValueError`` avec la liste des manquants."""
    manquants = [c for c in CHAMPS_REQUIS if c not in enreg or enreg[c] in (None, "")]
    if manquants:
        apercu = json.dumps(enreg, ensure_ascii=False)[:160]
        raise ValueError(f"enregistrement invalide (champs requis absents : "
                         f"{', '.join(manquants)}) — {apercu}")
    orateur = enreg["orateur"]
    if not isinstance(orateur, dict) or not orateur.get("nom"):
        raise ValueError(f"champ « orateur » attendu comme objet avec une clé « nom » : {orateur}")
    if not _DATE.fullmatch(str(enreg["date"])):
        raise ValueError(f"champ « date » attendu au format AAAA-MM-JJ : {enreg['date']}")


def normaliser_enregistrement(enreg: dict, alias: dict[str, str]) -> dict:
    """Enrichit un enregistrement validé : ``text_normalise`` + ``nom_canonique``."""
    valider(enreg)
    orateur = dict(enreg["orateur"])
    nom = str(orateur["nom"])
    orateur["nom_canonique"] = alias.get(cle_alias(nom), nom)
    return {
        **enreg,
        "orateur": orateur,
        "text_normalise": normaliser_texte(str(enreg["text_brut"])),
    }


def ecrire_jsonl(enregistrements: list[dict], chemin: Path) -> None:
    chemin = Path(chemin)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with chemin.open("w", encoding="utf-8") as flux:
        for enreg in enregistrements:
            flux.write(json.dumps(enreg, ensure_ascii=False) + "\n")


def lire_jsonl(chemin: Path) -> list[dict]:
    chemin = Path(chemin)
    if not chemin.exists():
        raise FileNotFoundError(f"{chemin} absent — lancer l'étape qui le produit d'abord")
    return [json.loads(ligne) for ligne in chemin.read_text(encoding="utf-8").splitlines() if ligne.strip()]


def etape1(config) -> int:
    """Point d'entrée de l'étape 1 : corpus → ``data/normalise/interventions.jsonl``."""
    bruts = charger_corpus(config.corpus_dir)
    alias = charger_alias(config.corpus_dir / "alias_orateurs.json")
    enrichis = [normaliser_enregistrement(e, alias) for e in bruts]
    ecrire_jsonl(enrichis, config.normalise_dir / "interventions.jsonl")
    return len(enrichis)
