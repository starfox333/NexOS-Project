"""
NexOS -- Bibliotheque de Connaissance Humaine
Savoirs transmis aux ISOs : physique, social, ecologie, logique, communication.
Exclut explicitement tout comportement negatif (agression, vol, deception).
"""

from typing import Dict
from collections import defaultdict


DOMAINS = ['physics', 'social', 'ecology', 'logic', 'communication']


class KnowledgeLibrary:
    """
    Bibliotheque statique de connaissances pre-codees.
    Fournit des modificateurs de Q-values par domaine.
    Chaque entree : (state_pattern, action) -> bonus

    Les patterns utilisent le meme format que _state_to_key():
    "energy_level|ground|terrain|crowd" avec '*' comme wildcard.
    """

    def __init__(self, config: dict = None):
        self.config = config or {}
        knowledge_cfg = self.config.get('life', {}).get('knowledge', {})
        self.bonus_scale = knowledge_cfg.get('bonus_scale', 0.5)
        self._library = self._build_library()

    def _build_library(self) -> Dict[str, list]:
        library = {}

        # PHYSICS -- Conservation d'energie, couts de mouvement, effets terrain
        library['physics'] = [
            ('critical|rich|*|*', 'harvest', 1.0),
            ('low|rich|*|*', 'harvest', 0.8),
            ('critical|empty|*|*', 'move_to_energy', 0.9),
            ('critical|some|*|*', 'harvest', 0.6),
            ('low|empty|barren|*', 'rest', 0.7),
            ('critical|*|*|*', 'explore', -0.5),
            ('mid|rich|fertile|*', 'harvest', 0.4),
        ]

        # SOCIAL -- Cooperation, partage, comportement de groupe
        library['social'] = [
            ('high|*|*|some', 'share_energy', 0.6),
            ('high|*|*|crowded', 'share_energy', 0.5),
            ('*|*|*|crowded', 'cooperate', 0.7),
            ('*|*|*|some', 'cooperate', 0.4),
            ('critical|*|*|*', 'share_energy', -1.0),
            ('low|*|*|*', 'share_energy', -0.5),
        ]

        # ECOLOGY -- Gestion des ressources, preference terrain, durabilite
        library['ecology'] = [
            ('*|*|fertile|*', 'harvest', 0.3),
            ('*|some|barren|*', 'harvest', -0.2),
            ('*|empty|barren|*', 'harvest', -0.4),
            ('*|*|barren|*', 'explore', 0.3),
            ('*|*|barren|*', 'move_to_energy', 0.4),
            ('*|empty|*|*', 'harvest', -0.3),
        ]

        # LOGIC -- Reconnaissance de patterns, planification
        library['logic'] = [
            ('low|empty|*|*', 'move_to_energy', 0.6),
            ('high|*|*|alone', 'explore', 0.5),
            ('high|*|*|some', 'reproduce', 0.4),
            ('high|*|*|crowded', 'reproduce', 0.3),
            ('mid|rich|*|*', 'harvest', 0.3),
            ('mid|some|*|*', 'harvest', 0.2),
        ]

        # COMMUNICATION -- Comportement de signalisation
        library['communication'] = [
            ('*|rich|*|some', 'signal', 0.5),
            ('*|rich|*|crowded', 'signal', 0.4),
            ('critical|*|*|some', 'signal', 0.8),
            ('critical|*|*|crowded', 'signal', 0.7),
            ('*|*|*|alone', 'signal', -0.3),
        ]

        return library

    def get_bonuses(self, state_key: str, knowledge_levels: Dict[str, float]
                    ) -> Dict[str, float]:
        """
        Retourne les bonus d'action bases sur l'etat et les niveaux de connaissance.
        knowledge_levels: {'physics': 0.0-1.0, 'social': 0.0-1.0, ...}
        """
        bonuses = defaultdict(float)
        parts = state_key.split('|')

        for domain, rules in self._library.items():
            level = knowledge_levels.get(domain, 0.0)
            if level < 0.01:
                continue

            for pattern, action, bonus in rules:
                if self._matches(parts, pattern):
                    bonuses[action] += bonus * level * self.bonus_scale

        return dict(bonuses)

    def _matches(self, state_parts: list, pattern: str) -> bool:
        pattern_parts = pattern.split('|')
        if len(pattern_parts) != len(state_parts):
            return False
        for sp, pp in zip(state_parts, pattern_parts):
            if pp != '*' and pp != sp:
                return False
        return True


class ISOKnowledge:
    """
    Etat de connaissance par ISO. Suit l'absorption de savoir par domaine.
    Plafonne par le gene intelligence.
    """

    def __init__(self, intelligence: float = 0.5,
                 initial_levels: Dict[str, float] = None):
        self.intelligence = intelligence

        self.levels: Dict[str, float] = {}
        for domain in DOMAINS:
            if initial_levels and domain in initial_levels:
                self.levels[domain] = min(initial_levels[domain], intelligence)
            else:
                self.levels[domain] = 0.0

        self._experience_counts: Dict[str, int] = defaultdict(int)

    def absorb_experience(self, domain: str, amount: float = 0.01):
        """Apprend par l'experience dans un domaine."""
        if domain not in DOMAINS:
            return
        self._experience_counts[domain] += 1
        growth = amount * self.intelligence
        self.levels[domain] = min(self.intelligence,
                                  self.levels[domain] + growth)

    def absorb_from_nearby(self, other_knowledge: 'ISOKnowledge',
                           proximity_factor: float = 1.0):
        """Transmission culturelle : apprend d'un ISO proche."""
        cultural_rate = 0.002 * proximity_factor * self.intelligence
        for domain in DOMAINS:
            if other_knowledge.levels.get(domain, 0) > self.levels[domain]:
                diff = other_knowledge.levels[domain] - self.levels[domain]
                self.levels[domain] = min(
                    self.intelligence,
                    self.levels[domain] + diff * cultural_rate
                )

    def absorb_from_minerve(self, teaching_rate: float = 0.01):
        """Apprentissage accelere par Minerve."""
        growth = teaching_rate * self.intelligence
        for domain in DOMAINS:
            self.levels[domain] = min(self.intelligence,
                                      self.levels[domain] + growth)

    def absorb_from_symmetra(self, teaching_rate: float = 0.008):
        """Apprentissage construction par Symmetra (ecologie + logique)."""
        growth = teaching_rate * self.intelligence
        # Symmetra enseigne principalement ecologie et logique
        for domain in ['ecology', 'logic']:
            self.levels[domain] = min(self.intelligence,
                                      self.levels[domain] + growth * 1.5)
        # Bonus mineur aux autres domaines
        for domain in ['physics', 'social', 'communication']:
            self.levels[domain] = min(self.intelligence,
                                      self.levels[domain] + growth * 0.3)

    def inherit_from_parents(self, parent1: 'ISOKnowledge',
                             parent2: 'ISOKnowledge',
                             inheritance_factor: float = 0.3):
        """Les enfants heritent partiellement du savoir parental."""
        for domain in DOMAINS:
            p1 = parent1.levels.get(domain, 0.0)
            p2 = parent2.levels.get(domain, 0.0)
            avg = (p1 + p2) / 2.0
            self.levels[domain] = min(self.intelligence,
                                      avg * inheritance_factor)

    def get_total_knowledge(self) -> float:
        return sum(self.levels.values())

    def to_dict(self) -> dict:
        return {
            'intelligence': round(self.intelligence, 3),
            'levels': {d: round(v, 3) for d, v in self.levels.items()},
            'total': round(self.get_total_knowledge(), 3)
        }
