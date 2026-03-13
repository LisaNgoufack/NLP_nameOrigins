"""
Utilitaires pour la gestion des fichiers JSON.
"""
import json
import os
from pathlib import Path
from typing import Any


def load_json(filepath: str) -> Any:
    """
    Charge un fichier JSON.
    
    Args:
        filepath: Chemin du fichier à charger
        
    Returns:
        Contenu du fichier (dict ou list)
    """
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data: Any, filepath: str, indent: int = 2) -> None:
    """
    Sauvegarde des données dans un fichier JSON.
    
    Args:
        data: Données à sauvegarder
        filepath: Chemin du fichier de destination
        indent: Indentation du JSON (par défaut 2)
    """
    # Créer le dossier parent si nécessaire
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)


def ensure_output_dir(output_dir: str = "output") -> None:
    """
    S'assure que le dossier output existe.
    
    Args:
        output_dir: Nom du dossier à créer
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)


def file_exists(filepath: str) -> bool:
    """
    Vérifie si un fichier existe.
    
    Args:
        filepath: Chemin du fichier à vérifier
        
    Returns:
        True si le fichier existe, False sinon
    """
    return Path(filepath).exists()