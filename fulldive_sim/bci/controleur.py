#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================================
# CONTRÔLEUR D'AVATAR
# Intègre BCI + IMU → mouvement fluide dans le monde virtuel
# ============================================================
#
# PRINCIPE : L'IMU fait 80% du travail (tête = rapide, précis)
#            L'EEG fait les 20% restants (corps = intention)
#
# C'est ce qui rend le système RÉALISTE et PAS CHER
#
# ============================================================

import numpy as np
from typing import Dict, Optional
from collections import deque

from .capteurs import CapteurEEG, CapteurIMU, FusionCapteurs
from .decodeur import DecodeurMoteur
from .predicteur import PredicteurMouvement, LisseurCommandes


class ControleurAvatar:
    """
    Contrôleur complet de l'avatar virtuel

    Architecture :
    ┌────────────┐     ┌──────────────┐     ┌────────────────┐
    │ IMU (100Hz)│────▶│ Orientation  │────▶│ Rotation tête  │
    │ MPU6050    │     │ tête directe │     │ (instantané)   │
    └────────────┘     └──────────────┘     └────────────────┘

    ┌────────────┐     ┌──────────────┐     ┌────────────────┐
    │ EEG (250Hz)│────▶│ Décodeur     │────▶│ Mouvement corps│
    │ ADS1299    │     │ + Prédicteur │     │ (50ms latence) │
    └────────────┘     └──────────────┘     └────────────────┘

                       ┌──────────────┐     ┌────────────────┐
                       │ Fusion       │────▶│ Avatar unifié  │
                       │ IMU + EEG    │     │ dans le monde  │
                       └──────────────┘     └────────────────┘
    """

    def __init__(self, fs_eeg=250, fs_imu=100):
        # Capteurs
        self.eeg = CapteurEEG(nb_canaux=8, fs=fs_eeg)
        self.imu = CapteurIMU(fs=fs_imu)
        self.fusion = FusionCapteurs(self.eeg, self.imu)

        # Décodage EEG
        self.decodeur = DecodeurMoteur(fs=fs_eeg, nb_canaux=8)
        self.predicteur = PredicteurMouvement(horizon_ms=200)
        self.lisseur = LisseurCommandes(alpha=0.3)

        # État de l'avatar
        self.position = np.zeros(3)       # x, y, z (mètres)
        self.orientation = np.zeros(3)    # roll, pitch, yaw (radians)
        self.vitesse_deplacement = 1.5    # m/s (vitesse de marche)

        # Paramètres
        self.fs_eeg = fs_eeg
        self.fs_imu = fs_imu

        # Compteur de mise à jour
        self.tick_count = 0
        self.eeg_tick_ratio = fs_eeg // fs_imu  # 2.5 → arrondi à 2

        # Historique pour debug
        self.historique_commandes = deque(maxlen=500)

    def update(self, dt: float) -> dict:
        """
        Mise à jour principale (appelée à chaque tick du simulateur)

        Args:
            dt: Pas de temps en secondes

        Returns:
            État de l'avatar
        """
        self.tick_count += 1

        # === 1. IMU → Rotation tête (TOUJOURS, rapide) ===
        imu_data = self.imu.lire()
        self.orientation = imu_data['orientation']

        # === 2. EEG → Décodage intention motrice ===
        # L'EEG est traité à chaque tick mais la décision
        # sort seulement quand la fenêtre est pleine
        eeg_sample = self.eeg.lire_echantillon()
        resultat_eeg = self.decodeur.traiter_echantillon(eeg_sample)

        commande = 'repos'
        confiance = 0.0

        if resultat_eeg:
            commande = resultat_eeg['commande']
            confiance = resultat_eeg['confiance']

            # === 3. Prédiction anticipée ===
            prediction = self.predicteur.mettre_a_jour(
                resultat_eeg['features'],
                resultat_eeg['commande_brute'],
                confiance
            )

            if prediction:
                commande = prediction
                confiance = 0.8

        # === 4. Lissage → Axes continus ===
        axes = self.lisseur.lisser(commande, confiance)

        # === 5. Appliquer le mouvement ===
        self._appliquer_mouvement(axes, dt)

        # Historique
        etat = {
            'position': self.position.copy(),
            'orientation': self.orientation.copy(),
            'commande': commande,
            'confiance': confiance,
            'axes': axes.copy(),
            'tick': self.tick_count
        }
        self.historique_commandes.append(etat)

        return etat

    def _appliquer_mouvement(self, axes: dict, dt: float):
        """
        Applique les axes de mouvement à la position de l'avatar

        Le mouvement se fait dans la direction où regarde la tête (IMU)
        """
        yaw = self.orientation[2]  # Direction du regard

        # Direction avant (basée sur le regard)
        dir_avant = np.array([
            np.cos(yaw),
            np.sin(yaw),
            0
        ])

        # Direction latérale
        dir_lateral = np.array([
            -np.sin(yaw),
            np.cos(yaw),
            0
        ])

        # Déplacement
        vitesse = self.vitesse_deplacement * dt

        # Avant/arrière (EEG)
        self.position += dir_avant * axes['avant_arriere'] * vitesse

        # Gauche/droite (EEG)
        self.position += dir_lateral * axes['gauche_droite'] * vitesse

    def simuler_session(self, duree_s: float = 30.0, scenario: str = "marche"):
        """
        Simule une session complète de contrôle

        Args:
            duree_s: Durée en secondes
            scenario: Type de scénario à simuler
        """
        print(f"\nSimulation: {scenario} ({duree_s}s)")
        print("-" * 50)

        dt = 1.0 / self.fs_imu  # Pas de temps basé sur IMU (100Hz)
        nb_ticks = int(duree_s * self.fs_imu)

        # Scénario
        for tick in range(nb_ticks):
            temps = tick * dt

            # Appliquer le scénario
            self._appliquer_scenario(scenario, temps, duree_s)

            # Mise à jour
            etat = self.update(dt)

            # Affichage périodique
            if tick % (self.fs_imu * 2) == 0:  # Toutes les 2 secondes
                print(f"  t={temps:5.1f}s | "
                      f"pos=({etat['position'][0]:+6.2f}, {etat['position'][1]:+6.2f}) | "
                      f"cmd={etat['commande']:>12s} | "
                      f"conf={etat['confiance']:.2f}")

        # Résumé
        self._afficher_resume()

    def _appliquer_scenario(self, scenario: str, temps: float, duree_totale: float):
        """Applique un scénario de test"""
        if scenario == "marche":
            # Marche en ligne droite
            if 2 < temps < duree_totale - 2:
                self.eeg.set_etat_moteur('avancer')
            else:
                self.eeg.set_etat_moteur('repos')

        elif scenario == "slalom":
            # Alterner gauche/droite toutes les 3 secondes
            phase = int(temps / 3) % 3
            if phase == 0:
                self.eeg.set_etat_moteur('avancer')
            elif phase == 1:
                self.eeg.set_etat_moteur('main_gauche')
                self.imu.set_mouvement_tete(np.array([0, 0, -30]))
            else:
                self.eeg.set_etat_moteur('main_droite')
                self.imu.set_mouvement_tete(np.array([0, 0, 30]))

        elif scenario == "interaction":
            # Marche + actions
            if temps < 5:
                self.eeg.set_etat_moteur('avancer')
            elif 5 <= temps < 7:
                self.eeg.set_etat_moteur('action')
            elif 7 <= temps < 12:
                self.eeg.set_etat_moteur('avancer')
            elif 12 <= temps < 14:
                self.eeg.set_etat_moteur('main_droite')
            else:
                self.eeg.set_etat_moteur('repos')

    def _afficher_resume(self):
        """Affiche le résumé de la session"""
        if not self.historique_commandes:
            return

        commandes = [h['commande'] for h in self.historique_commandes]
        positions = [h['position'] for h in self.historique_commandes]

        # Distance parcourue
        distance = 0
        for i in range(1, len(positions)):
            distance += np.linalg.norm(positions[i] - positions[i-1])

        # Distribution des commandes
        compteur = {}
        for c in commandes:
            compteur[c] = compteur.get(c, 0) + 1

        print("\n" + "=" * 50)
        print("RÉSUMÉ SESSION")
        print("=" * 50)
        print(f"Distance parcourue: {distance:.2f}m")
        print(f"Position finale: ({positions[-1][0]:.2f}, {positions[-1][1]:.2f})")
        print(f"\nDistribution commandes:")
        for cmd, count in sorted(compteur.items(), key=lambda x: -x[1]):
            pct = count / len(commandes) * 100
            bar = "█" * int(pct / 2)
            print(f"  {cmd:>12s}: {bar} {pct:.1f}%")
        print("=" * 50)

    def get_latence_estimee(self) -> dict:
        """Estime la latence totale du système"""
        return {
            'imu_ms': 10,                                    # IMU → orientation
            'eeg_acquisition_ms': 1000 / self.fs_eeg * 4,   # 4 échantillons
            'eeg_fenetre_ms': 500,                           # Fenêtre d'analyse
            'classification_ms': 1,                          # LDA très rapide
            'prediction_gain_ms': -200,                      # Gain prédicteur
            'total_imu_ms': 10,                              # Rotation tête
            'total_eeg_ms': 500 + 16 + 1 - 200,             # Mouvement corps
            'note': 'IMU: instantané, EEG: ~317ms avec prédiction'
        }
