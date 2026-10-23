# Leçon 0001 (suite) : raisonne déjà en stratification stockage / génération / affichage

Deuxième question de la session : où attacher des métadonnées dérivées (thème, résumé) d'une intervention. La réponse enseignée — champ indexé du record, étage d'enrichissement versionné entre normalisation et embedding, affichage étiqueté — a été reçue sans friction ; l'utilisateur situe maintenant de lui-même une notion nouvelle dans les trois étages du pipeline.

**Implications (ZPD).**
- Ne plus enseigner les briques isolément : systématiquement positionner chaque notion dans le pipeline (normalisation → enrichissement → encodage → index → retrieval → UI) et dans ses contraintes (coût LLM, vérifiabilité, déterminisme).
- Les thèmes/résumés relèvent d'un arbitrage non tranché par la veille (coût = l'objection RAPTOR, §2 axe 1) : bonne piste pour une leçon « atelier enrichissement » (classifieur léger sur vocabulaire contrôlé, CPU) après la leçon 0006.
- Notion à rejouer plus tard : l'analogie résumé-d'intervention ↔ résumé-de-séance (variante soft de RAPTOR) — vérifier qu'il la fait de lui-même.
