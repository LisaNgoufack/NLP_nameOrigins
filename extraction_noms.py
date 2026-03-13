"""
NLP-nameOrigins | Étape 6 : Extraction des noms de famille dans les textes
===========================================================================
Objectif :
    Extraire automatiquement toutes les variantes de noms de famille
    cachées dans les textes d'origine, en combinant :

    Méthode 1 : Majuscules + contexte (rapide, sans API)
    Méthode 2 : Validation par Mistral (précis, avec API)

Exemple :
    Texte : "latinisé en Durandus, variante Duran, voir Durant"
    → Extrait : ["Durandus", "Duran", "Durant"]

Entrées :
    data/origins.json          → textes d'origine
    data/names.json            → noms déjà connus
    output/full_database.json  → base complète

Sortie :
    output/nouveaux_noms.json  → nouveaux noms extraits
    output/evaluation.json     → comparaison méthode 1 vs méthode 2
"""

import json
import re
import os
import time
from dotenv import load_dotenv
from openai import OpenAI


# ── 1. Chargement des données ─────────────────────────────────────────────────

print(" Chargement des données...")

with open("data/origins.json", "r", encoding="utf-8") as f:
    origins = json.load(f)

with open("data/names.json", "r", encoding="utf-8") as f:
    names_data = json.load(f)

with open("output/full_database.json", "r", encoding="utf-8") as f:
    full_db = json.load(f)

# Ensemble de tous les noms déjà connus
noms_connus = {n["name"].lower() for n in names_data}
noms_connus.update({n["nom"].lower() for n in full_db})

print(f" {len(origins)} textes d'origine chargés")
print(f" {len(noms_connus)} noms déjà connus dans la base")


# ── 2. Liste des mots français courants à ignorer ────────────────────────────

# Ces mots apparaissent souvent avec une majuscule mais ne sont PAS des noms
# de famille : régions, pays, mois, mots historiques, etc.
MOTS_A_IGNORER = {
    # Régions françaises
    "france", "bretagne", "normandie", "alsace", "lorraine", "provence",
    "occitanie", "gascogne", "picardie", "bourgogne", "auvergne", "savoie",
    "languedoc", "anjou", "maine", "touraine", "poitou", "berry", "limousin",
    "paris", "lyon", "marseille", "bordeaux", "toulouse", "nantes", "strasbourg",
    "rennes", "brest", "rouen", "grenoble", "montpellier", "dijon", "reims",

    # Régions et villes étrangères
    "italie", "espagne", "allemagne", "angleterre", "belgique", "portugal",
    "europe", "sicile", "lombardie", "catalogne", "aragon", "lazio", "corse",
    "haguenau", "baviere", "prusse", "autriche", "suisse", "hollande",
    "pologne", "russie", "hongrie", "irlande", "ecosse", "galice",

    # Départements et zones géographiques
    "nord", "sud", "est", "ouest", "centre", "haut-rhin", "bas-rhin",
    "haute-loire", "puy-de-dome", "cote-d", "haute-savoie", "haute-garonne",
    "seine", "loire", "rhone", "garonne", "dordogne", "charente", "vendee",

    # Siècles et périodes
    "moyen", "age", "antiquite", "renaissance", "revolution",
    "xive", "xve", "xvie", "xviie", "xviiie", "xixe", "xxe",
    "xii", "xiii", "xiv", "xvi", "xvii", "xviii", "xix",

    # Mots religieux
    "saint", "sainte", "dieu", "eglise", "christ", "marie", "joseph",
    "paul", "pierre", "jean", "jacques", "simon", "andre", "luc", "marc",

    # Langues et origines linguistiques
    "latin", "grec", "germanique", "gaulois", "celtique", "hebreu",
    "arabe", "basque", "breton", "occitan", "catalan", "flamand",
    "francique", "francais", "provencal", "gascon", "picard", "normand",

    # Auteurs et références bibliographiques
    "morlet", "bahlow", "dauzat", "nègre", "niobey", "vincent",
    "chapuy", "rostaing", "gendron", "richard",

    # Mots grammaticaux avec majuscule en début de phrase
    "le", "la", "les", "un", "une", "des", "du", "de", "ce", "cet",
    "cette", "il", "elle", "ils", "elles", "on", "nous", "vous",
    "also", "voir", "chez", "avec", "sans", "dans", "pour", "par",

    # Mots du texte étymologique (pas des noms de famille)
    "forme", "formes", "variante", "variantes", "diminutif", "diminutifs",
    "derive", "derives", "nom", "patronyme", "prenom", "surnom", "sobriquet",
    "toponyme", "etymologie", "origine", "sens", "signification",
    "egalement", "ecrit", "orthographie", "aussi", "autre", "autres",
    "plusieurs", "souvent", "parfois", "surtout", "notamment", "environ",
    "porte", "porté", "trouve", "rencontre", "designe", "signifie",
    "pourrait", "pourrait", "semble", "agit", "etre", "avoir",
    "fait", "vient", "venir", "prendre", "donner", "former",
}


# ── 3. MÉTHODE 1 : Extraction par majuscules + contexte ──────────────────────

# Mots-clés qui précèdent souvent un nom de famille dans les textes
CONTEXTES = [
    r'[Vv]ariantes?\s+(?:de\s+)?:?\s*([A-ZÀ-Ÿ][a-zà-ÿA-ZÀ-Ÿ\-]+)',
    r'[Ff]ormes?\s+(?:voisines?|dérivées?|latinisées?)?\s*:?\s*([A-ZÀ-Ÿ][a-zà-ÿA-ZÀ-Ÿ\-]+)',
    r'[Vv]oir\s+([A-ZÀ-Ÿ][a-zà-ÿA-ZÀ-Ÿ\-]+)',
    r'[Ll]atinisé\s+en\s+([A-ZÀ-Ÿ][a-zà-ÿA-ZÀ-Ÿ\-]+)',
    r'[Dd]érivé\s+de\s+([A-ZÀ-Ÿ][a-zà-ÿA-ZÀ-Ÿ\-]+)',
    r'[Aa]ussi\s+(?:écrit|orthographié)\s+([A-ZÀ-Ÿ][a-zà-ÿA-ZÀ-Ÿ\-]+)',
    r'[Éé]galement\s+(?:écrit|orthographié)\s+([A-ZÀ-Ÿ][a-zà-ÿA-ZÀ-Ÿ\-]+)',
    r'[Dd]iminutifs?\s*:?\s*([A-ZÀ-Ÿ][a-zà-ÿA-ZÀ-Ÿ\-]+)',
    r'[Aa]utre\s+forme\s*:?\s*([A-ZÀ-Ÿ][a-zà-ÿA-ZÀ-Ÿ\-]+)',
    r'[Ss]ous\s+la\s+forme\s+([A-ZÀ-Ÿ][a-zà-ÿA-ZÀ-Ÿ\-]+)',
    r'(?:nom|patronyme)\s+([A-ZÀ-Ÿ][a-zà-ÿA-ZÀ-Ÿ\-]+)\s+(?:est|se)',
]


def extraire_methode1(texte: str) -> set:
    """
    Méthode 1 : Extraction par majuscules + contexte linguistique.

    Stratégie :
    1. Chercher les mots après des mots-clés contextuels
    2. Chercher tous les mots avec majuscule
    3. Filtrer les mots à ignorer

    Args:
        texte : texte d'origine d'un nom

    Returns:
        Ensemble des noms candidats trouvés
    """
    candidats = set()

    # Étape A : extraction par contexte (très fiable)
    for pattern in CONTEXTES:
        for match in re.finditer(pattern, texte):
            # Peut être une liste séparée par virgules
            partie = match.group(1)
            for mot in re.split(r'[,;\s]+', partie):
                mot = mot.strip('()[].,;:')
                if len(mot) > 2:
                    candidats.add(mot)

    # Étape B : tous les mots avec majuscule NON en début de phrase
    # (on cherche les majuscules au milieu du texte)
    mots_majuscules = re.findall(
        r'(?<=[a-zà-ÿ,;:\s])\b([A-ZÀ-Ÿ][a-zà-ÿA-ZÀ-Ÿ\-]{2,})\b',
        texte
    )
    for mot in mots_majuscules:
        candidats.add(mot)

    # Étape C : filtrage
    candidats_filtres = set()
    for c in candidats:
        c_lower = c.lower()
        # Ignorer les mots de la liste noire
        if c_lower in MOTS_A_IGNORER:
            continue
        # Ignorer les mots trop courts
        if len(c) <= 2:
            continue
        # Ignorer les mots trop longs (probablement pas un nom)
        if len(c) > 25:
            continue
        # Ignorer les mots qui contiennent des chiffres
        if any(ch.isdigit() for ch in c):
            continue
        candidats_filtres.add(c)

    return candidats_filtres


# ── 4. MÉTHODE 2 : Validation par Mistral ────────────────────────────────────

load_dotenv()
api_key = os.getenv("MISTRAL_API_KEY")
use_llm = bool(api_key)

if use_llm:
    client = OpenAI(api_key=api_key, base_url="https://api.mistral.ai/v1")
    print(" API Mistral activée pour la validation")
else:
    print("  MISTRAL_API_KEY non définie → méthode 1 uniquement")


def extraire_methode2(texte: str, nom_principal: str) -> list:
    """
    Méthode 2 : Extraction directe par Mistral.
    Demande à Mistral d'identifier tous les noms de famille dans le texte.

    Args:
        texte          : texte d'origine
        nom_principal  : nom de famille principal du texte

    Returns:
        Liste des noms de famille trouvés par Mistral
    """
    prompt = (
        f"Dans ce texte etymologique sur le nom de famille {nom_principal}, "
        "identifie TOUS les noms de famille, variantes orthographiques "
        "et formes latines mentionnes. "
        f"Texte : {texte} "
        "Reponds UNIQUEMENT avec une liste JSON de noms, sans explication. "
        'Exemple : ["Durand", "Durant", "Durandus", "Duran"] '
        "N inclus PAS les noms de regions, pays, prenoms de saints, ou mots communs."
    )

    try:
        response = client.chat.completions.create(
            model="mistral-large-latest",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.1,
        )
        contenu = response.choices[0].message.content.strip()
        contenu = contenu.replace("```json", "").replace("```", "").strip()
        noms = json.loads(contenu)
        return [n for n in noms if isinstance(n, str)]
    except Exception:
        return []


def valider_par_mistral(candidats: list, texte: str) -> list:
    """
    Méthode combinée : Mistral valide les candidats de la Méthode 1.
    Prend la liste brute de la Méthode 1 et demande à Mistral
    lesquels sont vraiment des noms de famille.

    Args:
        candidats : liste de candidats trouvés par Méthode 1
        texte     : texte d'origine pour le contexte

    Returns:
        Liste des candidats confirmés comme noms de famille
    """
    if not candidats:
        return []

    prompt = (
        "Parmi ces mots extraits d'un texte etymologique, "
        "lesquels sont des noms de famille ou formes latines d'un nom de famille ? "
        f"Mots candidats : {candidats} "
        f"Contexte (texte) : {texte[:300]} "
        "Reponds UNIQUEMENT avec une liste JSON des noms confirmes. "
        'Exemple : ["Bideaud", "Bideault"] '
        "Exclure : regions, pays, verbes, adjectifs, mots communs, siecles."
    )

    try:
        response = client.chat.completions.create(
            model="mistral-large-latest",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.1,
        )
        contenu = response.choices[0].message.content.strip()
        contenu = contenu.replace("```json", "").replace("```", "").strip()
        noms = json.loads(contenu)
        return [n for n in noms if isinstance(n, str)]
    except Exception:
        return []


# ── 5. Application sur tous les textes ───────────────────────────────────────

print("\n Extraction des noms par Méthode 1 (majuscules + contexte)...")

resultats_m1 = {}   # origin_id → {noms trouvés}
nouveaux_m1  = 0

for oid, texte in origins.items():
    if not texte.strip():
        continue

    noms_trouves = extraire_methode1(texte)

    # Garder uniquement les noms NON connus dans la base
    nouveaux = {n for n in noms_trouves if n.lower() not in noms_connus}

    if nouveaux:
        resultats_m1[oid] = {
            "texte":    texte[:150],
            "trouves":  list(noms_trouves),
            "nouveaux": list(nouveaux),
        }
        nouveaux_m1 += len(nouveaux)

print(f" Méthode 1 terminée :")
print(f"   {len(resultats_m1)} textes avec nouveaux noms")
print(f"   {nouveaux_m1} nouveaux noms potentiels")

# Afficher quelques exemples
print(f"\n Exemples Méthode 1 :")
for oid, data in list(resultats_m1.items())[:5]:
    print(f"\n   Texte   : {data['texte'][:100]}...")
    print(f"   Trouvés : {data['trouves']}")
    print(f"   Nouveaux: {data['nouveaux']}")


# ── 6. Validation par Mistral sur un échantillon ──────────────────────────────

resultats_m2     = {}
comparaison      = []

if use_llm:
    # Prendre les 200 premiers textes pour comparer les deux méthodes
    echantillon = list(resultats_m1.items())[:200]
    print(f"\n Validation Mistral sur {len(echantillon)} textes...")

    for i, (oid, data) in enumerate(echantillon):
        if (i + 1) % 20 == 0:
            print(f"   {i+1}/{len(echantillon)} validés...")

        texte = origins[oid]
        # Trouver le nom principal associé à cet origin_id
        nom_principal = next(
            (n["name"] for n in names_data if oid in n["origins"]),
            "inconnu"
        )

        # Méthode 2 : Mistral extraction directe
        noms_m2 = extraire_methode2(texte, nom_principal)

        # Méthode combinée : Mistral valide les candidats de Méthode 1
        noms_combines = valider_par_mistral(data["trouves"], texte)

        resultats_m2[oid] = noms_m2

        # Comparer les trois méthodes
        noms_m1_set  = set(n.lower() for n in data["trouves"])
        noms_m2_set  = set(n.lower() for n in noms_m2)
        noms_comb_set = set(n.lower() for n in noms_combines)

        comparaison.append({
            "origin_id":      oid,
            "nom_principal":  nom_principal,
            "methode1":       list(data["trouves"]),
            "methode2":       noms_m2,
            "combinee":       noms_combines,
            "seulement_m1":   list(noms_m1_set - noms_m2_set),
            "seulement_m2":   list(noms_m2_set - noms_m1_set),
            "communs":        list(noms_m1_set & noms_m2_set),
            "communs_comb":   list(noms_comb_set & noms_m2_set),
        })

        time.sleep(0.3)

    # Statistiques de comparaison
    total_m1   = sum(len(c["methode1"])  for c in comparaison)
    total_m2   = sum(len(c["methode2"])  for c in comparaison)
    total_comb = sum(len(c["combinee"])  for c in comparaison)
    communs    = sum(len(c["communs"])   for c in comparaison)
    seul_m1    = sum(len(c["seulement_m1"]) for c in comparaison)
    seul_m2    = sum(len(c["seulement_m2"]) for c in comparaison)
    communs_comb = sum(len(c["communs_comb"]) for c in comparaison)

    print(f"\n Comparaison des 3 méthodes (référence = Mistral) :")
    print(f"   {'Méthode':<30} {'Total':>7} {'Précision':>10} {'Rappel':>8} {'F1':>8}")
    print(f"   {'-'*63}")

    # Méthode 1
    p1 = communs / total_m1 if total_m1 > 0 else 0
    r1 = communs / total_m2 if total_m2 > 0 else 0
    f1_1 = 2*p1*r1/(p1+r1) if (p1+r1) > 0 else 0
    print(f"   {'Méthode 1 (regex+majuscules)':<30} {total_m1:>7} {p1*100:>9.1f}% {r1*100:>7.1f}% {f1_1*100:>7.1f}%")

    # Méthode combinée (M1 + validation Mistral)
    p_c = communs_comb / total_comb if total_comb > 0 else 0
    r_c = communs_comb / total_m2   if total_m2   > 0 else 0
    f1_c = 2*p_c*r_c/(p_c+r_c) if (p_c+r_c) > 0 else 0
    print(f"   {'Méthode combinée (M1+Mistral)':<30} {total_comb:>7} {p_c*100:>9.1f}% {r_c*100:>7.1f}% {f1_c*100:>7.1f}%")

    # Méthode 2 seule (référence)
    print(f"   {'Méthode 2 (Mistral seul)':<30} {total_m2:>7} {'100.0':>9}% {'100.0':>7}% {'100.0':>7}%")

    print(f"\n La méthode combinée améliore la précision de {(p_c-p1)*100:.1f} points")
    print(f"   en éliminant les faux positifs de la Méthode 1")

    # Sauvegarder la comparaison
    with open("output/evaluation.json", "w", encoding="utf-8") as f:
        json.dump(comparaison, f, ensure_ascii=False, indent=2)
    print(f"\n Évaluation sauvegardée : output/evaluation.json")


# ── 7. Sauvegarde des nouveaux noms trouvés ───────────────────────────────────

nouveaux_noms = []
for oid, data in resultats_m1.items():
    for nom in data["nouveaux"]:
        nouveaux_noms.append({
            "nom":       nom.lower(),
            "origin_id": oid,
            "texte":     data["texte"],
            "methode":   "majuscules_contexte",
        })

with open("output/nouveaux_noms.json", "w", encoding="utf-8") as f:
    json.dump(nouveaux_noms, f, ensure_ascii=False, indent=2)

print(f"\n Nouveaux noms sauvegardés : output/nouveaux_noms.json")
print(f"   ({len(nouveaux_noms)} nouveaux noms trouvés)")