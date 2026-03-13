"""
Service pour l'intégration des données INSEE (Étape 4).
"""
import csv
from src.utils.file_utils import load_json, save_json


class InseeService:
    """Service pour intégrer les données de fréquence INSEE."""
    
    # Colonnes des décennies dans le fichier INSEE
    DECADES = [
        "_1891_1900", "_1901_1910", "_1911_1920", "_1921_1930",
        "_1931_1940", "_1941_1950", "_1951_1960", "_1961_1970",
        "_1971_1980", "_1981_1990", "_1991_2000"
    ]
    
    def __init__(self, config):
        self.config = config
        self.geneanet_path = config.FINAL_DATABASE
        self.insee_path = config.INSEE_FILE
        self.output_path = config.INSEE_DATABASE
    
    def run(self) -> list:
        """
        Exécute l'intégration des données INSEE.
        
        Returns:
            Liste des noms enrichis avec fréquences INSEE
        """
        print("[ETAPE 4] Integration des donnees INSEE...")
        
        # Chargement Geneanet
        geneanet_db = load_json(self.geneanet_path)
        print(f"   {len(geneanet_db)} entrees Geneanet chargees")
        
        # Index pour recherche rapide
        index_geneanet = self._build_geneanet_index(geneanet_db)
        print(f"   {len(index_geneanet)} variantes indexees")
        
        # Chargement INSEE
        insee_noms = self._load_insee_data()
        print(f"   {len(insee_noms)} noms INSEE charges")
        
        # Croisement
        resultats = self._cross_insee_geneanet(insee_noms, index_geneanet)
        
        # Sauvegarde
        save_json(resultats, self.output_path)
        print(f"[OK] {len(resultats)} noms sauvegardes dans {self.output_path}")
        
        return resultats
    
    def _build_geneanet_index(self, geneanet_db: list) -> dict:
        """Construit un index variante → entrée Geneanet."""
        index = {}
        for entree in geneanet_db:
            for variante in entree["variants"]:
                index[variante.upper()] = entree
        return index
    
    def _load_insee_data(self) -> list:
        """Charge le fichier INSEE."""
        insee_noms = []
        
        with open(self.insee_path, encoding="latin-1") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for row in reader:
                nom = row["NOM"].strip()
                
                # Calculer la fréquence totale
                frequence_totale = sum(
                    int(row.get(d, 0)) for d in self.DECADES
                )
                
                # Évolution par décennie
                evolution = {d: int(row.get(d, 0)) for d in self.DECADES}
                
                insee_noms.append({
                    "nom": nom,
                    "frequence": frequence_totale,
                    "evolution": evolution,
                })
        
        return insee_noms
    
    def _cross_insee_geneanet(self, insee_noms: list, index_geneanet: dict) -> list:
        """Croise les données INSEE avec Geneanet."""
        avec_origine = 0
        sans_origine = 0
        resultats = []
        
        for nom_insee in insee_noms:
            nom = nom_insee["nom"]
            
            # Chercher ce nom dans Geneanet
            entree_geneanet = index_geneanet.get(nom)
            
            if entree_geneanet:
                # Nom trouvé dans Geneanet → on a l'origine
                avec_origine += 1
                resultats.append({
                    "nom": nom.lower(),
                    "variantes": entree_geneanet["variants"],
                    "frequence": nom_insee["frequence"],
                    "evolution": nom_insee["evolution"],
                    "origin_text": entree_geneanet.get("origin_text", ""),
                    "source": "geneanet",
                })
            else:
                # Nom absent de Geneanet → pas d'origine pour l'instant
                sans_origine += 1
                resultats.append({
                    "nom": nom.lower(),
                    "variantes": [nom.lower()],
                    "frequence": nom_insee["frequence"],
                    "evolution": nom_insee["evolution"],
                    "origin_text": "",
                    "source": "insee_only",
                })
        
        print(f"   - {avec_origine} noms avec origine Geneanet")
        print(f"   - {sans_origine} noms sans origine (INSEE uniquement)")
        
        return resultats