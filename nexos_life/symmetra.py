"""
NexOS -- Symmetra, Batisseuse et Architecte

Symmetra -- entite speciale immortelle.
Construit differents types de structures sur la grille :
  - ABRI (Shelter)       : protection + bonus energie
  - BIBLIOTHEQUE (Library): boost connaissance, Minerve y enseigne 2x plus vite
  - CENTRALE (Energy Plant): regenere l'energie des cellules autour
  - TOUR COMM (Comm Tower): amplifie la portee des signaux
  - ARENE (Arena)         : accelere le fitness / ameliore les genes

Enseigne aux ISOs proches l'art de la construction.
Les ISOs formes peuvent maintenir et reparer les structures.
"""

import random
import math
from typing import List, Dict, Tuple, Optional


# ─── Grille urbaine ────────────────────────────────────────
# Symmetra planifie sur une grille de blocs (comme un plan de ville).
# Chaque bloc = BLOCK_SIZE x BLOCK_SIZE cellules de la grille principale.
# Les routes suivent les bordures de blocs.
# Les structures sont placees au centre des blocs.
BLOCK_SIZE = 40          # Taille d'un bloc urbain (cellules)
ROAD_WIDTH = 4           # Largeur des routes (cellules)
MIN_DISTRICT_STRUCTURES = 3  # Minimum pour former un quartier

# Zones de la ville : chaque type a des voisins preferes
ZONE_AFFINITIES = {
    'shelter':      ['library', 'arena', 'comm_tower'],     # Residentiel pres des services
    'library':      ['shelter', 'arena'],                    # Savoir pres des habitations
    'energy_plant': ['comm_tower'],                          # Infra ensemble, loin du centre
    'comm_tower':   ['energy_plant', 'arena'],               # Infra + loisirs
    'arena':        ['shelter', 'library'],                  # Loisirs pres du residentiel
}


# ─── Types de structures ───────────────────────────────────
STRUCTURE_TYPES = {
    'shelter': {
        'name': 'ABRI',
        'color': '#ff44ff',        # magenta
        'energy_bonus': 2.0,       # bonus energie aux ISOs
        'durability': 100.0,
        'decay': 0.15,
        'description': 'Zone protegee, bonus energie',
    },
    'library': {
        'name': 'BIBLIO',
        'color': '#ffd700',        # gold (Minerve)
        'energy_bonus': 0.5,       # petit bonus energie
        'durability': 120.0,       # plus solide
        'decay': 0.10,             # se degrade moins vite
        'knowledge_boost': 2.5,    # multiplicateur connaissance
        'description': 'Boost connaissance, Minerve enseigne 2x',
    },
    'energy_plant': {
        'name': 'CENTRALE',
        'color': '#00ff88',        # vert neon
        'energy_bonus': 0.0,       # pas de bonus direct ISO
        'durability': 80.0,        # fragile
        'decay': 0.20,
        'grid_regen': 3.0,         # regeneration grille autour
        'description': 'Regenere l\'energie de la grille',
    },
    'comm_tower': {
        'name': 'TOUR COMM',
        'color': '#4488ff',        # bleu
        'energy_bonus': 0.3,
        'durability': 90.0,
        'decay': 0.12,
        'signal_boost': 2.0,       # double la portee des signaux
        'description': 'Amplifie la portee des signaux',
    },
    'arena': {
        'name': 'ARENE',
        'color': '#ff6633',        # orange
        'energy_bonus': 1.0,
        'durability': 110.0,
        'decay': 0.18,
        'fitness_boost': 1.5,      # ameliore fitness
        'description': 'Ameliore le fitness des ISOs',
    },
}


class Structure:
    """
    Structure construite par Symmetra.
    Chaque structure a un type, un niveau (1-3), et determine ses bonus.
    Niveau 1 : construction de base
    Niveau 2 : amelioration (age > 300, utilisation > 50)
    Niveau 3 : monument (age > 800, utilisation > 200)
    """

    _next_id = 1

    # Seuils d'evolution
    LEVEL_2_AGE = 300
    LEVEL_2_USAGE = 50
    LEVEL_3_AGE = 800
    LEVEL_3_USAGE = 200

    def __init__(self, x: int, z: int, structure_type: str = 'shelter',
                 radius: int = 8, durability: float = None):
        self.id = Structure._next_id
        Structure._next_id += 1

        self.x = x
        self.z = z
        self.structure_type = structure_type
        self.radius = radius

        # Proprietes du type
        type_info = STRUCTURE_TYPES.get(structure_type, STRUCTURE_TYPES['shelter'])
        self.energy_bonus = type_info['energy_bonus']
        self.durability = durability or type_info['durability']
        self.max_durability = self.durability
        self.decay_rate = type_info['decay']
        self.name = type_info['name']
        self.color = type_info['color']

        # Niveau du batiment (1, 2, 3)
        self.level = 1
        self.total_usage = 0  # Nombre cumule d'ISOs ayant utilise la structure

        # Stats
        self.age = 0
        self.isos_inside = 0
        self.total_energy_given = 0.0

    def tick(self):
        """Vieillissement + check evolution de niveau."""
        self.age += 1
        self.durability -= self.decay_rate

        # Accumulation d'usage
        self.total_usage += self.isos_inside

        # Check evolution de niveau
        self._check_level_up()

    def _check_level_up(self):
        """Verifie si la structure peut monter de niveau."""
        if self.level == 1:
            if self.age >= self.LEVEL_2_AGE and self.total_usage >= self.LEVEL_2_USAGE:
                self.level = 2
                # Amelioration : +50% durabilite max, -20% decay
                self.max_durability *= 1.5
                self.durability = self.max_durability
                self.decay_rate *= 0.8
                self.energy_bonus *= 1.3
                self.radius += 2
        elif self.level == 2:
            if self.age >= self.LEVEL_3_AGE and self.total_usage >= self.LEVEL_3_USAGE:
                self.level = 3
                # Monument : +100% durabilite max, -40% decay, +50% bonus
                self.max_durability *= 2.0
                self.durability = self.max_durability
                self.decay_rate *= 0.6
                self.energy_bonus *= 1.5
                self.radius += 3

    def repair(self, amount: float):
        """Reparation par un ISO competent ou par Symmetra."""
        self.durability = min(self.max_durability, self.durability + amount)

    def is_alive(self) -> bool:
        return self.durability > 0

    def contains(self, x: int, z: int) -> bool:
        """Verifie si une position est dans le rayon."""
        return abs(x - self.x) <= self.radius and abs(z - self.z) <= self.radius

    def get_bonus(self, x: int, z: int) -> float:
        """Bonus d'energie selon la proximite au centre."""
        if not self.contains(x, z):
            return 0.0
        dist = max(1, abs(x - self.x) + abs(z - self.z))
        proximity = 1.0 - (dist / (self.radius * 2))
        health = self.durability / self.max_durability
        return self.energy_bonus * max(0.2, proximity) * health

    def get_health(self) -> float:
        return max(0, self.durability / self.max_durability)

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'x': self.x,
            'z': self.z,
            'type': self.structure_type,
            'name': self.name,
            'color': self.color,
            'radius': self.radius,
            'level': self.level,
            'durability': round(self.durability, 1),
            'max_durability': self.max_durability,
            'health': round(self.get_health(), 2),
            'age': self.age,
            'isos_inside': self.isos_inside,
            'total_usage': self.total_usage,
        }


class Symmetra:
    """
    Batisseuse multi-types et enseignante en construction.
    Entite speciale -- PAS un ISO.
    Immortelle, methodique, creative.

    Decide quoi construire selon les besoins de la population :
    - Beaucoup d'ISOs sans abri -> Abri
    - Connaissance basse + Minerve presente -> Bibliotheque
    - Energie grille basse -> Centrale
    - Peu de signaux -> Tour comm
    - Fitness bas -> Arene
    """

    def __init__(self, config: dict = None):
        self.config = config or {}
        sym_cfg = self.config.get('life', {}).get('symmetra', {})

        # Position
        pos = sym_cfg.get('position', [150, 150])
        self.x = pos[0]
        self.z = pos[1]

        # Parametres
        self.build_radius = sym_cfg.get('build_radius', 8)
        self.teaching_radius = sym_cfg.get('teaching_radius', 12)
        self.teaching_rate = sym_cfg.get('teaching_rate', 0.008)
        self.move_speed = sym_cfg.get('move_speed', 1)
        self.max_structures = sym_cfg.get('max_shelters', 12)
        self.build_cooldown_max = sym_cfg.get('build_cooldown', 200)
        self.shelter_energy_bonus = sym_cfg.get('shelter_energy_bonus', 2.0)
        self.enabled = sym_cfg.get('enabled', True)

        # Structures construites (remplace shelters)
        self.structures: List[Structure] = []
        # Alias pour compatibilite
        self.shelters = self.structures

        # Routes (connexions entre structures)
        # Chaque route = {'from_id': int, 'to_id': int, 'points': [(x,z), ...]}
        self.roads: List[Dict] = []
        self._road_check_cooldown = 0

        # Zones urbaines detectees
        # Chaque zone = {'center_x': int, 'center_z': int, 'radius': int,
        #                'structures': [id], 'type': str}
        self.zones: List[Dict] = []

        # Grille de blocs urbains -- chaque cellule = un bloc BLOCK_SIZE x BLOCK_SIZE
        # Valeur = None (vide) ou structure_type occupant le bloc
        self._city_blocks: Dict[Tuple[int, int], Optional[str]] = {}
        # Arteres principales (routes entre les blocs occupes)
        self._main_roads: List[Tuple[int, int, int, int]] = []  # (x1,z1,x2,z2)

        # Etat
        self.total_built = 0
        self.builds_by_type: Dict[str, int] = {t: 0 for t in STRUCTURE_TYPES}
        self.total_taught = 0
        self.current_students = 0
        self.cycles_active = 0
        self.mode = 'survey'  # survey, building, teaching

        # Cooldown avant prochaine construction
        self._build_cooldown = 50
        self._target_x = self.x
        self._target_z = self.z
        self._retarget_cooldown = 0

        # Grid size
        self._grid_size = 200

        # Contexte pour les decisions (mis a jour chaque cycle)
        self._avg_knowledge = 0.0
        self._avg_energy = 0.0
        self._avg_fitness = 0.0
        self._signal_count = 0
        self._minerve_pos = None

    def spawn_monoliths(self, grid_size: int, count: int = 12):
        """Place des monolithes d'energie disperses sur la grille au demarrage.
        Servent de points de ralliement pour les ISOs."""
        self._grid_size = grid_size
        margin = grid_size // 10  # 10% de marge aux bords
        spacing = (grid_size - 2 * margin) // max(1, int(count ** 0.5))

        placed = 0
        # Grille reguliere avec un peu de jitter
        cols = int(count ** 0.5) + 1
        rows = (count + cols - 1) // cols
        for row in range(rows):
            for col in range(cols):
                if placed >= count:
                    break
                base_x = margin + col * spacing + random.randint(-spacing // 4, spacing // 4)
                base_z = margin + row * spacing + random.randint(-spacing // 4, spacing // 4)
                base_x = max(margin, min(grid_size - margin, base_x))
                base_z = max(margin, min(grid_size - margin, base_z))

                # Creer la structure monolithe hexagonal
                monolith = Structure(base_x, base_z, 'hex_monolith', self.shelter_energy_bonus * 1.6)
                monolith.durability = 9999.0  # Quasi-permanent
                monolith.decay_rate = 0.001   # Declin negligeable
                self.structures.append(monolith)
                self.total_built += 1
                self.builds_by_type['hex_monolith'] = self.builds_by_type.get('hex_monolith', 0) + 1

                # Enregistrer le bloc urbain
                bx = base_x // BLOCK_SIZE
                bz = base_z // BLOCK_SIZE
                self._city_blocks[(bx, bz)] = 'hex_monolith'
                placed += 1

        print(f"[Symmetra] {placed} monolithes d'energie places sur la grille {grid_size}x{grid_size}")

    def update(self, alive_isos: list, grid, signal_board=None,
               minerve=None):
        """Cycle principal de Symmetra."""
        if not self.enabled:
            return

        self._grid_size = grid.size
        self.cycles_active += 1

        # Mettre a jour le contexte
        self._update_context(alive_isos, grid, signal_board, minerve)

        # 1. Entretien des structures
        self._maintain_structures()

        # 2. Appliquer les bonus de chaque structure
        self._apply_structure_bonuses(alive_isos, grid, signal_board)

        # 3. Enseigner la construction aux ISOs proches
        self.current_students = self._teach_nearby(alive_isos)

        # 4. ISOs competents peuvent reparer
        self._iso_repairs(alive_isos)

        # 5. Construire une nouvelle structure si possible
        self._build_cooldown -= 1
        if self._build_cooldown <= 0 and len(self.structures) < self.max_structures:
            build_result = self._decide_and_build(alive_isos, grid)
            if build_result:
                self._build_cooldown = self.build_cooldown_max
                self.mode = 'building'

        # 6. Se deplacer
        self._retarget_cooldown -= 1
        if self._retarget_cooldown <= 0:
            self._find_next_target(alive_isos)
            self._retarget_cooldown = 40
        self._move_towards_target()

        # 7. Routes entre structures
        self._road_check_cooldown -= 1
        if self._road_check_cooldown <= 0:
            self._update_roads()
            self._detect_zones()
            self._road_check_cooldown = 50  # Verifier toutes les 50 frames

        # 8. Signal
        if signal_board and self.cycles_active % 12 == 0:
            signal_board.emit(
                self.x, self.z, 'WISDOM', sender_id=-3,
                radius=self.teaching_radius
            )

        # Mode par defaut
        if self.cycles_active % 5 == 0 and self.mode == 'building':
            self.mode = 'survey'

    def _update_context(self, alive_isos, grid, signal_board, minerve):
        """Analyse le contexte pour prendre de bonnes decisions."""
        if alive_isos:
            self._avg_knowledge = sum(
                iso.knowledge.get_total_knowledge() for iso in alive_isos
            ) / len(alive_isos)
            self._avg_energy = sum(iso.energy for iso in alive_isos) / len(alive_isos)
            from nexos_life.genetics import fitness_score
            self._avg_fitness = sum(
                fitness_score(iso.genes) for iso in alive_isos
            ) / len(alive_isos)
        else:
            self._avg_knowledge = 0
            self._avg_energy = 0
            self._avg_fitness = 0

        if signal_board:
            s = signal_board.get_stats()
            self._signal_count = s.get('active', 0)
        else:
            self._signal_count = 0

        if minerve and minerve.enabled:
            self._minerve_pos = (minerve.x, minerve.z)
        else:
            self._minerve_pos = None

    def _maintain_structures(self):
        """Fait vieillir les structures et supprime les detruites."""
        for struct in self.structures:
            struct.tick()

        # Symmetra repare la structure la plus proche d'elle
        for struct in self.structures:
            if struct.contains(self.x, self.z):
                struct.repair(0.5)
                break

        # Supprimer les structures detruites et liberer les blocs
        dead = [s for s in self.structures if not s.is_alive()]
        for s in dead:
            bx = s.x // BLOCK_SIZE
            bz = s.z // BLOCK_SIZE
            self._city_blocks.pop((bx, bz), None)
        self.structures = [s for s in self.structures if s.is_alive()]
        self.shelters = self.structures

    def _apply_structure_bonuses(self, alive_isos: list, grid, signal_board):
        """Applique les bonus specifiques de chaque type de structure."""
        for struct in self.structures:
            struct.isos_inside = 0

        for iso in alive_isos:
            for struct in self.structures:
                if not struct.contains(iso.x, iso.z):
                    continue

                struct.isos_inside += 1
                health = struct.get_health()

                # --- Bonus commun : energie ---
                bonus = struct.get_bonus(iso.x, iso.z)
                if bonus > 0:
                    iso.energy = min(iso.max_energy, iso.energy + bonus)
                    struct.total_energy_given += bonus

                # --- Bonus specifiques au type ---
                if struct.structure_type == 'library':
                    # Boost connaissance : l'ISO apprend plus vite
                    boost = STRUCTURE_TYPES['library']['knowledge_boost']
                    rate = 0.003 * boost * health
                    iso.knowledge.absorb_from_symmetra(rate)

                elif struct.structure_type == 'arena':
                    # Boost fitness : ameliore legerement les genes
                    fb = STRUCTURE_TYPES['arena']['fitness_boost']
                    if hasattr(iso, 'genes') and health > 0.3:
                        # Petit boost resilience et efficiency
                        r = iso.genes.get('resilience', 1.0)
                        iso.genes['resilience'] = min(1.5, r + 0.0005 * fb)
                        e = iso.genes.get('efficiency', 1.0)
                        iso.genes['efficiency'] = min(1.5, e + 0.0003 * fb)

                elif struct.structure_type == 'comm_tower':
                    # Les signaux emis par les ISOs dans la tour sont renforces
                    if hasattr(iso, '_signal_boost'):
                        iso._signal_boost = STRUCTURE_TYPES['comm_tower']['signal_boost']

                break  # Un seul bonus par ISO par cycle

        # --- Centrales d'energie : regenerent la grille ---
        for struct in self.structures:
            if struct.structure_type == 'energy_plant' and struct.get_health() > 0.2:
                regen = STRUCTURE_TYPES['energy_plant']['grid_regen'] * struct.get_health()
                r = int(struct.radius)
                for dx in range(-r, r + 1, 3):  # Echantillonnage pour perfs
                    for dz in range(-r, r + 1, 3):
                        gx = struct.x + dx
                        gz = struct.z + dz
                        if 0 <= gx < grid.size and 0 <= gz < grid.size:
                            grid.add_energy(gx, gz, regen * 0.3)

    def _teach_nearby(self, alive_isos: list) -> int:
        """Enseigne la construction aux ISOs dans le rayon."""
        students = 0
        for iso in alive_isos:
            dx = abs(iso.x - self.x)
            dz = abs(iso.z - self.z)
            if dx <= self.teaching_radius and dz <= self.teaching_radius:
                dist = max(1, dx + dz)
                proximity = 1.0 - (dist / (self.teaching_radius * 2))
                effective_rate = self.teaching_rate * max(0.2, proximity)
                iso.knowledge.absorb_from_symmetra(effective_rate)
                students += 1

        self.total_taught += students
        if students > 0:
            self.mode = 'teaching'
        return students

    def _iso_repairs(self, alive_isos: list):
        """Les ISOs competents reparent les structures."""
        for iso in alive_isos:
            if not hasattr(iso, 'knowledge'):
                continue

            eco_level = iso.knowledge.levels.get('ecology', 0)
            logic_level = iso.knowledge.levels.get('logic', 0)
            build_skill = (eco_level + logic_level) / 2

            if build_skill < 0.3:
                continue

            for struct in self.structures:
                if struct.contains(iso.x, iso.z) and struct.durability < struct.max_durability * 0.8:
                    repair_amount = build_skill * 0.3
                    struct.repair(repair_amount)
                    break

    # ─── Decision : quoi construire ? ─────────────────────────

    def _decide_and_build(self, alive_isos: list, grid) -> bool:
        """Decide quel type de structure construire et ou."""
        if not alive_isos:
            return False

        # Calculer les scores de besoin pour chaque type
        scores = self._evaluate_needs(alive_isos, grid)

        # Trier par score decroissant
        sorted_types = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        # Essayer de construire le type le plus necessaire
        for struct_type, score in sorted_types:
            if score < 0.1:
                break  # Pas assez de besoin

            spot = self._find_build_spot(alive_isos, struct_type)
            if spot:
                self._build_structure(spot[0], spot[1], struct_type)
                return True

        return False

    def _evaluate_needs(self, alive_isos: list, grid) -> Dict[str, float]:
        """Evalue le besoin de chaque type de structure (0 a 1).

        Symmetra est une batisseuse visionnaire -- elle construit une cite
        diversifiee, pas uniquement en reaction aux besoins urgents.
        Chaque type a un score de base + un bonus si absent de la cite.
        """
        scores = {}
        existing = {}
        for t in STRUCTURE_TYPES:
            existing[t] = sum(1 for s in self.structures if s.structure_type == t)

        n_alive = max(1, len(alive_isos))
        total_structs = len(self.structures)

        # Compter les types uniques presents
        unique_types = sum(1 for t in STRUCTURE_TYPES if existing.get(t, 0) > 0)

        # --- ABRI : protection de base ---
        unsheltered = 0
        for iso in alive_isos:
            in_struct = any(s.contains(iso.x, iso.z) for s in self.structures)
            if not in_struct:
                unsheltered += 1
        shelter_need = min(0.7, unsheltered / n_alive * 1.5)  # Plafonné à 0.7
        shelter_need *= max(0.2, 1.0 - existing.get('shelter', 0) / 5)
        scores['shelter'] = shelter_need

        # --- BIBLIOTHEQUE : savoir ---
        knowledge_need = max(0.15, 1.0 - self._avg_knowledge * 1.5)
        if self._minerve_pos and existing.get('library', 0) == 0:
            knowledge_need = max(knowledge_need, 0.7)
        knowledge_need *= max(0.3, 1.0 - existing.get('library', 0) / 4)
        scores['library'] = min(1.0, knowledge_need)

        # --- CENTRALE ENERGIE : regeneration ---
        energy_need = max(0.15, 1.0 - self._avg_energy / 200)
        if existing.get('energy_plant', 0) == 0:
            energy_need = max(energy_need, 0.75)  # Forte priorité si aucune
        energy_need *= max(0.3, 1.0 - existing.get('energy_plant', 0) / 3)
        scores['energy_plant'] = min(1.0, energy_need)

        # --- TOUR COMMUNICATION : signaux ---
        signal_need = max(0.15, 1.0 - self._signal_count / 100)
        if existing.get('comm_tower', 0) == 0:
            signal_need = max(signal_need, 0.6)
        signal_need *= max(0.3, 1.0 - existing.get('comm_tower', 0) / 3)
        scores['comm_tower'] = min(1.0, signal_need)

        # --- ARENE : fitness et amelioration ---
        fitness_need = max(0.15, 1.0 - self._avg_fitness / 25)
        if existing.get('arena', 0) == 0:
            fitness_need = max(fitness_need, 0.65)  # Forte priorité si aucune
        fitness_need *= max(0.3, 1.0 - existing.get('arena', 0) / 3)
        scores['arena'] = min(1.0, fitness_need)

        # Bonus diversité : les types absents reçoivent un boost massif
        # après les 3 premières structures
        if total_structs >= 3:
            for t in STRUCTURE_TYPES:
                if existing.get(t, 0) == 0:
                    scores[t] = max(scores.get(t, 0), 0.8)

        return scores

    def _find_build_spot(self, alive_isos: list,
                         struct_type: str) -> Optional[Tuple[int, int]]:
        """Trouve le meilleur bloc urbain pour un type de structure.

        Urbanisme intelligent :
        1. Identifie les blocs les plus peuples (demande)
        2. Verifie que le bloc est libre
        3. Privilegie la proximite avec les types affinitaires
        4. Place au centre du bloc (pas de position aleatoire)
        """
        if not alive_isos:
            return None

        # Compter les ISOs par bloc
        iso_density: Dict[Tuple[int, int], int] = {}
        for iso in alive_isos:
            bx = iso.x // BLOCK_SIZE
            bz = iso.z // BLOCK_SIZE
            key = (bx, bz)
            iso_density[key] = iso_density.get(key, 0) + 1

        if not iso_density:
            return None

        # Cas special : Bibliotheque pres de Minerve
        if struct_type == 'library' and self._minerve_pos:
            mx, mz = self._minerve_pos
            target_block = (mx // BLOCK_SIZE, mz // BLOCK_SIZE)
            # Chercher le bloc libre le plus proche de Minerve
            best = self._find_nearest_free_block(target_block, struct_type)
            if best:
                return self._block_center(best[0], best[1])

        # Trier les blocs par densite d'ISOs
        sorted_blocks = sorted(iso_density.items(), key=lambda x: x[1], reverse=True)

        # Seuil minimum d'ISOs pour justifier une construction
        threshold = 2 if struct_type in ('comm_tower', 'energy_plant') else 3

        for block_key, count in sorted_blocks[:12]:
            if count < threshold:
                break

            # Verifier si le bloc est libre
            if block_key in self._city_blocks:
                # Bloc occupe -- chercher un voisin libre
                neighbor = self._find_neighbor_block(block_key, struct_type)
                if neighbor:
                    return self._block_center(neighbor[0], neighbor[1])
                continue

            # Verifier l'affinite avec les voisins
            if self._check_zone_affinity(block_key, struct_type):
                center = self._block_center(block_key[0], block_key[1])
                if center:
                    return center

        # Fallback : premier bloc libre avec des ISOs
        for block_key, count in sorted_blocks:
            if count >= 2 and block_key not in self._city_blocks:
                center = self._block_center(block_key[0], block_key[1])
                if center:
                    return center

        return None

    def _block_center(self, bx: int, bz: int) -> Optional[Tuple[int, int]]:
        """Retourne la position centrale d'un bloc urbain."""
        cx = bx * BLOCK_SIZE + BLOCK_SIZE // 2
        cz = bz * BLOCK_SIZE + BLOCK_SIZE // 2
        # Verifier les limites de la grille
        if 10 <= cx < self._grid_size - 10 and 10 <= cz < self._grid_size - 10:
            return (cx, cz)
        return None

    def _find_nearest_free_block(self, target: Tuple[int, int],
                                  struct_type: str) -> Optional[Tuple[int, int]]:
        """Trouve le bloc libre le plus proche d'un bloc cible."""
        tx, tz = target
        max_blocks = self._grid_size // BLOCK_SIZE
        best = None
        best_dist = 999

        for dx in range(-3, 4):
            for dz in range(-3, 4):
                bx, bz = tx + dx, tz + dz
                if 0 <= bx < max_blocks and 0 <= bz < max_blocks:
                    if (bx, bz) not in self._city_blocks:
                        dist = abs(dx) + abs(dz)
                        if dist < best_dist:
                            best_dist = dist
                            best = (bx, bz)
        return best

    def _find_neighbor_block(self, block: Tuple[int, int],
                              struct_type: str) -> Optional[Tuple[int, int]]:
        """Trouve un bloc voisin libre adjacent a un bloc occupe."""
        bx, bz = block
        max_blocks = self._grid_size // BLOCK_SIZE
        # Voisins directs (croix) puis diagonales
        neighbors = [(0, 1), (1, 0), (0, -1), (-1, 0),
                     (1, 1), (-1, 1), (1, -1), (-1, -1)]

        for dx, dz in neighbors:
            nx, nz = bx + dx, bz + dz
            if 0 <= nx < max_blocks and 0 <= nz < max_blocks:
                if (nx, nz) not in self._city_blocks:
                    return (nx, nz)
        return None

    def _check_zone_affinity(self, block: Tuple[int, int],
                              struct_type: str) -> bool:
        """Verifie si un bloc est compatible avec le type de structure.
        Retourne True si le bloc n'a pas de voisin incompatible,
        ou s'il a un voisin affinitaire (bonus)."""
        affinities = ZONE_AFFINITIES.get(struct_type, [])
        bx, bz = block

        # Verifier les 8 voisins
        has_affinity = len(self.structures) == 0  # Premiere structure = toujours OK
        for dx in range(-1, 2):
            for dz in range(-1, 2):
                if dx == 0 and dz == 0:
                    continue
                neighbor_type = self._city_blocks.get((bx + dx, bz + dz))
                if neighbor_type:
                    # Pas deux structures du meme type collees
                    if neighbor_type == struct_type:
                        return False
                    # Bonus si voisin affinitaire
                    if neighbor_type in affinities:
                        has_affinity = True

        return has_affinity or len(self._city_blocks) < 3

    def _build_structure(self, x: int, z: int, struct_type: str):
        """Construit une nouvelle structure et enregistre le bloc urbain."""
        struct = Structure(
            x=x, z=z,
            structure_type=struct_type,
            radius=self.build_radius,
        )
        self.structures.append(struct)
        self.shelters = self.structures
        self.total_built += 1
        self.builds_by_type[struct_type] = self.builds_by_type.get(struct_type, 0) + 1

        # Enregistrer le bloc urbain comme occupe
        bx = x // BLOCK_SIZE
        bz = z // BLOCK_SIZE
        self._city_blocks[(bx, bz)] = struct_type

    def _find_next_target(self, alive_isos: list):
        """Choisit la prochaine destination."""
        if not alive_isos:
            return

        # Priorite : structure la plus degradee
        damaged = [s for s in self.structures if s.durability < s.max_durability * 0.5]
        if damaged:
            damaged.sort(key=lambda s: s.durability)
            self._target_x = damaged[0].x
            self._target_z = damaged[0].z
            return

        # Sinon : zone avec le plus d'ISOs sans structure
        spot = self._find_build_spot(alive_isos, 'shelter')
        if spot:
            self._target_x = spot[0]
            self._target_z = spot[1]
        else:
            self._target_x = random.randint(10, self._grid_size - 10)
            self._target_z = random.randint(10, self._grid_size - 10)

    def _move_towards_target(self):
        """Deplacement vers la cible."""
        dx = self._target_x - self.x
        dz = self._target_z - self.z
        dist = abs(dx) + abs(dz)

        if dist < 2:
            return

        step = max(1, int(self.move_speed))
        if abs(dx) > abs(dz):
            self.x += step if dx > 0 else -step
        else:
            self.z += step if dz > 0 else -step

        self.x = max(0, min(self._grid_size - 1, self.x))
        self.z = max(0, min(self._grid_size - 1, self.z))

    # ─── Routes entre structures ───────────────────────────────

    def _update_roads(self):
        """Cree des routes (connexions) entre structures proches."""
        alive_ids = {s.id for s in self.structures}

        # Nettoyer les routes vers des structures detruites
        self.roads = [r for r in self.roads
                      if r['from_id'] in alive_ids and r['to_id'] in alive_ids]

        existing_pairs = {(r['from_id'], r['to_id']) for r in self.roads}
        existing_pairs |= {(r['to_id'], r['from_id']) for r in self.roads}

        # Connecter les structures proches (distance < 100)
        for i, s1 in enumerate(self.structures):
            for s2 in self.structures[i + 1:]:
                pair = (s1.id, s2.id)
                if pair in existing_pairs:
                    continue

                dist = math.sqrt((s1.x - s2.x) ** 2 + (s1.z - s2.z) ** 2)
                if dist < 100:
                    # Creer la route avec quelques points intermediaires
                    points = self._generate_road_points(s1.x, s1.z, s2.x, s2.z)
                    self.roads.append({
                        'from_id': s1.id,
                        'to_id': s2.id,
                        'points': points,
                    })

    def _generate_road_points(self, x1: int, z1: int, x2: int, z2: int) -> list:
        """Genere les points d'une route entre deux positions.
        Urbanisme : routes rectilignes alignees sur la grille de blocs.
        Les virages se font a 90 degres aux intersections de blocs."""
        points = [{'x': x1, 'z': z1}]

        # Aligner le point de virage sur la grille de blocs
        # Le virage se fait a la bordure du bloc le plus proche du milieu
        mid_block_x = round((x1 + x2) / (2 * BLOCK_SIZE)) * BLOCK_SIZE
        mid_block_z = round((x1 + x2) / (2 * BLOCK_SIZE)) * BLOCK_SIZE

        dx = abs(x2 - x1)
        dz = abs(z2 - z1)

        if dx < BLOCK_SIZE // 2 or dz < BLOCK_SIZE // 2:
            # Presque aligne -- route directe
            points.append({'x': x2, 'z': z2})
        else:
            # Route en L alignee sur la grille (pas de random offset)
            # Choisir si on fait horizontal-puis-vertical ou l'inverse
            # selon lequel donne un virage aligne sur un bloc
            corner_x = round(x2 / BLOCK_SIZE) * BLOCK_SIZE
            corner_z = round(z1 / BLOCK_SIZE) * BLOCK_SIZE

            points.append({'x': corner_x, 'z': corner_z})
            points.append({'x': corner_x, 'z': z2})
            if abs(corner_x - x2) > ROAD_WIDTH:
                points.append({'x': x2, 'z': z2})

        return points

    def _detect_zones(self):
        """Detecte les zones urbaines (clusters de structures)."""
        self.zones = []
        if len(self.structures) < 2:
            return

        # Clustering simple : structures a moins de 60 unites
        visited = set()
        for struct in self.structures:
            if struct.id in visited:
                continue

            # Trouver le cluster
            cluster = [struct]
            visited.add(struct.id)
            queue = [struct]
            while queue:
                current = queue.pop(0)
                for other in self.structures:
                    if other.id in visited:
                        continue
                    dist = abs(current.x - other.x) + abs(current.z - other.z)
                    if dist < 60:
                        cluster.append(other)
                        visited.add(other.id)
                        queue.append(other)

            if len(cluster) >= 2:
                # Calculer le centre et rayon du cluster
                cx = sum(s.x for s in cluster) // len(cluster)
                cz = sum(s.z for s in cluster) // len(cluster)
                max_dist = max(
                    abs(s.x - cx) + abs(s.z - cz) for s in cluster
                )

                # Type de zone determine par le type de structure dominant
                type_counts: Dict[str, int] = {}
                for s in cluster:
                    type_counts[s.structure_type] = type_counts.get(s.structure_type, 0) + 1
                dominant_type = max(type_counts.items(), key=lambda x: x[1])[0]

                self.zones.append({
                    'center_x': cx,
                    'center_z': cz,
                    'radius': max_dist + 15,
                    'structures': [s.id for s in cluster],
                    'type': dominant_type,
                    'color': STRUCTURE_TYPES[dominant_type]['color'],
                    'count': len(cluster),
                })

    def force_build(self, x: int, z: int, struct_type: str = 'shelter'):
        """Force la construction d'une structure (mode build du joueur)."""
        if struct_type not in STRUCTURE_TYPES:
            struct_type = 'shelter'
        if len(self.structures) < self.max_structures:
            self._build_structure(x, z, struct_type)
            self._update_roads()
            self._detect_zones()

    def get_state(self) -> dict:
        """Serialisation pour API/frontend."""
        return {
            'x': self.x,
            'z': self.z,
            'enabled': self.enabled,
            'mode': self.mode,
            'teaching_radius': self.teaching_radius,
            'build_radius': self.build_radius,
            'total_built': self.total_built,
            'builds_by_type': self.builds_by_type,
            'total_taught': self.total_taught,
            'current_students': self.current_students,
            'active_structures': len(self.structures),
            'active_shelters': len(self.structures),  # Compat
            'max_shelters': self.max_structures,
            'cycles_active': self.cycles_active,
            'structures': [s.to_dict() for s in self.structures],
            # Compat : garder 'shelters' aussi
            'shelters': [s.to_dict() for s in self.structures],
            # City builder
            'roads': self.roads,
            'zones': self.zones,
            # Grille urbaine (blocs occupes)
            'city_blocks': [
                {'bx': bx, 'bz': bz, 'type': stype,
                 'cx': bx * BLOCK_SIZE + BLOCK_SIZE // 2,
                 'cz': bz * BLOCK_SIZE + BLOCK_SIZE // 2}
                for (bx, bz), stype in self._city_blocks.items()
            ],
        }
