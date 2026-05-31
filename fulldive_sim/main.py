#!/usr/bin/env python3
# ============================================================
# FULL-DIVE HEADSET SIMULATOR
# Point d'entree principal
# ============================================================
"""
Simulation complete d'un casque Full-Dive a stimulation corticale directe.

Usage:
    python -m fulldive_sim.main [options]

Options:
    --frames N      Nombre de frames a simuler (defaut: 300)
    --realtime      Respecter le timing temps reel (60fps)
    --trajectory T  Type de trajectoire: raster, spirale, lissajous, hilbert
    --visualize     Afficher la visualisation ASCII
    --report        Generer un rapport HTML
"""

import sys
import argparse
import time
import numpy as np

from .config import FullDiveConfig
from .simulator import FullDiveSimulator
from .scanner import TrajectoireType
from .visualizer import ASCIIVisualizer, sauvegarder_rapport


def parse_args():
    parser = argparse.ArgumentParser(
        description="Simulateur de casque Full-Dive"
    )
    parser.add_argument('--frames', type=int, default=300,
                       help='Nombre de frames a simuler')
    parser.add_argument('--realtime', action='store_true',
                       help='Respecter le timing temps reel')
    parser.add_argument('--trajectory', type=str, default='spirale',
                       choices=['raster', 'spirale', 'lissajous', 'hilbert'],
                       help='Type de trajectoire de balayage')
    parser.add_argument('--visualize', action='store_true',
                       help='Afficher la visualisation ASCII')
    parser.add_argument('--report', action='store_true',
                       help='Generer un rapport HTML')
    parser.add_argument('--points', type=int, default=10000,
                       help='Nombre de points de stimulation')
    parser.add_argument('--fps', type=int, default=60,
                       help='Framerate cible')

    return parser.parse_args()


def run_simulation(args):
    """Lance la simulation avec les arguments specifies"""

    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║   ███████╗██╗   ██╗██╗     ██╗     ██████╗ ██╗██╗   ██╗  ║
    ║   ██╔════╝██║   ██║██║     ██║     ██╔══██╗██║██║   ██║  ║
    ║   █████╗  ██║   ██║██║     ██║     ██║  ██║██║██║   ██║  ║
    ║   ██╔══╝  ██║   ██║██║     ██║     ██║  ██║██║╚██╗ ██╔╝  ║
    ║   ██║     ╚██████╔╝███████╗███████╗██████╔╝██║ ╚████╔╝   ║
    ║   ╚═╝      ╚═════╝ ╚══════╝╚══════╝╚═════╝ ╚═╝  ╚═══╝    ║
    ║                                                           ║
    ║              HEADSET SIMULATOR v0.1                       ║
    ║         Stimulation Corticale Directe                     ║
    ╚═══════════════════════════════════════════════════════════╝
    """)

    # Configuration
    # Trouver le carre parfait le plus proche
    sqrt_points = int(np.sqrt(args.points))
    nb_points = sqrt_points ** 2

    config = FullDiveConfig(
        nb_points=nb_points,
        fps=args.fps
    )

    # Creer le simulateur
    sim = FullDiveSimulator(config)

    # Changer la trajectoire
    traj_map = {
        'raster': TrajectoireType.RASTER,
        'spirale': TrajectoireType.SPIRALE,
        'lissajous': TrajectoireType.LISSAJOUS,
        'hilbert': TrajectoireType.HILBERT
    }
    sim.changer_trajectoire(traj_map[args.trajectory])

    # Visualiseur
    viz = ASCIIVisualizer()

    if args.visualize:
        print("\n" + viz.render_trajectoire(sim.trajectoire))
        print()

    # Callback pour visualisation en temps reel
    last_viz_time = [0]

    def on_frame(result):
        if args.visualize and time.time() - last_viz_time[0] > 0.5:
            # Effacer l'ecran (ANSI)
            print("\033[2J\033[H", end="")
            print(viz.render_frame_result(result))
            last_viz_time[0] = time.time()

    if args.visualize:
        sim.on_frame_complete = on_frame

    # Lancer la simulation
    print(f"\nDemarrage simulation: {args.frames} frames")
    print(f"Trajectoire: {args.trajectory}")
    print(f"Points: {nb_points}")
    print(f"Temps reel: {args.realtime}")
    print("-" * 60)

    sim.run(nb_frames=args.frames, temps_reel=args.realtime)

    # Afficher statistiques finales
    if not args.visualize:
        print("\n" + viz.render_statistiques(sim.historique_frames))

    # Generer rapport
    if args.report:
        sauvegarder_rapport(
            sim.historique_frames,
            sim.trajectoire,
            {
                'nb_points': config.nb_points,
                'fps': config.fps,
                'grille_size': config.grille_size
            }
        )

    return sim


def demo_interactive():
    """Demo interactive avec controles clavier"""
    print("Demo interactive non disponible sans dependances graphiques")
    print("Utilisez --visualize pour la visualisation ASCII")


def benchmark():
    """Benchmark des performances"""
    print("\n=== BENCHMARK FULL-DIVE ===\n")

    configurations = [
        (100, 60),    # 100 points, 60fps
        (2500, 60),   # 2500 points, 60fps
        (10000, 60),  # 10000 points, 60fps
        (10000, 120), # 10000 points, 120fps
    ]

    for nb_points, fps in configurations:
        # Trouver carre parfait
        sqrt_points = int(np.sqrt(nb_points))
        nb_points = sqrt_points ** 2

        config = FullDiveConfig(nb_points=nb_points, fps=fps)
        sim = FullDiveSimulator(config)

        # Simuler 100 frames
        t_start = time.perf_counter()
        for _ in range(100):
            sim.simuler_frame()
        t_end = time.perf_counter()

        fps_reel = 100 / (t_end - t_start)
        print(f"Config {nb_points:>5} pts @ {fps:>3}fps -> {fps_reel:>7.1f} fps reel "
              f"({'OK' if fps_reel >= fps else 'LENT'})")

    print()


def main():
    args = parse_args()

    if hasattr(args, 'benchmark') and args.benchmark:
        benchmark()
    else:
        run_simulation(args)


if __name__ == "__main__":
    main()
