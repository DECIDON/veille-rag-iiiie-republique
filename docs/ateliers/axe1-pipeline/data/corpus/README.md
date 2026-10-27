# Contrat d'entrée : le corpus JSON

Ce dossier reçoit le corpus que vous préparez. Chaque fichier `*.json` est un
**tableau d'interventions** (ou un seul objet, ou un fichier `*.jsonl` à un
enregistrement par ligne — le chargeur accepte les trois formes). Un
enregistrement = **une intervention** d'un orateur, jamais une séance entière.

## Format attendu (par enregistrement)

```json
{
  "id": "chambre-1890-01-28-s001-i003",
  "date": "1890-01-28",
  "chambre": "chambre",
  "session": "1890",
  "seance": "1",
  "résumé": "Ferry expose le budget de l'instruction primaire comme la vraie dette de l'État",
  "orateur": {"nom": "J. Ferry", "role": "ministre de l'instruction publique", "groupe": null},
  "text_brut": "… texte OCR tel quel …",
  "page_jo": 245
}
```

| Champ | Requis | Type | Rôle dans le pipeline |
|---|---|---|---|
| `id` | oui | chaîne | identifiant **unique** de l'intervention ; convention conseillée `{chambre}-{date}-s{séance}-i{n}` |
| `date` | oui | `AAAA-MM-JJ` | facettes temporelles, filtres, tri |
| `chambre` | oui | `"chambre"` \| `"senat"` ( valeurs stables et normalisées) | facette |
| `session` | oui | chaîne | facette (année parlementaire ou législature) |
| `seance` | oui | chaîne ou entier | identifie le parent avec `chambre` + `date` |
| `orateur` | oui | objet | `nom` (requis, graphie telle qu'observée), plus `role` et `groupe` en option |
| `text_brut` | oui | chaîne | texte OCR **sans nettoyage** : c'est lui qui nourrit la citation verbatim |
| `page_jo` | oui | entier | page du Journal officiel, pour la citation |
| `résumé` | non | chaîne | court résumé de l'intervention (métadonnée de contexte, restituée à l'affichage) |

## Ce que le pipeline ajoute (ne le fournissez pas)

- `text_normalise` : calculé par l'étape 1 (NFKD, apostrophes, césures, espaces) ;
  c'est lui, et lui seul, qui est encodé (`text_brut` reste intact, leçon 0001).
- `orateur.nom_canonique` : résolu par l'étape 1 via `alias_orateurs.json`,
  au format `{"nom canonique": ["variante 1", "variante 2", …]}`.
- Les champs de granulat (`id` d'enfant, `parent_id`, `chunk_index`…) créés par
  l'étape 2.

## Règles

1. Ne pré-nettoyez rien : césures (même si votre export les aplaties en
   « lec- ture » — l'étape 1 sait les rejoindre), apostrophes variées, accents
   instables sont
   exactement ce que l'étape 1 doit digérer — votre corpus réel doit les garder.
2. Un `id` par intervention, unique dans tout le dossier (le chargeur refuse les
   doublons).
3. Des valeurs de `chambre` stables : le filtre exact s'appuie dessus.
4. Fichier de départ fourni : `exemple.json` (5 interventions, 2 séances) — il
   fait tourner tout le pipeline et tous les tests sans données réelles ; vous le
   retirerez quand votre corpus sera en place.
5. Vos exports bruts (formats d'un autre jour, sans `id` ni date) ne vont **jamais**
   dans ce dossier : le chargeur lirait un fichier sans identifiants et refuserait
   tout le lot. Déposez-les dans `brut/` (souterrain, jamais scanné) et convertissez :

   ```sh
   uv run python outils/adaptateur_debats.py --chambre senat --date 1922-11-27
   ```

   L'adaptateur (`outils/adaptateur_debats.py`) traduit l'export « compte-rendu
   BnF » (`orateur`/`contenu`/`position`/`résumé`/`canvasId`) vers le contrat ci-dessus :
   le folio `/fN/` du canvas est le numéro de page du JO avec `--page-canvas`,
   sinon `position` → `page_jo` (première page du segment, `--offset-page` si vous
   connaissez le calage avec la page imprimée) ; les civilés « M. » sont retirées
   des noms, et le `résumé` traverse tel quel. Une sortie par fichier brut :
   `brut/x.json` → `x.converti.json`. Pour l'échantillon déposé ici (une seule
   séance, la 2 du 28 novembre 1922, page = folio du canvas) :

   ```sh
   uv run python outils/adaptateur_debats.py --chambre senat --date 1922-11-28 \
       --seance 2 --page-canvas
   ```
