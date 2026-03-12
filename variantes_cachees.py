"""
NLP-nameOrigins | Étape 1bis : Extraction des variantes cachées
================================================================
Objectif :
    Parcourir tous les textes d'origine et extraire les noms de famille
    mentionnés dans les textes mais ABSENTS de names.json.
    Ces noms sont des variantes "cachées" qui enrichissent la base.

Exemple :
    Le texte de O1 dit : "Formes voisines : Bideaud, Bideault, Bideaut"
    → Ces 3 noms ne sont pas dans names.json mais existent bien !
    → On les ajoute à la base avec leur origine associée.

Entrées :
    data/names.json          → noms existants
    data/origins.json        → textes d'origine
    output/clusters.json     → clusters de l'étape 1

Sortie :
    output/enriched_database.json → base enrichie avec les variantes cachées
"""

import json
import re
from collections import defaultdict


# ── 1. Chargement des données ─────────────────────────────────────────────────

with open("data/names.json", "r", encoding="utf-8") as f:
    names_data = json.load(f)

with open("data/origins.json", "r", encoding="utf-8") as f:
    origins_data = json.load(f)

with open("output/clusters.json", "r", encoding="utf-8") as f:
    clusters = json.load(f)

# Ensemble des noms déjà connus dans la base
names_set = {n["name"].lower() for n in names_data}

# Dictionnaire nom → origin_ids pour retrouver l'origine d'un nom
name_to_origins = {n["name"]: n["origins"] for n in names_data}

print(f" Chargement : {len(names_data)} noms, {len(origins_data)} origines")
print(f" {len(clusters)} clusters chargés")


# ── 2. Patterns de recherche des variantes dans les textes ───────────────────

# Ces patterns détectent les mentions de variantes dans les textes d'origine
# Ex: "Variantes : Bideaud, Bideault" → on extrait Bideaud et Bideault
PATTERNS = [
    r'[Vv]ariantes?\s*:\s*([^.;]+)',           # Variantes : X, Y, Z
    r'[Ff]ormes?\s*voisines?\s*:\s*([^.;]+)',  # Formes voisines : X, Y
    r'[Ff]ormes?\s*:\s*([^.;]+)',              # Formes : X, Y
    r'[Dd]iminutifs?\s*:\s*([^.;]+)',          # Diminutifs : X, Y
    r'[Aa]ussi\s+(?:écrit|orthographié)\s+([A-ZÀ-Ÿa-zà-ÿ\-]+)',  # Aussi écrit X
    r'[Éé]galement\s+(?:écrit|orthographié)\s+([A-ZÀ-Ÿa-zà-ÿ\-]+)',  # Également écrit X
]


def extraire_noms_du_texte(text: str) -> list[str]:
    """
    Extrait tous les noms mentionnés dans un texte d'origine.

    Args:
        text : texte d'origine d'un nom de famille

    Returns:
        Liste de noms extraits et nettoyés
    """
    noms_trouves = []

    for pattern in PATTERNS:
        for match in re.finditer(pattern, text):
            # La liste peut contenir plusieurs noms séparés par virgules
            partie = match.group(1)
            candidats = re.split(r'[,;]', partie)

            for candidat in candidats:
                # Nettoyer le candidat
                nom = re.sub(r'\s*\(.*?\)', '', candidat)  # enlever les parenthèses
                nom = re.sub(r'\s+', ' ', nom).strip()     # normaliser les espaces
                nom = nom.lower()
                nom = re.sub(r'[^a-zà-ÿ\-]', '', nom)     # garder lettres et tirets

                # Filtrer les noms trop courts ou trop longs
                if 2 < len(nom) < 30:
                    noms_trouves.append(nom)

    return noms_trouves


# ── 3. Recherche des variantes cachées ───────────────────────────────────────

print("\n Recherche des variantes cachées dans les textes...")

# Pour chaque origin_id, extraire les noms mentionnés mais absents de la base
variantes_cachees = []   # liste de {'nom': str, 'origin_id': str, 'texte': str}
origin_to_names_found = defaultdict(list)

for oid, text in origins_data.items():
    noms = extraire_noms_du_texte(text)
    for nom in noms:
        if nom not in names_set:
            # Ce nom est mentionné dans un texte mais absent de names.json !
            variantes_cachees.append({
                "nom":       nom,
                "origin_id": oid,
                "texte":     text[:200],   # extrait du texte pour vérification
            })
            origin_to_names_found[oid].append(nom)

print(f" {len(variantes_cachees)} variantes cachées trouvées")
print(f"   dans {len(origin_to_names_found)} textes d'origine différents")

# Afficher les 10 premières
print("\n Exemples de variantes cachées :")
for v in variantes_cachees[:10]:
    print(f"   '{v['nom']}' trouvé dans {v['origin_id']}: {v['texte'][:100]}...")


# ── 4. Enrichissement de la base ─────────────────────────────────────────────

print("\n Enrichissement de la base de données...")

# Construire un dictionnaire nom → cluster pour retrouver facilement un cluster
name_to_cluster_idx = {}
for i, cluster in enumerate(clusters):
    for variant in cluster["variants"]:
        name_to_cluster_idx[variant] = i

# Ajouter les variantes cachées aux clusters existants
nouveaux_noms   = 0
noms_dupliques  = 0

for variante in variantes_cachees:
    nom       = variante["nom"]
    origin_id = variante["origin_id"]

    # Vérifier si ce nom n'a pas déjà été ajouté dans cette passe
    if nom in names_set:
        noms_dupliques += 1
        continue

    # Trouver le cluster qui contient cet origin_id
    cluster_cible = None
    for cluster in clusters:
        if origin_id in cluster["origin_ids"]:
            cluster_cible = cluster
            break

    if cluster_cible:
        # Ajouter le nouveau nom au cluster existant
        if nom not in cluster_cible["variants"]:
            cluster_cible["variants"].append(nom)
            cluster_cible["variants"].sort()
            # Mettre à jour le représentant (nom canonique)
            cluster_cible["representative"] = min(cluster_cible["variants"])
    else:
        # Créer un nouveau cluster pour ce nom
        clusters.append({
            "representative": nom,
            "variants":       [nom],
            "origin_ids":     [origin_id],
            "origin_texts":   {origin_id: origins_data.get(origin_id, "")},
        })

    # Marquer ce nom comme connu pour éviter les doublons
    names_set.add(nom)
    nouveaux_noms += 1

print(f" {nouveaux_noms} nouveaux noms ajoutés à la base")
print(f"   {noms_dupliques} doublons ignorés")


# ── 5. Statistiques finales ───────────────────────────────────────────────────

total_noms    = sum(len(c["variants"]) for c in clusters)
total_groupes = sum(1 for c in clusters if len(c["variants"]) > 1)

print(f"\n Base enrichie :")
print(f"   Noms total (avant) : {len(names_data)}")
print(f"   Noms total (après) : {total_noms}")
print(f"   Nouveaux noms      : {total_noms - len(names_data)}")
print(f"   Groupes variantes  : {total_groupes}")


# ── 6. Sauvegarde ─────────────────────────────────────────────────────────────

# Trier par nom représentatif
clusters.sort(key=lambda x: x["representative"])

with open("output/enriched_database.json", "w", encoding="utf-8") as f:
    json.dump(clusters, f, ensure_ascii=False, indent=2)

print(f"\n Base enrichie sauvegardée : output/enriched_database.json")


# ── 7. Export de la liste des variantes cachées ───────────────────────────────

with open("output/variantes_cachees.json", "w", encoding="utf-8") as f:
    json.dump(variantes_cachees, f, ensure_ascii=False, indent=2)

print(f" Liste des variantes cachées : output/variantes_cachees.json")