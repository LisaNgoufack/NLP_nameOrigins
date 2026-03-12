"""
NLP-nameOrigins | Étape 4 : Intégration des données INSEE
==========================================================
Objectif :
    Intégrer les 218 982 noms de famille de la base INSEE
    et les croiser avec notre base Geneanet pour enrichir
    chaque nom avec :
    - Sa fréquence totale en France
    - Son évolution par décennie (1891 → 2000)
    - Son origine étymologique (si disponible dans Geneanet)

Entrées :
    data/noms2008nat_txt.txt  → fichier INSEE (218 982 noms)
    output/final_database.json → base Geneanet (21 777 noms)

Sortie :
    output/insee_database.json → base complète enrichie
"""

import csv
import json


# ── 1. Chargement de la base Geneanet ────────────────────────────────────────

print(" Chargement de la base Geneanet...")
with open("output/final_database.json", "r", encoding="utf-8") as f:
    geneanet_db = json.load(f)

# Index : variante → entrée Geneanet (pour croiser rapidement)
index_geneanet = {}
for entree in geneanet_db:
    for variante in entree["variants"]:
        index_geneanet[variante.upper()] = entree

print(f" {len(geneanet_db)} entrées Geneanet chargées")
print(f" {len(index_geneanet)} variantes indexées")


# ── 2. Chargement du fichier INSEE ───────────────────────────────────────────

print("\n Chargement du fichier INSEE...")

# Colonnes des décennies
DECADES = [
    "_1891_1900", "_1901_1910", "_1911_1920", "_1921_1930",
    "_1931_1940", "_1941_1950", "_1951_1960", "_1961_1970",
    "_1971_1980", "_1981_1990", "_1991_2000"
]

insee_noms = []

with open("data/noms2008nat_txt.txt", encoding="latin-1") as f:
    reader = csv.DictReader(f, delimiter="\t")
    for row in reader:
        nom = row["NOM"].strip()

        # Calculer la fréquence totale sur toutes les décennies
        frequence_totale = sum(int(row.get(d, 0)) for d in DECADES)

        # Évolution par décennie
        evolution = {d: int(row.get(d, 0)) for d in DECADES}

        insee_noms.append({
            "nom":       nom,
            "frequence": frequence_totale,
            "evolution": evolution,
        })

print(f" {len(insee_noms)} noms INSEE chargés")


# ── 3. Croisement INSEE × Geneanet ───────────────────────────────────────────

print("\n Croisement INSEE × Geneanet...")

avec_origine    = 0
sans_origine    = 0
resultats       = []

for nom_insee in insee_noms:
    nom = nom_insee["nom"]

    # Chercher ce nom dans Geneanet
    entree_geneanet = index_geneanet.get(nom)

    if entree_geneanet:
        #  Nom trouvé dans Geneanet → on a l'origine
        avec_origine += 1
        resultats.append({
            "nom":          nom.lower(),
            "variantes":    entree_geneanet["variants"],
            "frequence":    nom_insee["frequence"],
            "evolution":    nom_insee["evolution"],
            "origin_text":  entree_geneanet.get("origin_text", ""),
            "source":       "geneanet",
        })
    else:
        #  Nom absent de Geneanet → pas d'origine pour l'instant
        sans_origine += 1
        resultats.append({
            "nom":          nom.lower(),
            "variantes":    [nom.lower()],
            "frequence":    nom_insee["frequence"],
            "evolution":    nom_insee["evolution"],
            "origin_text":  "",
            "source":       "insee_only",
        })

# Trier par fréquence décroissante (les plus portés en premier)
resultats.sort(key=lambda x: x["frequence"], reverse=True)

print(f" {avec_origine} noms avec origine Geneanet")
print(f"  {sans_origine} noms sans origine (INSEE uniquement)")
print(f"   → Ces noms pourront être enrichis par Mistral (étape suivante)")


# ── 4. Statistiques ───────────────────────────────────────────────────────────

total_personnes = sum(r["frequence"] for r in resultats)
top10 = resultats[:10]

print(f"\n Statistiques :")
print(f"   Total noms           : {len(resultats)}")
print(f"   Avec origine         : {avec_origine} ({avec_origine/len(resultats)*100:.1f}%)")
print(f"   Sans origine         : {sans_origine} ({sans_origine/len(resultats)*100:.1f}%)")
print(f"   Total personnes      : {total_personnes:,}")

print(f"\n Top 10 noms les plus portés en France :")
for i, r in enumerate(top10):
    origine = "" if r["source"] == "geneanet" else ""
    print(f"   {i+1:2}. {r['nom'].capitalize():20} {r['frequence']:>8,} personnes  {origine}")


# ── 5. Sauvegarde ─────────────────────────────────────────────────────────────

with open("output/insee_database.json", "w", encoding="utf-8") as f:
    json.dump(resultats, f, ensure_ascii=False, indent=2)

print(f"\n Base INSEE sauvegardée : output/insee_database.json")
print(f"   ({len(resultats)} noms avec fréquences et origines)")