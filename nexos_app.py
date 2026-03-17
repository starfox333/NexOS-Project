"""
NexOS — Application Desktop
Lance la vie artificielle + interface dans une fenetre native.
Double-clic pour demarrer. Aucun terminal necessaire.
"""

import sys
import os
import time
import threading
import signal

# Résolution chemin pour PyInstaller
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
    _internal = os.path.join(BASE_DIR, '_internal')
    if os.path.isdir(_internal):
        BASE_DIR = _internal
    sys.path.insert(0, BASE_DIR)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Forcer le CWD au bon endroit
os.chdir(BASE_DIR)

from nexos_core.config import load_config, get
from nexos_core.grid import Grid
from nexos_core.time_system import VirtualTime
from nexos_life.population import Population
from nexos_interface.server import create_app, start_server

import webview


def life_loop(config, grid, vtime, population, running):
    """Boucle de vie artificielle (thread daemon)"""
    cycle_delay = get(config, 'time', 'cycle_delay', default=0.05)
    stats_interval = get(config, 'logging', 'stats_interval', default=100)

    while running['run']:
        vtime.tick()
        grid.update()
        population.update_all(grid)
        population.handle_reproduction(grid)
        population.remove_dead(grid)

        # Respawn si extinction
        if len(population.get_alive()) == 0:
            initial = get(config, 'life', 'initial_population', default=10)
            population.spawn_initial(grid, initial)

        # Stats console (debug)
        if vtime.get_cycles() % stats_interval == 0:
            stats = population.get_stats()
            print(f"  [{vtime.format_virtual()}] Cycle {vtime.get_cycles()} | "
                  f"ISOs: {stats['alive']} | Gen: {stats['max_generation']} | "
                  f"Fitness: {stats['avg_fitness']:.1f}")

        time.sleep(cycle_delay)


def main():
    print("")
    print("  NexOS — Application Desktop")
    print("  Vie Artificielle Emergente")
    print("")

    # Config
    config = load_config()
    print("  Configuration chargee")

    # Systemes
    grid_size = get(config, 'grid', 'size', default=200)
    grid = Grid(size=grid_size, config=config)

    acceleration = get(config, 'time', 'acceleration', default=35)
    vtime = VirtualTime(acceleration=acceleration)

    population = Population(config=config)
    initial = get(config, 'life', 'initial_population', default=10)
    population.spawn_initial(grid, initial)

    running = {'run': True}

    # Serveur Flask (thread)
    app = create_app(config, grid, vtime, population)
    host = get(config, 'server', 'host', default='127.0.0.1')
    port = get(config, 'server', 'port', default=5000)

    server_thread = threading.Thread(
        target=start_server, args=(app, config), daemon=True
    )
    server_thread.start()
    print(f"  Serveur web : http://{host}:{port}")

    # Attendre que le serveur soit pret
    import urllib.request
    for _ in range(30):
        try:
            urllib.request.urlopen(f'http://{host}:{port}', timeout=1)
            break
        except Exception:
            time.sleep(0.3)

    # Boucle de vie (thread)
    life_thread = threading.Thread(
        target=life_loop, args=(config, grid, vtime, population, running),
        daemon=True
    )
    life_thread.start()
    print("  Vie artificielle activee")

    # Fenetre native pywebview
    print("  Ouverture de la fenetre...")
    window = webview.create_window(
        'NexOS — Vie Artificielle',
        f'http://{host}:{port}',
        width=1280, height=800,
        resizable=True,
        min_size=(800, 600),
        background_color='#000508',
        text_select=False
    )

    webview.start(debug=False)

    # Fermeture
    running['run'] = False
    print("")
    stats = population.get_stats()
    print(f"  Fin — {stats['total_born']} ISOs nes, {stats['max_generation']} generations")
    print("  A bientot sur NexOS.")


if __name__ == '__main__':
    main()
