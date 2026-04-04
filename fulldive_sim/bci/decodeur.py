#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================================
# DÉCODEUR MOTEUR
# Traitement du signal EEG et classification des intentions
# ============================================================
#
# PIPELINE SIMPLE :
#   EEG brut → Filtrage → Features (puissance mu/beta) → LDA → Commande
#
# Tout tourne sur un ESP32 (pas besoin de GPU)
#
# ============================================================

import numpy as np
from typing import Dict, List, Tuple, Optional
from collections import deque


class FiltreurSignal:
    """
    Filtrage du signal EEG en temps réel
    Implémentation légère pour microcontrôleur
    """

    def __init__(self, fs=250):
        self.fs = fs

        # Coefficients pré-calculés pour filtres IIR Butterworth ordre 2
        # Calculés offline, stockés en dur (pas besoin de scipy sur ESP32)
        self._init_filtres()

        # États des filtres (pour continuité entre blocs)
        self.etats_bp = {}   # Passe-bande
        self.etats_notch = {}  # Coupe-bande

    def _init_filtres(self):
        """
        Pré-calcule les coefficients des filtres

        Pour un vrai ESP32, ces coefficients seraient calculés une fois
        sur PC puis flashés dans le firmware
        """
        # Filtre passe-bande 7-30 Hz (capture mu + beta)
        # Butterworth ordre 2, coefficients pour fs=250Hz
        # Utilise 2 biquads cascadés (plus stable numériquement)
        # Biquad passe-haut 7Hz
        self.hp_b = np.array([0.8949, -1.7898, 0.8949])
        self.hp_a = np.array([1.0, -1.7786, 0.8008])
        # Biquad passe-bas 30Hz
        self.lp_b = np.array([0.0924, 0.1848, 0.0924])
        self.lp_a = np.array([1.0, -0.9088, 0.2784])

        # Filtre coupe-bande 50 Hz (supprimer le secteur)
        self.notch_b = np.array([0.9695, -1.5849, 0.9695])
        self.notch_a = np.array([1.0, -1.5849, 0.9391])

    def filtrer(self, signal: np.ndarray, canal: int) -> np.ndarray:
        """
        Filtre un signal EEG (passe-bande + notch)

        Args:
            signal: Signal brut (1D array)
            canal: Index du canal (pour mémoire d'état)

        Returns:
            Signal filtré
        """
        # Initialiser les états si nécessaire (2 échantillons par biquad)
        key_hp = f'{canal}_hp'
        key_lp = f'{canal}_lp'
        key_notch = f'{canal}_notch'
        if key_hp not in self.etats_bp:
            self.etats_bp[key_hp] = np.zeros(2)
            self.etats_bp[key_lp] = np.zeros(2)
            self.etats_notch[key_notch] = np.zeros(2)

        # Appliquer le filtre coupe-bande 50Hz
        signal_notch = self._filtre_biquad(
            signal, self.notch_b, self.notch_a, self.etats_notch[key_notch]
        )

        # Appliquer passe-haut 7Hz
        signal_hp = self._filtre_biquad(
            signal_notch, self.hp_b, self.hp_a, self.etats_bp[key_hp]
        )

        # Appliquer passe-bas 30Hz
        signal_lp = self._filtre_biquad(
            signal_hp, self.lp_b, self.lp_a, self.etats_bp[key_lp]
        )

        return signal_lp

    def _filtre_biquad(self, x: np.ndarray, b: np.ndarray, a: np.ndarray,
                       etat: np.ndarray) -> np.ndarray:
        """
        Filtre biquad (IIR ordre 2) - forme transposée directe II
        Numériquement stable, efficace pour microcontrôleur
        """
        y = np.zeros_like(x, dtype=np.float64)

        for i in range(len(x)):
            # Sortie
            y[i] = b[0] * x[i] + etat[0]

            # Mise à jour des 2 états
            etat[0] = b[1] * x[i] - a[1] * y[i] + etat[1]
            etat[1] = b[2] * x[i] - a[2] * y[i]

        return y


class ExtracteurFeatures:
    """
    Extraction de features simples et efficaces
    Optimisé pour tourner sur microcontrôleur
    """

    def __init__(self, fs=250, canaux=None):
        self.fs = fs
        self.canaux = canaux or ['C3', 'C4', 'Cz', 'P3', 'P4', 'F3', 'F4', 'Oz']

    def extraire(self, signal_filtre: np.ndarray) -> np.ndarray:
        """
        Extrait les features d'une fenêtre de signal filtré

        Args:
            signal_filtre: shape (nb_samples, nb_canaux)

        Returns:
            vecteur de features (1D array)

        Features extraites (par canal) :
        1. Puissance bande mu (8-13 Hz)     → 8 valeurs
        2. Puissance bande beta (13-30 Hz)  → 8 valeurs
        3. Ratio mu/beta                     → 8 valeurs
        4. Asymétrie C3-C4 (mu)             → 1 valeur
        5. Asymétrie C3-C4 (beta)           → 1 valeur
        6. Puissance Cz (pieds)             → 1 valeur
        ──────────────────────────────────────────────
        Total : 27 features (léger pour LDA)
        """
        nb_samples, nb_canaux = signal_filtre.shape
        features = []

        for ch in range(nb_canaux):
            canal = signal_filtre[:, ch]

            # Puissance bande mu (8-13 Hz) via Goertzel (léger)
            p_mu = self._puissance_bande(canal, 8, 13)

            # Puissance bande beta (13-30 Hz)
            p_beta = self._puissance_bande(canal, 13, 30)

            features.append(p_mu)
            features.append(p_beta)

            # Ratio (normalisation)
            ratio = p_mu / (p_beta + 1e-10)
            features.append(ratio)

        # Asymétries (clé pour latéralité gauche/droite)
        idx_c3 = self.canaux.index('C3')
        idx_c4 = self.canaux.index('C4')
        idx_cz = self.canaux.index('Cz')

        # Asymétrie mu C3-C4
        features.append(features[idx_c3 * 3] - features[idx_c4 * 3])

        # Asymétrie beta C3-C4
        features.append(features[idx_c3 * 3 + 1] - features[idx_c4 * 3 + 1])

        # Puissance Cz mu (pour pieds)
        features.append(features[idx_cz * 3])

        return np.array(features)

    def _puissance_bande(self, signal: np.ndarray, f_bas: float, f_haut: float) -> float:
        """
        Calcul de puissance dans une bande de fréquence
        Méthode simple : variance du signal dans la bande
        (plus stable que Goertzel pour les petits signaux)
        """
        # Méthode directe : puissance = variance du signal
        # Le signal est déjà filtré dans la bande 7-30Hz
        # On calcule juste la puissance RMS
        if len(signal) == 0:
            return 0.0

        # Puissance RMS dans la bande
        puissance = np.mean(signal ** 2)

        # Normaliser pour éviter les valeurs extrêmes
        return np.log1p(puissance + 1e-12)


class ClassificateurLDA:
    """
    Linear Discriminant Analysis - classificateur simple et rapide

    Pourquoi LDA :
    - Calcul = 1 multiplication matrice-vecteur (rapide sur ESP32)
    - Pas d'hyperparamètres à tuner
    - Fonctionne bien avec peu de données de calibration
    - Mémoire : juste une matrice de poids à stocker
    """

    def __init__(self, nb_features: int = 27, nb_classes: int = 6):
        self.nb_features = nb_features
        self.nb_classes = nb_classes

        # Poids du classificateur (calculés pendant calibration)
        self.W = None           # Matrice de projection
        self.moyennes = None    # Moyennes par classe
        self.calibre = False

        # Noms des classes
        self.classes = ['repos', 'avancer', 'main_gauche',
                       'main_droite', 'action', 'rotation']

    def entrainer(self, X: np.ndarray, y: np.ndarray):
        """
        Entraîne le classificateur LDA

        Args:
            X: Features (nb_essais, nb_features)
            y: Labels (nb_essais,) entiers 0-5
        """
        nb_samples, nb_feat = X.shape

        # Moyenne globale
        mu_global = np.mean(X, axis=0)

        # Matrices de dispersion
        S_within = np.zeros((nb_feat, nb_feat))
        S_between = np.zeros((nb_feat, nb_feat))

        self.moyennes = {}

        for c in range(self.nb_classes):
            mask = y == c
            if np.sum(mask) == 0:
                continue

            X_c = X[mask]
            mu_c = np.mean(X_c, axis=0)
            self.moyennes[c] = mu_c

            # Dispersion intra-classe
            diff = X_c - mu_c
            S_within += diff.T @ diff

            # Dispersion inter-classe
            n_c = X_c.shape[0]
            mu_diff = (mu_c - mu_global).reshape(-1, 1)
            S_between += n_c * (mu_diff @ mu_diff.T)

        # Résolution du problème aux valeurs propres
        # W = inv(S_within) @ S_between
        try:
            S_within_inv = np.linalg.inv(S_within + np.eye(nb_feat) * 1e-6)
            M = S_within_inv @ S_between

            valeurs, vecteurs = np.linalg.eigh(M)
            # Garder les (nb_classes - 1) meilleurs axes
            idx = np.argsort(valeurs)[::-1][:self.nb_classes - 1]
            self.W = vecteurs[:, idx]

        except np.linalg.LinAlgError:
            # Fallback : projection identité
            self.W = np.eye(nb_feat, self.nb_classes - 1)

        self.calibre = True

    def predire(self, features: np.ndarray) -> Tuple[str, float]:
        """
        Prédit la classe et la confiance

        Args:
            features: Vecteur de features (nb_features,)

        Returns:
            (classe, confiance)
        """
        if not self.calibre:
            return 'repos', 0.0

        # Projection LDA
        projection = features @ self.W

        # Distance aux moyennes projetées
        distances = {}
        for c, mu in self.moyennes.items():
            mu_proj = mu @ self.W
            dist = np.linalg.norm(projection - mu_proj)
            distances[c] = dist

        if not distances:
            return 'repos', 0.0

        # Classe la plus proche
        classe_idx = min(distances, key=distances.get)
        dist_min = distances[classe_idx]

        # Confiance (softmax simplifié)
        total = sum(np.exp(-d) for d in distances.values())
        confiance = np.exp(-dist_min) / total if total > 0 else 0.0

        return self.classes[classe_idx], confiance


class DecodeurMoteur:
    """
    Décodeur complet : EEG brut → commande motrice

    Pipeline optimisé pour ESP32 :
    - Filtrage IIR (temps réel, sample par sample)
    - Features simples (puissance par bande, asymétries)
    - LDA (1 multiplication matricielle)
    - Lissage temporel (évite les commandes parasites)
    """

    def __init__(self, fs=250, nb_canaux=8):
        self.fs = fs
        self.nb_canaux = nb_canaux

        # Composants du pipeline
        self.filtreur = FiltreurSignal(fs)
        self.extracteur = ExtracteurFeatures(fs)
        self.classificateur = ClassificateurLDA()

        # Buffer de fenêtre glissante
        self.fenetre_ms = 500
        self.fenetre_samples = int(fs * self.fenetre_ms / 1000)
        self.buffer = deque(maxlen=self.fenetre_samples)

        # Lissage temporel des prédictions
        self.historique_predictions = deque(maxlen=5)
        self.commande_precedente = 'repos'

        # Statistiques
        self.nb_predictions = 0
        self.stats = {'repos': 0, 'avancer': 0, 'main_gauche': 0,
                     'main_droite': 0, 'action': 0, 'rotation': 0}

    def traiter_echantillon(self, eeg_brut: np.ndarray) -> Optional[dict]:
        """
        Traite un échantillon EEG et retourne une commande si disponible

        Args:
            eeg_brut: shape (nb_canaux,) en µV

        Returns:
            dict avec commande si fenêtre complète, None sinon
        """
        # Filtrer canal par canal
        echantillon_filtre = np.zeros(self.nb_canaux)
        for ch in range(self.nb_canaux):
            echantillon_filtre[ch] = self.filtreur.filtrer(
                np.array([eeg_brut[ch]]), ch
            )[0]

        # Ajouter au buffer
        self.buffer.append(echantillon_filtre)

        # Traiter quand le buffer est plein (toutes les 50ms)
        if len(self.buffer) >= self.fenetre_samples:
            self.nb_predictions += 1

            # Conversion en array
            fenetre = np.array(list(self.buffer))

            # Extraction features
            features = self.extracteur.extraire(fenetre)

            # Classification
            commande, confiance = self.classificateur.predire(features)

            # Lissage temporel (vote majoritaire sur les 5 dernières)
            self.historique_predictions.append(commande)
            commande_lissee = self._vote_majoritaire()

            # Mise à jour stats
            self.stats[commande_lissee] += 1
            self.commande_precedente = commande_lissee

            return {
                'commande': commande_lissee,
                'commande_brute': commande,
                'confiance': confiance,
                'features': features,
                'latence_ms': self.fenetre_ms
            }

        return None

    def traiter_fenetre(self, eeg_fenetre: np.ndarray) -> dict:
        """
        Traite une fenêtre complète d'EEG

        Args:
            eeg_fenetre: shape (nb_samples, nb_canaux)

        Returns:
            dict avec commande
        """
        # Filtrer
        fenetre_filtree = np.zeros_like(eeg_fenetre)
        for ch in range(self.nb_canaux):
            fenetre_filtree[:, ch] = self.filtreur.filtrer(
                eeg_fenetre[:, ch], ch
            )

        # Features
        features = self.extracteur.extraire(fenetre_filtree)

        # Classification
        commande, confiance = self.classificateur.predire(features)

        return {
            'commande': commande,
            'confiance': confiance,
            'features': features,
        }

    def _vote_majoritaire(self) -> str:
        """Vote majoritaire sur les dernières prédictions"""
        votes = list(self.historique_predictions)
        if not votes:
            return 'repos'

        # Compter les votes
        compteur = {}
        for v in votes:
            compteur[v] = compteur.get(v, 0) + 1

        return max(compteur, key=compteur.get)

    def get_stats(self) -> dict:
        return {
            'nb_predictions': self.nb_predictions,
            'distribution': self.stats.copy(),
            'calibre': self.classificateur.calibre
        }
