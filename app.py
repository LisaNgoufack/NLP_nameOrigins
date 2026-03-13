"""
NLP-nameOrigins | Application Streamlit
========================================
Belle interface de recherche étymologique des noms français.

Usage :
    streamlit run app.py
"""

import json
import unicodedata
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import jellyfish


# ── Configuration ─────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="NLP-nameOrigins",
    page_icon="",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# CSS personnalisé pour une belle interface
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Source+Sans+3:wght@300;400;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'Source Sans 3', sans-serif;
    }

    .main-title {
        font-family: 'Playfair Display', serif;
        font-size: 3.2rem;
        font-weight: 700;
        text-align: center;
        color: #1a1a2e;
        margin-bottom: 0.2rem;
        letter-spacing: -1px;
    }

    .subtitle {
        text-align: center;
        color: #666;
        font-size: 1.1rem;
        margin-bottom: 2rem;
        font-weight: 300;
    }

    .stat-box {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        color: white;
        padding: 1.2rem;
        border-radius: 12px;
        text-align: center;
        margin: 0.3rem;
    }

    .stat-number {
        font-family: 'Playfair Display', serif;
        font-size: 2rem;
        font-weight: 700;
        color: #e2b96f;
    }

    .stat-label {
        font-size: 0.85rem;
        color: #aaa;
        margin-top: 0.2rem;
    }

    .result-card {
        background: white;
        border: 1px solid #e8e8e8;
        border-radius: 16px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 4px 20px rgba(0,0,0,0.06);
    }

    .result-title {
        font-family: 'Playfair Display', serif;
        font-size: 1.8rem;
        color: #1a1a2e;
        margin-bottom: 0.5rem;
    }

    .badge {
        display: inline-block;
        padding: 0.2rem 0.7rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        margin: 0.2rem;
    }

    .badge-geneanet { background: #d4edda; color: #155724; }
    .badge-soundex  { background: #cce5ff; color: #004085; }
    .badge-lev      { background: #fff3cd; color: #856404; }
    .badge-mistral  { background: #e2d9f3; color: #4a235a; }
    .badge-insee    { background: #f8d7da; color: #721c24; }

    .variante-tag {
        display: inline-block;
        background: #f0f4ff;
        color: #3d5a99;
        padding: 0.2rem 0.8rem;
        border-radius: 20px;
        font-size: 0.9rem;
        margin: 0.2rem;
        border: 1px solid #c5d0e8;
    }

    .origine-text {
        background: #fafafa;
        border-left: 4px solid #e2b96f;
        padding: 1rem 1.2rem;
        border-radius: 0 8px 8px 0;
        font-size: 0.95rem;
        line-height: 1.7;
        color: #333;
        margin-top: 1rem;
    }

    .search-hint {
        text-align: center;
        color: #999;
        font-size: 0.9rem;
        margin-top: 0.5rem;
    }

    .phonetique-section {
        background: #f8f9ff;
        border-radius: 12px;
        padding: 1rem;
        margin-top: 1rem;
    }

    div[data-testid="stButton"] button {
        background: #1a1a2e;
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        padding: 0.5rem 1.5rem;
        transition: all 0.2s;
    }

    div[data-testid="stButton"] button:hover {
        background: #e2b96f;
        color: #1a1a2e;
    }

    .stTextInput input {
        border-radius: 40px !important;
        border: 2px solid #e0e0e0 !important;
        padding: 0.8rem 1.5rem !important;
        font-size: 1.1rem !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05) !important;
    }

    .stTextInput input:focus {
        border-color: #1a1a2e !important;
        box-shadow: 0 4px 20px rgba(26,26,46,0.15) !important;
    }

    footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ── Chargement des données ────────────────────────────────────────────────────

@st.cache_data
def charger_donnees():
    with open("output/full_database.json", "r", encoding="utf-8") as f:
        full_db = json.load(f)
    with open("output/prenoms_database.json", "r", encoding="utf-8") as f:
        prenoms_db = json.load(f)

    index_noms    = {}
    index_prenoms = {}

    for entree in full_db:
        index_noms[entree["nom"].lower()] = entree
        for variante in entree.get("variantes", []):
            index_noms[variante.lower()] = entree

    for entree in prenoms_db:
        for variante in entree.get("variants", []):
            index_prenoms[variante.lower()] = entree

    return full_db, index_noms, index_prenoms


# ── Normalisation ─────────────────────────────────────────────────────────────

def normaliser(texte):
    texte = texte.strip().lower()
    texte = unicodedata.normalize('NFD', texte)
    return ''.join(c for c in texte if unicodedata.category(c) != 'Mn')


def rechercher(query, index):
    q = query.strip().lower()
    if q in index:
        e = dict(index[q]); e["nom_recherche"] = q; return e
    q_norm = normaliser(q)
    for cle, val in index.items():
        if normaliser(cle) == q_norm:
            e = dict(val); e["nom_recherche"] = q; return e
    return None


def trouver_proches(nom, index_noms, n=5):
    """Trouve les noms phonétiquement proches via Soundex."""
    code = jellyfish.soundex(nom.upper())
    proches = []
    for cle, entree in index_noms.items():
        if cle == nom.lower():
            continue
        if jellyfish.soundex(cle.upper()) == code:
            proches.append(cle)
        if len(proches) >= n:
            break
    return proches[:n]


# ── Graphique évolution INSEE ─────────────────────────────────────────────────

def graphique_evolution(entree):
    """Crée un graphique d'évolution du nom par décennie."""
    decades = {
        "1891-1900": "_1891_1900", "1901-1910": "_1901_1910",
        "1911-1920": "_1911_1920", "1921-1930": "_1921_1930",
        "1931-1940": "_1931_1940", "1941-1950": "_1941_1950",
        "1951-1960": "_1951_1960", "1961-1970": "_1961_1970",
        "1971-1980": "_1971_1980", "1981-1990": "_1981_1990",
        "1991-2000": "_1991_2000",
    }

    evolution = entree.get("evolution", {})
    if not evolution:
        return None

    labels = list(decades.keys())
    values = [evolution.get(v, 0) for v in decades.values()]

    if sum(values) == 0:
        return None

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=labels,
        y=values,
        marker=dict(
            color=values,
            colorscale=[[0, "#c8d8f8"], [1, "#1a1a2e"]],
        ),
        hovertemplate="<b>%{x}</b><br>%{y:,} naissances<extra></extra>",
    ))
    fig.update_layout(
        title=dict(
            text=f"Évolution de '{entree['nom'].capitalize()}' en France (1891-2000)",
            font=dict(family="Playfair Display, serif", size=16, color="#1a1a2e"),
        ),
        xaxis=dict(title="Décennie", tickangle=-30, tickfont=dict(size=11)),
        yaxis=dict(title="Naissances", gridcolor="#f0f0f0"),
        plot_bgcolor="white",
        paper_bgcolor="white",
        height=320,
        margin=dict(t=50, b=60, l=60, r=20),
        showlegend=False,
    )
    return fig


# ── Badge source ──────────────────────────────────────────────────────────────

BADGES = {
    "geneanet":          ('<span class="badge badge-geneanet"> Geneanet</span>', "Étymologie confirmée"),
    "soundex":           ('<span class="badge badge-soundex"> Phonétique</span>', "Correspondance sonore"),
    "levenshtein":       ('<span class="badge badge-lev"> Orthographe</span>', "Orthographe proche"),
    "mistral_generated": ('<span class="badge badge-mistral"> Mistral</span>', "Généré par IA"),
    "insee_only":        ('<span class="badge badge-insee"> INSEE</span>', "Données INSEE uniquement"),
}


# ── Carte de France par département ─────────────────────────────────────────

# Données géographiques simplifiées : nom → départements principaux
NOMS_REGIONS = {
    # Bretagne
    "le goff": ["29", "56", "22", "35"],
    "even": ["22", "29", "56"],
    "le bris": ["29", "56"],
    "le floch": ["29", "22"],
    # Alsace
    "meyer": ["67", "68"],
    "muller": ["67", "68"],
    "klein": ["67", "68"],
    # Sud-Ouest
    "duran": ["31", "32", "40", "64", "65"],
    "garcia": ["31", "33", "64"],
    # Normandie
    "leroy": ["76", "14", "50", "27", "61"],
    "leclerc": ["76", "14", "50"],
}

@st.cache_data
def charger_dept_data():
    """Charge les données départementales INSEE si disponibles."""
    try:
        import csv
        dept_data = {}
        with open("data/noms2008nat_txt.txt", encoding="latin-1") as f:
            reader = csv.DictReader(f, delimiter="	")
            for row in reader:
                nom = row["NOM"].strip().lower()
                freq = sum(int(v) for k, v in row.items() if k != "NOM")
                dept_data[nom] = freq
        return dept_data
    except:
        return {}


def graphique_carte(entree):
    """Crée une carte de France simplifiée montrant la concentration du nom."""
    nom = entree.get("nom_recherche", entree.get("nom", "")).lower()

    # Chercher les régions connues pour ce nom
    regions = None
    for cle, depts in NOMS_REGIONS.items():
        if cle in nom or nom in cle:
            regions = depts
            break

    # Si pas de données régionales, pas de carte
    if not regions:
        return None

    # Créer une carte simple avec les départements colorés
    # Utiliser une carte choroplèthe simplifiée
    labels = []
    values = []
    dept_names = {
        "29": "Finistère", "56": "Morbihan", "22": "Côtes-d'Armor",
        "35": "Ille-et-Vilaine", "67": "Bas-Rhin", "68": "Haut-Rhin",
        "31": "Haute-Garonne", "33": "Gironde", "76": "Seine-Maritime",
        "14": "Calvados", "50": "Manche", "64": "Pyrénées-Atlantiques",
        "27": "Eure", "61": "Orne", "32": "Gers", "40": "Landes",
        "65": "Hautes-Pyrénées",
    }

    for dept in regions:
        labels.append(dept_names.get(dept, dept))
        values.append(100 // len(regions))

    fig = go.Figure(go.Bar(
        x=labels,
        y=values,
        marker_color=["#1a1a2e"] * len(labels),
        text=[f"Dept {d}" for d in regions],
        hovertemplate="<b>%{x}</b><br>Concentration élevée<extra></extra>",
    ))

    fig.update_layout(
        title=dict(
            text=f" Concentration régionale de '{nom.capitalize()}'",
            font=dict(family="Playfair Display, serif", size=15, color="#1a1a2e"),
        ),
        xaxis_title="Département",
        yaxis_title="Concentration relative",
        plot_bgcolor="white",
        paper_bgcolor="white",
        height=280,
        margin=dict(t=50, b=60, l=40, r=20),
        showlegend=False,
    )
    return fig


# ── Affichage nom de famille ──────────────────────────────────────────────────

def afficher_nom(entree, index_noms):
    nom_affiche = entree.get("nom_recherche", entree["nom"]).capitalize()
    source      = entree.get("source", "inconnu")
    badge_html, badge_desc = BADGES.get(source, (source, ""))
    frequence   = entree.get("frequence", 0)
    variantes   = [v.capitalize() for v in entree.get("variantes", []) if v.lower() != nom_affiche.lower()]

    st.markdown(f"""
    <div class="result-card">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap;">
            <div>
                <div style="color:#888; font-size:0.9rem; margin-bottom:0.3rem;"> NOM DE FAMILLE</div>
                <div class="result-title">{nom_affiche}</div>
                <div>{badge_html} <span style="color:#888; font-size:0.8rem;">{badge_desc}</span></div>
            </div>
            {'<div style="text-align:right;"><div style="font-size:2rem;font-weight:700;color:#1a1a2e;font-family:Playfair Display,serif;">' + f"{frequence:,}" + '</div><div style="color:#888;font-size:0.8rem;">personnes en France</div></div>' if frequence > 0 else ''}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Variantes
    if variantes:
        st.markdown("**Variantes orthographiques :**")
        tags = " ".join(f'<span class="variante-tag">{v}</span>' for v in variantes[:10])
        st.markdown(tags, unsafe_allow_html=True)

    # Noms phonétiquement proches
    proches = trouver_proches(nom_affiche, index_noms)
    if proches:
        st.markdown("**Noms phonétiquement proches :**")
        tags = " ".join(f'<span class="variante-tag" style="background:#fff3f0;border-color:#f4b8a8;color:#8b3a2a;">🔊 {p.capitalize()}</span>' for p in proches)
        st.markdown(tags, unsafe_allow_html=True)

    # Origine
    texte = entree.get("origin_text", "").strip()
    if texte:
        st.markdown(f'<div class="origine-text"> {texte}</div>', unsafe_allow_html=True)

    # Graphique évolution
    fig = graphique_evolution(entree)
    if fig:
        st.plotly_chart(fig, use_container_width=True)

    # Carte de France par département
    carte = graphique_carte(entree)
    if carte:
        st.plotly_chart(carte, use_container_width=True)

    # Bouton partager
    nom_url = entree.get("nom_recherche", entree["nom"])
    lien = f"http://localhost:8501/?nom={nom_url}"
    if st.button(f" Partager '{nom_url.capitalize()}'", key=f"share_{nom_url}"):
        st.code(lien, language=None)
        st.success(" Lien copié ! Partagez cette URL pour accéder directement à ce nom.")


# ── Affichage prénom ──────────────────────────────────────────────────────────

def afficher_prenom(entree):
    nom_affiche = entree.get("nom_recherche", "")
    variantes   = entree.get("variants", [])
    genre       = entree.get("genre", "")
    icone       = "" if genre.lower() == "garcon" else "" if genre else ""

    if not nom_affiche and variantes:
        nom_affiche = variantes[0]

    autres = [v.capitalize() for v in variantes if v.lower() != nom_affiche.lower()]

    st.markdown(f"""
    <div class="result-card">
        <div style="display:flex; justify-content:space-between; align-items:flex-start;">
            <div>
                <div style="color:#888; font-size:0.9rem; margin-bottom:0.3rem;">{icone} PRÉNOM</div>
                <div class="result-title">{nom_affiche.capitalize()}</div>
                {f'<div style="color:#666;">{icone} {genre.capitalize()}</div>' if genre else ''}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if autres:
        st.markdown("**Variantes :**")
        tags = " ".join(f'<span class="variante-tag">{v}</span>' for v in autres[:8])
        st.markdown(tags, unsafe_allow_html=True)

    texte = entree.get("origin_text", "").strip()
    if texte:
        st.markdown(f'<div class="origine-text"> {texte}</div>', unsafe_allow_html=True)


# ── Historique des recherches ────────────────────────────────────────────────

def ajouter_historique(query: str):
    if "historique" not in st.session_state:
        st.session_state.historique = []
    if query and query not in st.session_state.historique:
        st.session_state.historique.insert(0, query)
        st.session_state.historique = st.session_state.historique[:5]


# ── Anecdote "Saviez-vous ?" ──────────────────────────────────────────────────

def saviez_vous(entree: dict) -> str:
    nom     = entree.get("nom_recherche", entree.get("nom", "")).capitalize()
    freq    = entree.get("frequence", 0)
    source  = entree.get("source", "")
    variantes = entree.get("variantes", [])

    if freq > 200000:
        return f" **{nom}** est l'un des noms les plus portés en France avec **{freq:,} personnes** !"
    elif freq > 100000:
        return f" **{nom}** est porté par plus de **{freq:,} personnes** en France."
    elif len(variantes) > 5:
        return f" **{nom}** possède **{len(variantes)} variantes orthographiques** recensées dans notre base."
    elif source == "soundex":
        correspond = entree.get("correspond_a", "")
        if correspond:
            return f" **{nom}** se prononce comme **{correspond.capitalize()}** — même origine étymologique !"
    elif freq > 0:
        return f" **{nom}** est porté par **{freq:,} personnes** en France."
    return ""


# ── Interface principale ──────────────────────────────────────────────────────

# Chargement silencieux
full_db, index_noms, index_prenoms = charger_donnees()

# Mode sombre dynamique
if 'mode_sombre' in dir() and mode_sombre:
    st.markdown("""
    <style>
        .main-title { color: #e2b96f !important; }
        .result-card { background: #1e1e2e !important; border-color: #333 !important; }
        .result-title { color: #e2b96f !important; }
        .origine-text { background: #2a2a3e !important; color: #ddd !important; border-left-color: #e2b96f; }
        .variante-tag { background: #2a2a4e !important; color: #9db4e8 !important; border-color: #444 !important; }
        .stApp { background-color: #0f0f1a !important; }
    </style>
    """, unsafe_allow_html=True)

# En-tête
st.markdown('<div class="main-title"> NLP-nameOrigins</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Explorez l\'origine étymologique des noms de famille et prénoms français</div>', unsafe_allow_html=True)

# Statistiques dans la sidebar (arrière-plan pour l'enseignant)
with st.sidebar:
    st.markdown("##  Base de données")
    st.caption("Informations techniques — arrière-plan")
    st.metric("Noms de famille", "218 982")
    st.metric("Prénoms", "11 455")
    st.metric("Taux de couverture", "96.2%")
    st.metric("Noms composés fusionnés", "2 688")
    st.metric("Groupes Union-Find", "1 030")
    st.metric("F1-score NER", "69.2%")
    st.markdown("---")
    st.markdown("**Sources :**")
    st.markdown("- Geneanet (étymologie)")
    st.markdown("- INSEE (fréquences)")
    st.markdown("- prenoms.com (prénoms)")
    st.markdown("---")
    st.markdown("**Techniques NLP :**")
    st.markdown("- Union-Find (clustering)")
    st.markdown("- Soundex (phonétique)")
    st.markdown("- Levenshtein (orthographe)")
    st.markdown("- Mistral AI (résumés + NER)")
    st.markdown("---")
    mode_sombre = st.toggle(" Mode sombre", value=False)

# ── Onglet 1 : Recherche ─────────────────────────────────────────────────────
tab_recherche, tab_comparer = st.tabs([" Recherche", " Comparer deux noms"])

with tab_recherche:

    # Barre de recherche
    col_l, col_c, col_r = st.columns([1, 4, 1])
    with col_c:
        query = st.text_input(
            label="recherche",
            placeholder="  Tapez un nom, prénom ou les deux...",
            label_visibility="collapsed",
            key="search_input",
        )
        st.markdown('<div class="search-hint">Exemples : <b>Martin</b> · <b>Jean</b> · <b>Jean Martin</b> · <b>Le Goff</b> · <b>Durant</b></div>', unsafe_allow_html=True)

    # Boutons exemples
    st.markdown("<br>", unsafe_allow_html=True)
    col_ex = st.columns(6)
    exemples = ["Martin", "Jean", "Dupont", "Marie", "Le Goff", "Durant"]
    for i, ex in enumerate(exemples):
        if col_ex[i].button(ex, key=f"ex_{ex}", use_container_width=True):
            query = ex.lower()

    # Historique des recherches
    if "historique" in st.session_state and st.session_state.historique:
        with st.expander(" Recherches récentes", expanded=False):
            cols_hist = st.columns(len(st.session_state.historique))
            for i, h in enumerate(st.session_state.historique):
                if cols_hist[i].button(h.capitalize(), key=f"hist_{i}"):
                    query = h

    # Traitement
    if query:
        ajouter_historique(query.strip().lower())
        mots   = query.strip().split()
        trouve = False

        st.markdown("---")

        if len(mots) == 1:
            mot = mots[0]
            res_nom    = rechercher(mot, index_noms)
            res_prenom = rechercher(mot, index_prenoms)

            if res_nom:
                # Saviez-vous ?
                anecdote = saviez_vous(res_nom)
                if anecdote:
                    st.info(anecdote)
                afficher_nom(res_nom, index_noms)
                # Suggestions : noms de la même famille
                proches = trouver_proches(mot, index_noms, n=6)
                if proches:
                    st.markdown("####  Noms de la même famille")
                    cols_p = st.columns(len(proches))
                    for i, p in enumerate(proches):
                        if cols_p[i].button(p.capitalize(), key=f"proche_{p}"):
                            query = p
                trouve = True

            if res_prenom:
                afficher_prenom(res_prenom)
                trouve = True

            if not trouve:
                st.error(f" **'{mot}'** non trouvé dans la base.")
                st.info(" Vérifiez l'orthographe ou essayez une variante.")

        elif len(mots) == 2:
            # Essai 1 : prénom + nom
            res_prenom = rechercher(mots[0], index_prenoms)
            res_nom    = rechercher(mots[1], index_noms)

            if res_prenom and res_nom:
                st.markdown(f"### Résultats pour *{mots[0].capitalize()} {mots[1].capitalize()}*")
                anecdote = saviez_vous(res_nom)
                if anecdote:
                    st.info(anecdote)
                col_a, col_b = st.columns(2)
                with col_a:
                    afficher_prenom(res_prenom)
                with col_b:
                    afficher_nom(res_nom, index_noms)
                trouve = True

            # Essai 2 : nom + prénom
            if not trouve:
                res_nom    = rechercher(mots[0], index_noms)
                res_prenom = rechercher(mots[1], index_prenoms)
                if res_nom and res_prenom:
                    st.markdown(f"### Résultats pour *{mots[1].capitalize()} {mots[0].capitalize()}*")
                    anecdote = saviez_vous(res_nom)
                    if anecdote:
                        st.info(anecdote)
                    col_a, col_b = st.columns(2)
                    with col_a:
                        afficher_prenom(res_prenom)
                    with col_b:
                        afficher_nom(res_nom, index_noms)
                    trouve = True

            # Essai 3 : chaque mot seul
            if not trouve:
                for mot in mots:
                    r_n = rechercher(mot, index_noms)
                    r_p = rechercher(mot, index_prenoms)
                    if r_n:
                        afficher_nom(r_n, index_noms); trouve = True
                    if r_p:
                        afficher_prenom(r_p); trouve = True

            if not trouve:
                st.error(f" **'{query}'** non trouvé.")
                st.info(" Essayez avec un seul mot à la fois.")
        else:
            st.warning(" Entrez un prénom, un nom, ou les deux séparés par un espace.")


# ── Onglet 2 : Comparer deux noms ────────────────────────────────────────────

with tab_comparer:
    st.markdown("###  Comparez deux noms de famille")
    st.markdown("Entrez deux noms pour voir leurs différences et similarités.")

    col1, col2 = st.columns(2)
    with col1:
        nom1 = st.text_input("Premier nom", placeholder="Ex: Durand", key="comp1")
    with col2:
        nom2 = st.text_input("Deuxième nom", placeholder="Ex: Durant", key="comp2")

    if nom1 and nom2:
        res1 = rechercher(nom1, index_noms)
        res2 = rechercher(nom2, index_noms)

        if res1 and res2:
            # Comparaison côte à côte
            col_a, col_b = st.columns(2)
            with col_a:
                afficher_nom(res1, index_noms)
            with col_b:
                afficher_nom(res2, index_noms)

            # Analyse des similarités
            st.markdown("---")
            st.markdown("###  Analyse comparative")

            # Distance Levenshtein
            from Levenshtein import distance as lev_dist
            dist = lev_dist(nom1.lower(), nom2.lower())

            # Soundex
            code1 = jellyfish.soundex(nom1.upper())
            code2 = jellyfish.soundex(nom2.upper())
            meme_son = code1 == code2

            # Fréquences
            freq1 = res1.get("frequence", 0)
            freq2 = res2.get("frequence", 0)

            col_s1, col_s2, col_s3 = st.columns(3)
            with col_s1:
                st.metric("Distance orthographique", dist,
                    help="0 = identiques, 1 = 1 lettre de différence")
            with col_s2:
                st.metric("Même prononciation ?",
                    " Oui" if meme_son else " Non",
                    help=f"Soundex: {code1} vs {code2}")
            with col_s3:
                if freq1 > 0 and freq2 > 0:
                    st.metric("Plus fréquent",
                        nom1.capitalize() if freq1 > freq2 else nom2.capitalize(),
                        delta=f"{abs(freq1-freq2):,} personnes de différence")

            # Même origine ?
            orig1 = res1.get("origin_text", "")[:100]
            orig2 = res2.get("origin_text", "")[:100]
            if orig1 and orig2:
                if meme_son or dist <= 2:
                    st.success(f" **{nom1.capitalize()}** et **{nom2.capitalize()}** semblent être des variantes du même patronyme !")
                else:
                    st.warning(f" **{nom1.capitalize()}** et **{nom2.capitalize()}** ont des origines probablement différentes.")

        else:
            if not res1:
                st.error(f" '{nom1}' non trouvé.")
            if not res2:
                st.error(f" '{nom2}' non trouvé.")

# Footer
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("""
<div style='text-align:center; color:#aaa; font-size:0.8rem; border-top:1px solid #eee; padding-top:1rem;'>
     NLP-nameOrigins &nbsp;·&nbsp; Sources : Geneanet · INSEE · prenoms.com &nbsp;·&nbsp;
    Techniques : Union-Find · Soundex · Levenshtein · Mistral AI
</div>
""", unsafe_allow_html=True)