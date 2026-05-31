#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================================
# CAPTEURS - EEG (ADS1299) + IMU (MPU6050)
# Simulation des signaux cérébraux et mouvements de tête
# ============================================================

import numpy as np
from dataclasses import dataclass, field
from collections import deque
from typing import Dict, List, Optional, Tuple


# ============================================================
# CAPTEUR EEG (simule un ADS1299 8 canaux)
# ============================================================

class CapteurEEG:
    """
    Simule un capteur EEG 8 canaux basé sur ADS1299

    Signaux simulés :
    - Rythme mu (8-13 Hz) : supprimé quand on imagine un mouvement
    - Rythme beta (13-30 Hz) : rebond après mouvement
    - MRCP : potentiel lent pré-mouvement (-300ms)
    - SSVEP : réponse à stimulation visuelle rythmique
    - Bruit de fond : 1/f + bruit blanc
    """

    def __init__(self, nb_canaux=8, fs=250):
        self.nb_canaux = nb_canaux
        self.fs = fs
        self.dt = 1.0 / fs

        # Noms des canaux
        self.canaux = ['C3', 'C4', 'Cz', 'P3', 'P4', 'F3', 'F4', 'Oz']

        # État interne
        self.temps = 0.0
        self.etat_moteur = 'repos'  # repos, main_gauche, main_droite, pieds
        self.buffer = deque(maxlen=fs * 5)  # 5 secondes de buffer

        # Paramètres physiologiques simulés
        self.amplitude_mu = 10.0      # µV
        self.amplitude_beta = 5.0     # µV
        self.amplitude_bruit = 3.0    # µV
        self.freq_mu = 10.0           # Hz (centre bande mu)
        self.freq_beta = 20.0         # Hz (centre bande beta)

    def set_etat_moteur(self, etat: str):
        """Change l'état moteur simulé (ce que l'utilisateur imagine)"""
        self.etat_moteur = etat

    def lire_echantillon(self) -> np.ndarray:
        """
        Lit un échantillon de tous les canaux

        Returns:
            np.ndarray shape (nb_canaux,) en microvolts
        """
        echantillon = np.zeros(self.nb_canaux)

        for i, canal in enumerate(self.canaux):
            echantillon[i] = self._generer_signal_canal(canal)

        self.temps += self.dt
        self.buffer.append(echantillon.copy())

        return echantillon

    def lire_bloc(self, nb_echantillons: int) -> np.ndarray:
        """
        Lit un bloc de données

        Returns:
            np.ndarray shape (nb_echantillons, nb_canaux)
        """
        bloc = np.zeros((nb_echantillons, self.nb_canaux))
        for i in range(nb_echantillons):
            bloc[i] = self.lire_echantillon()
        return bloc

    def _generer_signal_canal(self, canal: str) -> float:
        """Génère le signal pour un canal spécifique"""
        t = self.temps
        signal = 0.0

        # === 1. RYTHME MU (8-13 Hz) ===
        # Présent au repos, supprimé (ERD) lors d'imagerie motrice
        mu = self.amplitude_mu * np.sin(2 * np.pi * self.freq_mu * t)

        if canal == 'C3':  # Cortex moteur gauche → contrôle main DROITE
            if self.etat_moteur == 'main_droite':
                mu *= 0.2  # Suppression mu (ERD) → imagerie main droite
            elif self.etat_moteur == 'main_gauche':
                mu *= 1.2  # Léger renforcement (ERS controlatéral)
            signal += mu

        elif canal == 'C4':  # Cortex moteur droit → contrôle main GAUCHE
            if self.etat_moteur == 'main_gauche':
                mu *= 0.2  # Suppression mu
            elif self.etat_moteur == 'main_droite':
                mu *= 1.2
            signal += mu

        elif canal == 'Cz':  # Central → pieds
            if self.etat_moteur == 'avancer':
                mu *= 0.15  # Forte suppression mu pour les pieds
            signal += mu

        else:
            signal += mu * 0.5  # Mu plus faible sur les autres canaux

        # === 2. RYTHME BETA (13-30 Hz) ===
        beta = self.amplitude_beta * np.sin(2 * np.pi * self.freq_beta * t)

        if canal in ['C3', 'C4', 'Cz']:
            if self.etat_moteur != 'repos':
                beta *= 0.3  # Beta aussi supprimé pendant imagerie
            signal += beta

        # === 3. BRUIT DE FOND (1/f + blanc) ===
        bruit_blanc = np.random.normal(0, self.amplitude_bruit)
        # Bruit 1/f simplifié
        bruit_rose = np.random.normal(0, self.amplitude_bruit * 0.5) * 0.3
        signal += bruit_blanc + bruit_rose

        # === 4. ARTEFACT 50Hz (secteur) ===
        signal += 0.5 * np.sin(2 * np.pi * 50 * t)

        return signal

    def get_buffer(self, duree_ms: int) -> np.ndarray:
        """Retourne les dernières données du buffer"""
        nb_samples = int(duree_ms * self.fs / 1000)
        data = list(self.buffer)
        if len(data) < nb_samples:
            return np.array(data)
        return np.array(data[-nb_samples:])


# ============================================================
# CAPTEUR IMU (simule un MPU6050)
# ============================================================

class CapteurIMU:
    """
    Simule un MPU6050 (accéléromètre + gyroscope 6 axes)
    Utilisé pour le tracking de tête

    Coût : ~2€
    """

    def __init__(self, fs=100):
        self.fs = fs
        self.dt = 1.0 / fs

        # État
        self.position = np.zeros(3)      # x, y, z (mètres)
        self.orientation = np.zeros(3)   # roll, pitch, yaw (radians)
        self.vitesse = np.zeros(3)
        self.vitesse_ang = np.zeros(3)

        # Bruit capteur (réaliste pour MPU6050)
        self.bruit_accel = 0.004    # g (400 µg/√Hz)
        self.bruit_gyro = 0.005     # °/s (5 m°/s/√Hz)
        self.derive_gyro = 0.001    # °/s (drift)

    def set_mouvement_tete(self, vitesse_ang: np.ndarray):
        """
        Simule un mouvement de tête

        Args:
            vitesse_ang: [roll, pitch, yaw] en °/s
        """
        self.vitesse_ang = np.radians(vitesse_ang)

    def lire(self) -> Dict[str, np.ndarray]:
        """
        Lit les données IMU

        Returns:
            dict avec accel (3,) et gyro (3,) et orientation (3,)
        """
        # Mise à jour orientation
        self.orientation += self.vitesse_ang * self.dt

        # Accéléromètre (gravité + mouvement)
        accel = np.array([0, 0, 9.81])  # Gravité
        accel += np.random.normal(0, self.bruit_accel, 3)

        # Gyroscope
        gyro = self.vitesse_ang.copy()
        gyro += np.random.normal(0, np.radians(self.bruit_gyro), 3)
        gyro += np.radians(self.derive_gyro)  # Dérive

        return {
            'accel': accel,
            'gyro': gyro,
            'orientation': self.orientation.copy(),
            'timestamp': 0
        }


# ============================================================
# FUSION DE CAPTEURS
# ============================================================

class FusionCapteurs:
    """
    Fusionne EEG + IMU pour un contrôle enrichi

    L'IMU donne le mouvement RÉEL de la tête (rapide, précis)
    L'EEG donne l'INTENTION de mouvement du corps virtuel

    Combinaison :
    - Rotation tête → IMU (direct, pas besoin d'EEG)
    - Marche/course → EEG (imagerie motrice pieds)
    - Actions mains → EEG (imagerie motrice mains)
    - Saut/action → EEG (SSVEP ou P300)
    """

    def __init__(self, eeg: CapteurEEG, imu: CapteurIMU):
        self.eeg = eeg
        self.imu = imu
        self.historique = deque(maxlen=1000)

    def lire_synchronise(self) -> dict:
        """Lecture synchronisée de tous les capteurs"""
        # Ratio d'échantillonnage : EEG 250Hz, IMU 100Hz
        # On lit l'EEG à chaque appel, l'IMU quand disponible

        eeg_data = self.eeg.lire_echantillon()
        imu_data = self.imu.lire()

        fusion = {
            'eeg': eeg_data,
            'imu_accel': imu_data['accel'],
            'imu_gyro': imu_data['gyro'],
            'orientation_tete': imu_data['orientation'],
        }

        self.historique.append(fusion)
        return fusion

    def get_fenetre(self, duree_ms: int) -> dict:
        """Retourne une fenêtre de données fusionnées"""
        nb_samples = int(duree_ms * self.eeg.fs / 1000)
        data = list(self.historique)

        if len(data) < nb_samples:
            nb_samples = len(data)

        recent = data[-nb_samples:]

        return {
            'eeg': np.array([d['eeg'] for d in recent]),
            'orientation': np.array([d['orientation_tete'] for d in recent]),
            'duree_ms': duree_ms,
            'nb_samples': nb_samples
        }
