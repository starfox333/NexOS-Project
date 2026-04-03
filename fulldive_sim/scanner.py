# ============================================================
# SYSTEME DE BALAYAGE CRT
# Balayage du cortex visuel avec un emetteur unique
# ============================================================

import numpy as np
from enum import Enum
from typing import List, Dict, Tuple, Generator
from dataclasses import dataclass


class TrajectoireType(Enum):
    """Types de trajectoires de balayage"""
    RASTER = "raster"           # Ligne par ligne (CRT classique)
    SPIRALE = "spirale"         # Spirale avec densite foveale
    LISSAJOUS = "lissajous"     # Courbe de Lissajous
    HILBERT = "hilbert"         # Courbe de Hilbert (couverture optimale)


@dataclass
class PointBalayage:
    """Un point dans la trajectoire de balayage"""
    index: int
    x: float                    # Position X dans la grille (0-1)
    y: float                    # Position Y dans la grille (0-1)
    t: float                    # Temps depuis debut frame (secondes)
    theta: float                # Angle deflexion horizontal (radians)
    phi: float                  # Angle deflexion vertical (radians)
    priorite: float = 1.0       # Priorite (pour fovea)


class BalayageCRT:
    """
    Systeme de balayage CRT pour le casque Full-Dive
    Genere les trajectoires et signaux de deflexion
    """

    def __init__(self, nb_points: int = 10_000, fps: int = 60,
                 angle_max_deg: float = 15.0, densite_foveale: float = 2.5):
        self.nb_points = nb_points
        self.fps = fps
        self.temps_frame = 1.0 / fps
        self.temps_point = self.temps_frame / nb_points
        self.grille_size = int(np.sqrt(nb_points))
        self.angle_max = np.radians(angle_max_deg)
        self.densite_foveale = densite_foveale

        # Cache des trajectoires
        self._trajectoires_cache: Dict[TrajectoireType, List[PointBalayage]] = {}

    def generer_trajectoire(self, type_traj: TrajectoireType) -> List[PointBalayage]:
        """Genere ou retourne la trajectoire demandee (avec cache)"""
        if type_traj not in self._trajectoires_cache:
            if type_traj == TrajectoireType.RASTER:
                traj = self._gen_raster()
            elif type_traj == TrajectoireType.SPIRALE:
                traj = self._gen_spirale()
            elif type_traj == TrajectoireType.LISSAJOUS:
                traj = self._gen_lissajous()
            elif type_traj == TrajectoireType.HILBERT:
                traj = self._gen_hilbert()
            else:
                raise ValueError(f"Type de trajectoire inconnu: {type_traj}")

            self._trajectoires_cache[type_traj] = traj

        return self._trajectoires_cache[type_traj]

    def _gen_raster(self) -> List[PointBalayage]:
        """Balayage raster (ligne par ligne, alternance)"""
        points = []
        centre = self.grille_size / 2

        for y in range(self.grille_size):
            ligne = range(self.grille_size)
            if y % 2 == 1:  # Lignes impaires: sens inverse
                ligne = reversed(list(ligne))

            for x in ligne:
                # Normaliser 0-1
                nx = x / (self.grille_size - 1)
                ny = y / (self.grille_size - 1)

                # Angles de deflexion
                theta = (nx - 0.5) * 2 * self.angle_max
                phi = (ny - 0.5) * 2 * self.angle_max

                # Priorite basee sur distance au centre (fovea)
                dist_centre = np.sqrt((nx - 0.5)**2 + (ny - 0.5)**2)
                priorite = 1.0 + (1.0 - dist_centre) * (self.densite_foveale - 1)

                points.append(PointBalayage(
                    index=len(points),
                    x=nx,
                    y=ny,
                    t=len(points) * self.temps_point,
                    theta=theta,
                    phi=phi,
                    priorite=priorite
                ))

        return points

    def _gen_spirale(self) -> List[PointBalayage]:
        """Balayage spirale avec sur-echantillonnage foveal"""
        points = []
        centre = 0.5

        # Ratio d'or pour distribution uniforme
        golden_angle = np.pi * (3 - np.sqrt(5))

        for i in range(self.nb_points):
            # Progression non-lineaire (plus lente au centre)
            progression = i / self.nb_points
            r = centre * (progression ** (1 / self.densite_foveale))

            # Angle avec ratio d'or
            theta_spiral = i * golden_angle

            # Position
            nx = centre + r * np.cos(theta_spiral)
            ny = centre + r * np.sin(theta_spiral)

            # Clipping
            nx = np.clip(nx, 0, 1)
            ny = np.clip(ny, 0, 1)

            # Angles de deflexion
            theta = (nx - 0.5) * 2 * self.angle_max
            phi = (ny - 0.5) * 2 * self.angle_max

            # Priorite plus haute au centre
            priorite = 1.0 + (1.0 - r / centre) * (self.densite_foveale - 1)

            points.append(PointBalayage(
                index=i,
                x=nx,
                y=ny,
                t=i * self.temps_point,
                theta=theta,
                phi=phi,
                priorite=priorite
            ))

        return points

    def _gen_lissajous(self) -> List[PointBalayage]:
        """Balayage par courbe de Lissajous"""
        points = []

        # Frequences avec ratio irrationnel pour couverture complete
        omega_x = 2 * np.pi * 99    # ~99 cycles par frame
        omega_y = omega_x * np.sqrt(2)  # Ratio irrationnel

        for i in range(self.nb_points):
            t = i * self.temps_point

            # Position Lissajous
            nx = 0.5 + 0.48 * np.sin(omega_x * t)
            ny = 0.5 + 0.48 * np.sin(omega_y * t + np.pi / 4)

            # Angles de deflexion
            theta = (nx - 0.5) * 2 * self.angle_max
            phi = (ny - 0.5) * 2 * self.angle_max

            # Priorite uniforme pour Lissajous
            dist_centre = np.sqrt((nx - 0.5)**2 + (ny - 0.5)**2)
            priorite = 1.0 + (1.0 - dist_centre * 2) * 0.5

            points.append(PointBalayage(
                index=i,
                x=nx,
                y=ny,
                t=t,
                theta=theta,
                phi=phi,
                priorite=max(0.5, priorite)
            ))

        return points

    def _gen_hilbert(self) -> List[PointBalayage]:
        """Balayage par courbe de Hilbert (couverture spatiale optimale)"""
        # Determiner l'ordre de la courbe
        ordre = int(np.log2(self.grille_size))
        if 2**ordre != self.grille_size:
            ordre = int(np.ceil(np.log2(self.grille_size)))

        # Generer la courbe de Hilbert
        hilbert_points = self._hilbert_curve(ordre)

        # Echantillonner nb_points depuis la courbe
        step = len(hilbert_points) / self.nb_points
        points = []

        for i in range(self.nb_points):
            idx = int(i * step) % len(hilbert_points)
            hx, hy = hilbert_points[idx]

            # Normaliser
            nx = hx / (2**ordre - 1)
            ny = hy / (2**ordre - 1)

            # Angles de deflexion
            theta = (nx - 0.5) * 2 * self.angle_max
            phi = (ny - 0.5) * 2 * self.angle_max

            # Priorite
            dist_centre = np.sqrt((nx - 0.5)**2 + (ny - 0.5)**2)
            priorite = 1.0 + (1.0 - dist_centre) * (self.densite_foveale - 1)

            points.append(PointBalayage(
                index=i,
                x=nx,
                y=ny,
                t=i * self.temps_point,
                theta=theta,
                phi=phi,
                priorite=priorite
            ))

        return points

    def _hilbert_curve(self, ordre: int) -> List[Tuple[int, int]]:
        """Genere les points d'une courbe de Hilbert"""
        def hilbert_d2xy(n: int, d: int) -> Tuple[int, int]:
            x = y = 0
            s = 1
            while s < n:
                rx = 1 & (d // 2)
                ry = 1 & (d ^ rx)
                if ry == 0:
                    if rx == 1:
                        x = s - 1 - x
                        y = s - 1 - y
                    x, y = y, x
                x += s * rx
                y += s * ry
                d //= 4
                s *= 2
            return x, y

        n = 2**ordre
        return [hilbert_d2xy(n, d) for d in range(n * n)]

    def generer_signaux_deflexion(self, trajectoire: List[PointBalayage],
                                   freq_echantillon: int = 10_000_000
                                   ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Genere les signaux de tension pour les bobines de deflexion

        Args:
            trajectoire: Liste des points de balayage
            freq_echantillon: Frequence d'echantillonnage DAC (Hz)

        Returns:
            (signal_x, signal_y): Signaux de deflexion en tension
        """
        # Nombre d'echantillons par point
        samples_par_point = int(freq_echantillon * self.temps_point)
        total_samples = len(trajectoire) * samples_par_point

        signal_x = np.zeros(total_samples)
        signal_y = np.zeros(total_samples)

        for point in trajectoire:
            start = point.index * samples_par_point
            end = start + samples_par_point

            # Tension proportionnelle a l'angle (±3V pour ±15°)
            tension_x = point.theta / self.angle_max * 3.0
            tension_y = point.phi / self.angle_max * 3.0

            # Rampe de transition (settling time)
            settling_samples = int(samples_par_point * 0.12)  # 12% du temps

            if point.index > 0:
                prev_point = trajectoire[point.index - 1]
                prev_vx = prev_point.theta / self.angle_max * 3.0
                prev_vy = prev_point.phi / self.angle_max * 3.0

                # Rampe lineaire
                ramp_x = np.linspace(prev_vx, tension_x, settling_samples)
                ramp_y = np.linspace(prev_vy, tension_y, settling_samples)

                signal_x[start:start+settling_samples] = ramp_x
                signal_y[start:start+settling_samples] = ramp_y
                signal_x[start+settling_samples:end] = tension_x
                signal_y[start+settling_samples:end] = tension_y
            else:
                signal_x[start:end] = tension_x
                signal_y[start:end] = tension_y

        return signal_x, signal_y

    def stream_points(self, type_traj: TrajectoireType) -> Generator[PointBalayage, None, None]:
        """Generateur de points pour streaming temps reel"""
        trajectoire = self.generer_trajectoire(type_traj)
        for point in trajectoire:
            yield point

    def calculer_statistiques(self, trajectoire: List[PointBalayage]) -> dict:
        """Calcule les statistiques de la trajectoire"""
        xs = [p.x for p in trajectoire]
        ys = [p.y for p in trajectoire]

        # Distance totale parcourue
        dist_totale = 0
        for i in range(1, len(trajectoire)):
            dx = trajectoire[i].x - trajectoire[i-1].x
            dy = trajectoire[i].y - trajectoire[i-1].y
            dist_totale += np.sqrt(dx**2 + dy**2)

        # Vitesse moyenne de balayage
        vitesse_moy = dist_totale / self.temps_frame

        # Couverture de la grille
        grille_couverte = np.zeros((self.grille_size, self.grille_size), dtype=bool)
        for p in trajectoire:
            gx = int(p.x * (self.grille_size - 1))
            gy = int(p.y * (self.grille_size - 1))
            grille_couverte[gy, gx] = True

        couverture = np.sum(grille_couverte) / (self.grille_size**2) * 100

        # Densite au centre vs peripherie
        centre_count = sum(1 for p in trajectoire
                          if np.sqrt((p.x-0.5)**2 + (p.y-0.5)**2) < 0.25)
        periph_count = len(trajectoire) - centre_count
        ratio_densite = centre_count / periph_count if periph_count > 0 else 0

        return {
            'nb_points': len(trajectoire),
            'temps_frame_ms': self.temps_frame * 1000,
            'temps_point_us': self.temps_point * 1e6,
            'frequence_balayage_khz': len(trajectoire) * self.fps / 1000,
            'distance_totale': dist_totale,
            'vitesse_moyenne': vitesse_moy,
            'couverture_pct': couverture,
            'ratio_densite_centre_periph': ratio_densite,
            'angle_max_deg': np.degrees(self.angle_max)
        }
