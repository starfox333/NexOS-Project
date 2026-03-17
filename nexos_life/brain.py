"""
NexOS -- Cerveau ISO
Perception, decision, apprentissage.
Le cerveau ne suit pas de script -- il apprend par experience.
Integre la Bibliotheque de Connaissance pour des decisions eclairees.
"""

import random
from typing import Dict, List, Tuple, Optional

from nexos_life.memory import Memory


# Actions possibles pour un ISO
ACTIONS = ['move_to_energy', 'explore', 'rest', 'reproduce', 'harvest',
           'signal', 'share_energy', 'cooperate']


class Brain:
    """
    Cerveau d'un ISO -- percoit, decide, apprend.

    Cycle :
    1. perceive() -> analyse l'environnement + signaux
    2. decide() -> choisit une action (Q-learning + knowledge bonuses)
    3. feedback() -> apprend du resultat
    """

    def __init__(self, genes: dict = None, config: dict = None,
                 knowledge_library=None):
        self.genes = genes or {}
        self.config = config or {}
        self.knowledge_library = knowledge_library

        life_cfg = self.config.get('life', {}).get('learning', {})
        lr = life_cfg.get('learning_rate', 0.1)
        cap = life_cfg.get('memory_capacity', 500)
        exp_rate = life_cfg.get('exploration_rate', 0.3)

        curiosity = self.genes.get('curiosity', 0.5)
        exp_rate = min(0.8, exp_rate * (0.5 + curiosity))

        self.memory = Memory(capacity=cap, learning_rate=lr, exploration_rate=exp_rate)
        self.last_perception = None
        self.last_state_key = None
        self.last_action = None

    def perceive(self, grid, position: Tuple[int, int],
                 energy: float, max_energy: float,
                 signal_board=None, iso_id: int = 0) -> dict:
        """Analyse l'environnement autour de l'ISO, y compris les signaux."""
        x, z = position
        radius = int(self.genes.get('perception', 5))
        neighbors = grid.get_neighbors(x, z, radius)

        energy_cells = [c for c in neighbors if c.energy > 10]
        energy_cells.sort(key=lambda c: c.energy, reverse=True)

        occupied = [c for c in neighbors if c.occupied_by is not None]

        current = grid.get_cell(x, z)

        terrains = {}
        for c in neighbors:
            terrains[c.terrain] = terrains.get(c.terrain, 0) + 1

        # Signaux proches
        nearby_signals = []
        if signal_board:
            nearby_signals = signal_board.get_nearby_signals(x, z, radius)
            nearby_signals = [s for s in nearby_signals if s.sender_id != iso_id]

        perception = {
            'current_cell': current,
            'energy_level': energy / max(1, max_energy),
            'energy_cells': energy_cells[:10],
            'avg_nearby_energy': sum(c.energy for c in neighbors) / max(1, len(neighbors)),
            'neighbors_count': len(occupied),
            'terrain_dominant': max(terrains, key=terrains.get) if terrains else 'plain',
            'ground_energy': current.energy,
            'is_fertile': current.terrain == 'fertile',
            'nearby_signals': nearby_signals,
            'food_signals': [s for s in nearby_signals if s.signal_type == 'FOOD_HERE'],
            'help_signals': [s for s in nearby_signals if s.signal_type == 'NEED_HELP'],
            'nearby_isos': occupied,
        }

        self.last_perception = perception
        self.last_state_key = self._state_to_key(perception, energy, max_energy)
        return perception

    def _state_to_key(self, perception: dict, energy: float, max_energy: float) -> str:
        """Encode l'etat en cle compacte pour la Q-table (4 dimensions)"""
        e_level = 'critical' if energy < 30 else ('low' if energy < 80 else ('mid' if energy < 150 else 'high'))
        ground = 'rich' if perception['ground_energy'] > 50 else ('some' if perception['ground_energy'] > 15 else 'empty')
        terrain = perception['terrain_dominant']
        crowded = 'crowded' if perception['neighbors_count'] > 3 else ('some' if perception['neighbors_count'] > 0 else 'alone')

        return f"{e_level}|{ground}|{terrain}|{crowded}"

    def decide(self, energy: float, max_energy: float, can_reproduce: bool,
               iso_knowledge=None) -> str:
        """Choisit une action -- Q-learning augmente par les connaissances."""
        if not self.last_perception:
            return 'explore'

        # Actions disponibles
        available = ['explore', 'rest']

        if self.last_perception['ground_energy'] > 5:
            available.append('harvest')

        if self.last_perception['energy_cells']:
            available.append('move_to_energy')

        if can_reproduce and energy > max_energy * 0.75:
            available.append('reproduce')

        # Actions debloquees par la connaissance
        if iso_knowledge:
            comm_level = iso_knowledge.levels.get('communication', 0)
            social_level = iso_knowledge.levels.get('social', 0)

            if comm_level > 0.1 and self.last_perception['neighbors_count'] > 0:
                available.append('signal')

            if social_level > 0.1 and self.last_perception['neighbors_count'] > 0:
                available.append('share_energy')

            if social_level > 0.2 and self.last_perception['neighbors_count'] > 1:
                available.append('cooperate')

        # Urgences
        if energy < 20:
            if 'harvest' in available:
                self.last_action = 'harvest'
                return 'harvest'
            if 'move_to_energy' in available:
                self.last_action = 'move_to_energy'
                return 'move_to_energy'

        # Decision avec ou sans knowledge bonuses
        state_key = self.last_state_key or 'unknown'

        if iso_knowledge and self.knowledge_library:
            knowledge_bonuses = self.knowledge_library.get_bonuses(
                state_key, iso_knowledge.levels
            )
            action = self._decide_with_knowledge(
                state_key, available, knowledge_bonuses
            )
        else:
            action = self.memory.get_best_action(state_key, available)

        self.last_action = action
        return action

    def _decide_with_knowledge(self, state_key: str, available: list,
                               bonuses: dict) -> str:
        """Decision Q-learning augmentee par les knowledge bonuses."""
        # Exploration epsilon-greedy
        if random.random() < self.memory.exploration_rate:
            return random.choice(available)

        # Q-values brutes
        scores = self.memory.q_table.get(state_key, {})

        # Combiner Q-values + knowledge bonuses
        combined = {}
        for action in available:
            q_val = scores.get(action, 0.0)
            k_bonus = bonuses.get(action, 0.0)
            combined[action] = q_val + k_bonus

        if not combined:
            return random.choice(available)

        return max(combined, key=combined.get)

    def feedback(self, reward: float, cycle: int = 0):
        """Apprend du resultat de l'action"""
        if self.last_state_key and self.last_action:
            self.memory.store_experience(
                self.last_state_key, self.last_action, reward, cycle
            )
            self.memory.learn()

    def get_target_position(self) -> Optional[Tuple[int, int]]:
        """Retourne la position cible (pour move_to_energy)"""
        if not self.last_perception or not self.last_perception['energy_cells']:
            return None
        best = self.last_perception['energy_cells'][0]
        return (best.x, best.z)

    def get_stats(self) -> dict:
        return {
            'memory': self.memory.get_stats(),
            'last_action': self.last_action,
            'exploration': round(self.memory.exploration_rate, 3)
        }
