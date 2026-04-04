#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================================
# CONFIGURATION BCI - VERSION LOW-COST
# ============================================================
#
# COMPOSANTS RÉELS ET PRIX ESTIMÉS :
#
# ┌──────────────────────────────────┬──────────┬──────────┐
# │ Composant                        │ Qté      │ Prix     │
# ├──────────────────────────────────┼──────────┼──────────┤
# │ ADS1299 (8ch EEG AFE)           │ 1        │ ~30€     │
# │ Électrodes sèches (Ag/AgCl)     │ 8        │ ~16€     │
# │ MPU6050 (IMU 6 axes)            │ 1        │ ~2€      │
# │ ESP32-S3 (microcontrôleur)      │ 1        │ ~8€      │
# │ Raspberry Pi Pico W             │ 1        │ ~7€      │
# │ Batterie LiPo 3.7V 1000mAh     │ 1        │ ~5€      │
# │ PCB custom                      │ 1        │ ~15€     │
# │ Connecteurs, câbles, mousse     │ divers   │ ~10€     │
# │ Boîtier imprimé 3D              │ 1        │ ~5€      │
# ├──────────────────────────────────┼──────────┼──────────┤
# │ TOTAL                           │          │ ~98€     │
# └──────────────────────────────────┴──────────┴──────────┘
#
# ============================================================

from dataclasses import dataclass, field


@dataclass
class ConfigBCI:
    """Configuration du système BCI low-cost"""

    # === ÉLECTRODES EEG ===
    # 8 canaux suffisent pour le contrôle moteur
    # Positions : C3, C4, Cz (moteur) + P3, P4 (spatial)
    #           + F3, F4 (intention) + Oz (référence visuelle)
    nb_electrodes: int = 8
    positions_electrodes: tuple = (
        'C3',   # Cortex moteur gauche (main droite)
        'C4',   # Cortex moteur droit (main gauche)
        'Cz',   # Cortex moteur central (pieds)
        'P3',   # Pariétal gauche (spatial)
        'P4',   # Pariétal droit (spatial)
        'F3',   # Frontal gauche (intention)
        'F4',   # Frontal droit (intention)
        'Oz',   # Occipital (référence + SSVEP)
    )
    type_electrodes: str = "seches"  # seches ou gel (sèches = moins cher)
    frequence_echantillonnage: int = 250  # Hz (ADS1299 supporte jusqu'à 16kHz)

    # === IMU (Inertial Measurement Unit) ===
    # MPU6050 : accéléromètre 3 axes + gyroscope 3 axes
    imu_freq: int = 100            # Hz
    imu_type: str = "MPU6050"

    # === TRAITEMENT SIGNAL ===
    fenetre_analyse_ms: int = 500  # Fenêtre glissante d'analyse
    pas_glissement_ms: int = 50    # Mise à jour toutes les 50ms → 20 Hz
    filtre_bas_hz: float = 7.0     # Filtre passe-bande bas
    filtre_haut_hz: float = 30.0   # Filtre passe-bande haut
    filtre_notch_hz: float = 50.0  # Filtre coupe-bande (secteur)

    # === CLASSIFICATEUR ===
    # On utilise un LDA (Linear Discriminant Analysis)
    # Simple, rapide, fonctionne sur ESP32
    type_classificateur: str = "LDA"  # LDA, SVM_lineaire, ou arbre
    nb_commandes: int = 6          # Nombre de commandes distinctes
    seuil_confiance: float = 0.65  # Seuil minimum pour accepter une commande

    # === COMMANDES DÉCODABLES ===
    commandes: tuple = (
        'repos',           # Aucun mouvement
        'avancer',         # Imagerie motrice pieds → Cz
        'main_gauche',     # Imagerie motrice main G → C4
        'main_droite',     # Imagerie motrice main D → C3
        'action',          # SSVEP ou P300 → Oz
        'rotation',        # Combiné IMU + EEG
    )

    # === CALIBRATION ===
    duree_calibration_min: int = 15  # 15 minutes de calibration
    nb_essais_par_commande: int = 30 # 30 essais par classe
    adaptation_continue: bool = True # Ajustement en temps réel

    # === PRÉDICTION ===
    # MRCP (Movement-Related Cortical Potential) détectable 300ms avant
    prediction_anticipee: bool = True
    horizon_prediction_ms: int = 200  # Anticiper de 200ms

    # === HARDWARE ===
    microcontroleur: str = "ESP32-S3"
    communication: str = "BLE"     # Bluetooth Low Energy
    batterie_mah: int = 1000
    autonomie_estimee_h: float = 8.0

    def afficher(self):
        print("=" * 55)
        print("CONFIGURATION BCI LOW-COST")
        print("=" * 55)
        print(f"Électrodes:     {self.nb_electrodes} ({self.type_electrodes})")
        print(f"Positions:      {', '.join(self.positions_electrodes)}")
        print(f"Échantillonnage: {self.frequence_echantillonnage} Hz")
        print(f"IMU:            {self.imu_type} @ {self.imu_freq} Hz")
        print(f"Classificateur: {self.type_classificateur}")
        print(f"Commandes:      {self.nb_commandes}")
        print(f"Latence:        ~{self.pas_glissement_ms}ms")
        print(f"MCU:            {self.microcontroleur}")
        print(f"Communication:  {self.communication}")
        print(f"Budget estimé:  ~98€")
        print("=" * 55)
