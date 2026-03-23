"""
NexOS — Point d'entree principal
Lance le moteur de vie artificielle et le serveur web.
"""

import sys
import os
import time
import threading
import signal

# Résolution du répertoire de base
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
os.chdir(BASE_DIR)

from nexos_core.config import load_config, get
from nexos_core.grid import Grid
from nexos_core.time_system import VirtualTime
from nexos_life.population import Population
from nexos_core.save_manager import save_state, load_state, restore_simulation, has_save, delete_save


def print_banner():
    print("")
    print("  =========================================")
    print("       NexOS -- Vie Artificielle")
    print("       Emergence d'ISOs Intelligents")
    print("  =========================================")
    print("")


def print_stats(vtime, grid, population):
    stats = population.get_stats()
    grid_stats = grid.get_stats()
    print(f"  [{vtime.format_virtual()}] "
          f"Cycle {vtime.get_cycles():>6} | "
          f"ISOs: {stats['alive']:>3} (nes:{stats['total_born']} morts:{stats['total_died']}) | "
          f"Gen max: {stats['max_generation']} | "
          f"Energie moy: {stats['avg_energy']:.0f} | "
          f"Fitness moy: {stats['avg_fitness']:.1f} | "
          f"Grille: {grid_stats['avg_energy']:.0f}")


class SimControl:
    """Controle partage entre la boucle de vie et le serveur web."""
    def __init__(self, config):
        self.paused = False
        self.speed = 1.0            # Multiplicateur (0.1 a 10)
        self.base_delay = get(config, 'time', 'cycle_delay', default=0.05)
        self.reset_requested = False
        self.logs = []              # Console debug logs
        self._max_logs = 200

    def log(self, msg, level='info'):
        import datetime
        entry = {
            'time': datetime.datetime.now().strftime('%H:%M:%S'),
            'level': level,
            'msg': msg
        }
        self.logs.append(entry)
        if len(self.logs) > self._max_logs:
            self.logs = self.logs[-self._max_logs:]

    @property
    def cycle_delay(self):
        return max(0.01, self.base_delay / max(0.1, self.speed))


def life_loop(config, grid, vtime, population, running_flag, control):
    """Boucle principale de vie artificielle"""
    stats_interval = get(config, 'logging', 'stats_interval', default=100)
    save_interval = get(config, 'logging', 'save_interval', default=1000)

    print(f"  Grille {grid.size}x{grid.size} initialisee")
    print(f"  {len(population.get_alive())} ISOs deployes")
    print(f"  Acceleration temporelle : x{vtime.acceleration}")
    print(f"  Cycle delay : {control.base_delay}s")
    print("")
    print("  La vie commence...")
    print("  " + "-" * 50)
    print("")

    control.log("Simulation demarree", "info")
    control.log(f"Grille {grid.size}x{grid.size}, {len(population.get_alive())} ISOs", "info")

    while running_flag['run']:
        # Reset demande
        if control.reset_requested:
            control.reset_requested = False
            population.isos.clear()
            population._iso_by_id.clear()
            population.total_born = 0
            population.total_died = 0
            population.total_generations = 0
            if population.signal_board:
                population.signal_board.signals.clear()
            if population.symmetra:
                population.symmetra.shelters.clear()
                population.symmetra.total_built = 0
            vtime.cycles = 0
            vtime.start_real = time.time()
            grid.reset_energy()
            initial_count = get(config, 'life', 'initial_population', default=30)
            population.spawn_initial(grid, initial_count)
            delete_save()  # Supprimer l'ancienne sauvegarde
            control.log("RESET -- Nouvelle simulation", "warn")
            continue

        # Pause
        if control.paused:
            time.sleep(0.1)
            continue

        # 1. Avancer le temps
        vtime.tick()

        # 2. Mettre a jour la grille (regeneration energie)
        grid.update()

        # 3. Mettre a jour tous les ISOs (perceive -> decide -> act -> tick)
        population.update_all(grid)

        # 4. Gerer la reproduction
        new_isos = population.handle_reproduction(grid)

        # 5. Retirer les morts
        dead_count = population.remove_dead(grid)

        # 6. Respawn si extinction
        alive = population.get_alive()
        if len(alive) == 0:
            control.log("EXTINCTION -- Respawn automatique", "error")
            print(f"\n  [!] EXTINCTION au cycle {vtime.get_cycles()} -- Respawn...")
            initial_count = get(config, 'life', 'initial_population', default=30)
            population.spawn_initial(grid, initial_count)

        # 7. Logs periodiques
        if vtime.get_cycles() % stats_interval == 0:
            print_stats(vtime, grid, population)
            stats = population.get_stats()
            control.log(f"Cycle {vtime.get_cycles()} | {stats['alive']} ISOs | Gen {stats['max_generation']} | E:{stats['avg_energy']:.0f}", "info")

        # 7b. Auto-save periodique
        if vtime.get_cycles() % save_interval == 0 and vtime.get_cycles() > 0:
            save_state(grid, vtime, population, config)
            control.log(f"Auto-save cycle {vtime.get_cycles()}", "info")

        # 8. Pause adaptee a la vitesse
        time.sleep(control.cycle_delay)


def main():
    print_banner()

    # Charger la configuration
    config = load_config()
    print("  Configuration chargee")

    # Initialiser les systemes
    grid_size = get(config, 'grid', 'size', default=200)
    grid = Grid(size=grid_size, config=config)

    acceleration = get(config, 'time', 'acceleration', default=35)
    vtime = VirtualTime(acceleration=acceleration)

    population = Population(config=config)

    # Charger la sauvegarde si elle existe
    saved = load_state(config) if has_save() else None
    if saved:
        print("  Restauration de la sauvegarde...")
        restore_simulation(saved, grid, vtime, population)
        print(f"  Sauvegarde restauree (cycle {vtime.get_cycles()})")
    else:
        print("  Nouvelle simulation")
        initial_count = get(config, 'life', 'initial_population', default=10)
        population.spawn_initial(grid, initial_count)

    # Flag d'arret propre
    running = {'run': True}

    def signal_handler(sig, frame):
        print("\n\n  Arret demande...")
        running['run'] = False

    signal.signal(signal.SIGINT, signal_handler)

    # Controle partage
    control = SimControl(config)

    # Lancer le serveur web en parallele
    try:
        from nexos_interface.server import create_app, start_server
        app = create_app(config, grid, vtime, population, control)
        server_thread = threading.Thread(
            target=start_server, args=(app, config), daemon=True
        )
        server_thread.start()
        host = get(config, 'server', 'host', default='127.0.0.1')
        port = get(config, 'server', 'port', default=5000)
        print(f"  Interface web : http://{host}:{port}")
    except ImportError as e:
        print(f"  Interface web non disponible : {e}")
    except Exception as e:
        print(f"  Erreur serveur web : {e}")

    # Lancer le serveur WebSocket pour Godot 4
    try:
        from ws_server import ws_server
        from nexos_interface.server import _generate_chat_response
        ws_server.configure(config, grid, vtime, population, control,
                           chat_handler=lambda t, m: {
                               'response': _generate_chat_response(t, m.lower().strip()),
                               'target': t
                           })
        ws_host = get(config, 'server', 'host', default='127.0.0.1')
        ws_server.start(host=ws_host, port=5001)
    except ImportError as e:
        print(f"  WebSocket Godot non disponible : {e}")
    except Exception as e:
        print(f"  Erreur WebSocket : {e}")

    print("")

    # Boucle de vie principale
    try:
        life_loop(config, grid, vtime, population, running, control)
    except KeyboardInterrupt:
        pass

    # Sauvegarde automatique a l'arret
    print("")
    print("  Sauvegarde en cours...")
    save_state(grid, vtime, population, config)

    # Fin
    print("")
    print("  --- Statistiques finales ---")
    print_stats(vtime, grid, population)
    stats = population.get_stats()
    print(f"  Temps reel : {vtime.format_real()}")
    print(f"  Temps virtuel : {vtime.format_virtual()}")
    print(f"  Total cycles : {vtime.get_cycles()}")
    print(f"  ISOs nes : {stats['total_born']}")
    print(f"  ISOs morts : {stats['total_died']}")
    print(f"  Generation max : {stats['max_generation']}")
    print(f"  Pic population : {stats['peak']}")
    print("")
    print("  A bientot sur NexOS.")
    print("")


if __name__ == '__main__':
    main()
