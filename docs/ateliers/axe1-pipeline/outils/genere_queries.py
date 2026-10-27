"""Construit data/questions/queries.json à partir du compte rendu brut de la BnF.

Usage :  uv run python outils/genere_queries.py
Sortie : data/questions/queries.json (28 questions, 117 citations ancrées).


Chaque réponse est rattachée aux interventions qui la fondent, avec une citation
verbatim du champ `contenu`. Les citations sont saisies en mode tolérant
(accents, apostrophes, césures OCR ignorés à la recherche) puis remises dans
leur graphie exacte du texte source : le script échoue si une citation n'est pas
ancrée dans l'intervention indiquée.
"""

import json
import re
import unicodedata
from pathlib import Path

# Le script se lance depuis n'importe o : les chemins sont pris relativement au fichier.
RACINE = Path(__file__).resolve().parent.parent
BRUT = RACINE / "data/corpus/brut/debats.json"
CANONIQUE = RACINE / "data/corpus/debats.converti.json"
SORTIE = RACINE / "data/questions/queries.json"

brut = json.loads(BRUT.read_text(encoding="utf-8"))
canonique = json.loads(CANONIQUE.read_text(encoding="utf-8"))

VARIANTES = {
    "a": "àâä",
    "c": "ç",
    "e": "éèêë",
    "i": "îï",
    "n": "ñ",
    "o": "ôö",
    "u": "ùûü",
    "y": "ÿ",
}


def motif(extrait: str) -> str:
    """Motif de recherche tolérant : un token alphanumrique à la fois, césures admises."""
    tokens = re.findall(r"[0-9A-Za-zÀ-ÿ]+", extrait)
    parties = []
    for token in tokens:
        chars = []
        for c in token.lower():
            cls = re.escape(c)
            for base, var in VARIANTES.items():
                if c in var:
                    cls = f"[{base}{var}]"
                    break
            chars.append(cls)
        parties.append(r"[-’\-\u2010-\u2015]?\s*".join(chars))
    # Les tokens ne peuvent être séparés que par de la ponctuation ou de l'espace, jamais
    # par d'autres mots : c'est ce qui empêche d'ancrer la citation en pleine phrase.
    écart = r"(?:[^0-9A-Za-zÀ-ÿ][^0-9A-Za-zÀ-ÿ]{0,14}?)"
    return rf"(?<![0-9A-Za-zÀ-ÿ]){écart.join(parties)}(?![0-9A-Za-zÀ-ÿ])"


def canon(texte: str) -> str:
    """Forme de comparaison : minuscules, sans accents, sans ponctuation ni espaces."""
    t = unicodedata.normalize("NFKD", texte)
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = t.replace("’", "'").replace("‘", "'")
    return re.sub(r"[^0-9a-z]", "", t.lower())


def folio(entete):
    m = re.search(r"/f(\d+)/canvas", entete["canvasId"])
    return int(m.group(1)) if m else None


ERREURS = []


def citation(index, extrait):
    """Retourne la référence complète d'une citation, ancrée et vérifiée."""
    e, c = brut[index - 1], canonique[index - 1]
    m = re.search(motif(extrait), e["contenu"], re.DOTALL | re.IGNORECASE)
    verbatim = m.group(0) if m else None
    if verbatim is None or canon(verbatim) != canon(extrait):
        ERREURS.append((c["id"], extrait, e["contenu"]))
        verbatim = extrait
    return {
        "id": c["id"],
        "orateur": e["orateur"],
        "folio_du_jo": folio(e),
        "resume": e["résumé"],
        "citation": verbatim,
    }


Q = []


def q(intitule, reponse, requete, methode, sources, *, realiste):
    """Ajoute une question.

    Règle d'annotation : `requete` est la formulation *oracle* — les mots-clés
    qui constituent la réponse (listes, chiffres, hapax relevés dans les sources).
    Elle sert de plafond de comparaison, jamais de question réelle. `realiste`
    est la formulation recherchable, dérivée de l'intitulé seul : celui qui
    pose la question ne connaît pas encore le texte qui la fonde, et l'évaluateur
    mesure l'écart entre les deux (le « gap lexical » du système).
    """
    Q.append((intitule, reponse, requete, methode, sources, realiste))


q(
    "Quel texte est à l'ordre du jour de cette séance et de quelle section précise du budget débat-on ?",
    "La séance reprend le projet de loi portant fixation du budget général de l'exercice 1923, et plus précisément la 3e section du ministère des Travaux publics : Aéronautique et transports aériens. La discussion générale avait été commencée la veille, et le vote de ce budget est présenté comme « impatiemment attendu ».",
    "budget général exercice 1923 travaux publics 3e section aéronautique transports aériens",
    "L'énoncé présidentiel d'ouverture contient la formule réglementaire complète : la réponse se relève mot à mot dans cette seule intervention, sans recoupement nécessaire.",
    [(7, "la suite de la discussion du projet de loi portant fixation du budget général de l'exercice 1923")],
    realiste='ordre du jour séance section budget',
)

q(
    "Qui est le sous-secrétaire d'État de l'Aéronautique qui monte à la tribune, et de quels dossiers doit-il répondre ici ?",
    "M. Laurent Eynac, sous-secrétaire d'État de l'Aéronautique. On l'y voit appelé sur quatre dossiers distincts : la politique de subventions aux compagnies et aux colonies, l'état d'avancement du projet de loi sur le régime des compagnies de navigation aérienne, la représentation française aux conversations de Lausanne, et le recrutement du personnel des aérodromes, qu'il défend pied à pied contre Montjou.",
    "Laurent Eynac sous-secrétaire d'État aéronautique subventions Lausanne concours",
    "Le nom complet n'apparaît que dans trois interventions (la sienne et deux fois sous la plume de Flandin) ; le dossier d'attribution se reconstitue en agrégant des interventions très éloignées (i037, i041 pour les subventions ; i053 pour le projet de loi ; i127 pour Lausanne ; i144 à i160 pour le personnel). Aucune intervention ne les énumère toutes.",
    [
        (37, "mon attention est très tournée sur le développement de l'aéronautique aux colonies"),
        (100, "dans la personne de M. Laurent Eynac et de ses collaborateurs d'hier et d'aujourd'hui"),
        (127, "Le sous-secrétariat d'État de l'aéronautique est représenté dans les conversations de Lausanne"),
        (146, "Notre personnel est recruté par voie de concours"),
    ],
    realiste="sous-secrétaire d'État aéronautique tribune dossiers",
)

q(
    "Quelles mesures concrètes de sécurité aérienne Tisseyre réclame-t-il pour « donner confiance au public » ?",
    "Sept mesures, annoncées comme de simples « petites mesures de précaution » : (1) le double poste de pilotage imposé à tous les appareils des compagnies, quel que soit le nombre de passagers ; (2) la vérification des moteurs par un personnel étranger aux compagnies et qui ne navigue pas ; (3) le maintien d'un nombre élevé de terrains d'atterrissage, contre l'avis du rapporteur ; (4) la multiplication des postes de météorologie ; (5) la T. S. F. et les extincteurs à bord de tous les appareils ; (6) la mise à contribution des sociétés aéronautiques locales pour former des pilotes ; (7) des écoles de pilotage créées par les compagnies et subventionnées par les constructeurs, avec avantages militaires accordés aux pilotes civils.",
    "sécurité double poste de pilotage moteurs météorologie extincteurs T.S.F. terrains d'atterrissage écoles de pilotage",
    "Tisseyre annonce lui-même un programme (i011) puis le déroule en une succession d'interventions courtes et spécialisées ; la liste n'existe nulle part en tant que telle. Elle se reconstitue en agrégeant i012, i013, i014, i016, i017, i018 et i019, toutes du même orateur et reliées par les formules d'enchaînement (« Il faudrait, d'autre part », « Je voudrais aussi », « Il est également indispensable »).",
    [
        (11, "il suffirait, dans l'état actuel des choses, de prendre quelques petites mesures de précaution"),
        (12, "tous les appareils mis en service dans les compagnies d'aviation devraient, quel que soit le nombre des passagers emportés, comporter un double poste de pilotage"),
        (13, "les moteurs ne fussent pas vérifiés par le personnel navigant des compagnies"),
        (16, "Je voudrais aussi que les postes de météorologie fussent multipliés"),
        (17, "tous les appareils soient munis d'appareils de T. S. F."),
    ],
    realiste='Tisseyre mesures sécurité aérienne confiance du public',
)

q(
    "Comment Tisseyre imagine-t-il la carrière d'un jeune pilote à bord des lignes ?",
    "Par échelons progressifs, rendus possibles par le doublage permanent du pilote : le second, jeune pilote, reçoit la manœuvre au-delà d'une certaine altitude, là où elle est la plus facile, tandis que le pilote chef se repose et garde les manœuvres délicates du décollage et de l'atterrissage ; après un certain nombre de voyages ainsi faits, on lui confie un appareil ne transportant que messageries ou courriers postaux ; enfin, après avoir transporté colis et lettres, il reçoit la direction d'un appareil portant des passagers. Il acquiert ainsi la maîtrise de son appareil et la connaissance des terrains survolés.",
    "double poste jeune pilote messageries courriers postaux passagers altitude atterrissage décollage",
    "Tout tient dans une seule intervention (i012), la plus longue de la série de Tisseyre ; la réponse tient à la chronologie interne du paragraphe, et non à un mot isolé, ce qui en fait un bon test de granulat : une fenêtre de recherche trop courte ne conserverait qu'un des trois échelons.",
    [(12, "Le second pourrait être un jeune pilote à qui serait confiée la manœuvre de l'appareil au delà d'une certaine altitude")],
    realiste='Tisseyre carrière jeune pilote à bord des lignes',
)

q(
    "Pourquoi Tisseyre exige-t-il que les moteurs ne soient pas vérifiés par les compagnies elles-mêmes ?",
    "Parce que les pilotes contractent très vite une « insouciance » qu'il admire, mais qui risque d'être préjudiciable aux passagers qui confient leur vie à ces appareils et à ces pilotes : d'où la nécessité d'un vérificateur indépendant, appartenant à un personnel qui ne navigue pas.",
    "vérification des moteurs insouciance passagers personnel indépendant compagnies",
    "L'argument tient en une phrase finale (i013) ; le mot « insouciance » n'a d'autre emploi dans tout le corpus, ce qui fait de cette question un cas à rappel élevé pour peu de mots.",
    [(13, "Les pilotes acquièrent très rapidement une insouciance que j'admire, mais qui risque d'être préjudiciable aux passagers")],
    realiste='Tisseyre vérification des moteurs compagnies',
)

q(
    "Pourquoi réclamer beaucoup de terrains d'atterrissage alors que les appareils deviennent plus sûrs ?",
    "Tisseyre concède au rapporteur l'hypothèse la plus favorable — un appareil « géant, extrêmement puissant, multi-moteur » rendant les pannes presque l'exception — et conclut quand même à la multiplication des terrains : un appareil soumis à un élément mécanique restera « à la merci d'un petit accident qui l'obligera à atterrir n'importe où », et il faut qu'il trouve alors un terrain en bon état. Le général de Castelnau approuve cette position.",
    "terrains d'atterrissage nombreux appareil géant multi-moteur panne petit accident",
    "Le raisonnement est une concession dont les deux membres sont dans la même intervention (i014) ; la validation vient d'un orateur différent, dans l'une des plus courtes interventions du corpus (i015), qui transforme une opinion personnelle en position partagée.",
    [
        (14, "l'appareil de demain serait-il un appareil géant, extrêmement puissant, multi-moteur, avec lequel les pannes deviendraient presque l'exception, qu'il faudrait quand même des terrains d'atterrissage très nombreux"),
        (14, "un petit accident qui l'obligera à atterrir n'importe où, dans n'importe quelle circonstance"),
        (15, "C'est exact."),
    ],
    realiste="terrains d'atterrissage nombreux appareils plus sûrs",
)

q(
    "Comment Tisseyre réconcilie-t-il les accidents mortels avec l'idée que l'aviation de transport est sûre ?",
    "En distinguant deux populations d'accidents : ceux des exercices audacieux de la formation militaire et de la recherche d'appareils plus puissants ou plus rapides, qui les rend très nombreux en cumul ; et ceux de « l'aviation commerciale proprement dite », l'aviation pratique utilisée par le grand public, qui sont « heureusement encore assez rares ». Il n'en tire pourtant aucune sécurité acquise : après avoir salué les victimes — « La route du progrès est toujours ensanglantée » — il fait de la confiance du public la « pierre d'achoppement de l'avenir de l'aviation », sans laquelle l'aviation reste chère et sans passagers.",
    "accidents mortels aviation commerciale confiance du public passagers pierre d'achoppement",
    "La réponse est un montage de trois fragments consécutifs d'un même discours : la statistique comparative dans i009, la formule morale dans i010, la conséquence économique dans i021. Le deuxième fragment tient en deux lignes et ne serait pas retrouvé sur les mots-clés de la question : c'est le cas typique où le résumé méta-donné sauve le rappel.",
    [
        (9, "si nous ne considérons que ceux qui surviennent dans l'aviation commerciale proprement dite, dans l'aviation pratique, dans l'aviation utilisée par le grand public, nous nous apercevons qu'ils sont heureusement encore assez rares"),
        (10, "La route du progrès est toujours ensanglantée"),
        (21, "confiance qui restera la pierre d'achoppement de l'avenir de l'aviation"),
    ],
    realiste='Tisseyre accidents mortels aviation de transport sûre',
)

q(
    "Quelle hiérarchie Tisseyre établit-il entre lignes métropolitaines, continentales et coloniales, et au nom de quels critères ?",
    "Deux critères seulement : l'utilité économique et l'utilité politique. Les lignes purement métropolitaines ont un trafic « quasi nul » — ni lettres ni messageries — et n'ont plus qu'une « importance de propagande à l'intérieur », « payée trop cher » : les maintenir, mais les aider « au prorata des services qu'elles rendent ». Les lignes continentales ont un trafic un peu supérieur mais encore insuffisant, en revanche une importance politique « des plus grandes », de capitale à capitale. Les lignes coloniales sont les seules à remplir la double condition et « c'est celles-là qu'il faut soutenir de tous nos moyens ».",
    "lignes métropolitaines continentales coloniales trafic propagande importance politique subvention",
    "La hiérarchie est répartie sur quatre interventions (i023, i027, i028, i031) qui ne se suivent pas toutes ; la reconstruction passe par le critère commun, posé en thèse (i027) puis appliqué à chaque catégorie. Le rang de chaque catégorie se lit dans les comparatifs conservés par l'OCR.",
    [
        (23, "les lignes purement métropolitaines n'ont qu'un trafic quasi nul. Elles ne transportent pas de lettres, pas de messagerie"),
        (27, "c'est une propagande qui est payée trop cher. Ne les supprimez pas, toutefois ; aidez-les de façon différente, aidez-les au prorata des services qu'elles rendent"),
        (28, "Elles ont cependant une importance politique très sérieuse"),
        (31, "Ce sont uniquement, à mon avis, les lignes coloniales, et ce sont celles-là qu'il faut soutenir de tous nos moyens"),
    ],
    realiste='Tisseyre hiérarchie lignes métropolitaines continentales coloniales critères',
)

q(
    "La commission des finances a-t-elle supprimé les lignes aériennes coloniales ? Comment le désaccord se noue-t-il et se dénoue-t-il ?",
    "Non, et la controverse porte en réalité sur un glissement de vocabulaire. Tisseyre avait dit que la réduction imposée par la commission était « presque entièrement supportée par les lignes coloniales » ; le rapporteur Bouilloux-Lafont précise que la commission « n'a jamais indiqué qu'on devait supprimer » ces lignes et « a même dit tout le contraire » ; Tisseyre se corrige aussitôt : il n'a pas parlé de suppression, seulement de diminution. Le colonel Girod apporte la pièce technique : les crédits réduits sont ceux de « lignes d'études » — Marseille-Alger, Kayes-Bamako pour l'Afrique occidentale, Tuléar-Antsirabé pour Madagascar — et c'est au contraire sur elles que doit porter l'effort du Gouvernement, l'aviation nationale faisant « notre flotte de réserve ». Tisseyre conclut en demandant que les subventions permettent aux compagnies coloniales de réaliser le programme établi par le ministère des colonies lui-même.",
    "commission des finances lignes coloniales suppression réduction lignes d'études Marseille Alger Kayes Bamako Tuléar Antsirabé flotte de réserve",
    "Change à trois voix en six interventions (i029, i031, i032, i033, i034, i035) : la réponse exacte (non) est la seule intervention du rapporteur sur ce point (i032), la rectification de Tisseyre (i033) rétablit la formulation précise du grief, et l'incise de Girod (i034) donne la liste nominative des lignes — seule occurrence de cette géographie coloniale dans le corpus.",
    [
        (31, "la réduction qui vous a été imposée par la commission des finances est presque entièrement supportée par les lignes coloniales"),
        (32, "la commission des finances n'a jamais indiqué qu'on devait supprimer les lignes coloniales"),
        (33, "J'ai dit que je croyais que la diminution imposée par la commission des finances était presque entièrement supportée par les lignes coloniales"),
        (34, "le rapport classe comme lignes d'études : les lignes de Marseille à Alger, de Kayes à Bamako, pour l'Afrique occidentale, et de Tuléar à Antsirabé pour Madagascar"),
        (29, "c'est notre flotte de réserve, en partie tout au moins"),
    ],
    realiste='commission des finances lignes aériennes coloniales suppression désaccord',
)

q(
    "À quelle condition les subventions coloniales sont-elles aujourd'hui accordées, et pourquoi Tisseyre juge-t-il cette règle périmée ?",
    "La règle veut qu'on ne subventionne une entreprise française aux colonies qu'à la condition que le budget de la colonie fasse un effort semblable ; Eynac confirme que l'État n'a « jamais refusé » une subvention dans ce cas. Tisseyre répond qu'il ne demande pas l'aide aux colonies qui s'efforcent elles-mêmes, mais un effort de l'État pour les compagnies françaises qui viennent s'installer aux colonies, même sans subvention locale, et que la loi invoquée « a été faite avant que l'aviation soit née ». Il demande à tout le moins qu'on tienne compte des dépenses d'infrastructure des colonies, impossibles à chiffrer parce que la main-d'œuvre y coûte très bon marché. Eynac donne raison, et en donne la preuve : c'est pourquoi l'Afrique occidentale n'a pas été tenue à la participation d'un tiers, la colonie ayant eu la charge de l'infrastructure. Restait l'exception de Madagascar, rappelée par le colonel Girod, à laquelle Eynac répond que le projet n'y avait pas encore été établi.",
    "subventions colonies entreprises françaises effort semblable loi infrastructure Madagascar Afrique occidentale participation d'un tiers",
    "Cinq interventions enchaînées forment la séquence complète : la règle (i037), l'exception soulevée (i038) et la réponse ministérielle (i039), la thèse de Tisseyre (i040), l'acquiescement et sa justification pratique (i041). Aucune de ces interventions seule ne permet de répondre : la réponse est la trace d'un échange.",
    [
        (37, "nous n'avons jamais refusé une subvention d'État aux colonies qui faisaient elles-mêmes un effort sur leur propre budget"),
        (38, "Sauf à Madagascar, l'année dernière."),
        (40, "cette loi a été faite avant que l'aviation soit née. Elle n'a pas été faite pour l'aviation"),
        (40, "Tenez compte des efforts et des sacrifices faits par les colonies pour l'infrastructure"),
        (41, "nous n'avons pas exigé de l'Afrique occidentale française la participation d'un tiers, parce que la colonie avait eu la charge de l'infrastructure"),
    ],
    realiste='subventions coloniales condition accord Tisseyre règle périmée',
)

q(
    "Quel engagement du Gouvernement Flandin rappelle-t-il comme non tenu, et où le projet de loi est-il bloqué ?",
    "Flandin rappelle qu'il avait tenu l'année précédente le même langage à la tribune et que le sous-secrétaire d'État, au nom du Gouvernement, lui avait promis de déposer dans l'année « un projet de loi réglant le régime définitif des compagnies de navigation aérienne » — promesse qu'il n'a pas vue tenue. Eynac répond : « Vous savez qu'il est prêt. » Flandin convient qu'il est prêt dans ses services, mais qu'il est parti, « comme tant d'autres projets d'intérêt général », vers « une maison où partent bien des choses qui ne reviennent jamais : j'ai nommé le ministère des finances », où il a « dormi quelque trois mois d'été sous le coude gauche d'un honorable fonctionnaire » ; il souhaite que le ministre des finances s'y intéresse un jour où le banc des ministres sera plus garni.",
    "projet de loi régime définitif compagnies de navigation aérienne ministère des finances sommeil retard",
    "La séquence repose sur une promesse rapportée après coup (i052), une réplique de cinq mots du ministre (i053) et une reprise ironique (i054). Sans i053, la question « le projet était-il prêt ? » reste sans réponse ; sans i054, on ne saurait plus où le projet est retenu : l'exemple montre que l'unité de sens est ici l'échange, pas l'intervention.",
    [
        (52, "me promettre, au nom du Gouvernement, de déposer dans l'année un projet de loi réglant le régime définitif des compagnies de navigation aérienne"),
        (53, "Vous savez qu'il est prêt."),
        (54, "il est parti, comme tant d'autres projets d'intérêt général, vers une maison où partent bien des choses qui ne reviennent jamais : j'ai nommé le ministère des finances"),
        (54, "ce projet a dormi quelque trois mois d'été sous le coude gauche d'un honorable fonctionnaire du ministère des finances"),
    ],
    realiste='Flandin engagement du Gouvernement non tenu projet de loi bloqué',
)

q(
    "Quel inventaire des routes aériennes étrangères Flandin dresse-t-il pour montrer que la place est déjà prise ?",
    "Un inventaire du monde déjà occupé. États-Unis : New-York-Chicago, « la plus grande route aérienne du monde », et deux antennes, l'une par Key-West et La Havane vers les Antilles et Panama, l'autre sur le Mexique, avec une ligne de Mexico à Tampico. Japon : un mouvement visant à le relier plus tard à la Chine et à la Sibérie. Australie : trois lignes, Sydney-Geraldton-Derby, Sydney-Adelaïde, Sydney-Brisbane. Nouvelle-Zélande : deux lignes annonçant son raccordement à la future ligne des Indes. Angleterre : Le Caire-Bagdad, tronçon de sa ligne des Indes, et Londres-Amsterdam-Brême-Hambourg-Berlin, avec des prolongements allemands — Dantzig, Koenigsberg, Memel, Revel, Riga — et Koenigsberg-Moscou, exploitée « par une société russe de façade » entièrement financée par les Allemands. Allemagne : accord avec l'Espagne pour un service Europe-Afrique-Amérique du Sud raccordé au dirigeable Zeppelin de Séville sur Buenos-Aires, ligne Copenhague-Berlin-Leipzig-Munich-Constance-Genève « pour, dès qu'elle le pourra, passer par dessus la France », et Copenhague-Berlin-Prague avec prolongement vers l'Orient.",
    "routes aériennes mondiales New-York Chicago Le Caire Bagdad Koenigsberg Séville Buenos-Aires société russe de façade",
    "L'inventaire est la concaténation de deux interventions contiguës : i056 pour les continents, i057 pour l'Europe. C'est la plus longue suite de noms propres du corpus, donc le meilleur cas d'école pour la recherche lexicale ; il alimente la conclusion de Flandin trois cents segments plus loin (i102 : « toutes les routes aériennes du monde occupées »).",
    [
        (56, "Ils ont lancé New-York-Chicago, la plus grande route aérienne du monde"),
        (56, "Sur la route des Indes même, l'Angleterre a mis en exploitation Le Caire à Bagdad"),
        (57, "Dantzig, Koenigsberg, Memel, Revel, Riga. Koenigsberg, Moscou, exploité par une société russe de façade"),
        (102, "nous trouvions demain, devant nous, toutes les routes aériennes du monde occupées"),
    ],
    realiste='Flandin inventaire routes aériennes étrangères place déjà prise',
)

q(
    "Quels chiffres de dépenses aériennes comparées Flandin cite-t-il, de qui les tient-il, et quelle riposte lui est faite ?",
    "Une comparaison publiée aux États-Unis au moment de la conférence de Washington et empruntée à l'amiral Moffett : les États-Unis 32 millions de dollars d'aviation militaire et navale, plus 2 200 000 dollars de poste aérienne omis par Moffett, plus 6 500 000 dollars votés en juin pour de nouveaux avions de marine, soit en réalité 40 millions de dollars ; la Grande-Bretagne 66 424 000 dollars, non compris l'aviation des Indes, l'aviation civile et l'aviation coloniale, soit environ 72 millions de dollars par an ; la France estimée par Moffett à 44 millions de dollars, mais 32 millions seulement en appliquant le cours actuel du change. Le rapporteur objecte : « Les budgets ne sont pas les mêmes non plus ! » ; Flandin riposte que les États-Unis sont « complètement protégés de toute agression militaire possible » et l'Angleterre par un bras de mer, la brume et le brouillard, et que toutes deux dépensent plus que la France, qui a pourtant « la menace constante de l'autre côté du Rhin » — précisant aussitôt qu'il ne demande pour autant aucune augmentation de crédits, le rapporteur se déclarant même prêt à en demander une.",
    "dépenses aviation comparaison amiral Moffett conférence de Washington 40 millions de dollars 72 millions change",
    "Le corps de la réponse est dans i060, mais sa portée dépend des deux interventions qui l'encadrent (i061 l'objection, i062 la riposte géographique) et de la mise au point i063 : sans elles, le chiffre passerait pour une demande de crédits alors qu'il sert à écarter une accusation d'imprévoyance. Noter la double conversion dollars/change, seule occurrence de montants aussi précis dans le corpus.",
    [
        (60, "C'était une comparaison des sommes dépensées par les grandes puissances pour leur aéronautique et j'emprunte ces chiffres à l'amiral Moffett"),
        (60, "on peut dire que la Grande-Bretagne dépense, en réalité, 72 millions de dollars par an"),
        (60, "vous verrez que la France dépense 32 millions de dollars"),
        (61, "Les budgets ne sont pas les mêmes non plus!"),
        (62, "Elles dépensent toutes deux plus que nous pour leur aviation, et nous avons pourtant la menace constante de l'autre côté du Rhin"),
    ],
    realiste='Flandin chiffres dépenses aériennes comparées riposte',
)

q(
    "Comment, selon Flandin, l'Allemagne prépare-t-elle une armée aérienne malgré les interdictions du traité de paix ?",
    "Par trois procéd convergents. Une industrie logée hors d'Allemagne et prospère : l'ingénieur Fokker a repassé la frontière hollandaise et installé des usines en Hollande et aux États-Unis, Dornier est en Suisse et en Italie, les usines Brod en Yougo-Slavie, et la société viennoise Wiener-Flugzeug-Allgemeine-Gesellschaft — dans « cette pauvre Autriche » que secourt la Société des nations — distribue cette année 40 % de dividende. Des cadres : le Bund Deutscher Flieger, « union des aviateurs allemands », constitue des groupes de pilotes de réserve dans toute l'Allemagne, et la multiplication des écoles de vol à voile, dont Flandin doute qu'elle soit une conviction technique, dresse des pilotes qui « du jour au lendemain » et par l'intermédiaire de l'union deviendront « les cadres d'une armée aéronautique formidable ». Une base industrielle capable de basculer : trois mois suffisent pour lancer une fabrication de cellules et six mois pour des moteurs en grande série, si bien qu'une simple période de tension de six mois permettrait de reconstituer une flotte d'environ 3 000 avions.",
    "Allemagne réarmement aérien vol à voile Deutscher Flieger pilotes de réserve Fokker Dornier Wiener-Flugzeug trois mois six mois",
    "L'accusation est montée en trois temps sur quatre interventions — industrie (i069), personnel (i070), délais de fabrication (i071), synthèse (i074) — et aucune ne contient la conclusion seule : c'est l'accumulation qui fait l'argument. Deux graphies OCR instables (« Bunddeutscherflieger » collé, « Wiener-Flugzeug-Allgemeine-Gesellschaft ») testent en outre la robustesse de l'indexation.",
    [
        (69, "un dividende de 40 p. 100 à ses actionnaires cette année"),
        (70, "il se forme dans toute l'Allemagne, grâce à une société qui s'appelle le Bunddeutscherflieger (union des aviateurs allemands), des groupes de pilotes de réserve"),
        (70, "Elle multiplie, en effet, les écoles de vol à voile"),
        (71, "pour lancer une fabrication de moteurs en grande série, nous savons, en France, qu'il faut six mois, et que pour lancer une fabrication de cellules, il suffit de faire trois mois"),
        (74, "six mois après, vous vous trouverez en face d'une flotte aérienne allemande de 3 000 avions, conduite par des hommes qui auront fait leur apprentissage par le vol à voile"),
    ],
    realiste='Flandin Allemagne armée aérienne interdictions du traité de paix',
)

q(
    "Quelle contradiction du traité de paix Flandin dénonce-t-il, et qui tient-il pour responsable de l'échec de la thèse française ?",
    "D'un côté les articles 198 et suivants interdisent à l'Allemagne toute aviation militaire et navale ; de l'autre les articles 313 et suivants, en « contradiction flagrante » avec les premiers, lui permettent d'entretenir une aviation commerciale. Flandin reprend ici sa demande d'interpellation déposée en juin sur l'application des clauses aériennes de Versailles, que l'ordre du jour n'avait pas permis de discuter. Il met hors de cause les rédacteurs français : ils ont défendu « jusqu'au bout » la thèse de la suppression pure et simple du droit de construire du matériel aéronautique, mais ont dû « s'incliner devant une opposition formelle, un non catégorique » opposé par la délégation américaine et par M. Wilson. Le compromis obtenu — les neuf règles du 5 mai 1921, limites techniques des avions dits commerciaux — est jugé inutile par avance : garder une industrie aéronautique active suffit à l'Allemagne, car elle transformera le jour venu l'avion à caractéristiques limitées en avion de guerre perfectionné.",
    "traité de paix articles 198 313 contradiction flagrante aviation commerciale délégation américaine Wilson neuf règles du 5 mai 1921",
    "La réponse mobilise i072 pour la contradiction et la responsabilité, i073 pour l'existence et l'origine des règles de 1921, i074 pour leurs seuils chiffrés et leur neutralisation, i079 pour le contexte parlementaire (l'interpellation de juin). L'appariation conjointe des numéros d'articles 198 et 313 est le discriminant le plus fort du corpus : elle ne se rencontre que dans ces deux interventions.",
    [
        (72, "d'après les articles 313 et suivants — contradiction flagrante avec les premiers articles 198 et suivants — l'Allemagne peut entretenir une aviation commerciale"),
        (72, "Ils ont été obligés de s'incliner devant une opposition formelle, un non catégorique qui leur a été opposé par la délégation américaine et par M. le président Wilson"),
        (73, "les alliés se sont mis d'accord sur ce qu'on appelle les neuf règles du 5 mai 1921"),
        (74, "dont la vitesse n'excède pas 170 kilomètres à l'heure, à 2 000 mètres d'altitude, et dont la charge utile ne dépasse pas 600 kilogrammes"),
        (79, "j'avais déposé, au mois de juin dernier, une demande d'interpellation sur l'application des clauses aériennes du traité de Versailles"),
    ],
    realiste='Flandin contradiction traité de paix échec thèse française responsable',
)

q(
    "Quelle forme de limitation de l'aviation allemande Flandin oppose-t-il au contrôle technique, et quel appui étranger invoque-t-il ?",
    "Un contrôle numérique, portant sur le personnel comme sur le matériel, calqué sur la réglementation que la France applique à ses propres compagnies : « Si vous voulez mettre en service régulièrement, quotidiennement, 2 000 kilomètres de lignes allemandes, mettons que ce service représente 50 avions ; vous aurez donc 50 avions et pas un de plus. » Il signale au passage l'hypocrisie de la position française, qui impose à l'Allemagne, pour ses avions commerciaux, des caractéristiques techniques auxquelles les constructeurs français se réservent de ne pas se conformer. Sur cette thèse, assure-t-il, la France aurait « l'appui complet du gouvernement britannique ».",
    "limitation numérique contrôle technique 50 avions 2 000 kilomètres appui gouvernement britannique",
    "La thèse est distribuée en deux interventions complémentaires : i075 pose le diagnostic de la « fausse position » et l'appui britannique, i076 donne la « vraie formule » et l'exemple chiffré. C'est l'un des rares endroits du corpus où une proposition alternative tient en une seule phrase.",
    [
        (75, "Ce n'est pas un contrôle technique que vous auriez dû établir, c'est un contrôle numérique"),
        (75, "vous serez amené à dire à l'Allemagne : nous vous imposons, pour vos avions commerciaux, des caractéristiques auxquelles, pour les nôtres, nous nous réservons de ne pas nous conformer"),
        (76, "vous aurez donc 50 avions et pas un de plus. Voilà la véritable thèse"),
    ],
    realiste='Flandin limitation aviation allemande contrôle technique appui étranger',
)

q(
    "Que déduit Flandin du refus allemand d'adhérer à la convention aérienne internationale, et quelle échéance rend l'affaire urgente ?",
    "Que l'abstention est elle-même un indice. L'Allemagne, si désireuse de rentrer dans le concert européen et jusqu'à faire poser sa candidature à la Société des nations par personnes interposées, n'a « jamais fait la moindre tentative » pour adhérer à la convention aérienne de 1919 annexée au traité, parce qu'elle l'obligerait, comme toutes les puissances adhérentes, à échanger les renseignements sur l'immatriculation de ses appareils commerciaux et les licences de pilote délivrées à ses ressortissants : elle se fût donc obligée à livrer la liste de ses appareils et de ses pilotes brevetés. Le même soupçon porte sur l'International air traffic association — réunie à Copenhague puis à Amsterdam, où sont entrés l'Allemagne et tous les neutres de la guerre — présentée comme « toute une cabale » dirigée contre la convention et qui inscrit tout d'abord à son ordre du jour la discrimination des avions commerciaux et des avions militaires. L'échéance est proche : le 31 décembre de cette année, « l'Allemagne recouvre sa liberté » ; jusque-là on peut encore causer. Flandin demande donc au Gouvernement, dont il sait la décision déjà prise en sens contraire, de réviser son point de vue.",
    "Allemagne convention aérienne internationale 1919 immatriculation licences de pilote International air traffic association Copenhague Amsterdam 31 décembre",
    "Le raisonnement indiciaire se défait si l'on ne réunit pas i077 (le fait et sa lecture), i081 et i082 (l'association et son objet), i080 (l'échéance du 31 décembre) et i083 (la demande de révision) : la réponse n'est dans aucune de ces interventions prise isolément, ce qui en fait une question dont le rappel ne peut se faire qu'en plusieurs endroits à la fois.",
    [
        (77, "elle n'a jamais fait la moindre tentative pour adhérer à la convention aérienne internationale. Pourquoi cette abstention?"),
        (77, "l'Allemagne se fût obligée à communiquer la liste de tous ses appareils commerciaux et de tous ses pilotes brevetés"),
        (82, "toute une cabale en réalité dirigée contre la convention aérienne internationale"),
        (80, "le 31 décembre de cette année — on vous l'a dit — l'Allemagne recouvre sa liberté"),
        (83, "Je vous demande de reviser votre point de vue"),
    ],
    realiste='Flandin refus adhérer convention aérienne internationale échéance urgente',
)

q(
    "Quelle politique industrielle Flandin propose-t-il pour tirer l'aéronautique française de la crise ?",
    "Deux volets. Concentrer la commande et l'offre : restreindre le nombre des maisons de construction, faute de quoi la « poussière de commandes » n'en laisserait à chacune que 25, 30, 40 ou 50 avions par an, construits dans de très mauvaises conditions et mettant l'industrie en situation financière difficile ; en contrepartie des commandes de séries plus importantes, une économie sur le prix unitaire et un effort technique considérable imposé aux constructeurs. Faire ensuite participer l'État aux risques du prototype : avec le passage aux gros porteurs, le prototype passe de 400 000 ou 500 000 francs à 4 ou 5 millions — encore loin des 700 ou 800 millions d'un cuirassé — et une industrie qui les aventure seule commet une « grosse imprudence » ; la formule qu'il tient pour bonne est la « régie intéressée », un véritable contrat d'association avec l'État, calqué sur la collaboration technique déjà organisée entre le service technique de l'aéronautique et les constructeurs.",
    "crise industrie aéronautique poussière de commandes restriction du nombre d'usines prototype régie intéressée contrat d'association",
    "Le programme se déroule sur six interventions (i084 le constat de crise, i086 l'impossibilité de faire vivre l'industrie par des commandes de complaisance, i087 et i088 la concentration, i089 et i090 l'échelle des coûts et les modalités, i092 la régie intéressée). La progression se repère aux formules de proposition successives (« je vous propose un moyen terme », « Sous quelle forme l'État peut-il consentir cette participation ? »).",
    [
        (84, "Il est indéniable qu'il y a une crise dans l'industrie aéronautique"),
        (87, "consistant à restreindre le nombre des usines de construction aéronautique"),
        (87, "cette poussière de commandes mettrait en situation financière difficile l'industrie aéronautique"),
        (90, "c'est, pour une industrie, une grosse imprudence, si l'État ne participe pas aux risques de l'affaire"),
        (92, "Organisez la fabrication en régie intéressée."),
    ],
    realiste='Flandin politique industrielle aéronautique française crise',
)

q(
    "Quel parallèle historique Flandin emploie-t-il contre les détracteurs de l'aviation, et quelle autocritique nationale y joint-il ?",
    "Le parallèle des chemins de fer : « à l'origine de tous les moyens de transport, il y a eu des incrédules » qui abritaient leur incrédulité derrière la recherche du mieux ; on objectait déjà qu'on ne gagnait pas tant de temps sur la voiture ou la diligence, que « c'est beaucoup plus dangereux » et que « cela coûte beaucoup plus cher » — « les mêmes raisonnements qu'aujourd'hui », et M. Thiers les tenait déjà à cette tribune avant M. Bouilloux-Lafont. L'autocritique qui l'accompagne : la France forme dans le monde « une aristocratie, celle de l'esprit et de la pensée » et fait progresser la civilisation par ses grandes découvertes, mais « il est très rare que notre pays ait bénéficié matériellement de la mise au point et de l'exploitation de ces grandes découvertes mondiales » — « la rançon de notre génie inventif est de ne pas toujours en tirer profit » — et « combien de vastes desseins, combien d'initiatives fécondes et d'efforts passionnés ont été soudainement paralysés par notre esprit critique ! »",
    "chemins de fer incrédules Thiers mêmes raisonnements rançon de notre génie inventif esprit critique",
    "Deux interventions éloignées construisent la même figure de discours : le parallèle ferroviaire (i101), la digression sur les découvertes (i096) et la formule sur l'esprit critique (i099), reprise en conclusion (i108). Le nom de Thiers, qui désigne le rapporteur sous couvert d'histoire, est ce qui permet de lire le passage comme une réponse à Bouilloux-Lafont et non comme un cours d'histoire des transports.",
    [
        (101, "on tenait les mêmes raisonnements qu'aujourd'hui"),
        (101, "en dépit des réserves qu'avant M. Bouilloux-Lafont, M. Thiers apportait à cette tribune"),
        (96, "la rançon de notre génie inventif est de ne pas toujours en tirer profit"),
        (99, "Combien de vastes desseins, combien d'initiatives fécondes et d'efforts passionnés ont été soudainement paralysés par notre esprit critique!"),
    ],
    realiste="Flandin parallèle historique détracteurs de l'aviation autocritique nationale",
)

q(
    "Quelle est la thèse centrale de Guy de Montjou sur le budget de l'aéronautique civile, et quelle analogie navale la fonde ?",
    "Que « le budget de l'aéronautique civile est en réalité, en grande partie, un budget militaire » : les deux aviations sont « intimement liées » et ceux qui ont dit le contraire se trompent. L'analogie est avec la marine : les navires de guerre et les paquebots ont des emplois différenciés mais les mêmes caractéristiques essentielles et les mêmes qualités nautiques, et leurs ingénieurs « obéissent aux mêmes lois scientifiques ». Il en va de même pour les moteurs et pour les matériaux — métaux ultralégers, bois, toile —, le Diesel servant d'exemple, qui propulse le sous-marin et a de nombreux emplois civils. Preuve d'actualité : les escadrilles de bombardement sont constituées avec des appareils Goliath, c'est-à-dire les appareils civils de transport du moment. Conséquence institutionnelle : « le sous-secrétaire d'État de l'Aéronautique n'est pas autre chose que le fournisseur du ministre de la guerre », son service des fabrications étudiant les commandes de la guerre et de la marine et n'assurant que des réceptions pour les leur remettre.",
    "budget de l'aéronautique civile budget militaire intimement liées Goliath fournisseur du ministre de la guerre marine Diesel métaux ultralégers",
    "La thèse est posée dans i113, ses illustrations techniques dans i114 (les Goliath) et i116 (matériaux, moteurs, Diesel), sa conclusion institutionnelle dans i117 ; le cadre « voir la question dans son ensemble » est posé en i110. Deux brèves approbations d'autres orateurs (Fonck i111, Castelnau i115) attestent que la thèse est reçue dans l'Assemblée — information qu'aucune intervention de Montjou ne contient.",
    [
        (113, "Le budget de l'aéronautique civile est en réalité, en grande partie, un budget militaire"),
        (113, "Les ingénieurs qui établissent les plans des paquebots et ceux qui construisent des navires de guerre obéissent aux mêmes lois scientifiques"),
        (114, "les futures escadrilles de bombardement, celles qui comprennent les avions plus puissants, sont constituées avec des appareils Goliath"),
        (117, "Le sous-secrétaire d'État de l'aéronautique n'est pas autre chose que le fournisseur du ministre de la guerre"),
        (116, "Pour les moteurs, les relations sont encore plus étroites entre ces deux aéronautiques"),
    ],
    realiste="Montjou thèse budget de l'aéronautique civile analogie navale",
)

q(
    "À quelles conditions Montjou subordonne-t-il la subvention d'une ligne aérienne ?",
    "À trois conditions cumulatives, sous une « discrimination sévère » : la ligne doit être une cause de progrès pour la construction des appareils et servir à la mise au point du matériel de guerre ainsi qu'à la formation d'un grand nombre de mécaniciens et de pilotes ; elle doit préparer le développement commercial du pays ; elle doit enfin offrir un intérêt politique, c'est-à-dire représenter, par l'établissement et le service régulier de ports aériens comme celui de San-Stefano, un instrument d'influence politique internationale. Une ligne qui ne remplit pas ces trois conditions ne doit pas être subventionnée : « ce serait du gaspillage », notamment pour les lignes qui doublent les voies ferrées et n'abrégent guère la route quand on préfère voyager la nuit.",
    "subventions discrimination sévère mise au point du matériel de guerre développement commercial intérêt politique San-Stefano gaspillage",
    "La réponse tient dans une seule intervention (i131), dont la structure énumérative (« Il faut… il faut en outre… il faut, enfin… ») rend l'extraction fiable ; mais l'illustration du troisième critère renvoie trente segments plus haut à l'anecdote de Vienne et au port de San-Stefano (i128) : la question complète oblige donc à réunir deux interventions non contiguës.",
    [
        (131, "Pour mériter une subvention, il faut que ces lignes soient une cause de progrès pour la construction des appareils et qu'elles servent à la mise au point de notre matériel de guerre"),
        (131, "Il faut, enfin, qu'elles offrent un intérêt politique"),
        (131, "Si les lignes aériennes ne remplissent pas ces trois conditions, il ne faut pas les subventionner ; ce serait du gaspillage"),
        (128, "le port de San-Stéfano constitue une base très importante pour notre influence en Orient"),
    ],
    realiste='Montjou conditions subvention ligne aérienne',
)

q(
    "Que dénonce Montjou sous le mot d'« étatisme », et quel exemple personnel donne-t-il ?",
    "Que l'État s'est fait « la providence des lignes aériennes » sans savoir remplir ce rôle : il n'a donné que quelques terrains, de mauvaise qualité, d'où des accidents. L'exemple est pris dans sa propre circonscription, la ville de Laval : le conseil municipal a voté 200 000 francs pour acheter un terrain en vue d'une gare aérienne, à condition qu'il serve aussi aux sports — football, courses une fois l'an ; il ne manquait qu'une « toute petite somme » de l'État pour exproprier une bande d'une cinquantaine de mètres et abattre des arbres. Mais la douzième direction, c'est-à-dire l'armée, a envoyé un représentant déclarer qu'elle voulait un terrain « sur lequel seuls les militaires puissent atterrir », sans courses ni football, de peur d'abîmer la piste. Montjou qualifie cette conception d'« abracadabrante » : si chaque port aérien doit être acheté en double, un pour les civils et un pour les militaires, ce sont des « dépenses invraisemblables et tout à fait inutiles », un gaspillage qui « dure depuis la fin de la guerre » ; il réclame des terrains « pour tout le monde », avec, comme dans un port, un emplacement réservé aux hangars militaires.",
    "Laval conseil municipal 200 000 francs terrain de sports football douzième direction seuls les militaires puissent atterrir abracadabrante",
    "La démonstration court sur quatre interventions (i139 la thèse, i140 l'exemple de Laval, i141 l'opposition de la douzième direction, i142 la généralisation). L'orateur s'y désigne lui-même (« chef-lieu du département que j'ai l'honneur de représenter ») : c'est le seul endroit du corpus où l'identité géographique de l'orateur se déduit du texte, et ce qui permet de qualifier le témoignage de direct.",
    [
        (139, "le même mal se manifeste, c'est l'étatisme. L'État s'est institué la providence des lignes aériennes"),
        (140, "la ville de Laval, dis-je, a voté un crédit de 200,000 fr. pour acheter un terrain"),
        (141, "la douzième direction, c'est-à-dire l'armée, envoie un représentant"),
        (142, "S'il faut que tous nos ports aériens soient achetés en double par l'État, l'un pour les civils et l'autre pour les militaires"),
    ],
    realiste='Montjou étatisme exemple personnel',
)

q(
    "Comment se déroule la controverse sur le recrutement des chefs d'aérogare, et quelles défenses Eynac oppose-t-il à Montjou ?",
    "Montjou affirme que les aérogares créées et magnifiquement installées par l'État sont dirigées à la suite d'examens « analogues à celui des contributions directes », et que « d'anciens notaires qui n'ont pas réussi, ou d'anciens banquiers sont chefs d'aérogare dans différents coins de la France », d'où une « organisation invraisemblable ». Eynac oppose quatre défenses successives : « c'est tout à fait inexact » ; le personnel est recruté « par voie de concours », avec des places réservées aux mutilés présentés par l'autorité militaire ; les personnes visées sont en réalité des « gardiens de terrains de secours », c'est-à-dire d'aérodromes qui ne sont ni ports, ni gares, ni stations, où l'on va toucher en cas d'atterrissage forcé ; les chefs de service des aérodromes sont choisis au concours, la plupart parmi d'anciens aviateurs, les épreuves comportant une partie importante réservée à l'aéronautique. Montjou maintient, citant Dijon et Antibes et de « grandes aérogares », propose d'employer les militaires inactifs et d'anciens chefs d'escadrilles, et va jusqu'à qualifier les concours de « ridicules ». Flandin s'interpose pour rappeler que le ministre de la Guerre, qui a pourtant « trop d'officiers », refuse d'en donner à l'aéronautique ; le général de Castelnau ironise en suggérant de renvoyer chez eux ceux qui jouent au bridge.",
    "chefs d'aérogare concours anciens notaires anciens banquiers gardiens de terrains de secours mutilés présentés par l'autorité militaire bridge",
    "C'est l'échange le plus fragmenté du corpus : près de vingt interventions de quelques lignes (i143 à i164) en sept salves d'aller-retour, où chaque réplique ne se comprend que par la précédente. Une recherche par mots-clés remonte assez bien l'attaque (i143) et la première défense (i146), mais la clarification technique (i148, i150) et la concession de Montjou (i157) ne sont atteignables qu'en parcourant la séquence : cas typique où le rappel des très courtes interventions se joue.",
    [
        (143, "des examens ont eu lieu, analogues à celui des contributions directes. D'anciens notaires qui n'ont pas réussi, ou d'anciens banquiers sont chefs d'aérogare"),
        (144, "C'est tout à fait inexact."),
        (146, "Notre personnel est recruté par voie de concours et nous réservons des places aux mutilés qui sont présentés par l'autorité militaire"),
        (148, "Ils sont gardiens de terrains. De telles affirmations nécessitent une mise au point"),
        (150, "Ce sont des terrains de secours sur lesquels on va toucher en cas d'atterrissage forcé"),
        (154, "les épreuves du concours comportent une partie importante réservée à l'aéronautique"),
        (156, "le ministre de la guerre qui, par ailleurs, a trop d'officiers, refuse d'en donner à l'aéronautique"),
        (162, "S'ils jouent au bridge, il vaudrait mieux les renvoyer chez eux."),
    ],
    realiste="controverse recrutement chefs d'aérogare défenses Eynac Montjou",
)

q(
    "Que dit Montjou du fonctionnement des services de radio et de météorologie, et quelle en serait la cause ?",
    "Que ces services, « essentiels au fonctionnement des services aériens », « fonctionnent bien mal » : en règle générale, l'annonce du départ de l'aérodrome parvient au point d'arrivée « bien après l'appareil », ce qu'il atteste avoir constaté « par expérience personnelle » ; et les communications météorologiques lui paraissent souffrir d'une question de crédits — « est-ce parce qu'on a vu les choses trop en grand et que les services coûtent… », sa phrase s'arrêtant là. La même explication organisationnelle est développée plus haut : les crédits « études » reportés sur les lignes vont « précisément dans des organismes d'État, organismes déjà extrêmement gonflés, extrêmement complexes », alors que lui voudrait soutenir d'abord les bureaux d'études, les ingénieurs, les inventeurs et les initiatives privées.",
    "services de radiotélégraphie météorologie annonce du départ bien après l'appareil question de crédits organismes d'État",
    "La réponse repose sur i165, dernière intervention relevée du corpus, dont la phrase demeure inachevée dans l'export : le fragment « peut-être est-ce une question de crédits » n'a de sens que rapproché de i135, où la même explication est conduite à son terme. Cas typique où la frontière du document — ici la fin de l'export — empêche une réponse autonome sur l'intervention seule.",
    [
        (165, "Quant aux services de radios et de météorologie, ils sont essentiels au fonctionnement des services aériens. Je dois dire qu'ils fonctionnent bien mal"),
        (165, "l'annonce du départ de l'aérodrome parvient à l'arrivée bien après l'appareil"),
        (135, "ces crédits vont précisément dans des organismes d'État, organismes déjà extrêmement gonflés, extrêmement complexes"),
    ],
    realiste='Montjou services de radio météorologie fonctionnement cause',
)

q(
    "Comment Montjou défend-il le principe même des subventions contre la rigueur budgétaire du rapporteur ?",
    "Par trois registres. L'argument d'âge : l'aviation ne peut encore se passer de subventions, et « nous n'avons pas encore de compagnies de navigation ni même de chemins de fer qui exploitent leurs lignes sans subvention de l'État », alors que les chemins de fer existent depuis soixante-dix ans — « on ne peut donc pas exiger des compagnies de transports aériens qu'elles volent de leurs propres ailes après trois années d'existence ». L'argument de mobilisation : les subventions doivent faciliter la mobilisation en permettant l'installation d'usines prêtes à fabriquer très vite et en grand nombre, sans accumuler pour autant des stocks qui seraient une cause de stagnation en temps de paix et empêcheraient, en temps de guerre, de produire le type supérieur à celui de l'adversaire. L'argument de concurrence enfin : accepter « des catastrophes parmi les concurrents », loi « dure » mais « bienfaisante » sans laquelle aucun progrès n'est atteint, et commander à des prix avantageux les appareils ayant obtenu les meilleures performances constatées par le service technique pendant les concours.",
    "subventions chemins de fer soixante-dix ans leurs propres ailes mobilisation stocks concurrence catastrophes progrès",
    "Les trois registres occupent trois interventions distinctes du même discours continu (i121, i130, i138) et n'annoncent aucun transit commun : la réponse exige de les réunir. Le parallèle ferroviaire, déjà employé par Flandin (i101), y est inversé — il ne sert plus à légitimer culturellement l'aviation mais à démontrer économiquement sa dépendance à l'égard de l'État : la même analogie répond ici à une autre question.",
    [
        (121, "nous n'avons pas encore de compagnies de navigation ni même de chemins de fer qui exploitent leurs lignes sans subvention de l'État"),
        (121, "on ne peut donc pas exiger des compagnies de transports aériens qu'elles volent de leurs propres ailes après trois années d'existence"),
        (130, "Il faut que ces subventions contribuent aussi à faciliter la mobilisation"),
        (130, "N'accumulons pas, dans ce but, des stocks trop importants qui seraient pour nous une cause de stagnation"),
        (138, "il y aurait des catastrophes parmi les concurrents. Mais c'est la loi générale de la concurrence industrielle"),
    ],
    realiste='Montjou défense du principe des subventions rigueur budgétaire rapporteur',
)

q(
    "Que répond le rapporteur Bouilloux-Lafont aux orateurs qui réclament un grand effort aérien, et quel climat de séance cela révèle-t-il ?",
    "Par l'état des comptes, en une phrase : « Notre budget est en déficit de 4 milliards, ne l'oublions pas », et le rôle de rapporteur de la commission des finances « est plus ingrat que celui qui consiste à faire le très élégant et très utile discours que vous venez de prononcer ». La saillie de Guérin — « Tout le monde ne pourrait pas faire un aussi beau discours » — aussitôt rectifiée par Bouisson, qui observe sobrement que « M. le rapporteur n'a pas dit le contraire », montre une séance où l'ironie coexiste avec l'accord de fond : Montjou lui-même reconnaît que « beaucoup de critiques de M. le rapporteur sont justifiées par les faits » tout en en désapprouvant d'autres, et convient que la rigueur était « votre rôle ».",
    "déficit de 4 milliards rapporteur commission des finances rôle ingrat Guérin beau discours Bouisson",
    "Cinq interventions courtes et consécutives (i104 à i109) sont nécessaires : les deux mots d'à-propos (i105, i106) ne contiennent ni question ni réponse et ne s'éclairent que par leur voisinage immédiat. C'est un bon révélateur des limites du découpage par intervention : le sens est dans l'enchaînement, pas dans le segment.",
    [
        (104, "Notre budget est en déficit de 4 milliards, ne l'oublions pas. Aussi le rôle de rapporteur de la commission des finances est-il plus ingrat"),
        (106, "Tout le monde ne pourrait pas faire un aussi beau discours."),
        (107, "M. le rapporteur n'a pas dit le contraire."),
        (109, "beaucoup de critiques de M. le rapporteur sont justifiées par les faits ; mais il y en a un certain nombre que je ne saurais approuver"),
    ],
    realiste='Bouilloux-Lafont rapporteur grand effort aérien climat de séance',
)

q(
    "Quels incidents et quelles affaires de procédure encadrent cette séance du matin ?",
    "Une séance du matin « intime » : Tisseyre s'excuse d'y avoir « une voix insuffisante » et se plaindra plus tard de parler « à une heure aussi matinale », devant une Assemblée où « nos collègues coloniaux » brillent par leur absence. Côté procédure : lecture du procès-verbal de la 2e séance de la veille par M. Regaud, l'un des secrétaires ; deux absences excusées, M. Duval-Arnould et M. Edouard Soulier, dont le congé est accordé conformément à l'article 129 du règlement ; un décret du ministre de la marine (Raiberti) désignant cinq commissaires du Gouvernement pour assister le ministre de la marine à la Chambre des députés et au Sénat dans la discussion du projet d'ouverture et d'annulation de crédits de l'exercice 1922, parmi lesquels le contre-amiral Lanxade, chef du service central aéronautique ; deux communications du Sénat transmises par Léon Bourgeois le 27 novembre, savoir une proposition de loi tendant à rendre les femmes commerçantes éligibles aux chambres de commerce (imprimée sous le n° 5144, renvoyée à la commission du commerce et de l'industrie) et une proposition relative à la protection des enfants du premier âge et aux consultations de nourrissons (n° 5145, renvoyée à la commission de l'hygiène publique, sous réserve de l'avis de l'administration générale et des finances) ; enfin deux traits d'ironie de séance, la riposte du général de Castelnau sur les parties de bridge et le mot de Guérin.",
    "Regaud procès-verbal congé article 129 décret commissaires du Gouvernement marine Léon Bourgeois chambres de commerce consultations de nourrissons",
    "Ces faits ne se lisent que dans la frange procédurale du document (i001 à i006) et dans les épigrammes de séance (i008, i036, i162 à i164) : aucun n'est résumé de façon autonome, et la liste nominative des commissaires comme les numéros d'imprimés ne se trouvent que dans les textes longs lus à la tribune par le président. C'est l'interrogation la plus éloignée du débat de fond, donc la plus discriminante contre un système qui ne retrouverait que les grands discours.",
    [
        (1, "donne lecture du procès-verbal de la 2e séance d'hier"),
        (3, "Conformément à l'article 129 du règlement, le bureau est d'avis d'accorder ce congé"),
        (4, "Sont désignés, en qualité de commissaires du Gouvernement, pour assister le ministre de la marine"),
        (5, "une proposition de loi tendant à rendre les femmes commerçantes éligibles aux chambres de commerce"),
        (6, "relative à la protection des enfants du pre- mier âge et aux consultations de nourri- sons"),
        (8, "l'intimité de cette séance du matin me permettra de vous parler presque sur le ton de la confidence"),
        (164, "C'est donc que les parties de bridge sont un repos."),
    ],
    realiste='incidents affaires de procédure séance du matin',
)

q(
    "Sur quel point précis Flandin et Montjou se rencontrent-ils, et qu'apprend cet accord des clivages de la séance ?",
    "Sur la « dispersion des efforts » et le défaut d'organisation d'ensemble : Montjou reproche la dispersion des efforts et s'exclame « Nous sommes complètement d'accord » ; Flandin, deux interventions plus haut, avait dit : « Je suis entièrement de votre avis sur toute cette partie de votre exposé ». Le désaccord, tel que Montjou le délimite lui-même, ne porte donc ni sur le diagnostic ni sur la personne du sous-secrétaire d'État — « Il ne doit pas se croire visé par mes paroles ; c'est une question d'organisation générale » — mais sur le remède institutionnel : là où Montjou réclame un ministère de l'air à l'image de l'Angleterre, qui groupe tous les crédits, guerre, marine et colonies, la France s'en tient à un sous-secrétariat d'État ; et le mal, dit-il, est que « celui qui sera chargé d'employer les crédits… en gaspillera énormément », ministre de la guerre, des colonies, de la marine ou de l'air.",
    "dispersion des efforts « complètement d'accord » organisation d'ensemble ministère de l'air Angleterre gaspillage des crédits",
    "L'accord ne s'établit qu'en croisant i157 (l'assertion de convergence), i158 (l'approbation de Flandin) et i159 (la restriction « sans viser le sous-secrétaire »), puis en les rapportant à i132 et i134, où Montjou nomme la cause et le modèle anglais. Sans ce recoupement, la réponse resterait une affirmation sans contenu vérifiable.",
    [
        (157, "je reproche la dispersion des efforts. Nous sommes complètement d'accord"),
        (158, "Je suis entièrement de votre avis sur toute cette partie de votre exposé"),
        (159, "Il ne doit pas se croire visé par mes paroles ; c'est une question d'organisation générale"),
        (132, "le mal dont souffre l'aviation a une cause plus élevée, plus générale : le défaut d'organisation d'ensemble"),
        (134, "L'Angleterre a institué un ministère de l'air, groupe tous les crédits, aussi bien ceux de la guerre et de la marine que des colonies"),
    ],
    realiste='Flandin Montjou point de rencontre accord clivages de la séance',
)

RESUME_GLOBAL = (
    "Un seul jour, un seul objet, un seul ministère : la 2e séance du 28 novembre 1922 reprend la 3e section "
    "du ministère des Travaux publics, Aéronautique et transports aériens, au budget général de l'exercice "
    "1923, et livre 165 interventions, relevées sous seize graphies d'orateur qui n'en couvrent "
    "qu'une douzaine de personnes réellement entendues. Une brève frange procédurale l'ouvre — procès-verbal lu par Regaud, deux congés accordés, un "
    "décret désignant des commissaires du gouvernement auprès du ministre de la marine, deux propositions de "
    "loi venues du Sénat, l'une pour rendre les femmes commerçantes éligibles aux chambres de commerce, "
    "l'autre pour la protection des enfants du premier âge — puis le débat se partage en trois discours que "
    "rien ne sépare. M. Tisseyre ouvre le feu sous couvert d'une « collaboration amicale » au sous-secrétaire "
    "d'État : il plaide l'aviation commerciale contre son propre rapporteur en distinguant les accidents de la "
    "formation et de la vitesse de ceux du transport public, énumère sept mesures de sécurité (double poste de "
    "pilotage, vérification des moteurs hors des compagnies, terrains d'atterrissage maintenus, postes de "
    "météorologie, T. S. F. et extincteurs, écoles de pilotage payées par les constructeurs) et classe les "
    "lignes selon le double critère économique et politique, ce qui désigne les lignes coloniales comme seules "
    "méritant l'effort — d'où un vif échange avec le colonel Girod et le rapporteur Bouilloux-Lafont sur les "
    "« lignes d'études » de Marseille à Alger, Kayes à Bamako et Tuléar à Antsirabé, puis un débat de droit sur "
    "la vieille loi exigeant des colonies un effort budgétaire semblable. M. Pierre-Etienne Flandin déplace "
    "alors le débat sur le terrain de la puissance : il redemande le projet de loi sur le régime définitif des "
    "compagnies, promis l'année d'avant et endormi au ministère des finances, dresse l'inventaire des routes "
    "déjà occupées par les États-Unis, l'Angleterre, le Japon, l'Australie et l'Allemagne, chiffre les "
    "efforts étrangers d'après l'amiral Moffett (États-Unis 40 millions de dollars, Grande-Bretagne 72, France "
    "32 au change actuel), puis développe une longue diatribe sur les clauses aériennes du traité de "
    "Versailles : contradiction des articles 198 et 313, écoles de vol à voile et Deutscher Flieger dressant "
    "des pilotes de réserve, industries allemandes abritées à Vienne, en Suisse ou aux États-Unis jusqu'à 40 % "
    "de dividende, refus d'adhérer à la convention aérienne internationale pour soustraire appareils et "
    "brevets ; d'où l'exigence d'une limitation numérique — cinquante avions pour deux mille kilomètres de "
    "lignes — et l'avertissement qu'au 31 décembre l'Allemagne « recouvre sa liberté ». Il finit en politique "
    "industrielle : moins d'usines et des commandes en séries, participation de l'État aux risques du "
    "prototype jusqu'à la « régie intéressée », et, le parallèle des chemins de fer à l'appui, la "
    "« rançon de notre génie inventif ». M. Guy de Montjou prend le troisième la parole pour une thèse "
    "d'ensemble : « le budget de l'aéronautique civile est en réalité, en grande partie, un budget militaire », "
    "le sous-secrétaire d'État n'étant « que le fournisseur du ministre de la guerre » ; il veut une "
    "discrimination sévère des subventions selon trois fins — mise au point du matériel de guerre, "
    "développement commercial, intérêt politique —, illustre l'étatisme par le terrain de Laval, jugé insuffisant "
    "par la douzième direction parce que les civils auraient pu y jouer au football, et s'embarque avec Eynac "
    "dans une querelle de dix-huit interventions sur les chefs d'aérogare, « anciens notaires qui n'ont pas "
    "réussi » selon lui, concours et mutilés selon le ministre, épisode où il traitera le concours de "
    "« ridicule » et où le général de Castelnau ira jusqu'à proposer de renvoyer chez eux les militaires qui "
    "jouent au bridge. L'ensemble dessine moins un combat partisan qu'un consensus d'intérêt national fracassé "
    "sur l'organisation : tous veulent sauver l'aviation, mais le rapporteur oppose un budget « en déficit de "
    "4 milliards », l'armée revendique des terrains d'usage exclusif, et la déroute des services de radio et "
    "de météorologie, déjà dénoncée par Tisseyre, tombe ici comme un aveu."
)

# --- criture ---------------------------------------------------------------

questions = []
for n, (intitule, reponse, requete, methode, sources, realiste) in enumerate(Q, 1):
    questions.append(
        {
            "id": f"Q{n:02d}",
            "intitule": intitule,
            "requete": realiste,
            "requete_oracle": requete,
            "reponse_attendue": reponse,
            "generation": {
                "methode": methode,
                "interventions": [citation(i, x) for i, x in sources],
            },
        }
    )

doc = {
    "corpus": {
        "fichier_brut": str(BRUT),
        "fichier_canonique": str(CANONIQUE),
        "assemblée_observée": "Chambre des députés",
        "date_seance": "1922-11-28",
        "seance": "2",
        "objet": "Budget général de l'exercice 1923 — 3e section du ministère des Travaux publics (Aéronautique et transports aériens)",
        "interventions": len(brut),
        "graphies_orateurs": len({e["orateur"] for e in brut}),
        "resume_global": RESUME_GLOBAL,
        "observation_de_metadonnees": (
            "Le fichier canonique porte chambre='senat', mais le texte dit la Chambre : « Dans la 2e séance "
            "d'hier la Chambre a commencé la discussion » (i007), « Acte est donné de la communication dont la "
            "Chambre vient d'entendre la lecture » (i004), et les messages de Léon Bourgeois, président du "
            "Sénat, prient le président de « vouloir bien saisir la Chambre des députés » (i005, i006). Il "
            "faudrait probablement reconvertir l'export avec --chambre chambre."
        ),
    },
    "mode_de_generation": (
        "Lecture intégrale des 165 interventions (texte OCR et résumés méta-donnés), puis découpage du débat en "
        "unités de sens : procédure d'ouverture, sécurité et exploitation, répartition des subventions, aviation "
        "coloniale, clauses aériennes du traité de Versailles, politique industrielle, organisation et "
        "personnel, climat de séance. Pour chaque unité, forme d'une question telle qu'un historien la poserait "
        "au corpus, d'une réponse établie sur les seules interventions sources, et d'une citation verbatim par "
        "intervention. Les citations sont ancrées automatiquement dans le champ `contenu` (accents, apostrophes "
        "et césures OCR tolérés à la recherche, graphie source restituée) : une question n'est retenue que si "
        "chaque élément de sa réponse est ainsi témoigné."
    ),
    "usage": (
        "Vérité terrain pour l'étape 6 du pipeline (recall@k, MRR). Les `id` repris dans "
        "`generation.interventions` sont utilisables tels quels comme champs `attendus` du format "
        "data/questions/QUERIES.md ; le champ `requete` est la formulation réaliste, dérivée de "
        "l'intitulé seul ; `requete_oracle` reprend les mots-clés extraits de la réponse et sert "
        "de plafond de comparaison : l'écart entre les deux mesures le gap lexical du système."
    ),
    "questions": questions,
}

if ERREURS:
    for ident, extrait, contenu in ERREURS:
        print(f"\n### {ident}\n  voulu : {extrait}\n  texte : {contenu[:600]}")
    raise SystemExit(f"\n{len(ERREURS)} citation(s) non ancrée(s) — fichier non écrit.")

SORTIE.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"{len(questions)} questions, {sum(len(x['generation']['interventions']) for x in questions)} citations ancrées")
for x in questions:
    print(f"\n{x['id']} {x['intitule'][:70]}")
    for i in x["generation"]["interventions"]:
        print(f"   {i['id']} f{i['folio_du_jo']} : {i['citation'][:88]}")
