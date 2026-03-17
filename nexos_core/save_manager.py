"""
NexOS -- Systeme de sauvegarde/chargement
Sauvegarde l'etat complet de la simulation dans data/
- Auto-save periodique (tous les N cycles, configurable)
- Sauvegarde a l'arret (Ctrl+C ou fermeture)
- Chargement au demarrage si un fichier existe
"""

import os
import json
import time
import numpy as np
from typing import Optional

# Repertoire de sauvegarde
SAVE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
SAVE_FILE = os.path.join(SAVE_DIR, 'nexos_save.json')
GRID_FILE = os.path.join(SAVE_DIR, 'nexos_grid.npz')  # Numpy compresse pour la grille


def ensure_save_dir():
    """Cree le repertoire data/ si necessaire."""
    os.makedirs(SAVE_DIR, exist_ok=True)


def save_state(grid, vtime, population, config) -> bool:
    """
    Sauvegarde l'etat complet de la simulation.
    Retourne True si succes, False sinon.
    """
    try:
        ensure_save_dir()
        start = time.time()

        # --- 1. Grille (numpy compresse -- rapide et compact) ---
        np.savez_compressed(GRID_FILE,
                            energy=grid.energy,
                            terrain_id=grid.terrain_id,
                            occupancy=grid.occupancy)

        # --- 2. Etat general (JSON) ---
        state = {
            'version': '3.1',
            'saved_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'grid_size': grid.size,
            'cycles': vtime.get_cycles(),
            'real_elapsed': vtime.get_real_elapsed(),
            'virtual_elapsed': vtime.get_virtual_elapsed(),
        }

        # --- 3. ISOs ---
        isos_data = []
        for iso in population.isos:
            if not iso.alive:
                continue
            iso_save = {
                'id': iso.id,
                'x': iso.x,
                'z': iso.z,
                'energy': round(iso.energy, 2),
                'max_energy': iso.max_energy,
                'age': iso.age,
                'generation': iso.generation,
                'genes': iso.genes,
                'children_count': iso.children_count,
                'total_harvested': round(iso.total_harvested, 2),
                'distance_traveled': round(iso.distance_traveled, 2),
                'needs': {k: round(v, 2) for k, v in iso.needs.items()},
                'mood': round(iso.mood, 2),
                'knowledge': iso.knowledge.to_dict(),
                # Q-table : sauvegarder les entrees les plus importantes
                'q_table': _compress_qtable(iso.brain.memory.q_table),
            }
            isos_data.append(iso_save)

        state['isos'] = isos_data
        state['total_born'] = population.total_born
        state['total_died'] = population.total_died
        state['total_generations'] = population.total_generations
        state['peak_population'] = population.peak_population
        state['next_iso_id'] = population.isos[-1].id + 1 if population.isos else 1

        # --- 4. Entites speciales ---
        if population.minerve and population.minerve.enabled:
            m = population.minerve
            state['minerve'] = {
                'x': m.x, 'z': m.z,
                'total_taught': m.total_taught,
                'cycles_active': m.cycles_active,
            }

        if population.tron and population.tron.enabled:
            t = population.tron
            state['tron'] = {
                'x': t.x, 'z': t.z,
                'total_saved': t.total_saved,
                'total_energy_given': round(t.total_energy_given, 2),
                'cycles_active': t.cycles_active,
            }

        if population.symmetra and population.symmetra.enabled:
            s = population.symmetra
            state['symmetra'] = {
                'x': s.x, 'z': s.z,
                'total_built': s.total_built,
                'builds_by_type': s.builds_by_type,
                'cycles_active': s.cycles_active,
                'structures': [{
                    'id': st.id,
                    'x': st.x, 'z': st.z,
                    'structure_type': st.structure_type,
                    'durability': round(st.durability, 2),
                    'radius': st.radius,
                    'level': st.level,
                    'age': st.age,
                    'total_usage': st.total_usage,
                } for st in s.structures if st.get_health() > 0],
            }

        if hasattr(population, 'daedalus') and population.daedalus and population.daedalus.enabled:
            d = population.daedalus
            state['daedalus'] = {
                'x': d.x, 'z': d.z,
                'cycles_active': d.cycles_active,
                'total_inspired': getattr(d, 'total_inspired', 0),
            }

        # --- 5. Signaux actifs ---
        if population.signal_board:
            sigs = population.signal_board.get_all_signals()
            # Limiter a 200 signaux pour la taille du fichier
            state['signals'] = sigs[:200]

        # --- Ecrire le JSON ---
        with open(SAVE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=None)

        elapsed = time.time() - start
        iso_count = len(isos_data)
        struct_count = len(state.get('symmetra', {}).get('structures', []))
        print(f"  [SAVE] Sauvegarde OK ({elapsed:.2f}s) -- "
              f"{iso_count} ISOs, {struct_count} structures, cycle {state['cycles']}")
        return True

    except Exception as e:
        print(f"  [SAVE] ERREUR sauvegarde : {e}")
        return False


def load_state(config) -> Optional[dict]:
    """
    Charge l'etat sauvegarde. Retourne None si pas de sauvegarde.
    Retourne un dict avec toutes les donnees pour restaurer.
    """
    if not os.path.exists(SAVE_FILE):
        return None
    if not os.path.exists(GRID_FILE):
        return None

    try:
        start = time.time()

        # Charger le JSON
        with open(SAVE_FILE, 'r', encoding='utf-8') as f:
            state = json.load(f)

        # Verifier que la taille de grille correspond
        saved_grid_size = state.get('grid_size', 0)
        current_grid_size = config.get('grid', {}).get('size', 200)
        if saved_grid_size != current_grid_size:
            print(f"  [LOAD] Taille de grille differente (save={saved_grid_size} vs config={current_grid_size}) -- sauvegarde ignoree")
            return None

        # Charger la grille numpy
        grid_data = np.load(GRID_FILE)
        state['grid_energy'] = grid_data['energy']
        state['grid_terrain_id'] = grid_data['terrain_id']
        state['grid_occupancy'] = grid_data['occupancy']

        elapsed = time.time() - start
        iso_count = len(state.get('isos', []))
        print(f"  [LOAD] Chargement OK ({elapsed:.2f}s) -- "
              f"{iso_count} ISOs, cycle {state.get('cycles', 0)}")
        return state

    except Exception as e:
        print(f"  [LOAD] ERREUR chargement : {e}")
        return None


def restore_simulation(state, grid, vtime, population):
    """
    Restaure l'etat complet de la simulation a partir des donnees chargees.
    """
    from nexos_life.iso import ISO
    from nexos_life.genetics import create_genes
    from nexos_life.knowledge import ISOKnowledge

    # --- 1. Grille ---
    grid.energy = state['grid_energy'].astype(np.float32)
    grid.terrain_id = state['grid_terrain_id'].astype(np.int8)
    grid.occupancy = state['grid_occupancy'].astype(np.int32)
    # Recalculer les multiplicateurs de regen
    grid._regen_mult = np.ones((grid.size, grid.size), dtype=np.float32)
    grid._regen_mult[grid.terrain_id == 1] = 2.0
    grid._regen_mult[grid.terrain_id == 2] = 0.3

    # --- 2. Temps ---
    vtime.cycles = state.get('cycles', 0)

    # --- 3. Population stats ---
    population.total_born = state.get('total_born', 0)
    population.total_died = state.get('total_died', 0)
    population.total_generations = state.get('total_generations', 0)
    population.peak_population = state.get('peak_population', 0)

    # --- 4. ISOs ---
    population.isos.clear()
    population._iso_by_id.clear()
    next_id = state.get('next_iso_id', 1)

    for iso_data in state.get('isos', []):
        genes = iso_data.get('genes', create_genes())
        iso = ISO(
            position=(iso_data['x'], iso_data['z']),
            genes=genes,
            config=population.config,
            generation=iso_data.get('generation', 0),
            knowledge_library=population.knowledge_library,
        )
        # Restaurer l'ID original
        iso.id = iso_data['id']
        iso.energy = iso_data.get('energy', 100)
        iso.max_energy = iso_data.get('max_energy', 200)
        iso.age = iso_data.get('age', 0)
        iso.children_count = iso_data.get('children_count', 0)
        iso.total_harvested = iso_data.get('total_harvested', 0)
        iso.distance_traveled = iso_data.get('distance_traveled', 0)

        # Besoins
        needs = iso_data.get('needs', {})
        for k in iso.needs:
            if k in needs:
                iso.needs[k] = needs[k]
        iso.mood = iso_data.get('mood', 50)

        # Connaissance
        know = iso_data.get('knowledge', {})
        if know:
            levels = know.get('levels', {})
            for domain in iso.knowledge.levels:
                if domain in levels:
                    iso.knowledge.levels[domain] = levels[domain]

        # Q-table (restaurer comme defaultdict)
        qt = iso_data.get('q_table', {})
        if qt:
            from collections import defaultdict
            new_qt = defaultdict(lambda: defaultdict(float))
            for state_key, actions in qt.items():
                for action, value in actions.items():
                    new_qt[state_key][action] = value
            iso.brain.memory.q_table = new_qt

        # Enregistrer l'occupancy
        grid.set_occupancy(iso.x, iso.z, iso.id)
        population.isos.append(iso)
        population._iso_by_id[iso.id] = iso

    # Mettre a jour le compteur d'ID
    ISO._next_id = next_id

    # --- 5. Entites speciales ---
    if 'minerve' in state and population.minerve:
        m = state['minerve']
        population.minerve.x = m.get('x', population.minerve.x)
        population.minerve.z = m.get('z', population.minerve.z)
        population.minerve.total_taught = m.get('total_taught', 0)
        population.minerve.cycles_active = m.get('cycles_active', 0)

    if 'tron' in state and population.tron:
        t = state['tron']
        population.tron.x = t.get('x', population.tron.x)
        population.tron.z = t.get('z', population.tron.z)
        population.tron.total_saved = t.get('total_saved', 0)
        population.tron.total_energy_given = t.get('total_energy_given', 0)
        population.tron.cycles_active = t.get('cycles_active', 0)

    if 'symmetra' in state and population.symmetra:
        from nexos_life.symmetra import Structure, BLOCK_SIZE
        s_data = state['symmetra']
        population.symmetra.x = s_data.get('x', population.symmetra.x)
        population.symmetra.z = s_data.get('z', population.symmetra.z)
        population.symmetra.total_built = s_data.get('total_built', 0)
        population.symmetra.builds_by_type = s_data.get('builds_by_type', {})
        population.symmetra.cycles_active = s_data.get('cycles_active', 0)

        # Restaurer les structures
        population.symmetra.structures.clear()
        population.symmetra._city_blocks.clear()
        for sd in s_data.get('structures', []):
            st = Structure(sd['x'], sd['z'], sd['structure_type'],
                          radius=sd.get('radius', 8),
                          durability=sd.get('durability', 100))
            st.id = sd.get('id', st.id)
            st.level = sd.get('level', 1)
            st.age = sd.get('age', 0)
            st.total_usage = sd.get('total_usage', 0)
            population.symmetra.structures.append(st)
            bx = st.x // BLOCK_SIZE
            bz = st.z // BLOCK_SIZE
            population.symmetra._city_blocks[(bx, bz)] = st.structure_type

    if 'daedalus' in state and hasattr(population, 'daedalus') and population.daedalus:
        d = state['daedalus']
        population.daedalus.x = d.get('x', population.daedalus.x)
        population.daedalus.z = d.get('z', population.daedalus.z)
        population.daedalus.cycles_active = d.get('cycles_active', 0)
        if hasattr(population.daedalus, 'total_inspired'):
            population.daedalus.total_inspired = d.get('total_inspired', 0)

    alive_count = len([i for i in population.isos if i.alive])
    struct_count = len(population.symmetra.structures) if population.symmetra else 0
    print(f"  [LOAD] Restauration terminee : {alive_count} ISOs, {struct_count} structures, cycle {vtime.get_cycles()}")


def delete_save():
    """Supprime les fichiers de sauvegarde (apres un reset)."""
    try:
        if os.path.exists(SAVE_FILE):
            os.remove(SAVE_FILE)
        if os.path.exists(GRID_FILE):
            os.remove(GRID_FILE)
        print("  [SAVE] Sauvegarde supprimee")
    except Exception as e:
        print(f"  [SAVE] Erreur suppression : {e}")


def has_save() -> bool:
    """Verifie si une sauvegarde existe."""
    return os.path.exists(SAVE_FILE) and os.path.exists(GRID_FILE)


def _compress_qtable(q_table: dict, max_entries: int = 200) -> dict:
    """Compresse la Q-table : garde seulement les entrees les plus utilisees."""
    if not q_table or len(q_table) <= max_entries:
        return q_table
    # Trier par valeur max de l'entree (les etats les plus 'connus')
    sorted_entries = sorted(q_table.items(),
                            key=lambda x: max(x[1].values()) if isinstance(x[1], dict) else 0,
                            reverse=True)
    return dict(sorted_entries[:max_entries])
