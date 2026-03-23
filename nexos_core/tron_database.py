"""
NexOS -- TronDatabase
Base de donnees SQLite inspiree de l'univers du film Tron.

"I fight for the Users." -- Tron

Tables :
  THE_GRID         -- sessions de simulation
  CYCLES           -- unites de temps virtuelles
  PROGRAMS         -- ISOs (algorithmes isomorphiques)
  IDENTITY_DISCS   -- memoires / connaissances / Q-tables
  GUARDIANS        -- entites speciales immortelles
  LIGHT_TRAILS     -- sillons de deplacement
  SIGNAL_BEACONS   -- communications entre programmes
  STRUCTURES       -- constructions de Symmetra
  ENERGY_SECTORS   -- carte energetique par secteur
  DEREZZED_LOG     -- archive des ISOs morts
  RECOGNITION_EVENTS -- journal des evenements marquants
  POPULATION_STATS   -- instantanes de population
"""

import os
import json
import sqlite3
import time
from typing import Optional, List, Dict, Any

# Chemin vers le schema SQL et la base de donnees
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
SCHEMA_PATH = os.path.join(_ROOT, 'data', 'tron_schema.sql')
DB_PATH     = os.path.join(_ROOT, 'data', 'tron_grid.db')


class TronDatabase:
    """
    Gestionnaire de la base de donnees Tron Grid.

    Usage :
        db = TronDatabase()
        db.connect()
        grid_id = db.init_grid(grid_size=200)
        db.save_programs(grid_id, population.isos)
        db.save_population_stats(grid_id, cycle, stats)
        db.close()
    """

    def __init__(self, db_path: str = None, schema_path: str = None):
        self.db_path     = db_path or DB_PATH
        self.schema_path = schema_path or SCHEMA_PATH
        self._conn: Optional[sqlite3.Connection] = None
        self._grid_id: Optional[int] = None
        # Parametres de sauvegarde
        self.trail_enabled       = True   # activer les trails (peut etre lourd)
        self.sector_snapshot_interval = 100  # cycles entre snapshots d'energie
        self.stats_interval      = 50     # cycles entre snapshots de stats

    # -------------------------------------------------------------------------
    # Connexion
    # -------------------------------------------------------------------------

    def connect(self) -> bool:
        """Ouvre la connexion et initialise le schema si necessaire."""
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            self._conn = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=30,
            )
            self._conn.row_factory = sqlite3.Row
            self._apply_schema()
            print(f"  [TRONDB] Connexion etablie : {self.db_path}")
            return True
        except Exception as exc:
            print(f"  [TRONDB] ERREUR connexion : {exc}")
            return False

    def close(self):
        """Ferme proprement la connexion."""
        if self._conn:
            self._conn.commit()
            self._conn.close()
            self._conn = None

    def _apply_schema(self):
        """Applique le schema SQL (idempotent grace aux IF NOT EXISTS)."""
        if not os.path.exists(self.schema_path):
            raise FileNotFoundError(f"Schema introuvable : {self.schema_path}")
        with open(self.schema_path, 'r', encoding='utf-8') as f:
            sql = f.read()
        self._conn.executescript(sql)
        self._conn.commit()

    # -------------------------------------------------------------------------
    # THE_GRID : gestion de la session
    # -------------------------------------------------------------------------

    def init_grid(self, grid_size: int = 200,
                  session_name: str = 'NexOS_Grid') -> int:
        """
        Cree ou recupère une session THE_GRID.
        Retourne le grid_id actif.
        """
        cur = self._conn.cursor()

        # Chercher une session ACTIVE existante
        cur.execute(
            "SELECT grid_id FROM THE_GRID WHERE status='ACTIVE' ORDER BY grid_id DESC LIMIT 1"
        )
        row = cur.fetchone()
        if row:
            self._grid_id = row['grid_id']
            self._touch_grid()
            print(f"  [TRONDB] Grid existant recupere : grid_id={self._grid_id}")
            return self._grid_id

        # Creer une nouvelle session
        cur.execute(
            "INSERT INTO THE_GRID (session_name, grid_size) VALUES (?, ?)",
            (session_name, grid_size)
        )
        self._conn.commit()
        self._grid_id = cur.lastrowid
        self._log_event('SIMULATION_START', entity_type='SIMULATION',
                        description=f'Grid {grid_size}x{grid_size} initialise')
        print(f"  [TRONDB] Nouveau Grid cree : grid_id={self._grid_id}")
        return self._grid_id

    def _touch_grid(self):
        """Met a jour last_active du Grid courant."""
        if self._grid_id:
            self._conn.execute(
                "UPDATE THE_GRID SET last_active=strftime('%Y-%m-%d %H:%M:%S','now') WHERE grid_id=?",
                (self._grid_id,)
            )

    def suspend_grid(self):
        """Passe le Grid en status SUSPENDED (pause)."""
        if self._grid_id:
            self._conn.execute(
                "UPDATE THE_GRID SET status='SUSPENDED', last_active=strftime('%Y-%m-%d %H:%M:%S','now') WHERE grid_id=?",
                (self._grid_id,)
            )
            self._conn.commit()
            self._log_event('SIMULATION_PAUSE', entity_type='SIMULATION')

    def reset_grid(self):
        """Archive le Grid courant et en cree un nouveau."""
        if self._grid_id:
            self._conn.execute(
                "UPDATE THE_GRID SET status='ARCHIVED' WHERE grid_id=?",
                (self._grid_id,)
            )
            self._conn.commit()
            self._log_event('SIMULATION_RESET', entity_type='SIMULATION')
        self._grid_id = None

    # -------------------------------------------------------------------------
    # CYCLES
    # -------------------------------------------------------------------------

    def record_cycle(self, cycle_number: int,
                     virtual_time: float, real_time: float,
                     speed_factor: float = 35.0):
        """Enregistre l'etat temporel courant."""
        if not self._grid_id:
            return
        self._conn.execute(
            """INSERT OR REPLACE INTO CYCLES
               (grid_id, cycle_number, virtual_time, real_time, speed_factor)
               VALUES (?, ?, ?, ?, ?)""",
            (self._grid_id, cycle_number, virtual_time, real_time, speed_factor)
        )

    # -------------------------------------------------------------------------
    # PROGRAMS (ISOs)
    # -------------------------------------------------------------------------

    def save_programs(self, isos: list, cycle_number: int = 0):
        """
        Upsert en masse de tous les ISOs vivants.
        Utilise INSERT OR REPLACE pour les mises a jour.
        """
        if not self._grid_id or not isos:
            return

        rows = []
        for iso in isos:
            if not iso.alive:
                continue
            genes = iso.genes
            rows.append((
                iso.id,
                self._grid_id,
                'ISO',
                iso.x,
                iso.z,
                round(iso.energy, 2),
                iso.max_energy,
                'ACTIVE',
                iso.generation,
                iso.age,
                iso.children_count,
                round(iso.mood, 2),
                round(genes.get('speed',        1.0), 4),
                round(genes.get('curiosity',     1.0), 4),
                round(genes.get('efficiency',    1.0), 4),
                round(genes.get('perception',    1.0), 4),
                round(genes.get('resilience',    1.0), 4),
                round(genes.get('intelligence',  0.5), 4),
                round(iso.total_harvested,  2),
                round(iso.distance_traveled, 2),
                iso.parent_ids[0] if len(getattr(iso, 'parent_ids', ())) > 0 else None,
                iso.parent_ids[1] if len(getattr(iso, 'parent_ids', ())) > 1 else None,
                cycle_number,
            ))

        self._conn.executemany(
            """INSERT OR REPLACE INTO PROGRAMS
               (program_id, grid_id, designation,
                pos_x, pos_z, energy_level, max_energy, status,
                generation, age, children_count, mood,
                gene_speed, gene_curiosity, gene_efficiency,
                gene_perception, gene_resilience, gene_intelligence,
                total_harvested, distance_traveled,
                parent_alpha_id, parent_beta_id, last_cycle)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            rows
        )

    def derez_program(self, iso, cycle_number: int, cause: str = 'starvation'):
        """Enregistre la mort d'un ISO (de-rez)."""
        if not self._grid_id:
            return

        # Mettre a jour le statut dans PROGRAMS
        self._conn.execute(
            """UPDATE PROGRAMS
               SET status='DEREZZED',
                   derezzed_at=strftime('%Y-%m-%d %H:%M:%S','now')
               WHERE program_id=?""",
            (iso.id,)
        )

        # Inserer dans le log des morts
        genes = iso.genes
        lvl = iso.knowledge.levels if hasattr(iso, 'knowledge') else {}
        self._conn.execute(
            """INSERT OR IGNORE INTO DEREZZED_LOG
               (program_id, grid_id, derez_cause, derez_cycle,
                final_pos_x, final_pos_z, final_energy, final_age,
                generation, children_count, total_harvested, distance_traveled,
                know_physics, know_social, know_ecology,
                know_logic, know_communication,
                gene_speed, gene_curiosity, gene_efficiency,
                gene_perception, gene_resilience, gene_intelligence)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                iso.id, self._grid_id, cause, cycle_number,
                iso.x, iso.z, round(iso.energy, 2), iso.age,
                iso.generation, iso.children_count,
                round(iso.total_harvested, 2), round(iso.distance_traveled, 2),
                round(lvl.get('physics',       0.0), 4),
                round(lvl.get('social',        0.0), 4),
                round(lvl.get('ecology',       0.0), 4),
                round(lvl.get('logic',         0.0), 4),
                round(lvl.get('communication', 0.0), 4),
                round(genes.get('speed',        1.0), 4),
                round(genes.get('curiosity',    1.0), 4),
                round(genes.get('efficiency',   1.0), 4),
                round(genes.get('perception',   1.0), 4),
                round(genes.get('resilience',   1.0), 4),
                round(genes.get('intelligence', 0.5), 4),
            )
        )

    # -------------------------------------------------------------------------
    # IDENTITY_DISCS
    # -------------------------------------------------------------------------

    def save_identity_discs(self, isos: list, cycle_number: int = 0,
                             save_qtable: bool = False):
        """
        Sauvegarde les disques d'identite (connaissances + besoins).
        save_qtable=True pour inclure la Q-table (plus lent, plus lourd).
        """
        if not isos:
            return

        rows = []
        for iso in isos:
            if not iso.alive:
                continue
            lvl = iso.knowledge.levels if hasattr(iso, 'knowledge') else {}
            needs = getattr(iso, 'needs', {})

            q_json = None
            if save_qtable and hasattr(iso, 'brain'):
                from nexos_core.save_manager import _compress_qtable
                q_json = json.dumps(_compress_qtable(iso.brain.memory.q_table))

            rows.append((
                iso.id,
                round(lvl.get('physics',       0.0), 4),
                round(lvl.get('social',        0.0), 4),
                round(lvl.get('ecology',       0.0), 4),
                round(lvl.get('logic',         0.0), 4),
                round(lvl.get('communication', 0.0), 4),
                q_json,
                round(needs.get('hunger',   80.0), 2),
                round(needs.get('social',   70.0), 2),
                round(needs.get('fun',      60.0), 2),
                round(needs.get('comfort',  75.0), 2),
                round(needs.get('hygiene',  85.0), 2),
                cycle_number,
            ))

        self._conn.executemany(
            """INSERT INTO IDENTITY_DISCS
               (program_id,
                know_physics, know_social, know_ecology,
                know_logic, know_communication,
                q_table_json,
                need_hunger, need_social, need_fun,
                need_comfort, need_hygiene,
                cycle_recorded,
                last_updated)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,
                       strftime('%Y-%m-%d %H:%M:%S','now'))
               ON CONFLICT(program_id) DO UPDATE SET
                 know_physics=excluded.know_physics,
                 know_social=excluded.know_social,
                 know_ecology=excluded.know_ecology,
                 know_logic=excluded.know_logic,
                 know_communication=excluded.know_communication,
                 q_table_json=COALESCE(excluded.q_table_json, q_table_json),
                 need_hunger=excluded.need_hunger,
                 need_social=excluded.need_social,
                 need_fun=excluded.need_fun,
                 need_comfort=excluded.need_comfort,
                 need_hygiene=excluded.need_hygiene,
                 cycle_recorded=excluded.cycle_recorded,
                 last_updated=excluded.last_updated""",
            rows
        )

    # -------------------------------------------------------------------------
    # GUARDIANS
    # -------------------------------------------------------------------------

    def save_guardian(self, name: str, designation: str,
                      pos_x: int, pos_z: int,
                      mode: str = 'PATROL', enabled: bool = True,
                      cycles_active: int = 0, stats: dict = None):
        """Upsert d'un gardien (Tron, Minerve, Symmetra, Daedalus)."""
        if not self._grid_id:
            return
        stats_json = json.dumps(stats) if stats else None
        self._conn.execute(
            """INSERT INTO GUARDIANS
               (grid_id, name, designation, pos_x, pos_z,
                mode, enabled, cycles_active, stats_json)
               VALUES (?,?,?,?,?,?,?,?,?)
               ON CONFLICT(grid_id, name) DO UPDATE SET
                 pos_x=excluded.pos_x,
                 pos_z=excluded.pos_z,
                 mode=excluded.mode,
                 enabled=excluded.enabled,
                 cycles_active=excluded.cycles_active,
                 stats_json=excluded.stats_json,
                 last_updated=strftime('%Y-%m-%d %H:%M:%S','now')""",
            (self._grid_id, name, designation, pos_x, pos_z,
             mode, int(enabled), cycles_active, stats_json)
        )

    # -------------------------------------------------------------------------
    # LIGHT_TRAILS
    # -------------------------------------------------------------------------

    def record_trail(self, entity_id: int, entity_type: str,
                     pos_x: int, pos_z: int,
                     cycle_number: int,
                     action: str = None, energy_level: float = None):
        """Enregistre un point de deplacement dans les trails."""
        if not self.trail_enabled:
            return
        self._conn.execute(
            """INSERT INTO LIGHT_TRAILS
               (entity_id, entity_type, pos_x, pos_z,
                cycle_number, action, energy_level)
               VALUES (?,?,?,?,?,?,?)""",
            (entity_id, entity_type, pos_x, pos_z,
             cycle_number, action, energy_level)
        )

    def record_trails_bulk(self, trail_rows: list):
        """Insertion en masse de trails [(entity_id, type, x, z, cycle, action, energy), ...]."""
        if not self.trail_enabled or not trail_rows:
            return
        self._conn.executemany(
            """INSERT INTO LIGHT_TRAILS
               (entity_id, entity_type, pos_x, pos_z,
                cycle_number, action, energy_level)
               VALUES (?,?,?,?,?,?,?)""",
            trail_rows
        )

    def prune_trails(self, keep_last_n_cycles: int = 500):
        """Supprime les vieux trails pour limiter la taille de la DB."""
        if not self._grid_id:
            return
        self._conn.execute(
            """DELETE FROM LIGHT_TRAILS
               WHERE trail_id IN (
                   SELECT trail_id FROM LIGHT_TRAILS
                   ORDER BY cycle_number DESC
                   LIMIT -1 OFFSET ?
               )""",
            (keep_last_n_cycles * 50,)  # estimation ~ 50 entites actives
        )

    # -------------------------------------------------------------------------
    # SIGNAL_BEACONS
    # -------------------------------------------------------------------------

    def save_signals(self, signals: list, cycle_number: int):
        """Enregistre les signaux actifs dans SIGNAL_BEACONS."""
        if not self._grid_id or not signals:
            return
        rows = []
        for sig in signals:
            rows.append((
                self._grid_id,
                sig.get('sender_id', 0),
                sig.get('type', 'FOOD_HERE'),
                sig.get('x', 0),
                sig.get('z', 0),
                sig.get('radius', 10),
                sig.get('intensity', 1.0),
                sig.get('ttl', 20),
                cycle_number,
            ))
        self._conn.executemany(
            """INSERT INTO SIGNAL_BEACONS
               (grid_id, sender_id, signal_type,
                pos_x, pos_z, radius, intensity, ttl, cycle_emitted)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            rows
        )

    # -------------------------------------------------------------------------
    # STRUCTURES
    # -------------------------------------------------------------------------

    def save_structures(self, structures: list):
        """Upsert en masse des structures de Symmetra."""
        if not self._grid_id or not structures:
            return
        rows = []
        for st in structures:
            rows.append((
                st.id,
                self._grid_id,
                st.structure_type,
                st.x,
                st.z,
                st.radius,
                round(st.durability, 2),
                st.level,
                st.age,
                st.total_usage,
                getattr(st, 'built_at_cycle', 0),
            ))
        self._conn.executemany(
            """INSERT INTO STRUCTURES
               (structure_id, grid_id, structure_type,
                pos_x, pos_z, radius, durability,
                level, age, total_usage, built_at_cycle)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(structure_id) DO UPDATE SET
                 durability=excluded.durability,
                 level=excluded.level,
                 age=excluded.age,
                 total_usage=excluded.total_usage""",
            rows
        )

    def demolish_structure(self, structure_id: int):
        """Marque une structure comme demolie."""
        self._conn.execute(
            """UPDATE STRUCTURES
               SET demolished_at=strftime('%Y-%m-%d %H:%M:%S','now')
               WHERE structure_id=?""",
            (structure_id,)
        )

    # -------------------------------------------------------------------------
    # ENERGY_SECTORS
    # -------------------------------------------------------------------------

    def save_energy_snapshot(self, grid, cycle_number: int,
                              nb_sectors: int = 10):
        """
        Divise le Grid en nb_sectors x nb_sectors et sauvegarde
        les statistiques energetiques de chaque secteur.
        """
        if not self._grid_id:
            return

        import numpy as np
        size = grid.size
        step = max(1, size // nb_sectors)
        rows = []

        for sx in range(nb_sectors):
            for sz in range(nb_sectors):
                x0 = sx * step
                x1 = min(x0 + step, size)
                z0 = sz * step
                z1 = min(z0 + step, size)

                sector_energy  = grid.energy[x0:x1, z0:z1]
                sector_terrain = grid.terrain_id[x0:x1, z0:z1]
                sector_occ     = grid.occupancy[x0:x1, z0:z1]

                avg_e = float(np.mean(sector_energy))
                max_e = float(np.max(sector_energy))
                min_e = float(np.min(sector_energy))
                iso_c = int(np.count_nonzero(sector_occ))

                # Terrain dominant
                unique, counts = np.unique(sector_terrain, return_counts=True)
                dominant_id = unique[counts.argmax()]
                terrain_map = {0: 'plain', 1: 'fertile', 2: 'barren'}
                terrain = terrain_map.get(int(dominant_id), 'mixed')

                rows.append((
                    self._grid_id, cycle_number,
                    sx, sz,
                    round(avg_e, 2), round(max_e, 2), round(min_e, 2),
                    terrain, iso_c,
                ))

        self._conn.executemany(
            """INSERT INTO ENERGY_SECTORS
               (grid_id, cycle_number, sector_x, sector_z,
                avg_energy, max_energy, min_energy,
                terrain_type, iso_count)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            rows
        )

    # -------------------------------------------------------------------------
    # POPULATION_STATS
    # -------------------------------------------------------------------------

    def save_population_stats(self, cycle_number: int, stats: dict):
        """
        Insere un snapshot de statistiques de population.
        stats = dict avec alive, total_born, total_died, peak, avg_energy,
                avg_age, avg_generation, avg_fitness, avg_knowledge, structures
        """
        if not self._grid_id:
            return
        self._conn.execute(
            """INSERT OR REPLACE INTO POPULATION_STATS
               (grid_id, cycle_number,
                alive_count, total_born, total_died, peak_population,
                avg_energy, avg_age, avg_generation, avg_fitness,
                avg_knowledge, structure_count)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                self._grid_id, cycle_number,
                stats.get('alive', 0),
                stats.get('total_born', 0),
                stats.get('total_died', 0),
                stats.get('peak', 0),
                round(stats.get('avg_energy', 0.0), 2),
                round(stats.get('avg_age', 0.0), 2),
                round(stats.get('avg_generation', 0.0), 2),
                round(stats.get('avg_fitness', 0.0), 4),
                round(stats.get('avg_knowledge', 0.0), 4),
                stats.get('structures', 0),
            )
        )

    # -------------------------------------------------------------------------
    # RECOGNITION_EVENTS
    # -------------------------------------------------------------------------

    def _log_event(self, event_type: str,
                   cycle_number: int = 0,
                   entity_id: int = None, entity_type: str = None,
                   description: str = None, data: dict = None):
        """Enregistre un evenement dans RECOGNITION_EVENTS."""
        if not self._grid_id:
            return
        data_json = json.dumps(data) if data else None
        self._conn.execute(
            """INSERT INTO RECOGNITION_EVENTS
               (grid_id, cycle_number, event_type,
                entity_id, entity_type, description, data_json)
               VALUES (?,?,?,?,?,?,?)""",
            (self._grid_id, cycle_number, event_type,
             entity_id, entity_type, description, data_json)
        )

    def log_birth(self, iso, cycle_number: int):
        """Evenement : naissance d'un ISO."""
        self._log_event('BIRTH', cycle_number,
                        entity_id=iso.id, entity_type='PROGRAM',
                        description=f'ISO #{iso.id} gen{iso.generation} compile',
                        data={'x': iso.x, 'z': iso.z,
                              'parent_ids': list(getattr(iso, 'parent_ids', []))})

    def log_death(self, iso, cycle_number: int, cause: str = 'starvation'):
        """Evenement : mort d'un ISO."""
        self._log_event('DEATH', cycle_number,
                        entity_id=iso.id, entity_type='PROGRAM',
                        description=f'ISO #{iso.id} de-rezze ({cause})',
                        data={'cause': cause, 'age': iso.age,
                              'energy': round(iso.energy, 2)})

    def log_structure_built(self, structure, cycle_number: int):
        """Evenement : structure construite."""
        self._log_event('STRUCTURE_BUILT', cycle_number,
                        entity_id=structure.id, entity_type='STRUCTURE',
                        description=f'{structure.structure_type} construit en ({structure.x},{structure.z})',
                        data={'x': structure.x, 'z': structure.z,
                              'type': structure.structure_type})

    def log_milestone(self, cycle_number: int, description: str, data: dict = None):
        """Evenement : jalon important de la simulation."""
        self._log_event('POPULATION_MILESTONE', cycle_number,
                        entity_type='SIMULATION',
                        description=description, data=data)

    # -------------------------------------------------------------------------
    # COMMIT / FLUSH
    # -------------------------------------------------------------------------

    def commit(self):
        """Commit explicite des transactions en attente."""
        if self._conn:
            self._conn.commit()

    # -------------------------------------------------------------------------
    # LECTURE (API)
    # -------------------------------------------------------------------------

    def get_population_history(self, last_n: int = 100) -> List[Dict]:
        """Retourne l'historique de population (pour graphes)."""
        if not self._conn or not self._grid_id:
            return []
        cur = self._conn.execute(
            """SELECT cycle_number, alive_count, avg_energy, avg_knowledge, structure_count
               FROM POPULATION_STATS
               WHERE grid_id=?
               ORDER BY cycle_number DESC LIMIT ?""",
            (self._grid_id, last_n)
        )
        return [dict(row) for row in cur.fetchall()]

    def get_derez_stats(self) -> List[Dict]:
        """Statistiques de mortalite par cause."""
        if not self._conn:
            return []
        cur = self._conn.execute("SELECT * FROM v_derez_stats")
        return [dict(row) for row in cur.fetchall()]

    def get_knowledge_elite(self) -> List[Dict]:
        """Top 10 ISOs les plus savants."""
        if not self._conn:
            return []
        cur = self._conn.execute("SELECT * FROM v_knowledge_elite")
        return [dict(row) for row in cur.fetchall()]

    def get_recent_events(self, last_n: int = 50) -> List[Dict]:
        """Derniers evenements RECOGNITION."""
        if not self._conn or not self._grid_id:
            return []
        cur = self._conn.execute(
            """SELECT cycle_number, event_type, entity_type, description
               FROM RECOGNITION_EVENTS
               WHERE grid_id=?
               ORDER BY event_id DESC LIMIT ?""",
            (self._grid_id, last_n)
        )
        return [dict(row) for row in cur.fetchall()]

    def get_guardians_status(self) -> List[Dict]:
        """Etat courant des gardiens."""
        if not self._conn:
            return []
        cur = self._conn.execute("SELECT * FROM v_guardians_status")
        rows = [dict(row) for row in cur.fetchall()]
        for row in rows:
            if row.get('stats_json'):
                try:
                    row['stats'] = json.loads(row['stats_json'])
                except Exception:
                    row['stats'] = {}
        return rows

    def get_grid_info(self) -> Optional[Dict]:
        """Informations sur la session Grid courante."""
        if not self._conn or not self._grid_id:
            return None
        cur = self._conn.execute(
            "SELECT * FROM THE_GRID WHERE grid_id=?", (self._grid_id,)
        )
        row = cur.fetchone()
        return dict(row) if row else None

    # -------------------------------------------------------------------------
    # SAUVEGARDE COMPLETE (point d'entree principal)
    # -------------------------------------------------------------------------

    def full_save(self, grid, vtime, population, cycle_number: int,
                  save_trails: bool = False,
                  save_signals: bool = True,
                  save_discs: bool = True,
                  save_qtable: bool = False):
        """
        Sauvegarde complete de l'etat de la simulation dans la DB.
        Equivalent au save_state() de save_manager.py mais en SQLite.
        """
        if not self._conn or not self._grid_id:
            return False

        start = time.time()

        # 1. ISOs
        isos = [iso for iso in population.isos if iso.alive]
        self.save_programs(isos, cycle_number)

        # 2. Disques d'identite
        if save_discs:
            self.save_identity_discs(isos, cycle_number, save_qtable=save_qtable)

        # 3. Gardiens
        if population.tron and population.tron.enabled:
            t = population.tron
            self.save_guardian('TRON', 'PROTECTOR',
                               t.x, t.z, t.mode, True, t.cycles_active,
                               stats={'total_saved': t.total_saved,
                                      'total_energy_given': round(t.total_energy_given, 1),
                                      'current_protected': t.current_protected,
                                      'emergency_count': t.current_emergencies})

        if population.minerve and population.minerve.enabled:
            m = population.minerve
            self.save_guardian('MINERVE', 'SAGE',
                               m.x, m.z, getattr(m, 'mode', 'TEACH'),
                               True, m.cycles_active,
                               stats={'total_taught': m.total_taught})

        if population.symmetra and population.symmetra.enabled:
            s = population.symmetra
            self.save_guardian('SYMMETRA', 'ARCHITECT',
                               s.x, s.z, getattr(s, 'mode', 'BUILD'),
                               True, s.cycles_active,
                               stats={'total_built': s.total_built,
                                      'builds_by_type': s.builds_by_type})
            self.save_structures(
                [st for st in s.structures if st.get_health() > 0]
            )

        if hasattr(population, 'daedalus') and population.daedalus \
                and population.daedalus.enabled:
            d = population.daedalus
            self.save_guardian('DAEDALUS', 'NAVIGATOR',
                               d.x, d.z, getattr(d, 'mode', 'EXPLORE'),
                               True, d.cycles_active,
                               stats={'total_inspired': getattr(d, 'total_inspired', 0)})

        # 4. Signaux
        if save_signals and population.signal_board:
            sigs = population.signal_board.get_all_signals()
            self.save_signals(sigs[:500], cycle_number)

        # 5. Stats de population
        stats_raw = population.get_stats() if hasattr(population, 'get_stats') else {}
        pop_stats = {
            'alive':          stats_raw.get('alive', len(isos)),
            'total_born':     population.total_born,
            'total_died':     population.total_died,
            'peak':           population.peak_population,
            'avg_energy':     stats_raw.get('avg_energy', 0.0),
            'avg_age':        stats_raw.get('avg_age', 0.0),
            'avg_generation': stats_raw.get('avg_generation', 0.0),
            'avg_fitness':    stats_raw.get('avg_fitness', 0.0),
            'avg_knowledge':  stats_raw.get('avg_knowledge', 0.0),
            'structures':     len(population.symmetra.structures)
                              if population.symmetra else 0,
        }
        self.save_population_stats(cycle_number, pop_stats)

        # 6. Snapshot energie (periodique)
        if cycle_number % self.sector_snapshot_interval == 0:
            self.save_energy_snapshot(grid, cycle_number)

        # 7. Temps
        self.record_cycle(
            cycle_number,
            virtual_time=vtime.get_virtual_elapsed(),
            real_time=vtime.get_real_elapsed(),
            speed_factor=getattr(vtime, 'speed_factor', 35.0),
        )

        self._touch_grid()
        self._conn.commit()

        elapsed = time.time() - start
        print(f"  [TRONDB] Sauvegarde DB OK ({elapsed:.3f}s) -- "
              f"{len(isos)} programmes, cycle {cycle_number}")
        return True

    # -------------------------------------------------------------------------
    # UTILITAIRES
    # -------------------------------------------------------------------------

    @property
    def grid_id(self) -> Optional[int]:
        return self._grid_id

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *_):
        self.close()
