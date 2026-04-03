# ============================================================
# MODELE DU CORTEX VISUEL
# Simulation simplifiee de la reponse neuronale
# ============================================================

import numpy as np
from typing import Dict, Tuple, Optional
from dataclasses import dataclass, field
from collections import deque


@dataclass
class ParametresCortex:
    """Parametres du modele cortical"""
    # Dimensions
    taille_v1: int = 100                    # Grille V1 (100x100)
    nb_colonnes: int = 10_000               # Colonnes corticales

    # Dynamique neuronale
    tau_activation_ms: float = 10.0         # Constante de temps montee
    tau_desactivation_ms: float = 50.0      # Constante de temps descente
    seuil_perception: float = 0.15          # Seuil de perception

    # Adaptation
    tau_adaptation_ms: float = 200.0        # Adaptation (fatigue)
    force_adaptation: float = 0.3           # Reduction max par adaptation

    # Bruit neuronal
    bruit_sigma: float = 0.05               # Ecart-type du bruit

    # Latence
    latence_ms: float = 80.0                # Delai de perception


@dataclass
class EtatColonneCortical:
    """Etat d'une colonne corticale individuelle"""
    activation: float = 0.0                 # Niveau d'activation actuel
    adaptation: float = 0.0                 # Niveau de fatigue
    historique: deque = field(default_factory=lambda: deque(maxlen=100))


class CortexVisuel:
    """
    Modele simplifie du cortex visuel (V1-V5)
    Simule la reponse neuronale a la stimulation FUS
    """

    def __init__(self, params: ParametresCortex = None):
        self.params = params or ParametresCortex()
        self.taille = self.params.taille_v1

        # Etat des colonnes corticales
        self.activation = np.zeros((self.taille, self.taille))
        self.adaptation = np.zeros((self.taille, self.taille))

        # Buffer pour la latence
        self.buffer_latence = deque(maxlen=100)

        # Historique de perception (pour analyse)
        self.historique_perception = []

        # Carte de sensibilite individuelle (calibration)
        self.sensibilite = np.ones((self.taille, self.taille))

        # Temps simule
        self.temps_ms = 0.0

    def stimuler(self, carte_stimulation: np.ndarray, dt_ms: float) -> np.ndarray:
        """
        Applique une stimulation et calcule la reponse neuronale

        Args:
            carte_stimulation: Carte d'intensite de stimulation (grille_size x grille_size)
            dt_ms: Pas de temps en millisecondes

        Returns:
            perception: Ce que le sujet "voit" (apres traitement neural)
        """
        # Redimensionner si necessaire
        if carte_stimulation.shape != (self.taille, self.taille):
            carte_stimulation = self._resize(carte_stimulation)

        # Appliquer la sensibilite individuelle
        stimulation_effective = carte_stimulation * self.sensibilite

        # === Dynamique d'activation ===
        # Equation differentielle: dA/dt = (S - A) / tau
        tau_act = self.params.tau_activation_ms
        tau_deact = self.params.tau_desactivation_ms

        # Tau adaptatif (plus rapide pour monter, plus lent pour descendre)
        tau = np.where(stimulation_effective > self.activation, tau_act, tau_deact)

        # Integration (Euler)
        delta = (stimulation_effective - self.activation) * (dt_ms / tau)
        self.activation += delta

        # === Adaptation (fatigue) ===
        # L'adaptation augmente avec l'activation soutenue
        self.adaptation += (self.activation - self.adaptation) * (dt_ms / self.params.tau_adaptation_ms)

        # Appliquer l'adaptation (reduit l'activation effective)
        activation_adaptee = self.activation * (1 - self.adaptation * self.params.force_adaptation)

        # === Bruit neuronal ===
        bruit = np.random.normal(0, self.params.bruit_sigma, (self.taille, self.taille))
        activation_bruitee = activation_adaptee + bruit

        # === Seuil de perception ===
        perception = np.where(activation_bruitee > self.params.seuil_perception,
                             activation_bruitee, 0)

        # === Latence ===
        self.buffer_latence.append(perception.copy())

        # Retourner la perception avec latence
        idx_latence = int(self.params.latence_ms / dt_ms)
        if len(self.buffer_latence) > idx_latence:
            perception_retardee = self.buffer_latence[-idx_latence]
        else:
            perception_retardee = np.zeros_like(perception)

        # Mise a jour du temps
        self.temps_ms += dt_ms

        # Sauvegarder pour analyse
        self.historique_perception.append({
            'temps_ms': self.temps_ms,
            'activation_moy': np.mean(self.activation),
            'perception_moy': np.mean(perception_retardee),
            'adaptation_moy': np.mean(self.adaptation)
        })

        return np.clip(perception_retardee, 0, 1)

    def calibrer_sensibilite(self, reponses_calibration: Dict[Tuple[int, int], float]):
        """
        Calibre la carte de sensibilite a partir des reponses comportementales

        Args:
            reponses_calibration: Dict {(x, y): perception_rapportee}
        """
        for (x, y), perception in reponses_calibration.items():
            # Ajuster la sensibilite pour que la perception soit uniforme
            if perception > 0:
                self.sensibilite[y, x] = 1.0 / perception
            else:
                self.sensibilite[y, x] = 2.0  # Augmenter si pas de perception

        # Normaliser
        self.sensibilite /= np.mean(self.sensibilite)

    def simuler_perception_3d(self, v1_gauche: np.ndarray, v1_droite: np.ndarray,
                               profondeur: np.ndarray, mouvement: np.ndarray,
                               dt_ms: float) -> dict:
        """
        Simule la perception 3D complete (V1 + V2 + V3 + V4 + V5)

        Returns:
            dict avec les differentes composantes de perception
        """
        # V1: Bords et contrastes (moyenne des deux yeux)
        v1_combine = (v1_gauche + v1_droite) / 2
        perception_v1 = self.stimuler(v1_combine, dt_ms)

        # V2: Disparite binoculaire -> profondeur
        disparite = np.abs(v1_gauche - v1_droite)
        perception_v2 = self._traiter_v2(disparite, profondeur, dt_ms)

        # V4: Couleur (simplifiee ici comme luminance)
        perception_v4 = perception_v1  # Simplification

        # V5/MT: Mouvement
        perception_v5 = self._traiter_v5(mouvement, dt_ms)

        # Integration (ce que le sujet percoit globalement)
        perception_integree = {
            'forme': perception_v1,
            'profondeur': perception_v2,
            'couleur': perception_v4,
            'mouvement': perception_v5,
            'luminosite_moyenne': np.mean(perception_v1),
            'profondeur_moyenne': np.mean(perception_v2)
        }

        return perception_integree

    def _traiter_v2(self, disparite: np.ndarray, profondeur: np.ndarray,
                    dt_ms: float) -> np.ndarray:
        """Traitement V2: integration de la profondeur"""
        # Combiner disparite et information de profondeur
        signal_profondeur = 0.5 * disparite + 0.5 * profondeur

        # Filtrage temporel (V2 est plus lent que V1)
        tau_v2 = self.params.tau_activation_ms * 2

        if not hasattr(self, '_etat_v2'):
            self._etat_v2 = np.zeros_like(signal_profondeur)

        self._etat_v2 += (signal_profondeur - self._etat_v2) * (dt_ms / tau_v2)

        return np.clip(self._etat_v2, 0, 1)

    def _traiter_v5(self, mouvement: np.ndarray, dt_ms: float) -> np.ndarray:
        """Traitement V5/MT: detection du mouvement"""
        # V5 est specialise dans la detection de mouvement
        # Il repond fortement aux changements rapides

        if not hasattr(self, '_etat_v5_prev'):
            self._etat_v5_prev = np.zeros_like(mouvement)

        # Detecteur de changement
        changement = np.abs(mouvement - self._etat_v5_prev)
        self._etat_v5_prev = mouvement.copy()

        # Amplifier les mouvements (V5 est tres sensible)
        perception_mouvement = np.tanh(changement * 3)

        return perception_mouvement

    def get_etat(self) -> dict:
        """Retourne l'etat complet du cortex"""
        return {
            'activation': self.activation.copy(),
            'adaptation': self.adaptation.copy(),
            'sensibilite': self.sensibilite.copy(),
            'temps_ms': self.temps_ms,
            'statistiques': {
                'activation_moy': np.mean(self.activation),
                'activation_max': np.max(self.activation),
                'adaptation_moy': np.mean(self.adaptation),
                'nb_colonnes_actives': np.sum(self.activation > self.params.seuil_perception)
            }
        }

    def reset(self):
        """Reinitialise l'etat du cortex"""
        self.activation = np.zeros((self.taille, self.taille))
        self.adaptation = np.zeros((self.taille, self.taille))
        self.buffer_latence.clear()
        self.historique_perception.clear()
        self.temps_ms = 0.0

    def _resize(self, array: np.ndarray) -> np.ndarray:
        """Redimensionne un array vers la taille du cortex"""
        from scipy.ndimage import zoom
        factors = (self.taille / array.shape[0], self.taille / array.shape[1])
        try:
            return zoom(array, factors, order=1)
        except ImportError:
            # Fallback sans scipy
            h, w = array.shape
            result = np.zeros((self.taille, self.taille))
            for y in range(self.taille):
                for x in range(self.taille):
                    sy = int(y * h / self.taille)
                    sx = int(x * w / self.taille)
                    result[y, x] = array[sy, sx]
            return result

    def generer_phosphene(self, x: float, y: float, intensite: float = 1.0,
                          taille: float = 0.05) -> np.ndarray:
        """
        Genere un phosphene (point lumineux percu) a une position donnee

        Args:
            x, y: Position (0-1)
            intensite: Intensite du phosphene (0-1)
            taille: Taille relative du phosphene

        Returns:
            Carte de stimulation pour ce phosphene
        """
        carte = np.zeros((self.taille, self.taille))

        # Position en pixels
        cx = int(x * (self.taille - 1))
        cy = int(y * (self.taille - 1))

        # Rayon en pixels
        rayon = int(taille * self.taille)

        # Gaussienne 2D
        for dy in range(-rayon*2, rayon*2+1):
            for dx in range(-rayon*2, rayon*2+1):
                px, py = cx + dx, cy + dy
                if 0 <= px < self.taille and 0 <= py < self.taille:
                    dist2 = dx**2 + dy**2
                    carte[py, px] = intensite * np.exp(-dist2 / (2 * rayon**2))

        return carte
