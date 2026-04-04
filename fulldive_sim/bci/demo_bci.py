#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================================
# DEMO BCI FULL-DIVE
# ============================================================

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np

from fulldive_sim.bci.config_bci import ConfigBCI
from fulldive_sim.bci.capteurs import CapteurEEG, CapteurIMU
from fulldive_sim.bci.decodeur import DecodeurMoteur
from fulldive_sim.bci.calibration import CalibreurBCI
from fulldive_sim.bci.controleur import ControleurAvatar


def demo():
    print("""
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   ██████╗  ██████╗██╗                                        ║
║   ██╔══██╗██╔════╝██║                                        ║
║   ██████╔╝██║     ██║                                        ║
║   ██╔══██╗██║     ██║                                        ║
║   ██████╔╝╚██████╗██║                                        ║
║   ╚═════╝  ╚═════╝╚═╝                                        ║
║                                                               ║
║   Brain-Computer Interface - Version Low-Cost                ║
║   Budget: ~98€ | 8 électrodes | ESP32-S3                    ║
╚═══════════════════════════════════════════════════════════════╝
    """)

    # === 1. CONFIGURATION ===
    print("[1/4] Configuration...")
    config = ConfigBCI()
    config.afficher()

    # === 2. CALIBRATION ===
    print("\n[2/4] Calibration (simulation)...")
    controleur = ControleurAvatar()
    calibreur = CalibreurBCI(controleur.decodeur, nb_essais_par_classe=20)
    resultats = calibreur.simuler_calibration_complete(controleur.eeg)

    if resultats.get('precision', 0) > 0:
        print(f"\nPrécision: {resultats['precision']*100:.1f}%")

    # === 3. SIMULATION DE CONTRÔLE ===
    print("\n[3/4] Simulation de contrôle...")

    # Scénario: marche
    print("\n--- Scénario: Marche ---")
    controleur_marche = ControleurAvatar()
    controleur_marche.decodeur.classificateur = controleur.decodeur.classificateur
    controleur_marche.simuler_session(duree_s=15.0, scenario="marche")

    # Scénario: slalom
    print("\n--- Scénario: Slalom ---")
    controleur_slalom = ControleurAvatar()
    controleur_slalom.decodeur.classificateur = controleur.decodeur.classificateur
    controleur_slalom.simuler_session(duree_s=15.0, scenario="slalom")

    # === 4. LATENCE ===
    print("\n[4/4] Analyse de latence...")
    latence = controleur.get_latence_estimee()

    print(f"""
╔═══════════════════════════════════════════════════════════╗
║              LATENCE DU SYSTÈME                          ║
╠═══════════════════════════════════════════════════════════╣
║                                                           ║
║  ROTATION TÊTE (IMU) :                                   ║
║  └─ IMU → orientation :     {latence['imu_ms']:>4}ms  ← INSTANTANÉ    ║
║                                                           ║
║  MOUVEMENT CORPS (EEG) :                                 ║
║  ├─ Acquisition EEG :       {latence['eeg_acquisition_ms']:>4.0f}ms                ║
║  ├─ Fenêtre analyse :       {latence['eeg_fenetre_ms']:>4}ms                ║
║  ├─ Classification LDA :    {latence['classification_ms']:>4}ms                ║
║  ├─ Gain prédicteur :      {latence['prediction_gain_ms']:>4}ms  ← ANTICIPATION  ║
║  └─ TOTAL :                 ~{latence['total_eeg_ms']:>3}ms                ║
║                                                           ║
║  BUDGET COMPOSANTS :                                     ║
║  ├─ ADS1299 (8ch EEG) :       30€                        ║
║  ├─ MPU6050 (IMU) :            2€                        ║
║  ├─ ESP32-S3 :                 8€                        ║
║  ├─ 8 électrodes sèches :    16€                        ║
║  ├─ Batterie LiPo :           5€                        ║
║  ├─ PCB + composants :       25€                        ║
║  └─ Boîtier imprimé 3D :      5€                        ║
║  ──────────────────────────────────                      ║
║  TOTAL :                     ~98€                        ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
    """)

    # Dimensions dans le casque
    print("""
╔═══════════════════════════════════════════════════════════╗
║           INTÉGRATION DANS LE CASQUE                     ║
╠═══════════════════════════════════════════════════════════╣
║                                                           ║
║  Le tout tient dans le bandeau AmuSphere :               ║
║                                                           ║
║  ┌─── BANDEAU (35mm large × 12mm épais) ───────────┐    ║
║  │                                                   │    ║
║  │  [ADS1299]  8×4mm chip                           │    ║
║  │  [ESP32-S3] 18×25mm module                       │    ║
║  │  [MPU6050]  4×4mm chip                           │    ║
║  │  [LiPo]    40×30×5mm (dans la partie arrière)    │    ║
║  │  [8 élec.] intégrées dans le bandeau             │    ║
║  │                                                   │    ║
║  │  Volume total électronique : ~15 cm³              │    ║
║  │  Poids électronique :       ~25g                  │    ║
║  │                                                   │    ║
║  └───────────────────────────────────────────────────┘    ║
║                                                           ║
║  Les 8 électrodes sont des pastilles conductrices        ║
║  intégrées dans la face interne du bandeau.              ║
║  Contact direct avec le cuir chevelu.                    ║
║  Pas de gel, pas de préparation → prêt en 30 secondes.  ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
    """)

    print("Demo BCI terminée!")


if __name__ == "__main__":
    demo()
