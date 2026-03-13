"""
Service pour l'extraction des variantes cachées (Étape 1bis).
"""
import re
from collections import defaultdict
from src.utils.file_utils import load_json, save_json
from src.utils.text_utils import nettoyer_nom, est_nom_valide


class VariantExtractionService:
    """Service pour extraire les variantes cachées dans les textes."""
    
    # Patterns pour détecter les variantes dans les textes
    PATTERNS = [
        r'[Vv]ariantes?\s*:\s*([^.;]+)',
        r'[Ff]ormes?\s*voisines?\s*:\s*([^.;]+)',
        r'[Ff]ormes?\s*:\s*([^.;]+)',
        r'[Dd]iminutifs?\s*:\s*([^.;]+)',
        r'[Aa]ussi\s+(?:écrit|orthographié)\s+([A-ZÀ-Ÿa-zà-ÿ\-]+)',
        r'[Éé]galement\s+(?:écrit|orthographié)\s+([A-ZÀ-Ÿa-zà-ÿ\-]+)',
    ]
    
    def __init__(self, config):
        self.config = config
        self.clusters_path = config.CLUSTERS_OUTPUT
        self.output_path = config.ENRICHED_OUTPUT
    
    def run(self) -> list:
        """
        Exécute l'extraction des variantes cachées.
        
        Returns:
            Liste des clusters enrichis avec variantes
        """
        print("🔄 ÉTAPE 1bis : Extraction des variantes cachées...")
        
        # Chargement
        clusters = load_json(self.clusters_path)
        print(f"   {len(clusters)} clusters chargés")
        
        # Extraction
        variantes_trouvees = self._extract_hidden_variants(clusters)
        print(f"   {len(variantes_trouvees)} variantes cachées trouvées")
        
        # Enrichissement
        enriched_clusters = self._enrich_clusters(clusters, variantes_trouvees)
        
        # Sauvegarde
        save_json(enriched_clusters, self.output_path)
        print(f"✅ {len(enriched_clusters)} clusters enrichis sauvegardés dans {self.output_path}")
        
        return enriched_clusters
    
    def _extract_hidden_variants(self, clusters: list) -> list:
        """Extrait les variantes mentionnées dans les textes."""
        # Ensemble des noms déjà connus
        noms_connus = set()
        for cluster in clusters:
            for variant in cluster["variants"]:
                noms_connus.add(variant.lower())
        
        # Extraire les variantes cachées
        variantes_cachees = []
        origin_to_names = defaultdict(list)
        
        for cluster in clusters:
            for origin_id, text in cluster["origin_texts"].items():
                noms = self._extraire_noms_du_texte(text)
                for nom in noms:
                    if nom not in noms_connus:
                        variantes_cachees.append({
                            "nom": nom,
                            "origin_id": origin_id,
                            "cluster_variants": cluster["variants"]
                        })
                        origin_to_names[origin_id].append(nom)
        
        return variantes_cachees
    
    def _extraire_noms_du_texte(self, text: str) -> list[str]:
        """
        Extrait tous les noms mentionnés dans un texte d'origine.
        
        Args:
            text: Texte d'origine
            
        Returns:
            Liste de noms extraits
        """
        noms_trouves = []
        
        for pattern in self.PATTERNS:
            for match in re.finditer(pattern, text):
                partie = match.group(1)
                candidats = re.split(r'[,;]', partie)
                
                for candidat in candidats:
                    nom = nettoyer_nom(candidat)
                    if est_nom_valide(nom):
                        noms_trouves.append(nom)
        
        return noms_trouves
    
    def _enrich_clusters(self, clusters: list, variantes: list) -> list:
        """Ajoute les variantes cachées aux clusters correspondants."""
        # Index pour retrouver rapidement un cluster par origin_id
        origin_to_cluster = {}
        for i, cluster in enumerate(clusters):
            for origin_id in cluster["origin_ids"]:
                if origin_id not in origin_to_cluster:
                    origin_to_cluster[origin_id] = i
        
        # Ajouter les variantes aux clusters
        nouveaux_noms = 0
        for variante in variantes:
            origin_id = variante["origin_id"]
            nom = variante["nom"]
            
            if origin_id in origin_to_cluster:
                cluster_idx = origin_to_cluster[origin_id]
                cluster = clusters[cluster_idx]
                
                # Ajouter le nom s'il n'existe pas déjà
                if nom not in cluster["variants"]:
                    cluster["variants"].append(nom)
                    nouveaux_noms += 1
        
        print(f"   {nouveaux_noms} nouveaux noms ajoutés aux clusters")
        
        return clusters