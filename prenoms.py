"""
NLP-nameOrigins | Étape 3 : Scraping des prénoms sur prenoms.com
=================================================================
Objectif :
    Scraper les textes d'origine de tous les prénoms disponibles sur
    prenoms.com, puis appliquer le même traitement de regroupement
    par variantes que pour les noms de famille.

Source :
    https://www.prenoms.com  (14 435 prénoms disponibles)

Entrée :
    Aucune (scraping direct du site)

Sorties :
    output/prenoms_raw.json      → prénoms bruts scrapés
    output/prenoms_database.json → base finale avec variantes regroupées

Usage :
    python etape3_prenoms.py
    python etape3_prenoms.py --limit 100   (pour tester sur 100 prénoms)
"""

import json
import os
import re
import time
import argparse
from collections import defaultdict

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from openai import OpenAI


# ── Configuration ─────────────────────────────────────────────────────────────

BASE_URL   = "https://www.prenoms.com"
HEADERS    = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}
DELAY = 0.3  # secondes entre chaque requête (politesse envers le site)
NB_SITEMAPS = 8    # nombre de fichiers sitemap sur prenoms.com


# ── 1. Chargement de la clé API Mistral ──────────────────────────────────────

load_dotenv()
api_key = os.getenv("MISTRAL_API_KEY")
use_llm = bool(api_key)

if use_llm:
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.mistral.ai/v1",
    )
    print(" API Mistral activée pour les résumés")
else:
    print("  MISTRAL_API_KEY non définie → concaténation simple des textes")


# ── 2. Récupération de la liste des prénoms via les sitemaps ─────────────────

def get_prenoms_urls() -> list[str]:
    """
    Parcourt les 8 fichiers sitemap de prenoms.com et extrait
    toutes les URLs de pages de prénoms individuels.

    Returns:
        Liste d'URLs comme 'https://www.prenoms.com/prenom-fille/emma-5845'
    """
    all_urls = []

    for i in range(NB_SITEMAPS):
        url = f"{BASE_URL}/sitemap/sitemap-{i}.xml"
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            r.raise_for_status()

            # Extraire toutes les URLs de prénoms individuels
            # On garde uniquement /prenom-fille/ et /prenom-garcon/
            urls = re.findall(
                r'<loc>(https://www\.prenoms\.com/prenom[^<]+)</loc>',
                r.text
            )
            prenoms = [
                u for u in urls
                if '/prenom-fille/' in u or '/prenom-garcon/' in u
            ]

            # Filtrer les articles (ils ont des tirets multiples dans le nom)
            # Une page de prénom ressemble à : /prenom-fille/emma-5845
            # Un article ressemble à : /prenom-fille/top-des-prenoms-russes-46
            prenoms_filtres = []
            for u in prenoms:
                # Extraire la dernière partie de l'URL
                slug = u.split('/')[-1]          # ex: emma-5845
                parts = slug.split('-')
                # Un vrai prénom a max 2-3 parties (prénom + id numérique)
                if len(parts) <= 3 and parts[-1].isdigit():
                    prenoms_filtres.append(u)

            all_urls.extend(prenoms_filtres)
            print(f"   sitemap-{i}: {len(prenoms_filtres)} prénoms trouvés")

        except Exception as e:
            print(f"     Erreur sitemap-{i}: {e}")

    # Déduplication
    unique = list(dict.fromkeys(all_urls))
    print(f"\n Total : {len(unique)} prénoms uniques")
    return unique


# ── 3. Scraping d'une page de prénom ─────────────────────────────────────────

def scrape_prenom(url: str) -> dict | None:
    """
    Scrape la page d'un prénom sur prenoms.com et extrait :
    - Le nom du prénom
    - Le genre (fille/garçon)
    - Le texte d'origine

    Args:
        url : URL complète de la page du prénom

    Returns:
        {'name': str, 'genre': str, 'origin_text': str} ou None si échec
    """
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
    except Exception:
        return None

    soup = BeautifulSoup(r.text, 'html.parser')

    # Extraire le nom du prénom depuis l'URL
    # ex: /prenom-fille/emma-5845 → emma
    slug  = url.split('/')[-1]           # emma-5845
    parts = slug.split('-')
    name  = parts[0].lower()             # emma

    # Extraire le genre depuis l'URL
    genre = 'fille' if '/prenom-fille/' in url else 'garcon'

    # Extraire le texte d'origine : on prend le premier paragraphe long
    # qui contient l'étymologie du prénom
    origin_text = ""
    for p in soup.find_all('p'):
        text = p.get_text(strip=True)
        # On garde les paragraphes suffisamment longs (vraie description)
        if len(text) > 80:
            origin_text = text
            break   # on prend uniquement le premier paragraphe pertinent

    if not origin_text:
        return None

    return {
        "name":        name,
        "genre":       genre,
        "origin_text": origin_text,
        "url":         url,
    }


# ── 4. Union-Find pour regrouper les variantes ───────────────────────────────

class UnionFind:
    """Même structure que l'étape 1, pour regrouper les variantes de prénoms."""

    def __init__(self, items):
        self.parent = {x: x for x in items}
        self.rank   = {x: 0  for x in items}

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        if self.rank[ra] < self.rank[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        if self.rank[ra] == self.rank[rb]:
            self.rank[ra] += 1


def detect_variantes(text: str, all_names: set) -> list[str]:
    """
    Cherche dans un texte d'origine les mentions d'autres prénoms connus.
    Ex: 'Variante de Jeanne', 'Voir Jean', 'Formes : Jeannine, Jeannette'

    Args:
        text      : texte d'origine du prénom
        all_names : ensemble de tous les prénoms connus

    Returns:
        Liste des variantes trouvées dans le texte
    """
    found = []
    patterns = [
        r'[Vv]ariante(?:s)? de ([A-ZÀ-Ÿa-zà-ÿ\-]+)',
        r'[Vv]oir ([A-ZÀ-Ÿ][a-zà-ÿ\-]+)',
        r'[Ff]ormes? (?:voisines?|féminines?|masculines?) : ([^.]+)',
        r'[Vv]ariantes? : ([^.]+)',
        r'[Dd]iminutifs? : ([^.]+)',
    ]
    for pat in patterns:
        for match in re.finditer(pat, text):
            # La liste peut contenir plusieurs noms séparés par virgules
            parts = re.split(r'[,;]', match.group(1))
            for part in parts:
                nom = re.sub(r'\s*\(.*?\)', '', part).strip().lower()
                nom = re.sub(r'[^a-zà-ÿ\-]', '', nom)
                if nom and len(nom) > 1 and nom in all_names:
                    found.append(nom)
    return found


def build_clusters(scraped: list[dict]) -> list[dict]:
    """
    Regroupe les prénoms en clusters de variantes via Union-Find.

    Args:
        scraped : liste des prénoms scrapés avec leurs textes

    Returns:
        Liste de clusters avec variantes et textes regroupés
    """
    name_to_text = {p["name"]: p["origin_text"] for p in scraped}
    name_to_genre = {p["name"]: p["genre"] for p in scraped}
    all_names = set(name_to_text.keys())

    uf = UnionFind(list(all_names))

    # Relier les prénoms qui se mentionnent mutuellement
    for name, text in name_to_text.items():
        variantes = detect_variantes(text, all_names)
        for v in variantes:
            uf.union(name, v)

    # Construire les clusters
    clusters = defaultdict(list)
    for name in all_names:
        clusters[uf.find(name)].append(name)

    result = []
    for root, members in clusters.items():
        result.append({
            "representative": min(members),
            "variants":       sorted(members),
            "genre":          name_to_genre.get(min(members), "inconnu"),
            "origin_texts":   {m: name_to_text[m] for m in members},
        })

    result.sort(key=lambda x: x["representative"])
    return result


# ── 5. Résumé LLM pour les clusters avec plusieurs textes ────────────────────

def resumer_textes(variants: list, textes: dict) -> str:
    """
    Utilise Mistral pour résumer plusieurs textes de prénoms en un seul.

    Args:
        variants : liste des prénoms du cluster
        textes   : dictionnaire {prenom: texte}

    Returns:
        Texte synthétique unique
    """
    combined = "\n\n---\n\n".join(
        f"Texte pour {name} :\n{txt}"
        for name, txt in textes.items()
        if txt.strip()
    )
    response = client.chat.completions.create(
        model="mistral-large-latest",
        messages=[
            {
                "role": "system",
                "content": (
                    "Tu es un expert en étymologie des prénoms. "
                    "Synthétise les textes fournis en un seul texte complet "
                    "et fluide, sans perdre d'information. "
                    "Réponds uniquement avec le texte synthétisé."
                )
            },
            {
                "role": "user",
                "content": f"Prénoms : {', '.join(variants)}\n\n{combined}"
            },
        ],
        max_tokens=1024,
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Scraper de prénoms - prenoms.com")
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Limiter à N prénoms (utile pour tester)"
    )
    args = parser.parse_args()

    # ── Étape A : Récupération des URLs ───────────────────────────────────────
    print("=" * 60)
    print("ÉTAPE A : Récupération de la liste des prénoms")
    print("=" * 60)
    urls = get_prenoms_urls()

    # Appliquer la limite si demandée
    if args.limit:
        urls = urls[:args.limit]
        print(f"  Mode test : limité à {args.limit} prénoms")

    # ── Étape B : Scraping des pages ──────────────────────────────────────────
    print("\n" + "=" * 60)
    print(f"ÉTAPE B : Scraping de {len(urls)} pages")
    print("=" * 60)

    scraped = []
    errors  = 0

    for i, url in enumerate(urls):
        # Afficher la progression toutes les 50 prénoms
        if (i + 1) % 50 == 0:
            print(f"   {i+1}/{len(urls)} scrapés ({errors} erreurs)...")

        result = scrape_prenom(url)
        if result:
            scraped.append(result)
        else:
            errors += 1

        time.sleep(DELAY)   # pause entre chaque requête

    print(f"\n {len(scraped)} prénoms récupérés, {errors} erreurs")

    # Sauvegarde intermédiaire (au cas où)
    with open("output/prenoms_raw.json", "w", encoding="utf-8") as f:
        json.dump(scraped, f, ensure_ascii=False, indent=2)
    print(" Sauvegarde intermédiaire : output/prenoms_raw.json")

    # ── Étape C : Regroupement des variantes ──────────────────────────────────
    print("\n" + "=" * 60)
    print("ÉTAPE C : Regroupement des variantes")
    print("=" * 60)

    clusters = build_clusters(scraped)
    multi    = [c for c in clusters if len(c["variants"]) > 1]
    simple   = [c for c in clusters if len(c["variants"]) == 1]

    print(f" {len(clusters)} clusters : {len(multi)} groupes, {len(simple)} isolés")

    # ── Étape D : Résumé des textes ───────────────────────────────────────────
    print("\n" + "=" * 60)
    print("ÉTAPE D : Résumé des textes")
    print("=" * 60)

    final = []

    for i, c in enumerate(clusters):
        if (i + 1) % 100 == 0:
            print(f"   {i+1}/{len(clusters)} traités...")

        non_empty = {k: v for k, v in c["origin_texts"].items() if v.strip()}

        if not non_empty:
            text   = ""
            source = "empty"

        elif len(non_empty) == 1:
            # Un seul texte → pas besoin de résumé
            text   = list(non_empty.values())[0]
            source = "direct"

        elif use_llm:
            # Plusieurs textes → résumé par Mistral
            try:
                text   = resumer_textes(c["variants"], non_empty)
                source = "mistral_summary"
                time.sleep(0.3)
            except Exception as e:
                print(f"     Erreur LLM pour {c['representative']}: {e}")
                text   = " | ".join(non_empty.values())
                source = "concatenated"
        else:
            # Pas de clé API → concaténation simple
            text   = " | ".join(non_empty.values())
            source = "concatenated"

        final.append({
            "representative": c["representative"],
            "variants":       c["variants"],
            "genre":          c["genre"],
            "origin_text":    text,
            "source":         source,
        })

    # ── Sauvegarde finale ─────────────────────────────────────────────────────
    with open("output/prenoms_database.json", "w", encoding="utf-8") as f:
        json.dump(final, f, ensure_ascii=False, indent=2)

    # ── Statistiques finales ──────────────────────────────────────────────────
    print(f"\n Résultats finaux :")
    print(f"   Total prénoms         : {len(final)}")
    print(f"   Groupes de variantes  : {len(multi)}")
    print(f"   Résumés Mistral       : {sum(1 for f in final if f['source'] == 'mistral_summary')}")

    print(f"\n Aperçu (Jean) :")
    jean = next((f for f in final if 'jean' in f['variants']), None)
    if jean:
        print(f"   Variantes : {jean['variants']}")
        print(f"   Genre     : {jean['genre']}")
        print(f"   Texte     : {jean['origin_text'][:200]}...")

    print(f"\n Base des prénoms sauvegardée : output/prenoms_database.json")


if __name__ == "__main__":
    main()