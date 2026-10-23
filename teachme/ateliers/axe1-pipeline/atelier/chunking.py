"""Étape 2 — découpage par intervention, hiérarchie enfant/parent (leçon 0002).

L'unité documentaire du Journal officiel est l'intervention ; elle sert de
*granulat enfant* indexé. La séance reconstituée sert de *parent*, stockée sur
disque (``data/parents/seances.jsonl``) et restituée à l'affichage et à la
génération : c'est la restitution parent-document « applicative » que la veille
décrit (§2), sans dépendre d'un framework.

Une intervention trop longue (``max_tokens_chunk``, ~1 200 tokens) est
sous-découpée en fragments numérotés qui partagent le même ``parent_id``.
L'estimation de tokens est un simple compteur de mots majoré de 30 % :
suffisant pour borne-réguler, et sans dépendance à un tokenizer HuggingFace.
"""
from __future__ import annotations

import re
from collections import OrderedDict

from .normalisation import lire_jsonl, ecrire_jsonl


def estimer_tokens(texte: str) -> int:
    """Estime des tokens par les mots (×1,3) ; suffisant pour encadrer la taille."""
    return max(1, round(len(texte.split()) * 1.3))


def _paragraphes(texte: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", texte) if p.strip()]


def _phrases(texte: str) -> list[str]:
    return [p.strip() for p in re.split(r"(?<=[.!?…:;])\s+", texte) if p.strip()]


def decouper_texte(texte: str, max_tokens: int) -> list[str]:
    """Découpe un texte normalisé en fragments ≤ ``max_tokens`` tokens estimés.

    Ordre de préférence : paragraphes entiers, puis phrases, puis découpe
    monotone en mots (dernier recours pour une phrase interminable).
    """
    if estimer_tokens(texte) <= max_tokens:
        return [texte]
    fragments: list[str] = []
    courant: list[str] = []

    def basculer() -> None:
        nonlocal courant
        if courant:
            fragments.append("\n\n".join(courant))
            courant = []

    for para in _paragraphes(texte):
        if estimer_tokens(para) <= max_tokens:
            if estimer_tokens("\n\n".join([*courant, para])) > max_tokens:
                basculer()
            courant.append(para)
            continue
        basculer()
        morceau: list[str] = []
        for phrase in _phrases(para):
            if morceau and estimer_tokens(" ".join([*morceau, phrase])) > max_tokens:
                fragments.append(" ".join(morceau))
                morceau = [phrase]
            else:
                morceau.append(phrase)
        if morceau:
            fragments.append(" ".join(morceau))
    basculer()

    finaux: list[str] = []
    for frag in fragments:
        if estimer_tokens(frag) <= max_tokens:
            finaux.append(frag)
            continue
        mots = frag.split()
        taille = max(50, int(max_tokens / 1.3))
        for i in range(0, len(mots), taille):
            finaux.append(" ".join(mots[i:i + taille]))
    return finaux


def identifiant_seance(enreg: dict) -> str:
    """Identifiant déterministe du parent : chambre, date, numéro de séance."""
    return f"{enreg['chambre']}-{enreg['date']}-s{str(enreg['seance']).zfill(3)}"


def enficher(enreg: dict, max_tokens: int = 1200) -> list[dict]:
    """Une intervention normalisée → un ou plusieurs granulats enfants indexables."""
    parent = identifiant_seance(enreg)
    fragments = decouper_texte(enreg["text_normalise"], max_tokens)
    enfants = []
    for rang, fragment in enumerate(fragments, start=1):
        enfants.append({
            "id": f"{enreg['id']}-c{rang:02d}",
            "intervention_id": enreg["id"],
            "parent_id": parent,
            "chunk_index": rang,
            "chunk_total": len(fragments),
            "texte": fragment,
            "date": enreg["date"],
            "chambre": enreg["chambre"],
            "session": enreg["session"],
            "seance": enreg["seance"],
            "orateur": enreg["orateur"].get("nom_canonique", enreg["orateur"]["nom"]),
            "orateur_brut": enreg["orateur"]["nom"],
            "role": enreg["orateur"].get("role"),
            "groupe": enreg["orateur"].get("groupe"),
            "titre_parent": enreg.get("titre_parent"),
            "ordre_du_jour": enreg.get("ordre_du_jour") or [],
            "page_jo": enreg["page_jo"],
        })
    return enfants


def seance_parent(interventions: list[dict]) -> dict:
    """Reconstitue le document parent (la séance) à partir de ses interventions."""
    premiere = interventions[0]
    texte = "\n\n".join(
        f"### {e['orateur'].get('nom_canonique', e['orateur']['nom'])} — "
        f"page {e['page_jo']}\n\n{e['text_brut']}"
        for e in interventions
    )
    return {
        "id": identifiant_seance(premiere),
        "date": premiere["date"],
        "chambre": premiere["chambre"],
        "session": premiere["session"],
        "seance": premiere["seance"],
        "intervenants": sorted({
            e["orateur"].get("nom_canonique", e["orateur"]["nom"]) for e in interventions
        }),
        "interventions": [e["id"] for e in interventions],
        "texte_reconstitue": texte,
    }


def etape2(config) -> tuple[int, int]:
    """Point d'entrée de l'étape 2 : interventions normalisées → enfants + parents."""
    interventions = lire_jsonl(config.normalise_dir / "interventions.jsonl")
    enfants: list[dict] = []
    par_seance: "OrderedDict[str, list[dict]]" = OrderedDict()
    for enreg in interventions:
        enfants.extend(enficher(enreg, config.max_tokens_chunk))
        par_seance.setdefault(identifiant_seance(enreg), []).append(enreg)
    parents = [seance_parent(groupe) for groupe in par_seance.values()]
    ecrire_jsonl(enfants, config.enfants_path)
    ecrire_jsonl(parents, config.parents_path)
    return len(enfants), len(parents)
