"""
Utilitaires pour le traitement de texte.
"""
import unicodedata
import re


def normaliser(texte: str) -> str:
    """
    Normalise un texte : minuscules + suppression des accents.
    
    Args:
        texte: Texte à normaliser
        
    Returns:
        Texte normalisé
    """
    texte = texte.strip().lower()
    texte = unicodedata.normalize('NFD', texte)
    texte = ''.join(c for c in texte if unicodedata.category(c) != 'Mn')
    return texte


def normaliser_compose(nom: str) -> str:
    """
    Normalise un nom composé pour la comparaison.
    Le Goff → legoff
    Le-Goff → legoff
    Legoff  → legoff
    
    Args:
        nom: Nom de famille
        
    Returns:
        Forme normalisée sans espaces ni tirets
    """
    nom = nom.lower().strip()
    nom = nom.replace("-", "").replace(" ", "").replace("'", "")
    return nom


def nettoyer_nom(nom: str) -> str:
    """
    Nettoie un nom extrait (enlève parenthèses, normalise espaces).
    
    Args:
        nom: Nom à nettoyer
        
    Returns:
        Nom nettoyé
    """
    # Enlever les parenthèses et leur contenu
    nom = re.sub(r'\s*\(.*?\)', '', nom)
    # Normaliser les espaces
    nom = re.sub(r'\s+', ' ', nom).strip()
    # Enlever caractères spéciaux sauf lettres, tirets et espaces
    nom = re.sub(r'[^a-zà-ÿ\-\s]', '', nom.lower())
    return nom


def est_nom_valide(nom: str, min_length: int = 2, max_length: int = 30) -> bool:
    """
    Vérifie si un nom est valide (longueur appropriée).
    
    Args:
        nom: Nom à vérifier
        min_length: Longueur minimale
        max_length: Longueur maximale
        
    Returns:
        True si valide, False sinon
    """
    return min_length <= len(nom) <= max_length