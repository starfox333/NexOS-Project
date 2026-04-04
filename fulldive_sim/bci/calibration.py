#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================================
# CALIBRATION BCI
# Protocole de calibration simple (15 minutes)
# ============================================================

import numpy as np
from typing import List, Dict, Tuple


class CalibreurBCI:
    """
    Calibre le système BCI pour un utilisateur spécifique

    Protocole en 3 phases (15 min total) :
    1. Repos (2 min) → baseline du cerveau
    2. Tâches guidées (10 min) → imagerie motrice
    3. Test libre (3 min) → validation

    Données nécessaires :
    - ~30 essais par commande
    - Chaque essai = 4 secondes (1s prépa + 3s imagerie)
    """

    def __init__(self, decodeur, nb_essais_par_classe=30):
        self.decodeur = decodeur
        self.nb_essais = nb_essais_par_classe
        self.commandes = ['repos', 'avancer', 'main_gauche',
                         'main_droite', 'action']

        # Données de calibration
        self.donnees_X = []  # Features
        self.donnees_y = []  # Labels

        # Résultats
        self.precision = 0.0
        self.matrice_confusion = None
        self.calibre = False

    def collecter_essai(self, eeg_fenetre: np.ndarray, label: int):
        """
        Collecte un essai de calibration

        Args:
            eeg_fenetre: Données EEG (nb_samples, nb_canaux)
            label: Index de la commande (0-4)
        """
        # Filtrer et extraire features
        fenetre_filtree = np.zeros_like(eeg_fenetre)
        for ch in range(eeg_fenetre.shape[1]):
            fenetre_filtree[:, ch] = self.decodeur.filtreur.filtrer(
                eeg_fenetre[:, ch], ch
            )

        features = self.decodeur.extracteur.extraire(fenetre_filtree)

        self.donnees_X.append(features)
        self.donnees_y.append(label)

    def entrainer(self) -> dict:
        """
        Entraîne le classificateur avec les données collectées

        Returns:
            dict avec précision et matrice de confusion
        """
        X = np.array(self.donnees_X)
        y = np.array(self.donnees_y)

        if len(X) < 10:
            return {'erreur': 'Pas assez de données'}

        # Séparation train/test (80/20)
        indices = np.random.permutation(len(X))
        split = int(0.8 * len(X))
        X_train, X_test = X[indices[:split]], X[indices[split:]]
        y_train, y_test = y[indices[:split]], y[indices[split:]]

        # Entraîner le LDA
        self.decodeur.classificateur.entrainer(X_train, y_train)

        # Évaluer
        nb_correct = 0
        nb_classes = len(self.commandes)
        confusion = np.zeros((nb_classes, nb_classes), dtype=int)

        for i in range(len(X_test)):
            pred, conf = self.decodeur.classificateur.predire(X_test[i])
            pred_idx = self.commandes.index(pred) if pred in self.commandes else 0
            vrai_idx = y_test[i]

            confusion[vrai_idx, pred_idx] += 1
            if pred_idx == vrai_idx:
                nb_correct += 1

        self.precision = nb_correct / len(X_test) if len(X_test) > 0 else 0
        self.matrice_confusion = confusion
        self.calibre = True

        return {
            'precision': self.precision,
            'confusion': confusion,
            'nb_essais_train': len(X_train),
            'nb_essais_test': len(X_test)
        }

    def simuler_calibration_complete(self, capteur_eeg, fs=250):
        """
        Simule une session de calibration complète

        Args:
            capteur_eeg: Instance de CapteurEEG
            fs: Fréquence d'échantillonnage
        """
        print("=" * 50)
        print("CALIBRATION BCI - 15 minutes")
        print("=" * 50)

        duree_essai = 3  # secondes
        samples_essai = fs * duree_essai

        for classe_idx, commande in enumerate(self.commandes):
            print(f"\n[{classe_idx+1}/{len(self.commandes)}] "
                  f"Classe: {commande.upper()}")

            for essai in range(self.nb_essais):
                # Simuler l'état moteur
                capteur_eeg.set_etat_moteur(commande)

                # Collecter 3 secondes de données
                eeg_data = capteur_eeg.lire_bloc(samples_essai)

                # Stocker
                self.collecter_essai(eeg_data, classe_idx)

                if (essai + 1) % 10 == 0:
                    print(f"   Essai {essai+1}/{self.nb_essais}")

            # Repos entre les classes
            capteur_eeg.set_etat_moteur('repos')

        # Entraîner
        print("\nEntraînement du classificateur...")
        resultats = self.entrainer()

        print(f"\nPrécision: {resultats['precision']*100:.1f}%")
        print(f"Essais train: {resultats['nb_essais_train']}")
        print(f"Essais test: {resultats['nb_essais_test']}")

        return resultats
