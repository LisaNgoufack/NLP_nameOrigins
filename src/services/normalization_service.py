"""
Service pour la normalisation des noms composés et variantes régionales (Étape 7).
"""
from collections import defaultdict
from openai import OpenAI
from src.utils.file_utils import load_json, save_json
from src.utils.text_utils import normaliser_compose


class NormalizationService:
    """Service pour normaliser les noms composés et variantes régionales."""
    
    def __init__(self, config):
        self.config = config
        self.input_path = config.FULL_DATABASE
        self.output_path = config.FULL_DATABASE_V2
        
        # Client Mistral (optionnel)
        self.use_mistral = config.has_mistral_key()
        if self.use_mistral:
            self.client = OpenAI(
                api_key=config.MISTRAL_API_KEY,
                base_url=config.MISTRAL_BASE_URL
            )
    
    def run(self) -> list:
        """
        Exécute la normalisation.
        
        Returns:
            Base de données normalisée
        """
        print("[ETAPE 7] Normalisation des noms composes et variantes...")
        
        # Chargement
        full_db = load_json(self.input_path)
        print(f"   {len(full_db)} noms charges")
        
        # Partie 1 : Noms composés
        full_db = self._normaliser_composes(full_db)
        
        # Partie 2 : Variantes régionales (optionnel avec Mistral)
        if self.use_mistral:
            print("   [INFO] Detection variantes regionales avec Mistral (desactive)")
            # Trop coûteux, on skip pour l'instant
        
        # Sauvegarde
        save_json(full_db, self.output_path)
        print(f"[OK] {len(full_db)} noms sauvegardes dans {self.output_path}")
        
        return full_db
    
    def _normaliser_composes(self, full_db: list) -> list:
        """Normalise les noms composés."""
        print("   Partie 1 : Detection des noms composes...")
        
        # Construire un index : forme normalisée → liste d'entrées
        index_normalise = defaultdict(list)
        for entree in full_db:
            forme = normaliser_compose(entree["nom"])
            index_normalise[forme].append(entree)
        
        # Trouver les groupes de noms composés
        groupes_composes = {
            forme: entrees
            for forme, entrees in index_normalise.items()
            if len(entrees) > 1
        }
        
        print(f"   {len(groupes_composes)} groupes de noms composes trouves")
        
        # Afficher quelques exemples
        if groupes_composes:
            print("   Exemples :")
            for forme, entrees in list(groupes_composes.items())[:5]:
                noms = [e["nom"] for e in entrees]
                print(f"     {forme:20} -> {noms}")
        
        # Fusionner les groupes
        fusions = 0
        entrees_a_supprimer = set()
        
        for forme, entrees in groupes_composes.items():
            if len(entrees) < 2:
                continue
            
            # Prendre l'entrée avec la fréquence la plus haute
            reference = max(entrees, key=lambda e: e.get("frequence", 0))
            
            # Fusionner les variantes et fréquences
            toutes_variantes = set(reference.get("variantes", [reference["nom"]]))
            freq_totale = reference.get("frequence", 0)
            
            for entree in entrees:
                if entree is reference:
                    continue
                toutes_variantes.update(entree.get("variantes", [entree["nom"]]))
                freq_totale += entree.get("frequence", 0)
                entrees_a_supprimer.add(id(entree))
            
            reference["variantes"] = sorted(list(toutes_variantes))
            reference["frequence"] = freq_totale
            fusions += 1
        
        # Supprimer les doublons
        full_db = [e for e in full_db if id(e) not in entrees_a_supprimer]
        
        print(f"   {fusions} groupes fusionnes")
        print(f"   {len(full_db)} entrees restantes")
        
        return full_db