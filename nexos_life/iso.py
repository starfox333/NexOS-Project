"""
NexOS -- Classe ISO (Isomorphic Algorithm)
Entite vivante autonome avec cerveau, memoire, genes et connaissances.
Un ISO nait, apprend, evolue, se reproduit et meurt.
"""

import random
import math
from typing import Tuple, Optional

from nexos_life.brain import Brain
from nexos_life.genetics import create_genes
from nexos_life.knowledge import ISOKnowledge


class ISO:
    """
    ISO -- Entite de vie artificielle.

    Cycle de vie complet :
    1. Perception -> observe l'environnement + signaux
    2. Decision -> choisit une action (Q-learning + knowledge)
    3. Action -> execute (deplacer, recolter, partager, signaler, cooperer...)
    4. Feedback -> apprend du resultat
    5. Vieillissement -> cout metabolique
    """

    _next_id = 1

    def __init__(self, position: Tuple[int, int], genes: dict = None,
                 config: dict = None, generation: int = 0,
                 parent_ids: tuple = None,
                 knowledge_library=None, parent_knowledge=None):
        self.id = ISO._next_id
        ISO._next_id += 1

        self.x, self.z = position
        self.config = config or {}
        self.generation = generation
        self.parent_ids = parent_ids or ()

        # Genes
        self.genes = genes or create_genes()

        # Cerveau & Memoire (avec reference a la bibliotheque)
        self.brain = Brain(genes=self.genes, config=self.config,
                           knowledge_library=knowledge_library)

        # Connaissance
        intelligence = self.genes.get('intelligence', 0.5)
        self.knowledge = ISOKnowledge(intelligence=intelligence)
        if parent_knowledge and len(parent_knowledge) == 2:
            inheritance = self.config.get('life', {}).get('knowledge', {}).get(
                'inheritance_factor', 0.3)
            self.knowledge.inherit_from_parents(
                parent_knowledge[0], parent_knowledge[1], inheritance)

        # Energie & Vie
        energy_cfg = self.config.get('life', {}).get('energy', {})
        self.energy = float(energy_cfg.get('start', 100))
        self.max_energy = float(energy_cfg.get('max', 200))
        self.alive = True
        self.age = 0
        self.children_count = 0

        # === BESOINS SIMS 4 (0-100, decroissance naturelle) ===
        self.needs = {
            'hunger': 80.0 + random.uniform(-10, 10),     # Faim (energy harvest)
            'social': 70.0 + random.uniform(-15, 15),      # Social (interactions)
            'fun': 60.0 + random.uniform(-20, 20),         # Divertissement
            'comfort': 75.0 + random.uniform(-10, 10),     # Confort (shelter)
            'hygiene': 85.0 + random.uniform(-5, 5),       # Hygiene
        }
        # Humeur derivee des besoins (0-100)
        self.mood = 50.0
        self.mood_label = 'neutral'

        # Couts (ajustes par les genes)
        eff = self.genes.get('efficiency', 1.0)
        self.move_cost = energy_cfg.get('move_cost', 2) / max(0.5, eff)
        self.rest_recovery = energy_cfg.get('rest_recovery', 5) * max(0.5, eff)
        self.harvest_amount = energy_cfg.get('harvest_amount', 15) * max(0.5, eff)
        self.reproduction_cost = energy_cfg.get('reproduction_cost', 80)
        self.reproduction_threshold = energy_cfg.get('reproduction_threshold', 150)

        # Etat courant
        self.last_action = None
        self.total_reward = 0.0
        self.total_harvested = 0.0
        self.distance_traveled = 0.0

        # Taux d'exploration (miroir de brain.memory.exploration_rate, modifiable par Daedalus)
        self.exploration_chance = self.brain.memory.exploration_rate

    # --- CYCLE PRINCIPAL ---

    def perceive(self, grid, signal_board=None):
        """Observe l'environnement + signaux"""
        return self.brain.perceive(
            grid, (self.x, self.z), self.energy, self.max_energy,
            signal_board=signal_board, iso_id=self.id)

    def decide(self) -> str:
        """Choisit une action"""
        can_repro = self.can_reproduce()
        action = self.brain.decide(
            self.energy, self.max_energy, can_repro,
            iso_knowledge=self.knowledge)
        self.last_action = action
        return action

    def act(self, grid, action: str = None, signal_board=None,
            population_lookup=None) -> float:
        """Execute l'action decidee. Retourne la recompense."""
        if not self.alive:
            return 0.0

        action = action or self.last_action or 'rest'
        reward = 0.0

        if action == 'move_to_energy':
            reward = self._act_move_to_energy(grid)
        elif action == 'explore':
            reward = self._act_explore(grid)
        elif action == 'harvest':
            reward = self._act_harvest(grid)
        elif action == 'rest':
            reward = self._act_rest()
        elif action == 'reproduce':
            reward = 0.5
        elif action == 'signal':
            reward = self._act_signal(grid, signal_board)
        elif action == 'share_energy':
            reward = self._act_share_energy(grid, population_lookup)
        elif action == 'cooperate':
            reward = self._act_cooperate(grid, population_lookup)
        else:
            reward = self._act_rest()

        # Feedback au cerveau
        self.brain.feedback(reward, self.age)
        self.total_reward += reward

        # Apprendre par l'experience
        self._learn_from_action(action, reward)

        return reward

    def tick(self):
        """Vieillissement -- cout metabolique + decroissance des besoins"""
        if not self.alive:
            return

        self.age += 1

        resilience = self.genes.get('resilience', 1.0)
        base_cost = 0.5 / max(0.5, resilience)
        self.consume_energy(base_cost)

        # === DECROISSANCE DES BESOINS (Sims 4 style) ===
        self.needs['hunger'] = max(0, self.needs['hunger'] - 0.15)
        self.needs['social'] = max(0, self.needs['social'] - 0.08)
        self.needs['fun'] = max(0, self.needs['fun'] - 0.10)
        self.needs['comfort'] = max(0, self.needs['comfort'] - 0.05)
        self.needs['hygiene'] = max(0, self.needs['hygiene'] - 0.03)

        # Calcul humeur (moyenne ponderee des besoins)
        w = {'hunger': 0.3, 'social': 0.2, 'fun': 0.2, 'comfort': 0.15, 'hygiene': 0.15}
        self.mood = sum(self.needs[k] * w[k] for k in w)
        if self.mood >= 70:
            self.mood_label = 'happy'
        elif self.mood >= 45:
            self.mood_label = 'neutral'
        elif self.mood >= 20:
            self.mood_label = 'sad'
        else:
            self.mood_label = 'miserable'

        # Malus si besoins critiques
        if self.needs['hunger'] < 10:
            self.consume_energy(0.3)  # Affame = perd plus d'energie
        if self.mood < 20:
            self.consume_energy(0.2)  # Miserable = stress

        if self.age > 5000:
            death_prob = (self.age - 5000) / 50000.0
            if random.random() < death_prob:
                self.die(cause='old_age')

    # --- ACTIONS DE BASE ---

    def _act_move_to_energy(self, grid) -> float:
        target = self.brain.get_target_position()
        if not target:
            return self._act_explore(grid)

        tx, tz = target
        reward = self._move_towards(grid, tx, tz)

        cell = grid.get_cell(self.x, self.z)
        if cell.energy > 30:
            reward += 0.3
        return reward

    def _act_explore(self, grid) -> float:
        curiosity = self.genes.get('curiosity', 0.5)
        speed = self.genes.get('speed', 1.0)
        dist = max(1, int(speed * (1 + curiosity)))

        dx = random.randint(-dist, dist)
        dz = random.randint(-dist, dist)
        nx = max(0, min(grid.size - 1, self.x + dx))
        nz = max(0, min(grid.size - 1, self.z + dz))

        reward = self._move_to(grid, nx, nz)
        # Explorer = fun
        self.needs['fun'] = min(100, self.needs['fun'] + 2.0)
        return reward

    def _act_harvest(self, grid) -> float:
        amount = self.harvest_amount
        harvested = grid.harvest_energy(self.x, self.z, amount)
        self.energy = min(self.max_energy, self.energy + harvested)
        self.total_harvested += harvested
        # Satisfait la faim
        if harvested > 0:
            self.needs['hunger'] = min(100, self.needs['hunger'] + harvested * 0.8)

        if harvested > 5:
            return 0.8
        elif harvested > 0:
            return 0.2
        return -0.3

    def _act_rest(self) -> float:
        self.energy = min(self.max_energy, self.energy + self.rest_recovery)
        # Repos = confort + hygiene
        self.needs['comfort'] = min(100, self.needs['comfort'] + 3.0)
        self.needs['hygiene'] = min(100, self.needs['hygiene'] + 1.5)
        return 0.1 if self.energy < self.max_energy * 0.5 else -0.1

    # --- NOUVELLES ACTIONS (CONNAISSANCE) ---

    def _act_signal(self, grid, signal_board) -> float:
        """Emet un signal veridique base sur l'etat reel."""
        if not signal_board:
            return -0.1

        comm_cfg = self.config.get('life', {}).get('communication', {})
        cost = comm_cfg.get('signal_cost', 3.0)

        if self.energy < cost + 10:
            return -0.2

        # Type determine par l'etat REEL (pas de deception possible)
        signal_type = None
        if self.brain.last_perception:
            ground_e = self.brain.last_perception.get('ground_energy', 0)
            energy_ratio = self.energy / max(1, self.max_energy)

            if energy_ratio < 0.2:
                signal_type = 'NEED_HELP'
            elif ground_e > 50:
                signal_type = 'FOOD_HERE'
            elif energy_ratio > 0.6:
                signal_type = 'COME_HERE'
            else:
                signal_type = 'COME_HERE'

        if signal_type:
            self.consume_energy(cost)
            signal_board.emit(self.x, self.z, signal_type, self.id)
            self.needs['social'] = min(100, self.needs['social'] + 4.0)
            return 0.3
        return 0.0

    def _act_share_energy(self, grid, population_lookup) -> float:
        """Partage de l'energie avec un ISO proche en difficulte."""
        if not population_lookup or self.energy < 60:
            return -0.2

        perception = self.brain.last_perception
        if not perception:
            return -0.1

        nearby_cells = perception.get('nearby_isos', [])
        if not nearby_cells:
            return -0.1

        # Trouver le voisin le plus en difficulte
        best_target = None
        lowest_energy = float('inf')
        for cell in nearby_cells:
            if cell.occupied_by and cell.occupied_by != self.id:
                target_iso = population_lookup(cell.occupied_by)
                if target_iso and target_iso.alive and target_iso.energy < lowest_energy:
                    lowest_energy = target_iso.energy
                    best_target = target_iso

        if not best_target or best_target.energy > self.energy * 0.5:
            return -0.1

        # Partager 15% de son energie
        share_amount = self.energy * 0.15
        self.consume_energy(share_amount)
        best_target.energy = min(best_target.max_energy,
                                 best_target.energy + share_amount)
        # Social boost pour les deux
        self.needs['social'] = min(100, self.needs['social'] + 8.0)
        best_target.needs['social'] = min(100, best_target.needs['social'] + 5.0)

        return 0.6  # L'altruisme est recompense

    def _act_cooperate(self, grid, population_lookup) -> float:
        """Cooperation de groupe -- bonus energie pour tous les proches."""
        perception = self.brain.last_perception
        if not perception or not population_lookup:
            return -0.1

        nearby_cells = perception.get('nearby_isos', [])
        if len(nearby_cells) < 2:
            return -0.1

        # Petit cout de coordination
        self.consume_energy(1.0)

        # Bonus pour soi et les voisins
        bonus = 2.0
        self.energy = min(self.max_energy, self.energy + bonus)

        cooperators = 0
        for cell in nearby_cells[:5]:
            if cell.occupied_by and cell.occupied_by != self.id:
                target = population_lookup(cell.occupied_by)
                if target and target.alive:
                    target.energy = min(target.max_energy,
                                        target.energy + bonus * 0.5)
                    cooperators += 1
        # Cooperation = social + fun
        self.needs['social'] = min(100, self.needs['social'] + 6.0)
        self.needs['fun'] = min(100, self.needs['fun'] + 4.0)

        return 0.4 + cooperators * 0.1

    # --- APPRENTISSAGE PAR L'ACTION ---

    def _learn_from_action(self, action: str, reward: float):
        """Gagne de la connaissance en executant des actions."""
        knowledge_cfg = self.config.get('life', {}).get('knowledge', {})
        if not knowledge_cfg.get('enabled', True):
            return

        growth = knowledge_cfg.get('experience_growth', 0.005)

        domain_map = {
            'harvest': 'physics',
            'move_to_energy': 'physics',
            'rest': 'physics',
            'share_energy': 'social',
            'cooperate': 'social',
            'signal': 'communication',
            'explore': 'ecology',
        }

        domain = domain_map.get(action)
        if domain and reward > 0:
            self.knowledge.absorb_experience(domain, growth * reward)

        # La logique grandit avec toute experience positive significative
        if reward > 0.3:
            self.knowledge.absorb_experience('logic', growth * 0.5)

    # --- DEPLACEMENT ---

    def _move_towards(self, grid, tx: int, tz: int) -> float:
        speed = max(1, int(self.genes.get('speed', 1.0)))
        dx = max(-speed, min(speed, tx - self.x))
        dz = max(-speed, min(speed, tz - self.z))
        nx = max(0, min(grid.size - 1, self.x + dx))
        nz = max(0, min(grid.size - 1, self.z + dz))
        return self._move_to(grid, nx, nz)

    def _move_to(self, grid, nx: int, nz: int) -> float:
        if nx == self.x and nz == self.z:
            return -0.1

        dist = math.sqrt((nx - self.x) ** 2 + (nz - self.z) ** 2)
        cost = self.move_cost * dist
        self.consume_energy(cost)

        grid.clear_occupancy(self.x, self.z)
        self.x = nx
        self.z = nz
        self.distance_traveled += dist
        grid.set_occupancy(self.x, self.z, self.id)

        return 0.1

    # --- ENERGIE & VIE ---

    def consume_energy(self, amount: float):
        self.energy -= amount
        if self.energy <= 0:
            self.die(cause='starvation')

    def can_reproduce(self) -> bool:
        return (self.alive and
                self.energy >= self.reproduction_threshold and
                self.age > 100)

    def die(self, cause: str = 'unknown'):
        self.alive = False
        self.energy = 0

    def get_position(self) -> Tuple[int, int]:
        return (self.x, self.z)

    # --- SERIALISATION ---

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'x': self.x, 'z': self.z,
            'energy': round(self.energy, 1),
            'max_energy': self.max_energy,
            'age': self.age,
            'generation': self.generation,
            'alive': self.alive,
            'genes': self.genes,
            'last_action': self.last_action,
            'children': self.children_count,
            'total_harvested': round(self.total_harvested, 1),
            'distance': round(self.distance_traveled, 1),
            'brain': self.brain.get_stats(),
            'knowledge': self.knowledge.to_dict(),
            'needs': {k: round(v, 1) for k, v in self.needs.items()},
            'mood': round(self.mood, 1),
            'mood_label': self.mood_label,
        }
