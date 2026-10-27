# Jeu de questions-réponses — évaluation du retrieval (leçon 0012, étape 6)

> Le corpus fourni (Sénat, 28 novembre 1922, budget de l'aéronautique) possède
> déjà 28 questions-réponses annotées et ancrées verbatim dans
> [`queries.json`](queries.json) — les seules que ce corpus rende possibles,
> car une vérité terrain annotée sans lire les sources ne vaut rien. Les deux
> questions ci-dessous en sont extraites pour que l'évaluation tourne de bout
> en bout dès aujourd'hui. Les questions de *vos* corpus devront être annotées
> à la main : une question réelle posée au corpus + l'identifiant (ou les
> identifiants) de l'intervention qu'une bonne recherche **doit** retrouver.

## Format d'un bloc

Un bloc = une question. La première ligne du bloc commence par un identifiant
court suivi de ` — ` et d'un intitulé libre. Les trois lignes d'attributs sont
des puces Markdown :

```markdown
## Q7 — courte description du cas
- question: la recherche textuelle envoyée au pipeline (mots-clés, pas une phrase bavarde)
- question_oracle: mots-clés pris dans la réponse — plafond de comparaison, jamais la question
- attendus: id-dintervention-attendue, autre-id-eventuel
- filtres: chambre=senat; from=1922-11-01; to=1922-11-30; orateur=Charles Tisseyre
```

- `question` : ce que tape le chercheur (mot-clés courts, sans verbe creux) ;
  dérivée du besoin **seul** — n'y remettez pas les termes qui constituent la
  réponse (listes, chiffres, citations relevées dans les sources), sinon vous
  notez un oracle, pas un système ;
- `question_oracle` : optionnel ; la requête idéale, telle que la connaît
  quelqu'un qui a déjà lu la source. `evaluer` affiche le rappel et le MRR des
  deux passes et leur écart (le « gap lexical ») ;
- `attendus` : séparés par des virgules, identifiants **d'intervention**
  (champ `id` du JSON canonique) — l'évaluation compare sur ce champ, pas sur
  l'identifiant du granulat ;
- `filtres` : optionnel, paires `clef=valeur` séparées par `;` (clés :
  `chambre`, `orateur`, `from`, `to`, `session`).

Un bloc sans `question:` ou sans `attendus:` est ignoré — les exemples de
gabarit peuvent donc rester dans ce fichier.

## Questions du corpus fourni

## Q1 — quel texte ouvre la discussion (Sénat, 1922)
- question: ordre du jour séance section budget
- question_oracle: budget general exercice 1923 travaux publics 3e section aeronautique
- attendus: senat-1922-11-28-s002-i007
- filtres: chambre=senat; from=1922-11-01; to=1922-11-30

## Q2 — l'exemple de Laval : terrains civils contre pistes militaires
- question: Montjou étatisme exemple personnel
- question_oracle: laval conseil municipal 200 000 francs terrain football abracadabrante
- attendus: senat-1922-11-28-s002-i139, senat-1922-11-28-s002-i140, senat-1922-11-28-s002-i141, senat-1922-11-28-s002-i142

## Gabarit à copier pour les questions du corpus réel

## Q_ — description du cas
- question:
- attendus:
