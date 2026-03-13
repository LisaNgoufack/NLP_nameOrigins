"""
Service pour la correspondance phonétique et orthographique (Étape 5).
"""
import jellyfish
from Levenshtein import distance as levenshtein_distance
from openai import OpenAI
from src.utils.file_utils import load_json, save_json



class PhoneticService:
    """Service pour trouver des correspondances phonétiques."""
    
    def __init__(self, config):
        self.config = config
        self.insee_path = config.INSEE_DATABASE
        self.geneanet_path = config.FINAL_DATABASE
        self.output_path = config.FULL_DATABASE
        
        # Client Mistral pour génération d'origines (optionnel)
        self.use_mistral = config.has_mistral_key() and config.USE_MISTRAL_FOR_PHONETIC
        if self.use_mistral:
            self.client = OpenAI(
                api_key=config.MISTRAL_API_KEY,
                base_url=config.MISTRAL_BASE_URL
            )
            print("   [OK] API Mistral activee pour generation d'origines")
        else:
            print("   [INFO] Mistral desactive pour la phonetique")
    
    def run(self) -> list:
        """
        Exécute la correspondance phonétique.
        
        Returns:
            Liste complète enrichie
        """
        print("[ETAPE 5] Correspondance phonetique...")
        
        # Chargement
        insee_db = load_json(self.insee_path)
        geneanet_db = load_json(self.geneanet_path)
        
        # Filtrer les noms avec et sans origine
        avec_origine = [n for n in insee_db if n["source"] == "geneanet"]
        sans_origine = [n for n in insee_db if n["source"] == "insee_only"]
        
        print(f"   {len(avec_origine)} noms avec origine")
        print(f"   {len(sans_origine)} noms sans origine")
        
        # Construire l'index Soundex
        soundex_index, geneanet_dict = self._build_indexes(geneanet_db)
        print(f"   {len(soundex_index)} codes Soundex indexes")
        
        # Chercher des correspondances
        enrichis = self._find_matches(sans_origine, soundex_index, geneanet_dict)
        
        # Combiner avec les noms déjà enrichis
        resultats = avec_origine + enrichis
        
        # Sauvegarde
        save_json(resultats, self.output_path)
        print(f"[OK] {len(resultats)} noms sauvegardes dans {self.output_path}")
        
        return resultats
    
    def _build_indexes(self, geneanet_db: list) -> tuple:
        """Construit les index Soundex et nom->entrée."""
        soundex_index = {}
        geneanet_dict = {}
        
        for entree in geneanet_db:
            for variante in entree["variants"]:
                code = jellyfish.soundex(variante.upper())
                if code not in soundex_index:
                    soundex_index[code] = []
                soundex_index[code].append(entree)
                geneanet_dict[variante.lower()] = entree
        
        return soundex_index, geneanet_dict
    
    def _find_matches(self, sans_origine: list, soundex_index: dict, geneanet_dict: dict) -> list:
        """Trouve des correspondances pour les noms sans origine."""
        stats = {
            "soundex": 0,
            "levenshtein": 0,
            "mistral": 0,
            "aucune": 0
        }
        
        resultats = []
        
        for i, nom_entry in enumerate(sans_origine):
            if i % 10000 == 0 and i > 0:
                print(f"   Progression : {i}/{len(sans_origine)}")
            
            nom = nom_entry["nom"]
            
            # Méthode 1 : Soundex
            match = self._chercher_par_soundex(nom, soundex_index)
            if match:
                stats["soundex"] += 1
                resultats.append(self._create_entry(nom_entry, match, "soundex"))
                continue
            
            # Méthode 2 : Levenshtein
            match = self._chercher_par_levenshtein(
                nom, 
                geneanet_dict, 
                self.config.LEVENSHTEIN_THRESHOLD
            )
            if match:
                stats["levenshtein"] += 1
                resultats.append(self._create_entry(nom_entry, match, "levenshtein"))
                continue
            
            # Méthode 3 : Mistral (pour les top 1000 uniquement)
            if self.use_mistral and nom_entry["frequence"] > 1000:
                origin_text = self._generate_with_mistral(nom)
                stats["mistral"] += 1
                resultats.append({
                    **nom_entry,
                    "origin_text": origin_text,
                    "source": "mistral_generated"
                })
                continue
            
            # Aucune correspondance trouvée
            stats["aucune"] += 1
            resultats.append(nom_entry)
        
        print(f"   Statistiques :")
        print(f"   - Soundex : {stats['soundex']}")
        print(f"   - Levenshtein : {stats['levenshtein']}")
        print(f"   - Mistral : {stats['mistral']}")
        print(f"   - Aucune : {stats['aucune']}")
        
        return resultats
    
    def _chercher_par_soundex(self, nom: str, soundex_index: dict) -> dict:
        """Cherche par code Soundex."""
        code = jellyfish.soundex(nom.upper())
        candidats = soundex_index.get(code, [])
        
        if not candidats:
            return None
        
        if len(candidats) == 1:
            return candidats[0]
        
        # Plusieurs candidats → le plus proche par Levenshtein
        meilleur = min(
            candidats,
            key=lambda e: min(
                levenshtein_distance(nom.lower(), v.lower()) 
                for v in e["variants"]
            )
        )
        return meilleur
    
    def _chercher_par_levenshtein(self, nom: str, geneanet_dict: dict, seuil: int) -> dict:
        """Cherche par distance de Levenshtein."""
        meilleur_nom = None
        meilleure_distance = seuil + 1
        
        for variante in geneanet_dict.keys():
            dist = levenshtein_distance(nom.lower(), variante.lower())
            if dist < meilleure_distance:
                meilleure_distance = dist
                meilleur_nom = variante
        
        if meilleur_nom and meilleure_distance <= seuil:
            return geneanet_dict[meilleur_nom]
        
        return None
    
    def _generate_with_mistral(self, nom: str) -> str:
        """Génère une origine avec Mistral."""
        try:
            response = self.client.chat.completions.create(
                model=self.config.MISTRAL_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "Tu es un expert en etymologie. Genere une origine plausible pour ce nom."
                    },
                    {
                        "role": "user",
                        "content": f"Nom de famille : {nom}"
                    }
                ],
                temperature=0.3,
                max_tokens=300
            )
            return response.choices[0].message.content.strip()
        except:
            return ""
    
    def _create_entry(self, nom_entry: dict, match: dict, source: str) -> dict:
        """Crée une entrée enrichie."""
        return {
            "nom": nom_entry["nom"],
            "variantes": match["variants"],
            "frequence": nom_entry["frequence"],
            "evolution": nom_entry["evolution"],
            "origin_text": match.get("origin_text", ""),
            "source": source
        }