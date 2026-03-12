"""
NLP-nameOrigins | Étape 2 : Résumé des textes d'origine avec Mistral
=====================================================================
Objectif :
    Pour chaque cluster ayant plusieurs textes d'origine, utiliser l'API
    Mistral pour produire un résumé unique, complet et sans perte
    d'information.
    Les clusters avec un seul texte sont conservés tels quels.

Entrée :
    output/clusters.json       → résultat de l'étape 1

Sortie :
    output/final_database.json → base finale avec un texte par cluster

Note :
    On utilise la librairie openai qui est compatible avec l'API Mistral
    en changeant simplement le base_url.
"""

import json
import os
import time

from dotenv import load_dotenv
from openai import OpenAI


# ── 1. Chargement de la clé API depuis le fichier .env ───────────────────────

# load_dotenv() lit le fichier .env et charge les variables d'environnement
load_dotenv()
api_key = os.getenv("MISTRAL_API_KEY")

if not api_key:
    raise ValueError(" MISTRAL_API_KEY introuvable dans le fichier .env !")

# Initialisation du client OpenAI pointant vers l'API Mistral
# Mistral est compatible avec le format OpenAI, on change juste le base_url
client = OpenAI(
    api_key=api_key,
    base_url="https://api.mistral.ai/v1",  # URL de l'API Mistral
)
print(" Connexion à l'API Mistral réussie")


# ── 2. Chargement des clusters (résultat étape 1) ────────────────────────────

with open("output/clusters.json", "r", encoding="utf-8") as f:
    clusters = json.load(f)

print(f" {len(clusters)} clusters chargés")

# Séparer les clusters simples (1 texte) des complexes (plusieurs textes)
simples   = [c for c in clusters if len(c["origin_ids"]) <= 1]
complexes = [c for c in clusters if len(c["origin_ids"]) > 1]

print(f"   - {len(simples)} clusters avec 1 seul texte (pas de résumé nécessaire)")
print(f"   - {len(complexes)} clusters avec plusieurs textes (résumé par Mistral)")


# ── 3. Fonction de résumé via l'API Mistral ──────────────────────────────────

def resumer_textes(variants: list, textes: dict) -> str:
    """
    Envoie plusieurs textes d'origine à Mistral et retourne un résumé unique.

    Args:
        variants : liste des noms du cluster (ex: ['durand', 'durant', 'duran'])
        textes   : dictionnaire {origin_id: texte} des textes à résumer

    Returns:
        Un texte synthétique unique en français
    """

    # Construction du prompt : on assemble tous les textes
    textes_assembles = "\n\n---\n\n".join(
        f"Texte {i+1} (réf. {oid}) :\n{txt}"
        for i, (oid, txt) in enumerate(textes.items())
        if txt.strip()  # on ignore les textes vides
    )

    # Message système : définit le rôle de Mistral
    system_prompt = """Tu es un expert en généalogie et en étymologie des noms de famille français.
Tu reçois plusieurs textes explicatifs sur l'origine d'un groupe de noms de famille (variantes d'un même patronyme).
Ton rôle est de produire un SEUL texte synthétique, en français, qui :
- Regroupe toutes les informations présentes dans les textes fournis
- N'omet aucune information importante (régions, étymologie, variantes, dates)
- Élimine les redondances et répétitions
- Est rédigé de manière fluide, dans le style d'un dictionnaire étymologique
Réponds UNIQUEMENT avec le texte synthétisé, sans introduction ni commentaire."""

    # Message utilisateur : les textes à résumer
    user_prompt = (
        f"Noms concernés : {', '.join(variants)}\n\n"
        f"Textes à synthétiser :\n\n{textes_assembles}"
    )

    # Appel à l'API Mistral via le client OpenAI compatible
    response = client.chat.completions.create(
        model="mistral-large-latest",   # modèle le plus performant de Mistral
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        max_tokens=1024,
        temperature=0.3,    # faible température = réponse plus factuelle
    )

    # Extraction du texte de la réponse
    return response.choices[0].message.content.strip()


# ── 4. Traitement des clusters ────────────────────────────────────────────────

results = []

# 4a. Clusters simples : on copie directement le texte sans appel API
print("\n Traitement des clusters simples...")
for c in simples:
    # Récupérer le seul texte disponible (ou vide si aucun)
    oid  = c["origin_ids"][0] if c["origin_ids"] else None
    text = c["origin_texts"].get(oid, "") if oid else ""

    results.append({
        "representative": c["representative"],  # nom canonique du groupe
        "variants":       c["variants"],         # toutes les variantes
        "origin_text":    text,                  # texte d'origine
        "source":         "direct",              # pas de résumé LLM
    })

print(f" {len(simples)} clusters simples traités")

# 4b. Clusters complexes : résumé par Mistral
print(f"\n Résumé Mistral pour {len(complexes)} clusters...")

for i, c in enumerate(complexes):

    # Afficher la progression toutes les 10 entrées
    if (i + 1) % 10 == 0:
        print(f"   {i+1}/{len(complexes)} clusters traités...")

    # Filtrer les textes vides
    textes_non_vides = {
        oid: txt
        for oid, txt in c["origin_texts"].items()
        if txt.strip()
    }

    if not textes_non_vides:
        # Aucun texte disponible
        summary = ""
        source  = "empty"

    elif len(textes_non_vides) == 1:
        # Un seul texte non vide → pas besoin de Mistral
        summary = list(textes_non_vides.values())[0]
        source  = "direct"

    else:
        # Plusieurs textes → on demande à Mistral de résumer
        try:
            summary = resumer_textes(c["variants"], textes_non_vides)
            source  = "mistral_summary"
            time.sleep(0.5)  # pause pour ne pas surcharger l'API

        except Exception as e:
            # En cas d'erreur, on concatène les textes sans résumé
            print(f"     Erreur pour '{c['representative']}' : {e}")
            summary = " | ".join(textes_non_vides.values())
            source  = "concatenated"

    results.append({
        "representative": c["representative"],
        "variants":       c["variants"],
        "origin_text":    summary,
        "source":         source,
    })


# ── 5. Sauvegarde du résultat final ──────────────────────────────────────────

# Tri alphabétique par nom représentatif
results.sort(key=lambda x: x["representative"])

with open("output/final_database.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)


# ── 6. Statistiques finales ───────────────────────────────────────────────────

total      = len(results)
nb_direct  = sum(1 for r in results if r["source"] == "direct")
nb_mistral = sum(1 for r in results if r["source"] == "mistral_summary")
nb_concat  = sum(1 for r in results if r["source"] == "concatenated")

print(f"\n Résultats :")
print(f"   Total entrées          : {total}")
print(f"   Textes directs         : {nb_direct}")
print(f"   Résumés par Mistral    : {nb_mistral}")
print(f"   Concaténés (erreurs)   : {nb_concat}")

print(f"\n Aperçu (exemple Durand) :")
durand = next((r for r in results if "durand" in r["variants"]), None)
if durand:
    print(f"   Variantes : {durand['variants']}")
    print(f"   Source    : {durand['source']}")
    print(f"   Texte     : {durand['origin_text'][:200]}...")

print(f"\n Base finale sauvegardée dans output/final_database.json")