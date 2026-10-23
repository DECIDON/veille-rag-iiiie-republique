"""Étape 7 (bonus) — génération RAG via Ollama (leçon 0006).

Ollama expose une API compatible OpenAI ; l'appel part donc sur l'URL
``/v1/chat/completions``, ce qui rend le servable interchangeable avec vLLM
sans rien changer d'autre (leçon 0006 : « dénominateur commun de l'écosystème »).
Le prompt impose : répondre seulement des extraits fournis, citer
l'intervention et la page du Journal officiel, et renvoyer « INSUFFISANT » si
les extraits ne suffisent pas — la génération reste citation-first.
"""
from __future__ import annotations

import json
import urllib.request

SYSTEME = (
    "Tu réponds exclusivement à partir des extraits fournis. Tu cites chaque "
    "information entre crochets avec l'identifiant d'intervention et la page du "
    "Journal officiel. Si les extraits ne permettent pas de répondre, tu réponds "
    "exactement : INSUFFISANT. N'invente jamais de date, de nom ou de page."
)


def construire_prompt(question: str, resultats: list[dict]) -> list[dict]:
    """Construit les messages (system + user) à partir des résultats rerankés."""
    extraits = []
    for rang, r in enumerate(resultats, start=1):
        entete = (
            f"[{rang}] intervention {r['intervention_id']}, {r['orateur']}, "
            f"{r['chambre']}, {r['date']}, page JO {r['page_jo']}"
        )
        extraits.append(entete + "\n" + r["texte"])
    contenu = (
        "Extraits :\n\n" + "\n\n".join(extraits)
        + "\n\nQuestion : " + question
    )
    return [
        {"role": "system", "content": SYSTEME},
        {"role": "user", "content": contenu},
    ]


def generer(question: str, resultats: list[dict], config, timeout: int = 300) -> str:
    """Appelle l'API OpenAI-compatible d'Ollama et retourne le texte généré."""
    corps = json.dumps({
        "model": config.ollama_model,
        "messages": construire_prompt(question, resultats),
        "temperature": 0.2,
        "stream": False,
    }).encode("utf-8")
    requete = urllib.request.Request(
        config.ollama_url.rstrip("/") + "/v1/chat/completions",
        data=corps,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(requete, timeout=timeout) as reponse:
        donnees = json.loads(reponse.read().decode("utf-8"))
    return donnees["choices"][0]["message"]["content"].strip()
