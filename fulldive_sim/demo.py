#!/usr/bin/env python3
# ============================================================
# DEMO RAPIDE DU SIMULATEUR FULL-DIVE
# Script standalone sans arguments
# ============================================================
"""
Demo rapide du simulateur Full-Dive.
Affiche une simulation de 60 frames avec visualisation ASCII.

Usage:
    python fulldive_sim/demo.py
"""

import sys
import os

# Ajouter le chemin parent pour les imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import time

# Imports locaux
from fulldive_sim.config import FullDiveConfig
from fulldive_sim.simulator import FullDiveSimulator
from fulldive_sim.scanner import TrajectoireType
from fulldive_sim.visualizer import ASCIIVisualizer


def demo():
    """Demo complete du systeme Full-Dive"""

    print("""
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║   ██████╗ ███████╗███╗   ███╗ ██████╗                            ║
║   ██╔══██╗██╔════╝████╗ ████║██╔═══██╗                           ║
║   ██║  ██║█████╗  ██╔████╔██║██║   ██║                           ║
║   ██║  ██║██╔══╝  ██║╚██╔╝██║██║   ██║                           ║
║   ██████╔╝███████╗██║ ╚═╝ ██║╚██████╔╝                           ║
║   ╚═════╝ ╚══════╝╚═╝     ╚═╝ ╚═════╝                            ║
║                                                                   ║
║   FULL-DIVE HEADSET SIMULATOR                                    ║
║   Casque de Realite Virtuelle a Stimulation Corticale Directe   ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
    """)

    # === 1. CONFIGURATION ===
    print("\n[1/5] Configuration du systeme...")
    config = FullDiveConfig(
        nb_points=2500,  # 50x50 pour la demo (plus rapide)
        fps=60
    )
    config.afficher_resume()

    # === 2. INITIALISATION ===
    print("\n[2/5] Initialisation du simulateur...")
    sim = FullDiveSimulator(config)

    # === 3. TEST DES TRAJECTOIRES ===
    print("\n[3/5] Test des trajectoires de balayage...")
    viz = ASCIIVisualizer(width=50, height=25)

    for traj_type in [TrajectoireType.RASTER, TrajectoireType.SPIRALE,
                      TrajectoireType.LISSAJOUS]:
        sim.changer_trajectoire(traj_type)
        print(f"\n--- Trajectoire: {traj_type.value.upper()} ---")
        print(viz.render_trajectoire(sim.trajectoire, nb_points=300))

        stats = sim.scanner.calculer_statistiques(sim.trajectoire)
        print(f"   Frequence: {stats['frequence_balayage_khz']:.0f} kHz")
        print(f"   Couverture: {stats['couverture_pct']:.1f}%")

    # Utiliser spirale pour la suite
    sim.changer_trajectoire(TrajectoireType.SPIRALE)

    # === 4. SIMULATION ===
    print("\n[4/5] Simulation de 60 frames...")
    print("-" * 60)

    resultats = []
    for i in range(60):
        result = sim.simuler_frame()
        resultats.append(result)

        # Affichage progression
        if (i + 1) % 10 == 0:
            print(f"   Frame {i+1:3d}/60 | "
                  f"FPS: {result.fps_reel:6.1f} | "
                  f"Perception: {np.mean(result.perception):.3f}")

    # === 5. RESULTATS ===
    print("\n[5/5] Resultats de la simulation")
    print("=" * 60)

    fps_list = [r.fps_reel for r in resultats]
    perc_list = [np.mean(r.perception) for r in resultats]

    print(f"Frames simulees:     {len(resultats)}")
    print(f"FPS moyen:           {np.mean(fps_list):.1f}")
    print(f"FPS minimum:         {min(fps_list):.1f}")
    print(f"FPS maximum:         {max(fps_list):.1f}")
    print(f"Perception moyenne:  {np.mean(perc_list):.4f}")
    print(f"Perception max:      {max(perc_list):.4f}")

    # Derniere frame
    print("\n--- Derniere Frame ---")
    print(viz.render_frame_result(resultats[-1]))

    # Statistiques
    print("\n" + viz.render_statistiques(resultats))

    # === RESUME TECHNIQUE ===
    print("""
╔═══════════════════════════════════════════════════════════════════╗
║                      RESUME TECHNIQUE                             ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  PIPELINE:                                                        ║
║  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐  ║
║  │  Scene 3D  │→ │ Encodage   │→ │  Balayage  │→ │  Cortex    │  ║
║  │  Stereo    │  │ Retinotop. │  │    CRT     │  │   Visuel   │  ║
║  └────────────┘  └────────────┘  └────────────┘  └────────────┘  ║
║                                                                   ║
║  SPECIFICATIONS:                                                  ║
║  • 10 000 points de stimulation (extensible)                     ║
║  • 60 fps (16.67ms par frame)                                    ║
║  • 600 kHz frequence de balayage                                 ║
║  • 1.667 µs par point                                            ║
║  • Latence perception: ~80ms                                     ║
║                                                                   ║
║  HARDWARE REQUIS (pour implementation reelle):                   ║
║  • Reseau de transducteurs FUS (500 kHz)                         ║
║  • Bobines de deflexion piezoelectriques                         ║
║  • FPGA pour generation signaux temps reel                       ║
║  • EEG haute densite pour feedback                               ║
║  • IRM pour cartographie V1 individuelle                         ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
    """)

    print("Demo terminee avec succes!")
    return sim, resultats


if __name__ == "__main__":
    demo()
