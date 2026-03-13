"""
NLP-nameOrigins | Étape 7 : Noms composés + Variantes régionales
=================================================================
Objectif :
    1. Noms composés : Le Goff / Legoff / Le-Goff → même nom
    2. Variantes régionales : Lefebre / Lefebvre / Lefeuvre → même origine

Entrées :
    output/full_database.json  → base complète

Sortie :
    output/full_database_v2.json → base enrichie
"""

import json
import re
import os
import time
from dotenv import load_dotenv
from openai import OpenAI


# ── 1. Chargement ─────────────────────────────────────────────────────────────

print(" Chargement des données...")

with open("output/full_database.json", "r", encoding="utf-8") as f:
    full_db = json.load(f)

print(f" {len(full_db)} noms chargés")


# ── 2. PARTIE 1 : Noms composés ───────────────────────────────────────────────
# Le Goff / Legoff / Le-Goff → normaliser en "legoff" pour comparer

print("\n Partie 1 : Détection des noms composés...")


def normaliser_compose(nom: str) -> str:
    """
    Normalise un nom composé pour la comparaison.
    Le Goff → legoff
    Le-Goff → legoff
    Legoff  → legoff

    Args:
        nom : nom de famille

    Returns:
        Forme normalisée sans espaces ni tirets
    """
    nom = nom.lower().strip()
    nom = nom.replace("-", "").replace(" ", "").replace("'", "")
    return nom


# Construire un index : forme normalisée → liste d'entrées
index_normalise = {}
for entree in full_db:
    forme = normaliser_compose(entree["nom"])
    if forme not in index_normalise:
        index_normalise[forme] = []
    index_normalise[forme].append(entree)

# Trouver les groupes de noms composés
groupes_composes = {
    forme: entrees
    for forme, entrees in index_normalise.items()
    if len(entrees) > 1
}

print(f" {len(groupes_composes)} groupes de noms composés trouvés")

# Afficher les 10 premiers exemples
print("\n Exemples de noms composés regroupés :")
for forme, entrees in list(groupes_composes.items())[:10]:
    noms = [e["nom"] for e in entrees]
    print(f"   {forme:20} → {noms}")

# Fusionner les groupes de noms composés
fusions_composes = 0
for forme, entrees in groupes_composes.items():
    if len(entrees) < 2:
        continue

    # Prendre l'entrée avec la fréquence la plus haute comme référence
    reference = max(entrees, key=lambda e: e.get("frequence", 0))

    # Fusionner les variantes et fréquences
    toutes_variantes = set(reference.get("variantes", [reference["nom"]]))
    freq_totale      = reference.get("frequence", 0)

    for entree in entrees:
        if entree is reference:
            continue
        toutes_variantes.update(entree.get("variantes", [entree["nom"]]))
        freq_totale += entree.get("frequence", 0)

    reference["variantes"]  = sorted(list(toutes_variantes))
    reference["frequence"]  = freq_totale
    fusions_composes += 1

print(f" {fusions_composes} fusions de noms composés effectuées")


# ── 3. PARTIE 2 : Variantes régionales ───────────────────────────────────────
# Lefebre / Lefebvre / Lefeuvre → textes parlent du même métier (forgeron)
# On utilise Mistral pour détecter si deux textes parlent du même nom

print("\n Partie 2 : Détection des variantes régionales par Soundex...")

import jellyfish

# Construire index Soundex
soundex_groupes = {}
for entree in full_db:
    if not entree.get("origin_text"):
        continue
    code = jellyfish.soundex(entree["nom"].upper())
    if code not in soundex_groupes:
        soundex_groupes[code] = []
    soundex_groupes[code].append(entree)

# Garder uniquement les groupes avec plusieurs noms ET des origines différentes
candidats_regionaux = []
for code, entrees in soundex_groupes.items():
    if len(entrees) < 2:
        continue
    # Vérifier que les textes sont différents (pas déjà regroupés)
    textes = set(e.get("origin_text", "")[:100] for e in entrees)
    if len(textes) > 1:
        candidats_regionaux.append({
            "code":    code,
            "noms":    [e["nom"] for e in entrees],
            "textes":  [e.get("origin_text", "")[:200] for e in entrees],
        })

print(f" {len(candidats_regionaux)} groupes candidats de variantes régionales")
print(f"   (même Soundex mais origines différentes)")

# Afficher quelques exemples
print("\n Exemples de variantes régionales candidates :")
for groupe in candidats_regionaux[:5]:
    print(f"\n   Noms    : {groupe['noms'][:5]}")
    print(f"   Texte 1 : {groupe['textes'][0][:100]}...")
    if len(groupe['textes']) > 1:
        print(f"   Texte 2 : {groupe['textes'][1][:100]}...")


# ── 4. Validation par Mistral des variantes régionales ───────────────────────

load_dotenv()
api_key = os.getenv("MISTRAL_API_KEY")

if api_key:
    client = OpenAI(api_key=api_key, base_url="https://api.mistral.ai/v1")

    # Prendre un échantillon de 100 groupes pour valider
    echantillon = candidats_regionaux[:100]
    print(f"\n Validation Mistral sur {len(echantillon)} groupes...")

    variantes_confirmees = []

    for i, groupe in enumerate(echantillon):
        if (i + 1) % 20 == 0:
            print(f"   {i+1}/{len(echantillon)} validés...")

        noms   = groupe["noms"][:3]   # max 3 noms pour le prompt
        textes = groupe["textes"][:3]

        prompt = (
            f"Ces noms de famille ont la même prononciation : {noms}. "
            f"Voici leurs textes étymologiques : {textes}. "
            "Ces noms sont-ils des variantes régionales du même patronyme ? "
            "Réponds UNIQUEMENT par 'OUI' ou 'NON' suivi d'une explication en 1 phrase."
        )

        try:
            response = client.chat.completions.create(
                model="mistral-large-latest",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100,
                temperature=0.1,
            )
            reponse = response.choices[0].message.content.strip()
            est_variante = reponse.upper().startswith("OUI")

            if est_variante:
                variantes_confirmees.append({
                    "noms":      noms,
                    "code":      groupe["code"],
                    "explication": reponse,
                })

            time.sleep(0.3)

        except Exception as e:
            pass

    print(f"\n {len(variantes_confirmees)} groupes de variantes régionales confirmés")
    print(f"\n Exemples confirmés :")
    for v in variantes_confirmees[:5]:
        print(f"\n   Noms        : {v['noms']}")
        print(f"   Explication : {v['explication'][:120]}")

    # Sauvegarder les variantes régionales
    with open("output/variantes_regionales.json", "w", encoding="utf-8") as f:
        json.dump(variantes_confirmees, f, ensure_ascii=False, indent=2)
    print(f"\n Variantes régionales sauvegardées : output/variantes_regionales.json")


# ── 5. Statistiques finales ───────────────────────────────────────────────────

print(f"\n Résumé :")
print(f"   Noms composés regroupés   : {fusions_composes}")
print(f"   Groupes variantes Soundex : {len(candidats_regionaux)}")
if api_key:
    print(f"   Variantes régionales conf : {len(variantes_confirmees)}")

# Sauvegarder la base mise à jour
with open("output/full_database_v2.json", "w", encoding="utf-8") as f:
    json.dump(full_db, f, ensure_ascii=False, indent=2)

print(f"\n Base v2 sauvegardée : output/full_database_v2.json")