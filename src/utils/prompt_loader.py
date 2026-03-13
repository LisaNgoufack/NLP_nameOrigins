"""
Utilitaire pour charger les prompts depuis des fichiers texte.
"""
from pathlib import Path


class PromptLoader:
    """Charge les prompts depuis le dossier src/prompts/."""
    
    def __init__(self):
        self.prompts_dir = Path(__file__).parent.parent / "prompts"
    
    def load(self, prompt_name: str) -> str:
        """
        Charge un prompt depuis un fichier texte.
        
        Args:
            prompt_name: Nom du fichier sans extension (ex: 'summarization_system')
        
        Returns:
            Contenu du prompt
        
        Raises:
            FileNotFoundError: Si le fichier n'existe pas
        """
        prompt_path = self.prompts_dir / f"{prompt_name}.txt"
        
        if not prompt_path.exists():
            raise FileNotFoundError(
                f"Prompt '{prompt_name}' introuvable dans {self.prompts_dir}"
            )
        
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    
    def format(self, prompt_name: str, **kwargs) -> str:
        """
        Charge un prompt et remplace les variables.
        
        Args:
            prompt_name: Nom du fichier sans extension
            **kwargs: Variables à remplacer dans le prompt
        
        Returns:
            Prompt formaté
        
        Example:
            loader.format('summarization_user', variants='Durand, Durant', texts='...')
        """
        prompt = self.load(prompt_name)
        return prompt.format(**kwargs)


# Instance globale pour faciliter l'utilisation
prompt_loader = PromptLoader()