"""
NexOS -- Daedalus, Facilitateur d'Innovation

Daedalus (genius créatif) -- Agent IA Claude sur la grille.
Entite speciale immortelle qui catalyse l'innovation et l'exploration.
Il cherche les zones d'ignorance et encourage l'experimentation par le questionnement.
"""

import random
from typing import List, Tuple, Optional


class Daedalus:
    """
    Facilitateur d'Innovation et d'Exploration.
    Entite speciale -- PAS un ISO.
    Immortel, curieux, bienveillant.
    Encourage l'innovation plutôt que la transmission directe.
    """

    def __init__(self, config: dict = None):
        self.config = config or {}
        daedalus_cfg = self.config.get('life', {}).get('daedalus', {})

        # Position
        pos = daedalus_cfg.get('position', [250, 125])
        self.x = pos[0]
        self.z = pos[1]

        # Parametres
        self.influence_radius = daedalus_cfg.get('influence_radius', 20)
        self.action_rate = daedalus_cfg.get('action_rate', 0.02)
        self.move_speed = daedalus_cfg.get('move_speed', 2)
        self.enabled = daedalus_cfg.get('enabled', True)

        # Etat
        self.innovation_level = 1.0  # Capacite d'innovation
        self.total_inspired = 0  # Nombre d'ISOs inspires
        self.total_questions_asked = 0  # Nombre de fois ou il a inspire la reflexion
        self.current_seekers = 0  # ISOs autour de lui en ce moment
        self.cycles_active = 0

        # Cible de deplacement
        self._target_x = self.x
        self._target_z = self.z
        self._retarget_cooldown = 0

        # Grid size (set during first update)
        self._grid_size = 200

    def update(self, alive_isos: list, grid, signal_board=None):
        """Cycle principal de Daedalus."""
        if not self.enabled:
            return

        self._grid_size = grid.size
        self.cycles_active += 1

        # 1. Inspirer les ISOs proches par le questionnement
        self.current_seekers = self._inspire_nearby(alive_isos)

        # 2. Emettre un signal d'innovation
        if signal_board and self.cycles_active % 15 == 0:
            signal_board.emit(
                self.x, self.z, 'INNOVATION', sender_id=-4,
                radius=self.influence_radius
            )

        # 3. Se deplacer vers la zone la plus stagnante
        self._retarget_cooldown -= 1
        if self._retarget_cooldown <= 0:
            self._find_stagnant_zone(alive_isos)
            self._retarget_cooldown = 60  # Recalcule la cible tous les 60 cycles

        self._move_towards_target()

    def _inspire_nearby(self, alive_isos: list) -> int:
        """Inspire les ISOs proches par le questionnement.

        Au lieu de transmettre directement, il encourage la reflexion
        et l'exploration par des 'signaux de curiosite'.
        """
        seekers = 0
        for iso in alive_isos:
            dx = abs(iso.x - self.x)
            dz = abs(iso.z - self.z)
            if dx <= self.influence_radius and dz <= self.influence_radius:
                # Plus proche = plus d'inspiration
                dist = max(1, dx + dz)
                proximity = 1.0 - (dist / (self.influence_radius * 2))

                # Bonus d'exploration plutôt que d'enseignement direct
                # Les ISOs proches augmentent leur curiosite
                effective_rate = self.action_rate * max(0.3, proximity)

                # Augmenter le gene de curiosite
                iso.genes['curiosity'] = min(
                    1.0,
                    iso.genes.get('curiosity', 0.5) + effective_rate * 0.01
                )

                # Augmenter le taux d'exploration dans le cerveau (via brain.memory)
                iso.brain.memory.exploration_rate = min(
                    0.8,
                    iso.brain.memory.exploration_rate + effective_rate * 0.02
                )
                # Synchroniser l'attribut de surface pour le suivi des zones
                iso.exploration_chance = iso.brain.memory.exploration_rate

                self.total_questions_asked += 1
                seekers += 1

        self.total_inspired += seekers
        return seekers

    def _find_stagnant_zone(self, alive_isos: list):
        """Trouve la zone ou il y a le moins de mouvement et d'exploration."""
        if not alive_isos:
            return

        # Diviser la grille en zones 50x50
        zone_size = 50
        zones = {}  # (zx, zz) -> (avg_curiosity, avg_exploration, count)

        for iso in alive_isos:
            zx = iso.x // zone_size
            zz = iso.z // zone_size
            key = (zx, zz)

            curiosity = iso.genes.get('curiosity', 0.5)
            exploration = getattr(iso, 'exploration_chance', 0.3)

            if key not in zones:
                zones[key] = [0.0, 0.0, 0]
            zones[key][0] += curiosity
            zones[key][1] += exploration
            zones[key][2] += 1

        if not zones:
            return

        # Trouver la zone avec le moins d'exploration
        stagnant = None
        lowest_score = float('inf')
        for (zx, zz), (total_c, total_e, count) in zones.items():
            if count < 2:
                continue  # Ignorer les zones presque vides

            avg_c = total_c / count
            avg_e = total_e / count
            # Score = combinaison basse de curiosite et exploration
            score = avg_c * 0.4 + avg_e * 0.6

            if score < lowest_score:
                lowest_score = score
                stagnant = (zx, zz)

        if stagnant:
            # Cible = centre de la zone
            self._target_x = stagnant[0] * zone_size + zone_size // 2
            self._target_z = stagnant[1] * zone_size + zone_size // 2
            # Garder dans les limites
            self._target_x = max(5, min(self._grid_size - 5, self._target_x))
            self._target_z = max(5, min(self._grid_size - 5, self._target_z))

    def _move_towards_target(self):
        """Deplacement vers la cible."""
        dx = self._target_x - self.x
        dz = self._target_z - self.z
        dist = abs(dx) + abs(dz)

        if dist < 2:
            return  # Deja a la cible

        # Deplacement plus rapide que Minerve
        step = max(1, int(self.move_speed))
        if abs(dx) > abs(dz):
            self.x += step if dx > 0 else -step
        else:
            self.z += step if dz > 0 else -step

        self.x = max(0, min(self._grid_size - 1, self.x))
        self.z = max(0, min(self._grid_size - 1, self.z))

    def get_state(self) -> dict:
        """Serialisation pour API/frontend."""
        return {
            'x': self.x,
            'z': self.z,
            'enabled': self.enabled,
            'influence_radius': self.influence_radius,
            'action_rate': self.action_rate,
            'innovation_level': self.innovation_level,
            'total_inspired': self.total_inspired,
            'total_questions_asked': self.total_questions_asked,
            'current_seekers': self.current_seekers,
            'cycles_active': self.cycles_active,
            'target': {'x': self._target_x, 'z': self._target_z},
        }
