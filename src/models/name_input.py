"""
Classe représentant une entrée de nom dans la base de données.
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class NameEntry:
    """
    Représente un nom de famille avec toutes ses métadonnées.
    """
    nom: str
    variantes: list[str] = field(default_factory=list)
    origin_text: str = ""
    frequence: int = 0
    evolution: dict = field(default_factory=dict)
    source: str = ""
    origin_ids: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convertit l'entrée en dictionnaire pour JSON."""
        return {
            "nom": self.nom,
            "variantes": self.variantes,
            "origin_text": self.origin_text,
            "frequence": self.frequence,
            "evolution": self.evolution,
            "source": self.source,
            "origin_ids": self.origin_ids
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'NameEntry':
        """Crée une instance depuis un dictionnaire."""
        return cls(
            nom=data.get("nom", ""),
            variantes=data.get("variantes", data.get("variants", [])),
            origin_text=data.get("origin_text", ""),
            frequence=data.get("frequence", 0),
            evolution=data.get("evolution", {}),
            source=data.get("source", ""),
            origin_ids=data.get("origin_ids", [])
        )