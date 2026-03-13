"""
Pipeline principal orchestrant toutes les étapes du projet.
"""
from src.config import Config
from src.services.clustering import ClusteringService


class NLPNameOriginsPipeline:
    """Pipeline principal du projet NLP-nameOrigins."""
    
    def __init__(self, config: Config):
        self.config = config
        print("=" * 70)
        print("🚀 NLP-nameOrigins Pipeline")
        print("=" * 70)
        
        # S'assurer que le dossier output existe
        self.config.ensure_output_dir()
    
    def run(self, steps: list = None):
        """
        Exécute le pipeline complet ou des étapes spécifiques.
        
        Args:
            steps: Liste des étapes à exécuter (None = toutes)
                   Valeurs possibles: ['clustering', 'variants', 'summary', 
                                       'prenoms', 'insee', 'phonetic', 
                                       'extraction', 'normalization']
        """
        if steps is None:
            steps = ['clustering']  # Pour l'instant, on n'a que le clustering
        
        results = {}
        
        try:
            if 'clustering' in steps:
                results['clusters'] = self._run_clustering()
            
            # TODO: Ajouter les autres étapes ici au fur et à mesure
            # if 'variants' in steps:
            #     results['variants'] = self._run_variant_extraction()
            
            print("\n" + "=" * 70)
            print("✅ Pipeline terminé avec succès !")
            print("=" * 70)
            
            return results
            
        except Exception as e:
            print(f"\n❌ Erreur dans le pipeline : {e}")
            raise
    
    def _run_clustering(self):
        """Exécute l'étape 1 : Clustering."""
        service = ClusteringService(self.config)
        return service.run()