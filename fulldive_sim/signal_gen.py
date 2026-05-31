# ============================================================
# GENERATEUR DE SIGNAUX
# Signaux de deflexion et stimulation FUS
# ============================================================

import numpy as np
from typing import List, Tuple, Optional
from dataclasses import dataclass
from .scanner import PointBalayage


@dataclass
class ParametresFUS:
    """Parametres du transducteur ultrasonique"""
    frequence_porteuse_hz: float = 500_000      # 500 kHz
    frequence_pulse_hz: float = 1_000           # 1 kHz PRF
    duree_pulse_us: float = 1.0                 # Duree du pulse
    puissance_max_w_cm2: float = 0.72           # Limite securite
    duty_cycle: float = 0.5                      # Rapport cyclique


@dataclass
class SignalFrame:
    """Signaux complets pour une frame"""
    signal_deflexion_x: np.ndarray      # Tension bobine X
    signal_deflexion_y: np.ndarray      # Tension bobine Y
    signal_fus: np.ndarray              # Signal ultrasonique
    signal_intensite: np.ndarray        # Enveloppe d'intensite
    temps: np.ndarray                   # Vecteur temps
    freq_echantillon: int               # Frequence d'echantillonnage


class SignalGenerator:
    """
    Generateur de signaux pour le casque Full-Dive
    Produit les signaux de deflexion et de stimulation FUS
    """

    def __init__(self, freq_echantillon: int = 10_000_000,
                 params_fus: ParametresFUS = None):
        """
        Args:
            freq_echantillon: Frequence d'echantillonnage en Hz (defaut 10 MHz)
            params_fus: Parametres du transducteur FUS
        """
        self.fs = freq_echantillon
        self.params = params_fus or ParametresFUS()

    def generer_frame(self, trajectoire: List[PointBalayage],
                      activation: np.ndarray,
                      temps_frame: float) -> SignalFrame:
        """
        Genere tous les signaux pour une frame complete

        Args:
            trajectoire: Points de balayage pour cette frame
            activation: Carte d'activation V1 (intensite par point)
            temps_frame: Duree de la frame en secondes

        Returns:
            SignalFrame avec tous les signaux
        """
        nb_samples = int(self.fs * temps_frame)
        samples_par_point = nb_samples // len(trajectoire)

        # Initialiser les signaux
        signal_x = np.zeros(nb_samples)
        signal_y = np.zeros(nb_samples)
        signal_intensite = np.zeros(nb_samples)
        temps = np.arange(nb_samples) / self.fs

        grille_size = int(np.sqrt(len(activation.flatten())))
        activation_flat = activation.reshape(grille_size, grille_size)

        # Generer pour chaque point
        for point in trajectoire:
            start = point.index * samples_par_point
            end = min(start + samples_par_point, nb_samples)

            # === Signaux de deflexion ===
            signal_x[start:end], signal_y[start:end] = self._gen_deflexion_point(
                point, trajectoire, samples_par_point, start, end
            )

            # === Intensite depuis la carte d'activation ===
            gx = int(point.x * (grille_size - 1))
            gy = int(point.y * (grille_size - 1))
            intensite = activation_flat[gy, gx] * point.priorite

            # Enveloppe avec settling time
            settling = int(samples_par_point * 0.18)  # 18% settling
            if end - start > settling:
                signal_intensite[start:start+settling] = 0  # Pas de stim pendant settling
                signal_intensite[start+settling:end] = np.clip(intensite, 0, 1)

        # === Signal FUS (porteuse modulee) ===
        signal_fus = self._gen_signal_fus(temps, signal_intensite)

        return SignalFrame(
            signal_deflexion_x=signal_x,
            signal_deflexion_y=signal_y,
            signal_fus=signal_fus,
            signal_intensite=signal_intensite,
            temps=temps,
            freq_echantillon=self.fs
        )

    def _gen_deflexion_point(self, point: PointBalayage,
                              trajectoire: List[PointBalayage],
                              samples_par_point: int,
                              start: int, end: int) -> Tuple[np.ndarray, np.ndarray]:
        """Genere les signaux de deflexion pour un point"""
        n = end - start

        # Tension cible (±3V pour ±15°)
        angle_max = np.radians(15.0)
        tension_x = point.theta / angle_max * 3.0
        tension_y = point.phi / angle_max * 3.0

        # Rampe de transition si pas le premier point
        settling_samples = int(samples_par_point * 0.12)

        sig_x = np.full(n, tension_x)
        sig_y = np.full(n, tension_y)

        if point.index > 0:
            prev = trajectoire[point.index - 1]
            prev_vx = prev.theta / angle_max * 3.0
            prev_vy = prev.phi / angle_max * 3.0

            # Rampe exponentielle (plus realiste que lineaire)
            tau = settling_samples / 3
            t_ramp = np.arange(min(settling_samples, n))
            ramp = 1 - np.exp(-t_ramp / tau)

            sig_x[:len(t_ramp)] = prev_vx + (tension_x - prev_vx) * ramp
            sig_y[:len(t_ramp)] = prev_vy + (tension_y - prev_vy) * ramp

        return sig_x, sig_y

    def _gen_signal_fus(self, temps: np.ndarray,
                        intensite: np.ndarray) -> np.ndarray:
        """
        Genere le signal ultrasonique module

        Signal = porteuse 500kHz × modulation PRF × enveloppe intensite
        """
        # Porteuse sinusoidale
        porteuse = np.sin(2 * np.pi * self.params.frequence_porteuse_hz * temps)

        # Modulation PRF (pulse repetition frequency)
        periode_prf = 1.0 / self.params.frequence_pulse_hz
        phase_prf = (temps % periode_prf) / periode_prf
        modulation_prf = (phase_prf < self.params.duty_cycle).astype(float)

        # Signal final
        signal_fus = porteuse * modulation_prf * intensite

        # Limiter la puissance
        puissance_normalisee = self.params.puissance_max_w_cm2 / 0.72
        signal_fus *= puissance_normalisee

        return signal_fus

    def generer_sequence_calibration(self, nb_points_test: int = 25,
                                      duree_point_ms: float = 100
                                      ) -> List[SignalFrame]:
        """
        Genere une sequence de calibration (grille de points)

        Args:
            nb_points_test: Nombre de points de calibration
            duree_point_ms: Duree de stimulation par point

        Returns:
            Liste de SignalFrame pour la calibration
        """
        frames = []
        grille = int(np.sqrt(nb_points_test))

        for i in range(nb_points_test):
            x = (i % grille) / (grille - 1)
            y = (i // grille) / (grille - 1)

            # Creer une activation avec un seul point actif
            activation = np.zeros((10, 10))
            ax, ay = int(x * 9), int(y * 9)
            activation[ay, ax] = 1.0

            # Creer un point de trajectoire unique
            angle_max = np.radians(15.0)
            point = PointBalayage(
                index=0,
                x=x, y=y,
                t=0,
                theta=(x - 0.5) * 2 * angle_max,
                phi=(y - 0.5) * 2 * angle_max,
                priorite=1.0
            )

            # Generer le signal pour ce point
            nb_samples = int(self.fs * duree_point_ms / 1000)
            temps = np.arange(nb_samples) / self.fs

            signal_x = np.full(nb_samples, point.theta / angle_max * 3.0)
            signal_y = np.full(nb_samples, point.phi / angle_max * 3.0)
            signal_intensite = np.ones(nb_samples)
            signal_fus = self._gen_signal_fus(temps, signal_intensite)

            frames.append(SignalFrame(
                signal_deflexion_x=signal_x,
                signal_deflexion_y=signal_y,
                signal_fus=signal_fus,
                signal_intensite=signal_intensite,
                temps=temps,
                freq_echantillon=self.fs
            ))

        return frames

    def calculer_spectre(self, signal: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Calcule le spectre frequentiel d'un signal"""
        n = len(signal)
        freqs = np.fft.rfftfreq(n, 1/self.fs)
        spectre = np.abs(np.fft.rfft(signal)) / n

        return freqs, spectre

    def verifier_securite(self, signal_fus: np.ndarray) -> dict:
        """
        Verifie que le signal FUS respecte les limites de securite

        Limites FDA pour ultrasons diagnostiques:
        - ISPTA (Spatial Peak Temporal Average) < 720 mW/cm²
        - ISPPA (Spatial Peak Pulse Average) < 190 W/cm²
        - MI (Mechanical Index) < 1.9
        """
        # Calcul puissance moyenne
        puissance_moy = np.mean(signal_fus**2)

        # Calcul puissance crete
        puissance_crete = np.max(signal_fus**2)

        # Index mecanique simplifie (proportionnel a pression / sqrt(freq))
        freq_mhz = self.params.frequence_porteuse_hz / 1e6
        mi = np.sqrt(puissance_crete) / np.sqrt(freq_mhz)

        # Verification limites
        limites_ok = {
            'ispta_ok': puissance_moy < 0.72,
            'isppa_ok': puissance_crete < 190,
            'mi_ok': mi < 1.9
        }

        return {
            'puissance_moyenne_w_cm2': puissance_moy,
            'puissance_crete_w_cm2': puissance_crete,
            'index_mecanique': mi,
            'securite_ok': all(limites_ok.values()),
            **limites_ok
        }

    def exporter_pour_fpga(self, frame: SignalFrame,
                           bits: int = 16) -> dict:
        """
        Exporte les signaux au format FPGA

        Args:
            frame: SignalFrame a exporter
            bits: Resolution du DAC (defaut 16 bits)

        Returns:
            dict avec signaux quantifies et metadata
        """
        max_val = 2**(bits-1) - 1

        # Quantification
        def quantifier(signal, v_max=3.0):
            normalized = signal / v_max
            return np.clip(normalized * max_val, -max_val, max_val).astype(np.int16)

        return {
            'deflexion_x': quantifier(frame.signal_deflexion_x),
            'deflexion_y': quantifier(frame.signal_deflexion_y),
            'fus': quantifier(frame.signal_fus, v_max=1.0),
            'metadata': {
                'freq_echantillon': frame.freq_echantillon,
                'nb_samples': len(frame.temps),
                'bits': bits,
                'v_max_deflexion': 3.0,
                'v_max_fus': 1.0
            }
        }
