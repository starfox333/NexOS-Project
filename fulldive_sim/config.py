# ============================================================
# CONFIGURATION DU SYSTEME FULL-DIVE
# ============================================================

from dataclasses import dataclass, field
from typing import Tuple
import numpy as np


@dataclass
class FullDiveConfig:
    """Configuration complete du casque Full-Dive"""

    # === PARAMETRES TEMPORELS ===
    fps: int = 60                           # Frames par seconde
    temps_frame_ms: float = field(init=False)

    # === GRILLE DE STIMULATION ===
    nb_points: int = 10_000                 # Points de stimulation
    grille_size: int = field(init=False)   # Racine carree (100x100)

    # === GEOMETRIE DU CASQUE ===
    rayon_casque_mm: float = 150.0          # Rayon de la demi-sphere
    angle_deflexion_max_deg: float = 15.0   # Deflexion maximale

    # === TRANSDUCTEUR FUS ===
    freq_porteuse_hz: float = 500_000       # 500 kHz
    puissance_max_w_cm2: float = 0.72       # Limite securite FDA
    duree_pulse_us: float = 1.0             # Duree stimulation par point

    # === TIMING PAR POINT ===
    temps_deflexion_us: float = 0.2         # Settling des bobines
    temps_stabilisation_us: float = 0.1     # Attente position
    temps_stimulation_us: float = 1.0       # Pulse FUS actif
    temps_repos_us: float = field(init=False)
    temps_total_point_us: float = field(init=False)

    # === CORTEX VISUEL (V1) ===
    surface_v1_mm2: float = 2500.0          # Surface moyenne V1
    nb_colonnes_corticales: int = 10_000    # Colonnes fonctionnelles
    latence_perception_ms: float = 80.0     # Delai cerveau

    # === SCENE 3D ===
    resolution_interne: Tuple[int, int] = (256, 256)
    fov_deg: float = 90.0                   # Champ de vision
    ipd_mm: float = 63.0                    # Distance inter-pupillaire

    # === CALIBRATION ===
    densite_foveale: float = 2.5            # Sur-echantillonnage centre

    def __post_init__(self):
        """Calcul des valeurs derivees"""
        self.temps_frame_ms = 1000.0 / self.fps
        self.grille_size = int(np.sqrt(self.nb_points))
        self.temps_total_point_us = (self.temps_frame_ms * 1000) / self.nb_points
        self.temps_repos_us = (self.temps_total_point_us -
                               self.temps_deflexion_us -
                               self.temps_stabilisation_us -
                               self.temps_stimulation_us)

    def valider(self) -> bool:
        """Verifie la coherence des parametres"""
        erreurs = []

        # Verification timing
        if self.temps_repos_us < 0:
            erreurs.append(f"Timing depasse: repos negatif ({self.temps_repos_us:.3f} us)")

        # Verification puissance
        if self.puissance_max_w_cm2 > 0.72:
            erreurs.append(f"Puissance FUS dangereuse: {self.puissance_max_w_cm2} W/cm2 > 0.72")

        # Verification grille
        if self.grille_size ** 2 != self.nb_points:
            erreurs.append(f"nb_points doit etre un carre parfait, got {self.nb_points}")

        if erreurs:
            for e in erreurs:
                print(f"[ERREUR CONFIG] {e}")
            return False

        print("[CONFIG] Validation OK")
        return True

    def afficher_resume(self):
        """Affiche un resume de la configuration"""
        print("=" * 60)
        print("CONFIGURATION FULL-DIVE HEADSET")
        print("=" * 60)
        print(f"Resolution:          {self.grille_size}x{self.grille_size} = {self.nb_points} points")
        print(f"Framerate:           {self.fps} fps")
        print(f"Temps par frame:     {self.temps_frame_ms:.2f} ms")
        print(f"Temps par point:     {self.temps_total_point_us:.3f} us")
        print(f"Frequence balayage:  {self.nb_points * self.fps / 1000:.0f} kHz")
        print(f"Frequence FUS:       {self.freq_porteuse_hz / 1000:.0f} kHz")
        print(f"Deflexion max:       +/-{self.angle_deflexion_max_deg} deg")
        print(f"Latence perception:  {self.latence_perception_ms:.0f} ms")
        print(f"Marge timing:        {self.temps_repos_us:.3f} us ({self.temps_repos_us/self.temps_total_point_us*100:.1f}%)")
        print("=" * 60)


# Configuration par defaut
DEFAULT_CONFIG = FullDiveConfig()
