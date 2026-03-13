"""
Configuration centrale du projet NLP-nameOrigins.
"""
import os
from pathlib import Path
from dotenv import load_dotenv


# Charger les variables d'environnement
load_dotenv()


class Config:
    """Configuration globale du projet."""
    
    # ── Chemins des dossiers ──
    BASE_DIR = Path(__file__).parent.parent
    DATA_DIR = BASE_DIR / "data"
    OUTPUT_DIR = BASE_DIR / "output"
    
    # ── Fichiers d'entrée (data/) ──
    NAMES_FILE = str(DATA_DIR / "names.json")
    ORIGINS_FILE = str(DATA_DIR / "origins.json")
    INSEE_FILE = str(DATA_DIR / "noms2008nat_txt.txt")
    
    # ── Fichiers de sortie (output/) ──
    CLUSTERS_OUTPUT = str(OUTPUT_DIR / "clusters.json")
    ENRICHED_OUTPUT = str(OUTPUT_DIR / "enriched_database.json")
    FINAL_DATABASE = str(OUTPUT_DIR / "final_database.json")
    PRENOMS_RAW = str(OUTPUT_DIR / "prenoms_raw.json")
    PRENOMS_DATABASE = str(OUTPUT_DIR / "prenoms_database.json")
    INSEE_DATABASE = str(OUTPUT_DIR / "insee_database.json")
    FULL_DATABASE = str(OUTPUT_DIR / "full_database.json")
    NOUVEAUX_NOMS = str(OUTPUT_DIR / "nouveaux_noms.json")
    EVALUATION = str(OUTPUT_DIR / "evaluation.json")
    FULL_DATABASE_V2 = str(OUTPUT_DIR / "full_database_v2.json")
    
    # ── API Configuration ──
    MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
    MISTRAL_BASE_URL = "https://api.mistral.ai/v1"
    MISTRAL_MODEL = "mistral-large-latest"
    
    # ── Constantes de scraping ──
    PRENOMS_BASE_URL = "https://www.prenoms.com"
    PRENOMS_NB_SITEMAPS = 8
    SCRAPING_DELAY = 0.3  # secondes entre requêtes
    
    # ── Constantes phonétiques ──
    LEVENSHTEIN_THRESHOLD = 2
    
    # ── Options d'exécution ──
    USE_MISTRAL_FOR_SUMMARY = True
    USE_MISTRAL_FOR_EXTRACTION = False
    USE_MISTRAL_FOR_PHONETIC = False
    PRENOMS_LIMIT = None  # None = tous les prénoms, ou un nombre pour tester
    
    @classmethod
    def ensure_output_dir(cls):
        """Crée le dossier output s'il n'existe pas."""
        cls.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def has_mistral_key(cls) -> bool:
        """Vérifie si la clé API Mistral est configurée."""
        return cls.MISTRAL_API_KEY is not None and cls.MISTRAL_API_KEY != ""