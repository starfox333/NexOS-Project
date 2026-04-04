#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================================
# PRÉDICTEUR DE MOUVEMENT
# Anticipe les mouvements pour compenser la latence
# ============================================================
#
# Le cerveau génère un signal 200-300ms AVANT le mouvement
# On peut le détecter et anticiper → réaction quasi-instantanée
#
# ============================================================

import numpy as np
from collections import deque
from typing import Optional, Tuple


class PredicteurMouvement:
    """
    Prédit les mouvements futurs pour compenser la latence

    Technique :
    1. Détection du MRCP (potentiel pré-mouvement)
    2. Accumulation de preuves (drift-diffusion)
    3. Prédiction avant le seuil de décision EEG

    Résultat : réaction perçue quasi-instantanée
    """

    def __init__(self, horizon_ms=200, seuil=0.7):
        self.horizon_ms = horizon_ms
        self.seuil = seuil

        # Accumulateurs de preuves par commande
        self.accumulateurs = {
            'repos': 0.0,
            'avancer': 0.0,
            'main_gauche': 0.0,
            'main_droite': 0.0,
            'action': 0.0,
            'rotation': 0.0,
        }

        # Paramètres du modèle drift-diffusion
        self.taux_accumulation = 0.15   # Vitesse d'accumulation
        self.taux_decroissance = 0.05   # Décroissance vers zéro
        self.bruit_decision = 0.02      # Bruit dans la décision

        # Historique
        self.historique = deque(maxlen=100)
        self.prediction_active = None

    def mettre_a_jour(self, features: np.ndarray,
                       commande_brute: str,
                       confiance: float) -> Optional[str]:
        """
        Met à jour les accumulateurs et prédit si un mouvement approche

        Args:
            features: Vecteur de features EEG
            commande_brute: Commande classifiée (peut être bruitée)
            confiance: Confiance du classificateur

        Returns:
            Commande prédite si seuil atteint, None sinon
        """
        # Décroissance de tous les accumulateurs
        for cmd in self.accumulateurs:
            self.accumulateurs[cmd] *= (1 - self.taux_decroissance)

        # Accumulation pour la commande détectée
        if commande_brute != 'repos' and confiance > 0.3:
            increment = confiance * self.taux_accumulation
            increment += np.random.normal(0, self.bruit_decision)
            self.accumulateurs[commande_brute] += max(0, increment)

        # Vérifier si un accumulateur dépasse le seuil
        for cmd, acc in self.accumulateurs.items():
            if cmd == 'repos':
                continue

            if acc >= self.seuil:
                # Mouvement prédit !
                self.prediction_active = cmd
                self.accumulateurs[cmd] = 0  # Reset
                self.historique.append({
                    'commande': cmd,
                    'confiance_accumulee': acc,
                    'anticipe': True
                })
                return cmd

        return None

    def get_etat(self) -> dict:
        return {
            'accumulateurs': self.accumulateurs.copy(),
            'prediction_active': self.prediction_active,
            'nb_predictions': len(self.historique)
        }


class LisseurCommandes:
    """
    Lisse les commandes pour éviter les saccades

    Problème : le décodeur EEG oscille entre commandes
    Solution : filtre exponentiel + zone morte

    Sortie : valeurs continues entre 0 et 1 par axe
    au lieu de commandes discrètes (oui/non)
    """

    def __init__(self, alpha=0.3):
        self.alpha = alpha  # Coefficient de lissage (0=lent, 1=réactif)

        # Axes de sortie continus
        self.axes = {
            'avant_arriere': 0.0,   # -1 (reculer) à +1 (avancer)
            'gauche_droite': 0.0,   # -1 (gauche) à +1 (droite)
            'action': 0.0,          # 0 (rien) à 1 (action)
        }

        # Zone morte (en dessous, on ignore)
        self.zone_morte = 0.1

    def lisser(self, commande: str, confiance: float) -> dict:
        """
        Convertit une commande discrète en axes continus lissés

        Args:
            commande: Commande décodée
            confiance: Confiance du décodeur

        Returns:
            dict avec axes continus lissés
        """
        # Cibles selon la commande
        cible_av = 0.0
        cible_gd = 0.0
        cible_act = 0.0

        if commande == 'avancer':
            cible_av = confiance
        elif commande == 'main_gauche':
            cible_gd = -confiance
        elif commande == 'main_droite':
            cible_gd = confiance
        elif commande == 'action':
            cible_act = confiance

        # Lissage exponentiel
        self.axes['avant_arriere'] += self.alpha * (cible_av - self.axes['avant_arriere'])
        self.axes['gauche_droite'] += self.alpha * (cible_gd - self.axes['gauche_droite'])
        self.axes['action'] += self.alpha * (cible_act - self.axes['action'])

        # Zone morte
        resultat = {}
        for axe, val in self.axes.items():
            if abs(val) < self.zone_morte:
                resultat[axe] = 0.0
            else:
                resultat[axe] = val

        return resultat
