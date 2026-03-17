"""
NexOS -- Systeme de vehicules (Lightcycles)
Les ISOs peuvent monter sur des Lightcycles pour se deplacer rapidement.
Chaque Lightcycle laisse un mur de lumiere derriere lui.
"""

import random
import math
from typing import List, Dict, Optional, Tuple


class Lightcycle:
    """
    Un Lightcycle : moto de lumiere du monde Tron.
    Se deplace en ligne droite, tourne a 90 degres.
    Laisse un mur de lumiere (trail) derriere lui.
    """

    _next_id = 0

    def __init__(self, x: float, z: float, grid_size: int = 500):
        Lightcycle._next_id += 1
        self.id = Lightcycle._next_id
        self.x = x
        self.z = z
        self.grid_size = grid_size

        # Direction (0=nord, 1=est, 2=sud, 3=ouest)
        self.direction = random.randint(0, 3)
        self.speed = 3.0 + random.random() * 2.0  # Vitesse variable

        # ISO passager (id ou None)
        self.rider_id: Optional[int] = None

        # Trail (mur de lumiere)
        self.trail: List[Dict[str, float]] = [{'x': x, 'z': z}]
        self.max_trail_length = 50  # Points max dans le trail
        self.trail_timer = 0.0

        # Couleur du trail (heritee du rider ou cyan par defaut)
        self.color = "cyan"  # cyan, orange, gold

        # Etat
        self.active = True
        self.lifetime = 0
        self.turn_cooldown = 0  # Empeche les tours trop rapides

    def update(self, grid=None) -> None:
        """Met a jour la position du Lightcycle."""
        if not self.active:
            return

        self.lifetime += 1
        self.turn_cooldown = max(0, self.turn_cooldown - 1)
        self.trail_timer += 1

        # Mouvement selon la direction
        dx, dz = self._direction_vector()
        self.x += dx * self.speed
        self.z += dz * self.speed

        # Bordures : rebondit
        if self.x < 5:
            self.x = 5
            self._turn_right()
        elif self.x > self.grid_size - 5:
            self.x = self.grid_size - 5
            self._turn_left()
        if self.z < 5:
            self.z = 5
            self._turn_left()
        elif self.z > self.grid_size - 5:
            self.z = self.grid_size - 5
            self._turn_right()

        # Ajouter un point au trail toutes les N updates
        if self.trail_timer >= 3:
            self.trail_timer = 0
            self.trail.append({'x': self.x, 'z': self.z})
            # Limiter la longueur du trail
            if len(self.trail) > self.max_trail_length:
                self.trail = self.trail[-self.max_trail_length:]

        # Changement de direction aleatoire
        if self.turn_cooldown == 0 and random.random() < 0.03:
            if random.random() < 0.5:
                self._turn_left()
            else:
                self._turn_right()
            self.turn_cooldown = 10

    def _direction_vector(self) -> Tuple[float, float]:
        """Retourne le vecteur de direction (dx, dz)."""
        if self.direction == 0:
            return (0, -1)   # Nord
        elif self.direction == 1:
            return (1, 0)    # Est
        elif self.direction == 2:
            return (0, 1)    # Sud
        else:
            return (-1, 0)   # Ouest

    def _turn_left(self) -> None:
        self.direction = (self.direction - 1) % 4

    def _turn_right(self) -> None:
        self.direction = (self.direction + 1) % 4

    def get_state(self) -> dict:
        """Retourne l'etat pour envoi JSON a Godot."""
        return {
            'id': self.id,
            'x': round(self.x, 1),
            'z': round(self.z, 1),
            'direction': self.direction,
            'speed': self.speed,
            'rider_id': self.rider_id,
            'color': self.color,
            'active': self.active,
            'trail': self.trail[-30:],  # Limiter le trail envoye
        }


class VehicleManager:
    """
    Gere la flotte de Lightcycles dans NexOS.
    Spawn/despawn automatique, attribution aux ISOs.
    """

    def __init__(self, config: dict = None):
        self.config = config or {}
        vehicle_cfg = self.config.get('life', {}).get('vehicles', {})
        self.enabled = vehicle_cfg.get('enabled', True)
        self.max_vehicles = vehicle_cfg.get('max_lightcycles', 20)
        self.spawn_chance = vehicle_cfg.get('spawn_chance', 0.02)
        self.grid_size = self.config.get('grid', {}).get('size', 500)

        self.lightcycles: List[Lightcycle] = []
        self._tick = 0

    def update(self, isos: list = None, grid=None) -> None:
        """Met a jour tous les vehicules."""
        if not self.enabled:
            return

        self._tick += 1

        # Spawn de nouveaux Lightcycles
        if len(self.lightcycles) < self.max_vehicles and random.random() < self.spawn_chance:
            self._spawn_lightcycle()

        # Update chaque Lightcycle
        for lc in self.lightcycles:
            lc.update(grid)

        # Nettoyage des Lightcycles inactifs ou trop vieux
        self.lightcycles = [lc for lc in self.lightcycles
                           if lc.active and lc.lifetime < 3000]

    def _spawn_lightcycle(self) -> None:
        """Spawn un nouveau Lightcycle a une position aleatoire."""
        x = random.uniform(50, self.grid_size - 50)
        z = random.uniform(50, self.grid_size - 50)
        lc = Lightcycle(x, z, self.grid_size)

        # Couleur aleatoire style Tron
        lc.color = random.choice(["cyan", "cyan", "cyan", "orange", "gold"])

        self.lightcycles.append(lc)

    def get_all_states(self) -> list:
        """Retourne les etats de tous les Lightcycles actifs."""
        return [lc.get_state() for lc in self.lightcycles if lc.active]

    def get_stats(self) -> dict:
        """Stats globales des vehicules."""
        return {
            'total': len(self.lightcycles),
            'active': sum(1 for lc in self.lightcycles if lc.active),
        }
