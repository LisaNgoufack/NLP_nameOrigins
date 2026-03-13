"""
Point d'entrée principal du projet NLP-nameOrigins.

Usage:
    python main.py                          # Exécute tout le pipeline
    python main.py --steps clustering       # Exécute uniquement le clustering
    python main.py --steps clustering summary  # Exécute plusieurs étapes
"""
import argparse
from src.config import Config
from src.pipeline import NLPNameOriginsPipeline


def main():
    """Fonction principale."""

    # cree un parser d'arguments pour permettre de choisir les étapes à exécuter
    parser = argparse.ArgumentParser(
        description="NLP-nameOrigins : Base de données des noms de famille français"
    )
    
    # permet de choisir les étapes à exécuter (clustering, 
    # variants, summary, prenoms, insee, 
    # phonetic, extraction, normalization)
    # par défaut, toutes les étapes sont exécutées
    parser.add_argument(
        '--steps',
        nargs='*',
        choices=['clustering', 'variants', 'summary', 'prenoms', 
                 'insee', 'phonetic', 'extraction', 'normalization', 'all'],
        default=['all'],
        help='Étapes à exécuter (par défaut: all)'
    )
    
    # option pour limiter le nombre de prénoms à scraper (pour tests)
    # exemple d'utilisation: python main.py --steps prenoms --prenoms-limit 100
    parser.add_argument(
        '--prenoms-limit',
        type=int,
        default=None,
        help='Limite de prénoms à scraper (pour tests)'
    )

    parser.add_argument(
    '--force',
    action='store_true',
    help='Force la regeneration des donnees meme si elles existent'
    )
    
    args = parser.parse_args()
    
    # Configuration
    config = Config()
    if args.prenoms_limit:
        config.PRENOMS_LIMIT = args.prenoms_limit
    
    # Lancer le pipeline
    steps = None if 'all' in args.steps else args.steps
    pipeline = NLPNameOriginsPipeline(config)
    # pipeline.run(steps=steps)
    pipeline.run(steps=steps, force_regenerate=args.force)


if __name__ == "__main__":
    main()