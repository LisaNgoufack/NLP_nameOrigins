#  NLP-nameOrigins

> Base étymologique des noms de famille et prénoms français

![Python](https://img.shields.io/badge/Python-3.10+-blue) ![Streamlit](https://img.shields.io/badge/Streamlit-1.x-red) ![Mistral](https://img.shields.io/badge/Mistral-AI-orange) ![INSEE](https://img.shields.io/badge/Data-INSEE-green)

---

##  Description

NLP-nameOrigins est un projet de traitement automatique du langage naturel qui construit une base de données complète des noms de famille et prénoms français avec leurs variantes orthographiques, phonétiques et leurs origines étymologiques.

Le projet combine plusieurs techniques NLP :
- **Union-Find** → regrouper les noms partageant la même origine
- **Soundex** → détecter les variantes phonétiques
- **Levenshtein** → détecter les variantes orthographiques
- **Mistral AI** → résumer les textes et extraire les variantes cachées (NER)

---

##  Problématique

> *Comment identifier automatiquement les variantes d'un nom de famille français et enrichir une base étymologique incomplète ?*

Un même nom peut s'écrire différemment selon les régions et les époques :

| Variantes | Origine |
|---|---|
| Durand / Durant / Duran | Germanique *dur* (dur, résistant) |
| Lefebre / Lefebvre / Lefeuvre | Latin *faber* (forgeron) |
| Le Goff / Legoff / Le-Goff | Breton *gof* (forgeron) |

---

##  Structure du projet

```
NLP-nameOrigins/
├── data/
│   ├── names.json                     ← 21 777 noms de famille (fourni)
│   ├── origins.json                   ← 20 981 textes étymologiques (fourni)
│   └── noms2008nat_txt.txt            ← 218 982 noms INSEE
├── output/                            ← Fichiers générés par le pipeline
│   ├── clusters.json                  ← groupes Union-Find (étape 1)
│   ├── final_database.json            ← base Geneanet résumée (étape 2)
│   ├── insee_database.json            ← base INSEE enrichie (étape 3)
│   ├── full_database.json             ← base avec matches phonétiques (étape 4)
│   ├── nouveaux_noms.json             ← variantes extraites NER (étape 5)
│   └── full_database_v2.json          ← base finale normalisée (étape 6)
├── src/                               ← Architecture modulaire
│   ├── config.py                      ← Configuration centralisée
│   ├── pipeline.py                    ← Orchestrateur avec caching intelligent
│   ├── models/
│   │   └── name_input.py              ← Modèle de données
│   ├── services/
│   │   ├── clustering_service.py      ← Union-Find
│   │   ├── summarization_service.py   ← Résumés Mistral AI
│   │   ├── insee_service.py           ← Intégration INSEE
│   │   ├── phonetic_service.py        ← Soundex + Levenshtein
│   │   ├── extraction_service.py      ← Extraction NER
│   │   ├── normalization_service.py   ← Noms composés + normalisation
│   │   └── variant_extraction_service.py ← Extraction variantes cachées
│   ├── utils/
│   │   ├── file_utils.py              ← Gestion JSON
│   │   ├── text_utils.py              ← Normalisation texte
│   │   └── prompt_loader.py           ← Chargement prompts
│   └── prompts/
│       ├── summarization_system.txt   ← Prompt système Mistral
│       └── summarization_user.txt     ← Prompt utilisateur Mistral
├── main.py                            ← Point d'entrée unique du pipeline
├── app.py                             ← Interface Streamlit
├── .env                               ← Clé API Mistral
├── .gitignore
└── requirements.txt
```

---

##  Installation

### Prérequis
- Python 3.10+
- pip
- Clé API Mistral → [console.mistral.ai](https://console.mistral.ai)

### Étapes

**1. Cloner le projet**
```bash
git clone https://github.com/votre-username/NLP-nameOrigins
cd NLP-nameOrigins
```

**2. Créer l'environnement virtuel**
```bash
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Linux/Mac
```

**3. Installer les dépendances**
```bash
pip install -r requirements.txt
```

**4. Configurer la clé API**

Créez un fichier `.env` à la racine :
```
MISTRAL_API_KEY=votre_cle_api_ici
```

**5. Placer les données**

Copiez `names.json`, `origins.json` et `noms2008nat_txt.txt` dans le dossier `data/`.

---

##  Utilisation

### Pipeline complet

**Exécuter toutes les étapes :**
```bash
python main.py
```

**Exécuter des étapes spécifiques :**
```bash
python main.py --steps 1,2,3     # Seulement clustering, summarization, insee
python main.py --steps 4         # Seulement phonétique
```

**Forcer la ré-exécution (bypass cache) :**
```bash
python main.py --force           # Re-génère tous les fichiers output/
```

**Options disponibles :**
- `--steps` : Liste d'étapes à exécuter (1-6), séparées par des virgules
- `--force` : Force la régénération même si les fichiers existent déjà

**Les 6 étapes du pipeline :**
1. **Clustering** → Regroupe les noms par origine (Union-Find)
2. **Summarization** → Résume les textes étymologiques avec Mistral AI
3. **INSEE** → Intègre la base INSEE avec fréquences
4. **Phonétique** → Détecte variantes Soundex + Levenshtein
5. **Extraction** → Extrait nouveaux noms des textes (NER)
6. **Normalisation** → Fusionne noms composés et variantes

### Interface web (Streamlit)
```bash
streamlit run app.py
```
Ouvre automatiquement `http://localhost:8501`

---

##  Sources de données

| Source | Méthode | Résultat |
|---|---|---|
| `names.json` + `origins.json` | Fourni (Geneanet) | 21 777 noms + 20 981 textes |
| prenoms.com | Scraping BeautifulSoup | 11 455 prénoms |
| INSEE `noms2008nat_txt.txt` | Téléchargement CSV | 218 982 noms + fréquences décennales |

---

##  Techniques NLP utilisées

| Technique | Outil | Usage | Résultat |
|---|---|---|---|
| Union-Find | Python natif | Regrouper variantes par origin_id | 1 030 groupes |
| Soundex | `jellyfish` | Encodage phonétique | 83.8% couverts |
| Levenshtein | `python-Levenshtein` | Distance orthographique | 4.6% supplémentaires |
| NER Regex | Python `re` | Extraire noms dans textes | Précision 51% |
| NER Combiné | Regex + Mistral | Validation par LLM | F1 = 69.2% |
| Résumé | Mistral AI | Fusionner textes d'origine | 372 résumés |
| Normalisation | Python natif | Noms composés | 2 688 fusions |
| Variantes régionales | Soundex + Mistral | Validation régionale | 31 groupes confirmés |

---

##  Architecture

### Design Pattern

Le projet utilise une **architecture modulaire orientée objet** avec :

- **Point d'entrée unique** : `main.py` orchestre tout le pipeline
- **Configuration centralisée** : `src/config.py` gère variables d'environnement et paramètres
- **Services indépendants** : Chaque étape = 1 classe dans `src/services/`
- **Caching intelligent** : Skip automatique si le fichier output existe déjà
- **Prompts externalisés** : Fichiers `.txt` modifiables sans toucher au code

### Pipeline orchestrator

La classe `NLPNameOriginsPipeline` (dans `src/pipeline.py`) :
- Charge la configuration une seule fois
- Exécute les services dans l'ordre correct
- Détecte si un fichier output existe → **skip automatique**
- Force la ré-exécution avec `--force`
- Gère les dépendances entre étapes

### Avantages

✅ **Maintenance facile** : Modifier un service n'affecte pas les autres  
✅ **Testabilité** : Chaque service peut être testé indépendamment  
✅ **Performance** : Le caching évite de relancer les étapes longues (Mistral = 15-30 min)  
✅ **Flexibilité** : Exécuter seulement certaines étapes avec `--steps`  
✅ **Configuration** : Modifier les prompts Mistral sans toucher au code Python

---

##  Performances

### Couverture de la base

| Métrique | Valeur |
|---|---|
| Noms de famille | 218 982 |
| Prénoms | 11 455 |
| Taux de couverture | **96.2%** |
| Noms composés fusionnés | 2 688 |
| Groupes de variantes (Union-Find) | 1 030 |
| Variantes régionales confirmées | 31 |

### Évaluation NER (sur 200 textes)

| Méthode | Précision | Rappel | F1-score |
|---|---|---|---|
| Regex + majuscules seul | 51.0% | 60.0% | 55.1% |
| **Combinée (Regex + Mistral)** | **86.9%** | **57.5%** | **69.2%** |
| Mistral seul *(référence)* | 100% | 100% | 100% |

---

##  Interface Streamlit

L'application web offre :
-  **Recherche** par nom, prénom ou nom complet (`Jean Martin`)
-  **Origine étymologique** avec texte détaillé
-  **Variantes** orthographiques et phonétiques
-  **Graphique d'évolution** par décennie (INSEE 1891-2000)
-  **Noms phonétiquement proches** (Soundex)
-  **Comparaison** de deux noms côte à côte
-  **Historique** des 5 dernières recherches
-  **Mode sombre** (sidebar)
-  **Statistiques** techniques (sidebar, pour présentation)

---

##  Dépendances

```
anthropic>=0.40.0    # Client API Anthropic (optionnel)
requests>=2.31.0     # Requêtes HTTP
beautifulsoup4>=4.12.0  # Parsing HTML
python-dotenv>=1.0.0 # Variables d'environnement
openai>=1.0.0        # Client API Mistral (compatible OpenAI)
python-dotenv        # Variables d'environnement
requests             # Requêtes HTTP (scraping)
beautifulsoup4       # Parsing HTML (scraping)
jellyfish            # Soundex et phonétique
python-Levenshtein   # Distance de Levenshtein
streamlit            # Interface web
plotly               # Graphiques interactifs
pandas               # Manipulation de données
```

---

##  Perspectives d'amélioration

- ✅ **Architecture modulaire** : Refactoring complet en OOP avec services indépendants
- ✅ **Caching intelligent** : Système de skip automatique pour éviter re-calculs
- ✅ **Prompts externalisés** : Fichiers `.txt` modifiables à la volée
- 🔲 Intégrer les données INSEE post-2000 pour l'évolution jusqu'en 2025
- 🔲 Ajouter une vraie carte choroplèthe par département
- 🔲 Étendre l'évaluation NER à plus de 200 textes
- 🔲 Ajouter des noms étrangers (espagnols, italiens, arabes...)
- 🔲 Déployer l'application sur Streamlit Cloud

---

##  Auteur

Projet réalisé dans le cadre d'un TP de NLP — 2026

**Sources :** Geneanet · INSEE · prenoms.com  
**Techniques :** Union-Find · Soundex · Levenshtein · Mistral AI