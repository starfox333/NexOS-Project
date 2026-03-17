"""
NexOS -- Gestion de population ISO
Naissance, mort, reproduction, connaissance, communication, Minerve.
"""

import random
from typing import List, Dict, Optional

from nexos_life.iso import ISO
from nexos_life.genetics import create_genes, reproduce, fitness_score
from nexos_life.knowledge import KnowledgeLibrary
from nexos_life.communication import SignalBoard
from nexos_life.minerve import Minerve
from nexos_life.tron import Tron
from nexos_life.symmetra import Symmetra
from nexos_life.daedalus import Daedalus
from nexos_life.vehicles import VehicleManager


class Population:
    """
    Gestionnaire de population ISO.
    Orchestre : vie, connaissance, communication, Minerve.
    """

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.isos: List[ISO] = []

        life_cfg = self.config.get('life', {})
        self.max_population = life_cfg.get('max_population', 500)
        genetics_cfg = life_cfg.get('genetics', {})
        self.mutation_rate = genetics_cfg.get('mutation_rate', 0.01)

        # Bibliotheque de connaissance
        knowledge_cfg = life_cfg.get('knowledge', {})
        self.knowledge_enabled = knowledge_cfg.get('enabled', True)
        self.knowledge_library = KnowledgeLibrary(config=self.config) if self.knowledge_enabled else None

        # Systeme de communication
        comm_cfg = life_cfg.get('communication', {})
        self.communication_enabled = comm_cfg.get('enabled', True)
        grid_size = self.config.get('grid', {}).get('size', 200)
        self.signal_board = SignalBoard(grid_size=grid_size, config=self.config) if self.communication_enabled else None

        # Minerve -- gardienne du savoir
        minerve_cfg = life_cfg.get('minerve', {})
        self.minerve_enabled = minerve_cfg.get('enabled', True)
        self.minerve = Minerve(config=self.config) if self.minerve_enabled else None

        # Tron -- protecteur des ISOs
        tron_cfg = life_cfg.get('tron', {})
        self.tron_enabled = tron_cfg.get('enabled', True)
        self.tron = Tron(config=self.config) if self.tron_enabled else None

        # Symmetra -- batisseuse d'abris
        sym_cfg = life_cfg.get('symmetra', {})
        self.symmetra_enabled = sym_cfg.get('enabled', True)
        self.symmetra = Symmetra(config=self.config) if self.symmetra_enabled else None

        # Daedalus -- facilitateur d'innovation
        daedalus_cfg = life_cfg.get('daedalus', {})
        self.daedalus_enabled = daedalus_cfg.get('enabled', True)
        self.daedalus = Daedalus(config=self.config) if self.daedalus_enabled else None

        # Lightcycles -- vehicules de transport
        self.vehicle_manager = VehicleManager(config=self.config)

        # Lookup rapide par ID
        self._iso_by_id: Dict[int, ISO] = {}

        # Statistiques
        self.total_born = 0
        self.total_died = 0
        self.total_generations = 0
        self.peak_population = 0
        self.deaths_by_cause: Dict[str, int] = {}

    def spawn_initial(self, grid, count: int = 10):
        """Cree la population initiale d'ISOs -- regroupes au centre"""
        # Spawn dans une zone centrale (25% de la grille) pour qu'ils soient trouvables
        center = grid.size // 2
        spawn_radius = max(grid.size // 8, 50)  # 12.5% du rayon de la grille
        for _ in range(count):
            x = random.randint(max(10, center - spawn_radius), min(grid.size - 10, center + spawn_radius))
            z = random.randint(max(10, center - spawn_radius), min(grid.size - 10, center + spawn_radius))
            genes = create_genes()
            iso = ISO(position=(x, z), genes=genes, config=self.config,
                      generation=0, knowledge_library=self.knowledge_library)
            grid.set_occupancy(x, z, iso.id)
            self.isos.append(iso)
            self._iso_by_id[iso.id] = iso
            self.total_born += 1

        self.peak_population = len(self.isos)

        # Placer des monolithes d'energie disperses (points de ralliement)
        if self.symmetra and self.symmetra.enabled:
            monolith_count = max(8, grid.size // 400)  # ~12 pour 5000
            self.symmetra.spawn_monoliths(grid.size, count=monolith_count)

    def update_all(self, grid):
        """Met a jour tous les ISOs : perceive -> decide -> act -> tick + Minerve"""
        # Decroitre les signaux
        if self.signal_board:
            self.signal_board.tick()

        for iso in self.isos:
            if not iso.alive:
                continue

            # 1. Perception (avec signaux)
            iso.perceive(grid, signal_board=self.signal_board)

            # 2. Decision
            action = iso.decide()

            # 3. Action (avec signaux et lookup)
            iso.act(grid, action,
                    signal_board=self.signal_board,
                    population_lookup=self._lookup_iso)

            # 4. Vieillissement
            iso.tick()

        # Transmission culturelle entre ISOs proches
        if self.knowledge_enabled:
            self._cultural_transmission()

        # Minerve enseigne et se deplace
        if self.minerve and self.minerve.enabled:
            alive = self.get_alive()
            self.minerve.update(alive, grid, self.signal_board)

        # Tron protege les ISOs en danger
        if self.tron and self.tron.enabled:
            alive = self.get_alive()
            self.tron.update(alive, grid, self.signal_board)

        # Symmetra construit des structures et enseigne
        if self.symmetra and self.symmetra.enabled:
            alive = self.get_alive()
            self.symmetra.update(alive, grid, self.signal_board,
                                 minerve=self.minerve)

        # Daedalus catalyse l'innovation
        if self.daedalus and self.daedalus.enabled:
            alive = self.get_alive()
            self.daedalus.update(alive, grid, self.signal_board)

        # Lightcycles se deplacent
        if self.vehicle_manager:
            self.vehicle_manager.update(isos=self.get_alive(), grid=grid)

        # Minerve bonus bibliotheque : si Minerve est dans une bibliotheque,
        # son taux d'enseignement double
        if self.minerve and self.minerve.enabled and self.symmetra:
            in_library = False
            for struct in self.symmetra.structures:
                if (struct.structure_type == 'library'
                        and struct.contains(self.minerve.x, self.minerve.z)):
                    in_library = True
                    break
            if in_library:
                self.minerve.teaching_rate = self.minerve._base_teaching_rate * 2.0
            else:
                self.minerve.teaching_rate = self.minerve._base_teaching_rate

    def _lookup_iso(self, iso_id: int) -> Optional[ISO]:
        """Lookup rapide d'un ISO par ID."""
        return self._iso_by_id.get(iso_id)

    def _cultural_transmission(self):
        """Les ISOs proches partagent leur savoir (echantillonnage)."""
        alive = self.get_alive()
        if len(alive) < 2:
            return

        sample_size = min(50, len(alive))
        sample = random.sample(alive, sample_size)

        for iso in sample:
            radius = int(iso.genes.get('perception', 5))
            for other in alive:
                if other.id == iso.id:
                    continue
                dx = abs(iso.x - other.x)
                dz = abs(iso.z - other.z)
                if dx <= radius and dz <= radius:
                    dist = max(1, dx + dz)
                    proximity = 1.0 / dist
                    iso.knowledge.absorb_from_nearby(
                        other.knowledge, proximity)
                    break  # Un seul voisin par cycle

    def handle_reproduction(self, grid):
        """Gere la reproduction des ISOs avec heritage de connaissance."""
        if len(self.isos) >= self.max_population:
            return []

        parents = [iso for iso in self.isos if iso.alive and iso.can_reproduce()]
        if len(parents) < 2:
            return []

        parents.sort(key=lambda iso: fitness_score(iso.genes), reverse=True)

        new_isos = []
        max_births = min(5, (self.max_population - len(self.isos)) // 2)

        for i in range(0, min(len(parents) - 1, max_births * 2), 2):
            p1 = parents[i]
            p2 = parents[i + 1]

            cx = (p1.x + p2.x) // 2 + random.randint(-3, 3)
            cz = (p1.z + p2.z) // 2 + random.randint(-3, 3)
            cx = max(0, min(grid.size - 1, cx))
            cz = max(0, min(grid.size - 1, cz))

            child_genes = reproduce(p1.genes, p2.genes, self.mutation_rate)
            gen = max(p1.generation, p2.generation) + 1

            child = ISO(
                position=(cx, cz),
                genes=child_genes,
                config=self.config,
                generation=gen,
                parent_ids=(p1.id, p2.id),
                knowledge_library=self.knowledge_library,
                parent_knowledge=(p1.knowledge, p2.knowledge)
            )

            energy_cfg = self.config.get('life', {}).get('energy', {})
            cost = energy_cfg.get('reproduction_cost', 80)
            p1.consume_energy(cost / 2)
            p2.consume_energy(cost / 2)
            p1.children_count += 1
            p2.children_count += 1

            grid.set_occupancy(cx, cz, child.id)
            new_isos.append(child)
            self._iso_by_id[child.id] = child
            self.total_born += 1
            self.total_generations = max(self.total_generations, gen)

        self.isos.extend(new_isos)
        self.peak_population = max(self.peak_population,
                                   len([i for i in self.isos if i.alive]))
        return new_isos

    def remove_dead(self, grid) -> int:
        """Retire les ISOs morts"""
        dead = [iso for iso in self.isos if not iso.alive]
        for iso in dead:
            grid.clear_occupancy(iso.x, iso.z)
            self.total_died += 1
            self._iso_by_id.pop(iso.id, None)

        alive_before = len(self.isos)
        self.isos = [iso for iso in self.isos if iso.alive]
        return alive_before - len(self.isos)

    def get_alive(self) -> List[ISO]:
        return [iso for iso in self.isos if iso.alive]

    def get_stats(self) -> dict:
        alive = self.get_alive()
        if not alive:
            stats = {
                'alive': 0, 'total_born': self.total_born,
                'total_died': self.total_died, 'peak': self.peak_population,
                'max_generation': self.total_generations,
                'avg_energy': 0, 'avg_age': 0, 'avg_fitness': 0,
                'avg_knowledge': 0, 'avg_intelligence': 0,
            }
            if self.signal_board:
                stats['signals'] = self.signal_board.get_stats()
            if self.minerve:
                stats['minerve'] = self.minerve.get_state()
            if self.tron:
                stats['tron'] = self.tron.get_state()
            if self.symmetra:
                stats['symmetra'] = self.symmetra.get_state()
            return stats

        energies = [iso.energy for iso in alive]
        ages = [iso.age for iso in alive]
        fitnesses = [fitness_score(iso.genes) for iso in alive]
        generations = [iso.generation for iso in alive]

        stats = {
            'alive': len(alive),
            'total_born': self.total_born,
            'total_died': self.total_died,
            'peak': self.peak_population,
            'max_generation': max(generations) if generations else 0,
            'avg_generation': round(sum(generations) / len(generations), 1) if generations else 0,
            'avg_energy': round(sum(energies) / len(energies), 1),
            'min_energy': round(min(energies), 1),
            'max_energy': round(max(energies), 1),
            'avg_age': round(sum(ages) / len(ages), 0),
            'oldest': max(ages),
            'avg_fitness': round(sum(fitnesses) / len(fitnesses), 2),
        }

        # Connaissance
        if self.knowledge_enabled:
            avg_k = sum(iso.knowledge.get_total_knowledge() for iso in alive) / len(alive)
            avg_i = sum(iso.genes.get('intelligence', 0.5) for iso in alive) / len(alive)
            stats['avg_knowledge'] = round(avg_k, 3)
            stats['avg_intelligence'] = round(avg_i, 3)

        # Signaux
        if self.signal_board:
            stats['signals'] = self.signal_board.get_stats()

        # Minerve
        if self.minerve:
            stats['minerve'] = self.minerve.get_state()

        # Tron
        if self.tron:
            stats['tron'] = self.tron.get_state()

        # Symmetra
        if self.symmetra:
            stats['symmetra'] = self.symmetra.get_state()

        # Daedalus
        if self.daedalus:
            stats['daedalus'] = self.daedalus.get_state()

        return stats

    def get_isos_data(self) -> list:
        return [iso.to_dict() for iso in self.isos if iso.alive]
