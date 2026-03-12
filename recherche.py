"""
NLP-nameOrigins | Recherche d'un nom complet (prénom + nom de famille)
=======================================================================
Objectif :
    Permettre à un utilisateur de rechercher :
    - Un nom seul         : 'martin'
    - Un prénom seul      : 'jean'
    - Un nom complet      : 'jean martin' ou 'martin jean'

    Pour chaque nom trouvé, afficher :
    - Le nom tel que recherché par l'utilisateur
    - Les variantes connues
    - La fréquence en France (INSEE)
    - L'origine étymologique
    - La source de l'information

Usage :
    python recherche.py
"""

import json
import unicodedata


# ── 1. Chargement de la base complète ────────────────────────────────────────

print(" Chargement de la base de données...")

with open("output/full_database.json", "r", encoding="utf-8") as f:
    full_db = json.load(f)

with open("output/prenoms_database.json", "r", encoding="utf-8") as f:
    prenoms_db = json.load(f)

print(f" {len(full_db)} noms de famille chargés")
print(f" {len(prenoms_db)} prénoms chargés")


# ── 2. Indexation ─────────────────────────────────────────────────────────────

index_noms    = {}
index_prenoms = {}

# Indexer chaque nom et ses variantes
for entree in full_db:
    index_noms[entree["nom"].lower()] = entree
    for variante in entree.get("variantes", []):
        index_noms[variante.lower()] = entree

# Indexer les prénoms et leurs variantes
for entree in prenoms_db:
    for variante in entree.get("variants", []):
        index_prenoms[variante.lower()] = entree


# ── 3. Normalisation ──────────────────────────────────────────────────────────

def normaliser(texte: str) -> str:
    """Minuscules + suppression des accents."""
    texte = texte.strip().lower()
    texte = unicodedata.normalize('NFD', texte)
    texte = ''.join(c for c in texte if unicodedata.category(c) != 'Mn')
    return texte


def rechercher(query: str, index: dict) -> dict | None:
    """
    Recherche exacte puis sans accents.
    Retourne une copie de l'entrée avec le nom recherché mémorisé.
    """
    q = query.strip().lower()

    # Recherche exacte
    if q in index:
        entree = dict(index[q])          # copie pour ne pas modifier l'original
        entree["nom_recherche"] = q      # mémoriser ce que l'utilisateur a tapé
        return entree

    # Recherche sans accents
    q_norm = normaliser(q)
    for cle, val in index.items():
        if normaliser(cle) == q_norm:
            entree = dict(val)
            entree["nom_recherche"] = q
            return entree

    return None


# ── 4. Affichage ──────────────────────────────────────────────────────────────

LABELS_SOURCE = {
    "geneanet":          "Geneanet (étymologie confirmée)",
    "soundex":           "Correspondance phonétique (Soundex)",
    "levenshtein":       "Correspondance orthographique (Levenshtein)",
    "mistral_generated": "Origine générée par Mistral",
    "insee_only":        "INSEE (pas d'origine disponible)",
}


def afficher_texte(texte: str):
    """Affiche un texte long formaté sur 60 caractères par ligne."""
    mots  = texte.split()
    ligne = "  "
    for mot in mots:
        if len(ligne) + len(mot) + 1 > 62:
            print(ligne)
            ligne = "  " + mot + " "
        else:
            ligne += mot + " "
    if ligne.strip():
        print(ligne)


def afficher_nom(entree: dict):
    """Affiche les informations d'un nom de famille."""

    print("\n" + "─" * 60)
    print(f"   NOM DE FAMILLE")
    print("─" * 60)

    # Afficher le nom tel que tapé par l'utilisateur
    nom_affiche = entree.get("nom_recherche", entree["nom"])
    print(f"  Nom        : {nom_affiche.capitalize()}")

    # Variantes : afficher toutes sauf le nom recherché lui-même
    variantes = entree.get("variantes", [])
    autres    = [
        v.capitalize() for v in variantes
        if v.lower() != nom_affiche.lower()
    ]
    if autres:
        print(f"  Variantes  : {', '.join(autres)}")

    # Fréquence en France
    frequence = entree.get("frequence", 0)
    if frequence > 0:
        print(f"  Fréquence  : {frequence:,} personnes en France")

    # Source de l'information
    source = entree.get("source", "inconnu")
    label  = LABELS_SOURCE.get(source, source)
    print(f"  Source     : {label}")

    # Nom Geneanet correspondant si trouvé par phonétique/Levenshtein
    if source in ("soundex", "levenshtein") and "correspond_a" in entree:
        print(f"  Proche de  : {entree['correspond_a'].capitalize()}")

    # Texte d'origine
    texte = entree.get("origin_text", "").strip()
    if texte:
        print(f"\n  Origine :\n")
        afficher_texte(texte)
    else:
        print("\n  Origine : (aucune information disponible)")


def afficher_prenom(entree: dict):
    """Affiche les informations d'un prénom."""

    print("\n" + "─" * 60)
    print(f"   PRÉNOM")
    print("─" * 60)

    # Afficher le prénom tel que tapé par l'utilisateur
    nom_affiche = entree.get("nom_recherche", "")
    variantes   = entree.get("variants", [])

    if nom_affiche:
        print(f"  Prénom     : {nom_affiche.capitalize()}")
        autres = [v.capitalize() for v in variantes if v.lower() != nom_affiche.lower()]
        if autres:
            print(f"  Variantes  : {', '.join(autres)}")
    elif len(variantes) == 1:
        print(f"  Prénom     : {variantes[0].capitalize()}")
    else:
        print(f"  Variantes  : {', '.join(v.capitalize() for v in variantes)}")

    # Genre
    if "genre" in entree:
        print(f"  Genre      : {entree['genre'].capitalize()}")

    # Texte d'origine
    texte = entree.get("origin_text", "").strip()
    if texte:
        print(f"\n  Origine :\n")
        afficher_texte(texte)
    else:
        print("\n  Origine : (aucune information disponible)")


# ── 5. Logique de recherche ───────────────────────────────────────────────────

def traiter_recherche(query: str):
    """
    Gère 3 cas :
    1. Un seul mot  → cherche dans noms ET prénoms
    2. Deux mots    → cherche prénom + nom de famille
    3. Rien trouvé  → message d'erreur
    """
    mots = query.strip().split()

    # ── Cas 1 : un seul mot ───────────────────────────────────────────────────
    if len(mots) == 1:
        mot    = mots[0]
        trouve = False

        res_nom = rechercher(mot, index_noms)
        if res_nom:
            afficher_nom(res_nom)
            trouve = True

        res_prenom = rechercher(mot, index_prenoms)
        if res_prenom:
            afficher_prenom(res_prenom)
            trouve = True

        if not trouve:
            print(f"\n   '{mot}' non trouvé dans la base.")
            print(f"   Vérifiez l'orthographe ou essayez une variante.")

    # ── Cas 2 : deux mots (prénom + nom) ─────────────────────────────────────
    elif len(mots) == 2:
        trouve = False

        # Essai 1 : mot1 = prénom, mot2 = nom
        res_prenom = rechercher(mots[0], index_prenoms)
        res_nom    = rechercher(mots[1], index_noms)

        if res_prenom and res_nom:
            print(f"\n   Résultats pour : {mots[0].capitalize()} {mots[1].capitalize()}")
            afficher_prenom(res_prenom)
            afficher_nom(res_nom)
            trouve = True

        # Essai 2 : mot1 = nom, mot2 = prénom
        if not trouve:
            res_nom    = rechercher(mots[0], index_noms)
            res_prenom = rechercher(mots[1], index_prenoms)

            if res_nom and res_prenom:
                print(f"\n   Résultats pour : {mots[1].capitalize()} {mots[0].capitalize()}")
                afficher_prenom(res_prenom)
                afficher_nom(res_nom)
                trouve = True

        # Essai 3 : chercher chaque mot indépendamment
        if not trouve:
            for mot in mots:
                res_nom    = rechercher(mot, index_noms)
                res_prenom = rechercher(mot, index_prenoms)
                if res_nom:
                    afficher_nom(res_nom)
                    trouve = True
                if res_prenom:
                    afficher_prenom(res_prenom)
                    trouve = True

        if not trouve:
            print(f"\n   '{query}' non trouvé dans la base.")
            print(f"   Essayez avec un seul mot à la fois.")

    # ── Cas 3 : plus de deux mots ─────────────────────────────────────────────
    else:
        print(f"\n    Entrez un prénom, un nom, ou les deux séparés par un espace.")
        print(f"   Exemple : 'martin', 'jean', ou 'jean martin'")


# ── 6. Boucle interactive ─────────────────────────────────────────────────────

print("\n" + "=" * 60)
print("   RECHERCHE DE NOMS ET PRÉNOMS")
print("  Exemples : 'martin', 'jean', 'jean martin'")
print("  Tapez 'quitter' pour arrêter")
print("=" * 60)

while True:
    print()
    query = input("  Votre recherche : ").strip()

    if query.lower() in ["quitter", "quit", "exit", "q"]:
        print("\n  Au revoir ! ")
        break

    if not query:
        print("    Veuillez entrer un nom.")
        continue

    traiter_recherche(query)