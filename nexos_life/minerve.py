"""
NexOS -- Minerve, Gardienne du Savoir

Minerve (Minerva) -- deesse romaine de la sagesse, de l'intelligence
et de la pensee elevee. Entite speciale immortelle sur la grille.
Elle enseigne les ISOs a proximite, se deplace vers les zones
ou le savoir est le plus faible, et emet des signaux de sagesse.
"""

import random
from typing import List, Tuple, Optional


class Minerve:
    """
    Gardienne de la Bibliotheque du Savoir.
    Entite speciale -- PAS un ISO.
    Immortelle, omnisciente, bienveillante.
    """

    def __init__(self, config: dict = None):
        self.config = config or {}
        minerve_cfg = self.config.get('life', {}).get('minerve', {})

        # Position
        pos = minerve_cfg.get('position', [100, 100])
        self.x = pos[0]
        self.z = pos[1]

        # Parametres
        self.teaching_radius = minerve_cfg.get('teaching_radius', 15)
        self.teaching_rate = minerve_cfg.get('teaching_rate', 0.01)
        self._base_teaching_rate = self.teaching_rate  # Pour le bonus bibliotheque
        self.move_speed = minerve_cfg.get('move_speed', 0.5)
        self.enabled = minerve_cfg.get('enabled', True)

        # Etat
        self.wisdom_level = 1.0  # Maitrise totale
        self.total_taught = 0
        self.total_knowledge_given = 0.0
        self.current_students = 0
        self.cycles_active = 0

        # Cible de deplacement
        self._target_x = self.x
        self._target_z = self.z
        self._retarget_cooldown = 0

        # Grid size (set during first update)
        self._grid_size = 200

    def update(self, alive_isos: list, grid, signal_board=None):
        """Cycle principal de Minerve."""
        if not self.enabled:
            return

        self._grid_size = grid.size
        self.cycles_active += 1

        # 1. Enseigner aux ISOs proches
        self.current_students = self._teach_nearby(alive_isos)

        # 2. Emettre un signal de sagesse
        if signal_board and self.cycles_active % 10 == 0:
            signal_board.emit(
                self.x, self.z, 'WISDOM', sender_id=-1,
                radius=self.teaching_radius
            )

        # 3. Se deplacer vers la zone la plus ignorante
        self._retarget_cooldown -= 1
        if self._retarget_cooldown <= 0:
            self._find_neediest_zone(alive_isos)
            self._retarget_cooldown = 50  # Recalcule la cible tous les 50 cycles

        self._move_towards_target()

    def _teach_nearby(self, alive_isos: list) -> int:
        """Enseigne a tous les ISOs dans le rayon."""
        students = 0
        for iso in alive_isos:
            dx = abs(iso.x - self.x)
            dz = abs(iso.z - self.z)
            if dx <= self.teaching_radius and dz <= self.teaching_radius:
                # Plus proche = enseignement plus efficace
                dist = max(1, dx + dz)
                proximity = 1.0 - (dist / (self.teaching_radius * 2))
                effective_rate = self.teaching_rate * max(0.2, proximity)

                iso.knowledge.absorb_from_minerve(effective_rate)
                self.total_knowledge_given += effective_rate * 5  # 5 domaines
                students += 1

        self.total_taught += students
        return students

    def _find_neediest_zone(self, alive_isos: list):
        """Trouve la zone ou les ISOs ont le moins de connaissances."""
        if not alive_isos:
            return

        # Diviser la grille en zones 50x50
        zone_size = 50
        zones = {}  # (zx, zz) -> (total_knowledge, count)

        for iso in alive_isos:
            zx = iso.x // zone_size
            zz = iso.z // zone_size
            key = (zx, zz)
            total_k = iso.knowledge.get_total_knowledge()
            if key not in zones:
                zones[key] = [0.0, 0]
            zones[key][0] += total_k
            zones[key][1] += 1

        if not zones:
            return

        # Trouver la zone avec la plus faible connaissance moyenne
        neediest = None
        lowest_avg = float('inf')
        for (zx, zz), (total_k, count) in zones.items():
            if count < 2:
                continue  # Ignorer les zones presque vides
            avg = total_k / count
            if avg < lowest_avg:
                lowest_avg = avg
                neediest = (zx, zz)

        if neediest:
            # Cible = centre de la zone
            self._target_x = neediest[0] * zone_size + zone_size // 2
            self._target_z = neediest[1] * zone_size + zone_size // 2
            # Garder dans les limites
            self._target_x = max(5, min(self._grid_size - 5, self._target_x))
            self._target_z = max(5, min(self._grid_size - 5, self._target_z))

    def _move_towards_target(self):
        """Deplacement lent vers la cible."""
        dx = self._target_x - self.x
        dz = self._target_z - self.z
        dist = abs(dx) + abs(dz)

        if dist < 2:
            return  # Deja a la cible

        # Deplacement lent
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
            'teaching_radius': self.teaching_radius,
            'teaching_rate': self.teaching_rate,
            'wisdom_level': self.wisdom_level,
            'total_taught': self.total_taught,
            'total_knowledge_given': round(self.total_knowledge_given, 1),
            'current_students': self.current_students,
            'cycles_active': self.cycles_active,
            'target': {'x': self._target_x, 'z': self._target_z},
        }
