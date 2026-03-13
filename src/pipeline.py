"""
Pipeline principal orchestrant toutes les étapes du projet.
"""
from src.config import Config
from src.services.clustering import ClusteringService
from src.services.variant_extraction import VariantExtractionService
from src.services.summarization import SummarizationService
from src.services.insee_service import InseeService
from src.services.phonetic_service import PhoneticService
from src.services.extraction_service import ExtractionService
from src.services.normalization_service import NormalizationService


class NLPNameOriginsPipeline:
    """Pipeline principal du projet NLP-nameOrigins."""
    
    def __init__(self, config: Config):
        self.config = config
        print("=" * 70)
        print(">> NLP-nameOrigins Pipeline")
        print("=" * 70)
        
        # S'assurer que le dossier output existe
        self.config.ensure_output_dir()
    
    def run(self, steps: list = None, force_regenerate: bool = False):
        """
        Exécute le pipeline complet ou des étapes spécifiques.
        
        Args:
            steps: Liste des étapes à exécuter (None = toutes)
            force_regenerate: Force la régénération même si les fichiers existent
        """
        if steps is None:
            # Par défaut, on exécute toutes les étapes implémentées
            steps = ['clustering', 'variants', 'summary', 'insee', 
                     'phonetic', 'extraction', 'normalization']
        
        results = {}
        
        try:
            if 'clustering' in steps:
                results['clusters'] = self._run_step(
                    'clustering',
                    self._run_clustering,
                    self.config.CLUSTERS_OUTPUT,
                    force_regenerate
                )
            
            if 'variants' in steps:
                results['enriched'] = self._run_step(
                    'variants',
                    self._run_variant_extraction,
                    self.config.ENRICHED_OUTPUT,
                    force_regenerate
                )
            
            if 'summary' in steps:
                results['final'] = self._run_step(
                    'summary',
                    self._run_summarization,
                    self.config.FINAL_DATABASE,
                    force_regenerate
                )
            
            if 'insee' in steps:
                results['insee'] = self._run_step(
                    'insee',
                    self._run_insee_integration,
                    self.config.INSEE_DATABASE,
                    force_regenerate
                )
            
            if 'phonetic' in steps:
                results['phonetic'] = self._run_step(
                    'phonetic',
                    self._run_phonetic_matching,
                    self.config.FULL_DATABASE,
                    force_regenerate
                )
            
            if 'extraction' in steps:
                results['extraction'] = self._run_step(
                    'extraction',
                    self._run_name_extraction,
                    self.config.NOUVEAUX_NOMS,
                    force_regenerate
                )
            
            if 'normalization' in steps:
                results['normalization'] = self._run_step(
                    'normalization',
                    self._run_normalization,
                    self.config.FULL_DATABASE_V2,
                    force_regenerate
                )
            
            print("\n" + "=" * 70)
            print("[OK] Pipeline termine avec succes !")
            print("=" * 70)
            
            return results
            
        except Exception as e:
            print(f"\n[ERREUR] Erreur dans le pipeline : {e}")
            raise
    
    def _run_step(self, step_name: str, step_function, output_path: str, force: bool):
        """
        Exécute une étape du pipeline avec vérification du cache.
        
        Args:
            step_name: Nom de l'étape pour l'affichage
            step_function: Fonction à exécuter
            output_path: Chemin du fichier de sortie
            force: Force la régénération
        
        Returns:
            Résultat de l'étape (chargé ou généré)
        """
        from src.utils.file_utils import file_exists, load_json
        
        # Vérifier si le fichier existe et si on ne force pas
        if file_exists(output_path) and not force:
            print(f"\n[SKIP] Etape '{step_name}' : donnees deja presentes")
            print(f"   Fichier : {output_path}")
            data = load_json(output_path)
            print(f"   {len(data)} entrees reutilisees")
            return data
        
        # Sinon, exécuter l'étape
        if force:
            print(f"\n[FORCE] Regeneration de l'etape '{step_name}'")
        
        return step_function()
    
    def _run_clustering(self):
        """Exécute l'étape 1 : Clustering."""
        service = ClusteringService(self.config)
        return service.run()
    
    def _run_variant_extraction(self):
        """Exécute l'étape 1bis : Extraction des variantes cachées."""
        service = VariantExtractionService(self.config)
        return service.run()
    
    def _run_summarization(self):
        """Exécute l'étape 2 : Résumé des textes avec Mistral."""
        service = SummarizationService(self.config)
        return service.run()
    
    def _run_insee_integration(self):
        """Exécute l'étape 4 : Intégration des données INSEE."""
        service = InseeService(self.config)
        return service.run()
    
    def _run_phonetic_matching(self):
        """Exécute l'étape 5 : Correspondance phonétique."""
        service = PhoneticService(self.config)
        return service.run()
    
    def _run_name_extraction(self):
        """Exécute l'étape 6 : Extraction des noms dans les textes."""
        service = ExtractionService(self.config)
        return service.run()
    
    def _run_normalization(self):
        """Exécute l'étape 7 : Normalisation des noms composés."""
        service = NormalizationService(self.config)
        return service.run()