"""
NexOS — Grille spatiale 2D
Environnement riche ou les ISOs evoluent.
Chaque cellule contient de l'energie que les ISOs peuvent recolter.
"""

import base64
import random
from dataclasses import dataclass, field
from typing import List, Tuple, Optional

import numpy as np


@dataclass
class GridCell:
    """Une cellule de la grille"""
    x: int
    z: int
    energy: float = 100.0
    max_energy: float = 200.0
    terrain: str = 'plain'       # plain, fertile, barren
    occupied_by: Optional[int] = None   # ID de l'ISO occupant


class Grid:
    """
    Grille 2D representant l'environnement physique.
    - Cellules avec energie regenerable
    - Terrains varies (fertile = plus d'energie)
    - Methodes de voisinage pour la perception ISO
    """

    def __init__(self, size: int = 200, config: dict = None):
        self.size = size
        self.config = config or {}

        grid_cfg = self.config.get('grid', {})
        self.regen_rate = grid_cfg.get('energy_regen_rate', 0.5)
        self.max_energy = grid_cfg.get('max_cell_energy', 200)
        e_min = grid_cfg.get('initial_energy_min', 50)
        e_max = grid_cfg.get('initial_energy_max', 150)

        # Grille d'energie (numpy pour la performance)
        self.energy = np.random.uniform(e_min, e_max, (size, size)).astype(np.float32)

        # Terrain : style configurable
        # VECTORISE -- supporte des grilles de 10000+ sans lag
        terrain_style = grid_cfg.get('terrain_style', 'tron')
        if terrain_style == 'tron':
            self.terrain_id = self._generate_tron_terrain()
        else:
            # Bruit blanc aleatoire (comportement original)
            terrain_roll = np.random.random((size, size)).astype(np.float32)
            self.terrain_id = np.zeros((size, size), dtype=np.int8)
            self.terrain_id[terrain_roll < 0.10] = 2   # barren (10%)
            self.terrain_id[(terrain_roll >= 0.10) & (terrain_roll < 0.30)] = 1  # fertile (20%)

        # Appliquer les multiplicateurs d'energie initiaux
        self.energy[self.terrain_id == 2] *= 0.3   # Aride = peu d'energie
        self.energy[self.terrain_id == 1] *= 1.5   # Fertile = bonus

        # Precalculer les multiplicateurs de regen (ne change jamais)
        self._regen_mult = np.ones((size, size), dtype=np.float32)
        self._regen_mult[self.terrain_id == 1] = 2.0   # fertile x2
        self._regen_mult[self.terrain_id == 2] = 0.3   # barren x0.3

        # Taux de diffusion d'energie entre cellules voisines
        self._diffusion_rate = float(grid_cfg.get('diffusion_rate', 0.01))

        # Compat : terrain string pour get_cell()
        self._terrain_names = {0: 'plain', 1: 'fertile', 2: 'barren'}

        # Grille d'occupation (ID de l'ISO ou 0)
        self.occupancy = np.zeros((size, size), dtype=np.int32)

        self.cycle = 0

    def _generate_tron_terrain(self) -> np.ndarray:
        """Genere un terrain inspire du monde Tron.

        Geographie :
        - Ville centrale  : zone fertile, haute regeneration (rayon 10%)
        - Conduits        : 4 lignes fertiles (H, V, diag x2) traversant le monde
        - Zone intermediaire : plaine + ilots fertiles epars
        - Outlands        : peripherie aride hostile (dist > 65%)
        """
        size = self.size
        cx, cz = size // 2, size // 2

        # Matrices de coordonnees (float32 pour economiser la memoire)
        xs = np.arange(size, dtype=np.float32)
        zs = np.arange(size, dtype=np.float32)
        X, Z = np.meshgrid(xs, zs, indexing='ij')

        # Distance euclidienne depuis le centre (normalisee 0-1, 1=coin)
        dist = np.sqrt((X - cx) ** 2 + (Z - cz) ** 2)
        dist_norm = dist / (cx * 1.4143)  # ~sqrt(2) * cx

        # Base : tout en plaine (0)
        terrain = np.zeros((size, size), dtype=np.int8)

        # --- Ville centrale : fertile ---
        terrain[dist_norm < 0.10] = 1

        # --- Conduits d'energie : fertile ---
        w_main = max(20, size // 100)   # largeur principale (~50 cells sur 5000)
        w_diag = max(10, size // 200)   # largeur diagonale (~25 cells sur 5000)

        # Conduit horizontal (x autour du centre)
        terrain[cx - w_main:cx + w_main, :] = 1
        # Conduit vertical (z autour du centre)
        terrain[:, cz - w_main:cz + w_main] = 1
        # Conduit diagonal principal (|X - Z| < w_diag)
        terrain[np.abs(X - Z) < w_diag] = 1
        # Conduit anti-diagonal (|X + Z - size| < w_diag)
        terrain[np.abs(X + Z - size) < w_diag] = 1

        # --- Ilots fertiles epars dans la zone plaine ---
        n_islands = 30
        island_x = np.random.randint(w_main, size - w_main, n_islands)
        island_z = np.random.randint(w_main, size - w_main, n_islands)
        island_r = np.random.randint(30, 120, n_islands)

        for i in range(n_islands):
            ix, iz, ir = int(island_x[i]), int(island_z[i]), int(island_r[i])
            x0, x1 = max(0, ix - ir), min(size, ix + ir)
            z0, z1 = max(0, iz - ir), min(size, iz + ir)
            sub_X = X[x0:x1, z0:z1]
            sub_Z = Z[x0:x1, z0:z1]
            sub_dist = np.sqrt((sub_X - ix) ** 2 + (sub_Z - iz) ** 2)
            # Seulement sur les plaines (pas sur conduits, pas en outlands futurs)
            mask = (sub_dist < ir) & (terrain[x0:x1, z0:z1] == 0)
            terrain[x0:x1, z0:z1][mask] = 1

        # --- Outlands : peripherie aride (ecrasent les conduits aux bords) ---
        terrain[dist_norm > 0.65] = 2

        return terrain

    def reset_energy(self):
        """Reinitialise l'energie de la grille."""
        grid_cfg = self.config.get('grid', {})
        e_min = grid_cfg.get('initial_energy_min', 50)
        e_max = grid_cfg.get('initial_energy_max', 150)
        self.energy = np.random.uniform(e_min, e_max, (self.size, self.size)).astype(np.float32)
        # Reappliquer les multiplicateurs terrain
        self.energy[self.terrain_id == 2] *= 0.3
        self.energy[self.terrain_id == 1] *= 1.5
        self.occupancy = np.zeros((self.size, self.size), dtype=np.int32)
        self.cycle = 0

    def _clamp(self, v: int) -> int:
        return max(0, min(self.size - 1, v))

    def get_cell(self, x: int, z: int) -> GridCell:
        """Retourne les donnees d'une cellule"""
        x, z = self._clamp(x), self._clamp(z)
        return GridCell(
            x=x, z=z,
            energy=float(self.energy[x, z]),
            max_energy=self.max_energy,
            terrain=self._terrain_names.get(int(self.terrain_id[x, z]), 'plain'),
            occupied_by=int(self.occupancy[x, z]) if self.occupancy[x, z] != 0 else None
        )

    def get_neighbors(self, x: int, z: int, radius: int = 5) -> List[GridCell]:
        """Retourne les cellules dans un rayon autour de (x,z)"""
        cells = []
        for dx in range(-radius, radius + 1):
            for dz in range(-radius, radius + 1):
                if dx == 0 and dz == 0:
                    continue
                nx, nz = x + dx, z + dz
                if 0 <= nx < self.size and 0 <= nz < self.size:
                    cells.append(self.get_cell(nx, nz))
        return cells

    def harvest_energy(self, x: int, z: int, amount: float) -> float:
        """ISO recolte de l'energie au sol. Retourne la quantite reellement recoltee."""
        x, z = self._clamp(x), self._clamp(z)
        available = self.energy[x, z]
        taken = min(amount, available)
        self.energy[x, z] -= taken
        return float(taken)

    def add_energy(self, x: int, z: int, amount: float):
        """Ajoute de l'energie au sol (ex: zone protegee par Tron)."""
        x, z = self._clamp(x), self._clamp(z)
        self.energy[x, z] = min(self.max_energy, self.energy[x, z] + amount)

    def set_occupancy(self, x: int, z: int, iso_id: int):
        """Marque une cellule comme occupee par un ISO"""
        x, z = self._clamp(x), self._clamp(z)
        self.occupancy[x, z] = iso_id

    def clear_occupancy(self, x: int, z: int):
        """Libere une cellule"""
        x, z = self._clamp(x), self._clamp(z)
        self.occupancy[x, z] = 0

    def is_occupied(self, x: int, z: int) -> bool:
        x, z = self._clamp(x), self._clamp(z)
        return self.occupancy[x, z] != 0

    def update(self):
        """Regeneration de l'energie — appelee chaque cycle.
        VECTORISE : supporte des grilles de 10000x10000 sans lag."""
        self.cycle += 1

        # Regeneration vectorisee (pas de boucle Python)
        self.energy += self.regen_rate * self._regen_mult
        np.clip(self.energy, 0, self.max_energy, out=self.energy)

        # Diffusion d'energie : flux vers les cellules voisines appauvries
        # Cree des gradients naturels que les ISOs peuvent suivre
        if self._diffusion_rate > 0:
            e = self.energy
            avg = np.empty_like(e)
            avg[1:-1, 1:-1] = (e[0:-2, 1:-1] + e[2:, 1:-1] +
                               e[1:-1, 0:-2] + e[1:-1, 2:]) * 0.25
            avg[0, :] = e[0, :]    # bords : pas de diffusion hors grille
            avg[-1, :] = e[-1, :]
            avg[:, 0] = e[:, 0]
            avg[:, -1] = e[:, -1]
            self.energy = (1.0 - self._diffusion_rate) * e + self._diffusion_rate * avg
            np.clip(self.energy, 0, self.max_energy, out=self.energy)

    def get_energy_map(self, downsample: int = None) -> list:
        """Retourne la carte d'energie sous-echantillonnee pour le frontend.
        Downsample adaptatif selon la taille de la grille pour limiter le volume."""
        if downsample is None:
            # Adaptatif : garder ~60k points max pour le frontend (perf)
            if self.size <= 500:
                downsample = 2
            elif self.size <= 1000:
                downsample = 4
            elif self.size <= 2000:
                downsample = 8
            elif self.size <= 5000:
                downsample = 20
            else:
                downsample = 40

        step = downsample
        # Vectorise avec reshape -- beaucoup plus rapide que la boucle
        # Tronquer pour que size soit divisible par step
        trim_size = (self.size // step) * step
        if trim_size == 0:
            return []

        # Sous-echantillonnage par blocs
        trimmed = self.energy[:trim_size, :trim_size]
        reshaped = trimmed.reshape(trim_size // step, step, trim_size // step, step)
        block_means = reshaped.mean(axis=(1, 3))

        # Vectorise : filtrer et construire la liste sans double boucle Python
        mask = block_means > 5
        rows, cols = np.where(mask)
        coords_x = (rows * step).astype(int)
        coords_z = (cols * step).astype(int)
        energies = block_means[mask]
        result = [
            {'x': int(coords_x[k]), 'z': int(coords_z[k]), 'e': round(float(energies[k]), 1)}
            for k in range(len(energies))
        ]
        return result

    def get_terrain_map(self, downsample: int = 50) -> dict:
        """Retourne la carte de terrain en base64 pour le shader Godot.
        Le terrain est statique, donc on l'envoie une seule fois.
        Retourne un dict {data: base64, resolution: int, grid_size: int}."""
        step = downsample
        trim_size = (self.size // step) * step
        if trim_size == 0:
            return {'data': '', 'resolution': 0, 'grid_size': self.size}

        res = trim_size // step  # ex: 5000/50 = 100

        # Mode par bloc (valeur la plus frequente)
        trimmed = self.terrain_id[:trim_size, :trim_size]
        reshaped = trimmed.reshape(res, step, res, step)
        # Pour le mode : on utilise la mediane arrondie (plus rapide que scipy.stats.mode)
        block_terrain = np.median(reshaped, axis=(1, 3)).astype(np.uint8)

        # Aplatir en row-major et encoder base64
        flat = block_terrain.flatten().tobytes()
        b64 = base64.b64encode(flat).decode('ascii')
        return {
            'data': b64,
            'resolution': int(res),
            'grid_size': self.size
        }

    def get_zones(self) -> list:
        """Retourne les zones geographiques du monde Tron (usage API / IA)."""
        cx, cz = self.size // 2, self.size // 2
        w = max(20, self.size // 100)
        return [
            {'name': 'City Center', 'cx': cx, 'cz': cz,
             'radius': int(self.size * 0.10), 'terrain': 'fertile'},
            {'name': 'Outlands',    'cx': cx, 'cz': cz,
             'radius': int(self.size * 0.46), 'terrain': 'barren', 'outer': True},
            {'name': 'H-Conduit',   'cx': cx, 'cz': cz, 'width': w, 'axis': 'x'},
            {'name': 'V-Conduit',   'cx': cx, 'cz': cz, 'width': w, 'axis': 'z'},
            {'name': 'D1-Conduit',  'cx': cx, 'cz': cz,
             'width': max(10, self.size // 200), 'axis': 'diag'},
            {'name': 'D2-Conduit',  'cx': cx, 'cz': cz,
             'width': max(10, self.size // 200), 'axis': 'anti-diag'},
        ]

    def get_stats(self) -> dict:
        return {
            'total_energy': float(np.sum(self.energy)),
            'avg_energy': float(np.mean(self.energy)),
            'min_energy': float(np.min(self.energy)),
            'max_energy': float(np.max(self.energy)),
            'size': self.size,
            'cycle': self.cycle
        }
