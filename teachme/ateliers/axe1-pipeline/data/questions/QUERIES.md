# Jeu de questions-réponses — évaluation du retrieval (leçon 0012, étape 6)

> **À compléter ensemble dans une autre session.** Les deux premières questions
> sont fournies et portent sur le mini-corpus d'exemple (`exemple.json`) pour
> que l'évaluation tourne de bout en bout dès aujourd'hui. Pour le corpus réel,
> chaque question devra être annotée à la main : une question réelle posée au
> corpus + l'identifiant (ou les identifiants) de l'intervention qu'une bonne
> recherche **doit** retrouver (la vérité terrain).

## Format d'un bloc

Un bloc = une question. La première ligne du bloc commence par un identifiant
court suivi de ` — ` et d'un intitulé libre. Les trois lignes d'attributs sont
des puces Markdown :

```markdown
## Q7 — courte description du cas
- question: la recherche textuelle envoyée au pipeline (mots-clés, pas une phrase bavarde)
- attendus: id-dintervention-attendue, autre-id-eventuel
- filtres: chambre=senat; from=1891-01-01; to=1891-12-31; orateur=Jules Ferry
```

- `question` : ce que tape le chercheur (mot-clés courts, sans verbe creux) ;
- `attendus` : séparés par des virgules, identifiants **d'intervention**
  (champ `id` du JSON canonique) — l'évaluation compare sur ce champ, pas sur
  l'identifiant du granulat ;
- `filtres` : optionnel, paires `clef=valeur` séparées par `;` (clés :
  `chambre`, `orateur`, `from`, `to`, `session`).

Un bloc sans `question:` ou sans `attendus:` est ignoré — les exemples de
gabarit peuvent donc rester dans ce fichier.

## Questions du corpus d'exemple (les deux seules qui tournent sans données réelles)

## Q1 — un ministre défend le budget des écoles primaires (Chambre, 1890)
- question: budget credit ecole primaire instituteurs
- attendus: chambre-1890-01-28-s001-i003
- filtres: chambre=chambre; from=1890-01-01; to=1890-12-31

## Q2 — critiques des crédits de l'expédition de Madagascar
- question: credits expedition Madagascar
- attendus: chambre-1890-01-28-s001-i007

## Gabarit à copier pour les questions du corpus réel

## Q_ — description du cas
- question:
- attendus:
