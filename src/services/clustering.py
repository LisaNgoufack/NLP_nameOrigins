"""
Service pour le regroupement des variantes de noms (Étape 1).
"""
from collections import defaultdict
from src.utils.file_utils import load_json, save_json


class UnionFind:
    """Structure de données Union-Find pour regrouper les noms."""
    
    def __init__(self, items):
        self.parent = {x: x for x in items}
        self.rank = {x: 0 for x in items}
    
    def find(self, x):
        """Trouve la racine du groupe de x (avec compression de chemin)."""
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x
    
    def union(self, a, b):
        """Fusionne les groupes de a et b."""
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        if self.rank[ra] < self.rank[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        if self.rank[ra] == self.rank[rb]:
            self.rank[ra] += 1


class ClusteringService:
    """Service pour regrouper les variantes de noms de famille."""
    
    def __init__(self, config):
        self.config = config
        self.names_path = config.NAMES_FILE
        self.origins_path = config.ORIGINS_FILE
        self.output_path = config.CLUSTERS_OUTPUT
    
    def run(self) -> list:
        """
        Exécute le clustering des noms.
        
        Returns:
            Liste des clusters avec variantes et origines
        """
        print("🔄 ÉTAPE 1 : Clustering des variantes...")
        
        # Chargement
        names_data = load_json(self.names_path)
        origins_data = load_json(self.origins_path)
        print(f"   Chargé : {len(names_data)} noms, {len(origins_data)} origines")
        
        # Construction des clusters
        clusters = self._build_clusters(names_data, origins_data)
        
        # Sauvegarde
        save_json(clusters, self.output_path)
        print(f"✅ {len(clusters)} clusters sauvegardés dans {self.output_path}")
        
        return clusters
    
    def _build_clusters(self, names_data: list, origins_data: dict) -> list:
        """Construit les clusters avec Union-Find."""
        all_names = [entry["name"] for entry in names_data]
        uf = UnionFind(all_names)
        
        # Regrouper les noms qui partagent un même origin_id
        origin_to_names = defaultdict(list)
        for entry in names_data:
            for oid in entry["origins"]:
                origin_to_names[oid].append(entry["name"])
        
        for oid, group in origin_to_names.items():
            for i in range(1, len(group)):
                uf.union(group[0], group[i])
        
        # Construction des clusters
        name_to_origins = {entry["name"]: entry["origins"] for entry in names_data}
        clusters_dict = defaultdict(lambda: {"names": [], "origin_ids": set()})
        
        for name in all_names:
            root = uf.find(name)
            clusters_dict[root]["names"].append(name)
            for oid in name_to_origins[name]:
                clusters_dict[root]["origin_ids"].add(oid)
        
        # Mise en forme
        output = []
        for root, cluster in clusters_dict.items():
            origin_ids = sorted(cluster["origin_ids"])
            origin_texts = {oid: origins_data.get(oid, "") for oid in origin_ids}
            
            output.append({
                "variants": sorted(cluster["names"]),
                "origin_ids": origin_ids,
                "origin_texts": origin_texts
            })
        
        return output