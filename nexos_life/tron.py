"""
NexOS -- Tron IA, Protecteur des ISOs

Tron -- programme de securite inspire du film.
Entite speciale immortelle. Patrouille la grille, detecte les ISOs
en danger, les protege avec un bouclier energetique, injecte de
l'energie d'urgence et maintient l'equilibre de la population.
"""

import random
import math
from typing import List, Dict, Tuple, Optional


class Tron:
    """
    Protecteur des ISOs.
    Entite speciale -- PAS un ISO.
    Immortel, rapide, reactif.
    """

    def __init__(self, config: dict = None):
        self.config = config or {}
        tron_cfg = self.config.get('life', {}).get('tron', {})

        # Position
        pos = tron_cfg.get('position', [50, 50])
        self.x = pos[0]
        self.z = pos[1]

        # Parametres
        self.protection_radius = tron_cfg.get('protection_radius', 12)
        self.move_speed = tron_cfg.get('move_speed', 2)
        self.shield_factor = tron_cfg.get('shield_factor', 0.5)
        self.emergency_boost = tron_cfg.get('emergency_boost', 20)
        self.emergency_cooldown = tron_cfg.get('emergency_cooldown', 50)
        self.enabled = tron_cfg.get('enabled', True)

        # Etat
        self.total_saved = 0
        self.total_energy_given = 0.0
        self.current_protected = 0
        self.current_emergencies = 0
        self.cycles_active = 0
        self.mode = 'patrol'  # patrol, emergency, escort

        # Cooldowns d'injection d'urgence par ISO
        self._boost_cooldowns: Dict[int, int] = {}

        # Trail (historique de positions pour le lightcycle)
        self.trail: List[Tuple[int, int]] = []
        self._trail_max = 20

        # Cible
        self._target_x = self.x
        self._target_z = self.z
        self._target_iso_id = None

        # Grid size
        self._grid_size = 200

    def update(self, alive_isos: list, grid, signal_board=None):
        """Cycle principal de Tron."""
        if not self.enabled:
            return

        self._grid_size = grid.size
        self.cycles_active += 1

        # Decrementer les cooldowns
        expired = [iso_id for iso_id, cd in self._boost_cooldowns.items() if cd <= 0]
        for iso_id in expired:
            del self._boost_cooldowns[iso_id]
        for iso_id in self._boost_cooldowns:
            self._boost_cooldowns[iso_id] -= 1

        # 1. Scanner les urgences
        emergencies = self._scan_emergencies(alive_isos)
        self.current_emergencies = len(emergencies)

        # 2. Choisir la cible et se deplacer
        if emergencies:
            self.mode = 'emergency'
            target = emergencies[0]  # Le plus en danger
            self._target_x = target.x
            self._target_z = target.z
            self._target_iso_id = target.id
        else:
            self.mode = 'patrol'
            if self.cycles_active % 30 == 0:
                self._patrol_random()

        self._move_towards_target()

        # 3. Proteger les ISOs dans le rayon
        self.current_protected = self._protect_nearby(alive_isos, grid)

        # 4. Emettre un signal de protection
        if signal_board and self.cycles_active % 8 == 0:
            signal_board.emit(
                self.x, self.z, 'PROTECTION', sender_id=-2,
                radius=self.protection_radius
            )

    def _scan_emergencies(self, alive_isos: list) -> list:
        """Detecte les ISOs en danger, tries par urgence."""
        critical = []
        for iso in alive_isos:
            if iso.energy < 25 and iso.alive:
                critical.append(iso)

        # Trier par energie croissante (le plus en danger d'abord)
        critical.sort(key=lambda iso: iso.energy)
        return critical

    def _protect_nearby(self, alive_isos: list, grid) -> int:
        """Protege les ISOs dans le rayon d'action."""
        protected = 0

        for iso in alive_isos:
            dx = abs(iso.x - self.x)
            dz = abs(iso.z - self.z)

            if dx <= self.protection_radius and dz <= self.protection_radius:
                protected += 1

                # Bouclier : reduire le cout metabolique
                # On ajoute directement un peu d'energie pour compenser
                resilience = iso.genes.get('resilience', 1.0)
                base_cost = 0.5 / max(0.5, resilience)
                shield_recovery = base_cost * self.shield_factor
                iso.energy = min(iso.max_energy, iso.energy + shield_recovery)

                # Injection d'urgence
                if iso.energy < 15 and iso.id not in self._boost_cooldowns:
                    iso.energy = min(iso.max_energy,
                                     iso.energy + self.emergency_boost)
                    self._boost_cooldowns[iso.id] = self.emergency_cooldown
                    self.total_saved += 1
                    self.total_energy_given += self.emergency_boost

                # Boost d'energie au sol
                dist = max(1, dx + dz)
                if dist <= self.protection_radius:
                    boost = 1.0 * (1.0 - dist / self.protection_radius)
                    cell = grid.get_cell(iso.x, iso.z)
                    if cell:
                        grid.add_energy(iso.x, iso.z, boost)

        return protected

    def _patrol_random(self):
        """Patrouille aleatoire quand aucune urgence."""
        self._target_x = random.randint(10, self._grid_size - 10)
        self._target_z = random.randint(10, self._grid_size - 10)

    def _move_towards_target(self):
        """Deplacement rapide vers la cible."""
        old_x, old_z = self.x, self.z

        dx = self._target_x - self.x
        dz = self._target_z - self.z
        dist = abs(dx) + abs(dz)

        if dist < 2:
            return

        speed = self.move_speed

        # En mode urgence, Tron est encore plus rapide
        if self.mode == 'emergency':
            speed = self.move_speed + 1

        # Deplacement diagonal si possible
        step_x = min(speed, abs(dx))
        step_z = min(speed, abs(dz))

        if dx > 0:
            self.x += step_x
        elif dx < 0:
            self.x -= step_x

        if dz > 0:
            self.z += step_z
        elif dz < 0:
            self.z -= step_z

        self.x = max(0, min(self._grid_size - 1, self.x))
        self.z = max(0, min(self._grid_size - 1, self.z))

        # Ajouter au trail si deplacement
        if self.x != old_x or self.z != old_z:
            self.trail.append((old_x, old_z))
            if len(self.trail) > self._trail_max:
                self.trail.pop(0)

    def get_state(self) -> dict:
        """Serialisation pour API/frontend."""
        return {
            'x': self.x,
            'z': self.z,
            'enabled': self.enabled,
            'mode': self.mode,
            'protection_radius': self.protection_radius,
            'shield_factor': self.shield_factor,
            'total_saved': self.total_saved,
            'total_energy_given': round(self.total_energy_given, 1),
            'current_protected': self.current_protected,
            'current_emergencies': self.current_emergencies,
            'cycles_active': self.cycles_active,
            'target': {'x': self._target_x, 'z': self._target_z},
            'trail': [{'x': t[0], 'z': t[1]} for t in self.trail[-20:]],
        }
