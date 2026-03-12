"""
NLP-nameOrigins | Étape 5 : Correspondance phonétique et orthographique
========================================================================
Objectif :
    Pour les 201 772 noms INSEE sans origine étymologique,
    trouver le nom Geneanet le plus proche via :
    1. Soundex       → même prononciation
    2. Levenshtein   → orthographe très proche (1-2 lettres de différence)
    3. Mistral       → dernier recours pour les top 1000 sans correspondance

Entrées :
    output/insee_database.json    → base INSEE complète
    output/final_database.json    → base Geneanet avec origines

Sortie :
    output/full_database.json     → base finale complète enrichie
"""

import json
import time
import os
from dotenv import load_dotenv
from openai import OpenAI
import jellyfish
from Levenshtein import distance as levenshtein_distance


# ── 1. Chargement des données ─────────────────────────────────────────────────

print(" Chargement des données...")

with open("output/insee_database.json", "r", encoding="utf-8") as f:
    insee_db = json.load(f)

with open("output/final_database.json", "r", encoding="utf-8") as f:
    geneanet_db = json.load(f)

# Filtrer "Autres noms" qui n'est pas un vrai nom
insee_db = [n for n in insee_db if n["nom"] != "autres noms"]

# Séparer les noms avec et sans origine
avec_origine  = [n for n in insee_db if n["source"] == "geneanet"]
sans_origine  = [n for n in insee_db if n["source"] == "insee_only"]

print(f" {len(insee_db)} noms INSEE chargés")
print(f"   - {len(avec_origine)} avec origine Geneanet")
print(f"   - {len(sans_origine)} sans origine")


# ── 2. Index Soundex de tous les noms Geneanet ───────────────────────────────

print("\n Construction de l'index phonétique Geneanet...")

# soundex_index : code_soundex → liste d'entrées Geneanet
soundex_index = {}
for entree in geneanet_db:
    for variante in entree["variants"]:
        code = jellyfish.soundex(variante.upper())
        if code not in soundex_index:
            soundex_index[code] = []
        soundex_index[code].append(entree)

# Index direct nom → entrée pour Levenshtein
geneanet_noms = [v for e in geneanet_db for v in e["variants"]]
geneanet_dict = {}
for entree in geneanet_db:
    for variante in entree["variants"]:
        geneanet_dict[variante.lower()] = entree

print(f" {len(soundex_index)} codes Soundex indexés")


# ── 3. Fonctions de correspondance ───────────────────────────────────────────

def chercher_par_soundex(nom: str) -> dict | None:
    """
    Cherche un nom Geneanet avec le même code Soundex.
    Si plusieurs trouvés, retourne celui avec le nom le plus proche.
    """
    code = jellyfish.soundex(nom.upper())
    candidats = soundex_index.get(code, [])

    if not candidats:
        return None

    if len(candidats) == 1:
        return candidats[0]

    # Plusieurs candidats → prendre le plus proche par Levenshtein
    meilleur = min(
        candidats,
        key=lambda e: min(levenshtein_distance(nom.lower(), v) for v in e["variants"])
    )
    return meilleur


def chercher_par_levenshtein(nom: str, seuil: int = 2) -> dict | None:
    """
    Cherche un nom Geneanet à distance de Levenshtein <= seuil.
    Ex: DURRAND → DURAND (distance 1) 

    Args:
        nom   : nom à chercher
        seuil : distance max acceptée (1 ou 2)
    """
    nom_lower = nom.lower()
    meilleur_dist   = seuil + 1
    meilleure_entree = None

    for variante, entree in geneanet_dict.items():
        # Optimisation : ignorer si longueur trop différente
        if abs(len(nom_lower) - len(variante)) > seuil:
            continue

        dist = levenshtein_distance(nom_lower, variante)
        if dist <= seuil and dist < meilleur_dist:
            meilleur_dist    = dist
            meilleure_entree = entree

    return meilleure_entree


# ── 4. Correspondance phonétique et orthographique ───────────────────────────

print("\n Recherche de correspondances...")

# Trier par fréquence décroissante (traiter les noms les plus portés en priorité)
sans_origine.sort(key=lambda x: x["frequence"], reverse=True)

trouves_soundex      = 0
trouves_levenshtein  = 0
non_trouves          = 0

for nom_data in sans_origine:
    nom = nom_data["nom"]

    # Étape A : Soundex
    correspondance = chercher_par_soundex(nom)
    if correspondance:
        nom_data["origin_text"]  = correspondance.get("origin_text", "")
        nom_data["variantes"]    = correspondance["variants"]
        nom_data["source"]       = "soundex"
        nom_data["correspond_a"] = correspondance["representative"]
        trouves_soundex += 1
        continue

    # Étape B : Levenshtein (distance max = 2)
    correspondance = chercher_par_levenshtein(nom, seuil=2)
    if correspondance:
        nom_data["origin_text"]  = correspondance.get("origin_text", "")
        nom_data["variantes"]    = correspondance["variants"]
        nom_data["source"]       = "levenshtein"
        nom_data["correspond_a"] = correspondance["representative"]
        trouves_levenshtein += 1
        continue

    # Aucune correspondance trouvée
    non_trouves += 1

print(f"\n Résultats de la correspondance :")
print(f"   Trouvés par Soundex      : {trouves_soundex}")
print(f"   Trouvés par Levenshtein  : {trouves_levenshtein}")
print(f"   Non trouvés              : {non_trouves}")
print(f"   Taux de couverture       : {(trouves_soundex + trouves_levenshtein + len(avec_origine)) / len(insee_db) * 100:.1f}%")


# ── 5. Mistral pour les top 1000 sans correspondance ─────────────────────────

load_dotenv()
api_key = os.getenv("MISTRAL_API_KEY")

if api_key:
    client = OpenAI(api_key=api_key, base_url="https://api.mistral.ai/v1")

    # Prendre les 1000 noms les plus portés sans correspondance
    top_sans_origine = [
        n for n in sans_origine
        if n["source"] == "insee_only"
    ][:1000]

    print(f"\n Génération d'origines par Mistral pour {len(top_sans_origine)} noms...")

    for i, nom_data in enumerate(top_sans_origine):
        if (i + 1) % 50 == 0:
            print(f"   {i+1}/{len(top_sans_origine)} traités...")

        try:
            response = client.chat.completions.create(
                model="mistral-large-latest",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Tu es un expert en étymologie des noms de famille français. "
                            "Pour le nom de famille donné, rédige en 2-3 phrases son origine "
                            "étymologique en français, dans le style d'un dictionnaire. "
                            "Si tu ne connais pas l'origine exacte, propose une hypothèse probable. "
                            "Réponds UNIQUEMENT avec le texte, sans introduction."
                        )
                    },
                    {
                        "role": "user",
                        "content": f"Origine du nom de famille : {nom_data['nom'].upper()}"
                    }
                ],
                max_tokens=200,
                temperature=0.3,
            )
            nom_data["origin_text"] = response.choices[0].message.content.strip()
            nom_data["source"]      = "mistral_generated"
            time.sleep(0.3)

        except Exception as e:
            print(f"     Erreur pour {nom_data['nom']}: {e}")
else:
    print("\n  MISTRAL_API_KEY non définie → pas de génération d'origines")


# ── 6. Assemblage de la base finale ──────────────────────────────────────────

print("\n Assemblage de la base finale...")

full_database = avec_origine + sans_origine
full_database.sort(key=lambda x: x["frequence"], reverse=True)

# Statistiques finales
sources = {}
for n in full_database:
    s = n.get("source", "inconnu")
    sources[s] = sources.get(s, 0) + 1

print(f"\n Base finale :")
print(f"   Total noms             : {len(full_database)}")
for source, count in sorted(sources.items(), key=lambda x: x[1], reverse=True):
    pct = count / len(full_database) * 100
    print(f"   {source:25} : {count:>7} ({pct:.1f}%)")


# ── 7. Sauvegarde ─────────────────────────────────────────────────────────────

with open("output/full_database.json", "w", encoding="utf-8") as f:
    json.dump(full_database, f, ensure_ascii=False, indent=2)

print(f"\n Base complète sauvegardée : output/full_database.json")
print(f"   ({len(full_database)} noms avec fréquences, variantes et origines)")

# Aperçu
print(f"\n Aperçu (top 5 noms les plus portés) :")
for r in full_database[:5]:
    print(f"\n   Nom       : {r['nom'].capitalize()}")
    print(f"   Fréquence : {r['frequence']:,} personnes")
    print(f"   Source    : {r['source']}")
    print(f"   Origine   : {r.get('origin_text', '')[:100]}...")