"""
Service pour l'extraction des noms dans les textes (Étape 6).
"""
import re
from openai import OpenAI
from src.utils.file_utils import load_json, save_json
from src.utils.text_utils import nettoyer_nom, est_nom_valide


class ExtractionService:
    """Service pour extraire les noms de famille dans les textes."""
    
    # Mots français courants à ignorer
    MOTS_A_IGNORER = {
        # Régions
        "france", "bretagne", "normandie", "alsace", "provence", "paris",
        "lyon", "marseille", "bordeaux", "toulouse", "italie", "espagne",
        # Périodes
        "moyen", "age", "antiquite", "renaissance", "xive", "xve", "xvie",
        # Religieux
        "saint", "sainte", "dieu", "eglise", "marie", "joseph", "pierre",
        # Langues
        "latin", "grec", "germanique", "gaulois", "francais", "arabe",
        # Auteurs
        "morlet", "dauzat", "negre", "vincent",
        # Grammaire
        "le", "la", "les", "un", "une", "des", "du", "de", "ce", "cette",
    }
    
    def __init__(self, config):
        self.config = config
        self.origins_path = config.ORIGINS_FILE
        self.names_path = config.NAMES_FILE
        self.full_db_path = config.FULL_DATABASE
        self.output_path = config.NOUVEAUX_NOMS
        
        # Client Mistral (optionnel)
        self.use_mistral = config.has_mistral_key() and config.USE_MISTRAL_FOR_EXTRACTION
        if self.use_mistral:
            self.client = OpenAI(
                api_key=config.MISTRAL_API_KEY,
                base_url=config.MISTRAL_BASE_URL
            )
    
    def run(self) -> list:
        """
        Exécute l'extraction des noms.
        
        Returns:
            Liste des nouveaux noms extraits
        """
        print("[ETAPE 6] Extraction des noms dans les textes...")
        
        # Chargement
        origins = load_json(self.origins_path)
        noms_connus = self._load_known_names()
        
        print(f"   {len(origins)} textes d'origine charges")
        print(f"   {len(noms_connus)} noms deja connus")
        
        # Extraction
        if self.use_mistral:
            nouveaux_noms = self._extract_with_mistral(origins, noms_connus)
        else:
            nouveaux_noms = self._extract_with_regex(origins, noms_connus)
        
        # Sauvegarde
        save_json(nouveaux_noms, self.output_path)
        print(f"[OK] {len(nouveaux_noms)} nouveaux noms extraits")
        
        return nouveaux_noms
    
    def _load_known_names(self) -> set:
        """Charge tous les noms déjà connus."""
        noms_connus = set()
        
        # Noms Geneanet
        names_data = load_json(self.names_path)
        noms_connus.update(n["name"].lower() for n in names_data)
        
        # Noms de la base complète
        full_db = load_json(self.full_db_path)
        noms_connus.update(n["nom"].lower() for n in full_db)
        
        return noms_connus
    
    def _extract_with_regex(self, origins: dict, noms_connus: set) -> list:
        """Méthode 1 : Extraction par majuscules + contexte."""
        print("   [INFO] Methode : Regex + majuscules")
        
        nouveaux_noms = []
        
        for origin_id, text in origins.items():
            # Chercher les mots avec majuscule
            mots = re.findall(r'\b[A-ZÀ-Ÿ][a-zà-ÿ-]+\b', text)
            
            for mot in mots:
                nom = nettoyer_nom(mot)
                
                # Filtrer
                if not est_nom_valide(nom):
                    continue
                if nom.lower() in self.MOTS_A_IGNORER:
                    continue
                if nom.lower() in noms_connus:
                    continue
                
                nouveaux_noms.append({
                    "nom": nom.lower(),
                    "origin_id": origin_id,
                    "texte_extrait": text[:200]
                })
                noms_connus.add(nom.lower())
        
        return nouveaux_noms
    
    def _extract_with_mistral(self, origins: dict, noms_connus: set) -> list:
        """Méthode 2 : Extraction avec Mistral."""
        print("   [INFO] Methode : Mistral AI")
        
        nouveaux_noms = []
        
        for i, (origin_id, text) in enumerate(origins.items()):
            if i % 100 == 0 and i > 0:
                print(f"   Progression : {i}/{len(origins)}")
            
            try:
                response = self.client.chat.completions.create(
                    model=self.config.MISTRAL_MODEL,
                    messages=[
                        {
                            "role": "system",
                            "content": "Extrais UNIQUEMENT les noms de famille du texte. Retourne une liste JSON."
                        },
                        {
                            "role": "user",
                            "content": f"Texte : {text}"
                        }
                    ],
                    temperature=0.1,
                    max_tokens=200
                )
                
                # Parser la réponse (liste JSON)
                noms_extraits = eval(response.choices[0].message.content)
                
                for nom in noms_extraits:
                    nom_clean = nettoyer_nom(nom)
                    if est_nom_valide(nom_clean) and nom_clean.lower() not in noms_connus:
                        nouveaux_noms.append({
                            "nom": nom_clean.lower(),
                            "origin_id": origin_id,
                            "texte_extrait": text[:200]
                        })
                        noms_connus.add(nom_clean.lower())
            
            except Exception as e:
                continue
        
        return nouveaux_noms