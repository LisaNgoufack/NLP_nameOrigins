"""
Service pour le résumé des textes d'origine avec Mistral (Étape 2).
"""
import time
from openai import OpenAI
from src.utils.file_utils import load_json, save_json
from src.utils.prompt_loader import prompt_loader


class SummarizationService:
    """Service pour résumer les textes d'origine avec Mistral."""
    
    def __init__(self, config):
        self.config = config
        self.input_path = config.ENRICHED_OUTPUT
        self.output_path = config.FINAL_DATABASE
        
        # Initialiser le client Mistral si la clé API est disponible
        self.use_mistral = config.has_mistral_key() and config.USE_MISTRAL_FOR_SUMMARY
        if self.use_mistral:
            self.client = OpenAI(
                api_key=config.MISTRAL_API_KEY,
                base_url=config.MISTRAL_BASE_URL
            )
            print("   ✅ API Mistral activée pour les résumés")
        else:
            print("   ⚠️  API Mistral désactivée → concaténation simple des textes")
    
    def run(self) -> list:
        """
        Exécute le résumé des textes d'origine.
        
        Returns:
            Liste des entrées avec textes résumés
        """
        print("🔄 ÉTAPE 2 : Résumé des textes d'origine...")
        
        # Chargement
        clusters = load_json(self.input_path)
        print(f"   {len(clusters)} clusters chargés")
        
        # Séparer clusters simples et complexes
        simples = [c for c in clusters if len(c.get("origin_texts", {})) <= 1]
        complexes = [c for c in clusters if len(c.get("origin_texts", {})) > 1]
        
        print(f"   - {len(simples)} clusters avec 1 texte (conservés tels quels)")
        print(f"   - {len(complexes)} clusters avec plusieurs textes (résumé nécessaire)")
        
        # Construire la base finale
        final_database = []
        
        # Clusters simples : conserver le texte tel quel
        for cluster in simples:
            origin_texts = cluster.get("origin_texts", {})
            origin_text = list(origin_texts.values())[0] if origin_texts else ""
            
            final_database.append({
                "variants": cluster["variants"],
                "origin_text": origin_text,
                "origin_ids": cluster["origin_ids"]
            })
        
        # Clusters complexes : résumer avec Mistral ou concaténer
        for i, cluster in enumerate(complexes):
            if i % 1 == 0 and i > 0:
                print(f"   Progression : {i}/{len(complexes)} clusters traités")
            
            origin_texts = cluster.get("origin_texts", {})
            
            if self.use_mistral:
                origin_text = self._summarize_with_mistral(
                    cluster["variants"],
                    origin_texts
                )
                time.sleep(0.5)  # Respecter les limites de rate API
            else:
                # Fallback : concaténation simple
                origin_text = self._concatenate_texts(origin_texts)
            
            final_database.append({
                "variants": cluster["variants"],
                "origin_text": origin_text,
                "origin_ids": cluster["origin_ids"]
            })
        
        # Sauvegarde
        save_json(final_database, self.output_path)
        print(f"✅ {len(final_database)} entrées sauvegardées dans {self.output_path}")
        
        return final_database
    
    def _summarize_with_mistral(self, variants: list, textes: dict) -> str:
        """Résume plusieurs textes avec l'API Mistral."""
        textes_assembles = "\n\n---\n\n".join(
            f"Texte {i+1} (réf. {oid}) :\n{txt}"
            for i, (oid, txt) in enumerate(textes.items())
            if txt.strip()
        )
        
        # Charger les prompts depuis les fichiers
        system_prompt = prompt_loader.load('summarization_system')
        user_prompt = prompt_loader.format(
            'summarization_user',
            variants=', '.join(variants[:5]),
            texts=textes_assembles
        )
        
        try:
            response = self.client.chat.completions.create(
                model=self.config.MISTRAL_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"   ⚠️  Erreur Mistral : {e}, fallback sur concaténation")
            return self._concatenate_texts(textes)
    
    def _concatenate_texts(self, textes: dict) -> str:
        """Concatène simplement les textes (fallback sans API)."""
        return "\n\n".join(txt for txt in textes.values() if txt.strip())