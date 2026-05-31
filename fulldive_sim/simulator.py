# ============================================================
# SIMULATEUR FULL-DIVE COMPLET
# Integration de tous les modules
# ============================================================

import numpy as np
import time
from typing import Optional, Callable, List, Dict
from dataclasses import dataclass

from .config import FullDiveConfig, DEFAULT_CONFIG
from .scene_3d import Scene3D, Camera, Vec3
from .retinotopic import RetinotopicEncoder, CarteRetinotopique
from .scanner import BalayageCRT, TrajectoireType
from .signal_gen import SignalGenerator, ParametresFUS, SignalFrame
from .brain_model import CortexVisuel, ParametresCortex


@dataclass
class FrameResult:
    """Resultat d'une frame de simulation"""
    frame_id: int
    temps_simule_ms: float
    temps_reel_ms: float

    # Images
    scene_gauche: np.ndarray
    scene_droite: np.ndarray
    profondeur: np.ndarray

    # Encodage V1
    activation_v1: np.ndarray

    # Perception simulee
    perception: np.ndarray

    # Metriques
    fps_reel: float
    latence_ms: float


class FullDiveSimulator:
    """
    Simulateur complet du casque Full-Dive

    Pipeline:
    Scene 3D -> Rendu stereo -> Encodage retinotopique -> Balayage CRT
    -> Generation signaux -> Stimulation cortex -> Perception
    """

    def __init__(self, config: FullDiveConfig = None):
        self.config = config or DEFAULT_CONFIG

        # Valider la configuration
        if not self.config.valider():
            raise ValueError("Configuration invalide")

        # Initialiser les modules
        self._init_modules()

        # Etat
        self.frame_id = 0
        self.temps_simule = 0.0
        self.running = False
        self.paused = False

        # Callbacks
        self.on_frame_complete: Optional[Callable[[FrameResult], None]] = None
        self.on_perception_change: Optional[Callable[[np.ndarray], None]] = None

        # Historique
        self.historique_frames: List[FrameResult] = []

    def _init_modules(self):
        """Initialise tous les sous-modules"""
        # Scene 3D
        self.scene = Scene3D(resolution=self.config.resolution_interne)
        self.scene.generer_scene_test()

        # Camera
        self.camera = Camera(
            position=Vec3(0, 0, 0),
            fov_deg=self.config.fov_deg,
            ipd_mm=self.config.ipd_mm
        )

        # Encodeur retinotopique
        carte = CarteRetinotopique(
            taille_v1_mm2=self.config.surface_v1_mm2
        )
        self.encodeur = RetinotopicEncoder(
            grille_size=self.config.grille_size,
            carte=carte
        )

        # Systeme de balayage
        self.scanner = BalayageCRT(
            nb_points=self.config.nb_points,
            fps=self.config.fps,
            angle_max_deg=self.config.angle_deflexion_max_deg,
            densite_foveale=self.config.densite_foveale
        )

        # Generateur de signaux
        params_fus = ParametresFUS(
            frequence_porteuse_hz=self.config.freq_porteuse_hz,
            puissance_max_w_cm2=self.config.puissance_max_w_cm2
        )
        self.signal_gen = SignalGenerator(params_fus=params_fus)

        # Modele cortical
        params_cortex = ParametresCortex(
            taille_v1=self.config.grille_size,
            latence_ms=self.config.latence_perception_ms
        )
        self.cortex = CortexVisuel(params=params_cortex)

        # Trajectoire par defaut
        self.trajectoire_type = TrajectoireType.SPIRALE
        self.trajectoire = self.scanner.generer_trajectoire(self.trajectoire_type)

    def simuler_frame(self) -> FrameResult:
        """Simule une frame complete"""
        t_start = time.perf_counter()

        # === 1. RENDU SCENE 3D ===
        scene_g, scene_d, profondeur = self.scene.render_stereo(self.camera)

        # === 2. ENCODAGE RETINOTOPIQUE ===
        encodage = self.encodeur.encoder_stereo(scene_g, scene_d, profondeur)
        activation_v1 = (encodage['v1_gauche'] + encodage['v1_droite']) / 2

        # === 3. GENERATION SIGNAUX ===
        # (Note: dans une vraie implementation, ceci irait vers le hardware)
        signal_frame = self.signal_gen.generer_frame(
            self.trajectoire,
            activation_v1,
            self.config.temps_frame_ms / 1000
        )

        # === 4. SIMULATION CORTEX ===
        # dt correspond au temps de frame
        dt_ms = self.config.temps_frame_ms
        perception = self.cortex.stimuler(activation_v1, dt_ms)

        # === 5. METRIQUES ===
        t_end = time.perf_counter()
        temps_reel_ms = (t_end - t_start) * 1000

        # Calculer FPS reel
        if temps_reel_ms > 0:
            fps_reel = 1000 / temps_reel_ms
        else:
            fps_reel = float('inf')

        # Creer le resultat
        result = FrameResult(
            frame_id=self.frame_id,
            temps_simule_ms=self.temps_simule,
            temps_reel_ms=temps_reel_ms,
            scene_gauche=scene_g,
            scene_droite=scene_d,
            profondeur=profondeur,
            activation_v1=activation_v1,
            perception=perception,
            fps_reel=fps_reel,
            latence_ms=self.config.latence_perception_ms
        )

        # Mise a jour etat
        self.frame_id += 1
        self.temps_simule += self.config.temps_frame_ms

        # Callbacks
        if self.on_frame_complete:
            self.on_frame_complete(result)
        if self.on_perception_change:
            self.on_perception_change(perception)

        # Historique (garder les 100 dernieres frames)
        self.historique_frames.append(result)
        if len(self.historique_frames) > 100:
            self.historique_frames.pop(0)

        return result

    def run(self, nb_frames: int = None, temps_max_s: float = None,
            temps_reel: bool = False):
        """
        Lance la simulation

        Args:
            nb_frames: Nombre de frames a simuler (None = infini)
            temps_max_s: Temps maximum de simulation (None = infini)
            temps_reel: Si True, respecte le timing reel (60fps)
        """
        self.running = True
        frame_count = 0
        temps_debut = time.perf_counter()

        print("=" * 60)
        print("DEMARRAGE SIMULATION FULL-DIVE")
        print("=" * 60)
        self.config.afficher_resume()

        try:
            while self.running:
                # Verifier conditions d'arret
                if nb_frames is not None and frame_count >= nb_frames:
                    break
                if temps_max_s is not None:
                    if time.perf_counter() - temps_debut > temps_max_s:
                        break

                # Pause
                if self.paused:
                    time.sleep(0.1)
                    continue

                # Simuler une frame
                t_frame_start = time.perf_counter()
                result = self.simuler_frame()
                frame_count += 1

                # Timing temps reel
                if temps_reel:
                    elapsed = time.perf_counter() - t_frame_start
                    sleep_time = (self.config.temps_frame_ms / 1000) - elapsed
                    if sleep_time > 0:
                        time.sleep(sleep_time)

                # Affichage periodique
                if frame_count % 60 == 0:
                    print(f"[Frame {frame_count}] FPS: {result.fps_reel:.1f}, "
                          f"Perception moy: {np.mean(result.perception):.3f}")

        except KeyboardInterrupt:
            print("\nSimulation interrompue par l'utilisateur")

        finally:
            self.running = False
            self._afficher_resume_final(frame_count, time.perf_counter() - temps_debut)

    def _afficher_resume_final(self, nb_frames: int, duree_s: float):
        """Affiche le resume de la simulation"""
        print("\n" + "=" * 60)
        print("FIN DE SIMULATION")
        print("=" * 60)
        print(f"Frames simulees: {nb_frames}")
        print(f"Duree reelle: {duree_s:.2f}s")
        print(f"FPS moyen: {nb_frames / duree_s:.1f}")

        if self.historique_frames:
            fps_list = [f.fps_reel for f in self.historique_frames]
            print(f"FPS min/max: {min(fps_list):.1f} / {max(fps_list):.1f}")

            perceptions = [np.mean(f.perception) for f in self.historique_frames]
            print(f"Perception moyenne: {np.mean(perceptions):.3f}")

        print("=" * 60)

    def stop(self):
        """Arrete la simulation"""
        self.running = False

    def pause(self):
        """Met en pause la simulation"""
        self.paused = True

    def resume(self):
        """Reprend la simulation"""
        self.paused = False

    def reset(self):
        """Reinitialise la simulation"""
        self.frame_id = 0
        self.temps_simule = 0.0
        self.cortex.reset()
        self.historique_frames.clear()
        self.camera.position = Vec3(0, 0, 0)

    def deplacer_camera(self, dx: float = 0, dy: float = 0, dz: float = 0):
        """Deplace la camera dans la scene"""
        self.camera.position = self.camera.position + Vec3(dx, dy, dz)

    def changer_trajectoire(self, type_traj: TrajectoireType):
        """Change le type de trajectoire de balayage"""
        self.trajectoire_type = type_traj
        self.trajectoire = self.scanner.generer_trajectoire(type_traj)
        print(f"Trajectoire changee: {type_traj.value}")

        # Afficher statistiques
        stats = self.scanner.calculer_statistiques(self.trajectoire)
        print(f"  - Frequence balayage: {stats['frequence_balayage_khz']:.0f} kHz")
        print(f"  - Couverture: {stats['couverture_pct']:.1f}%")

    def get_etat(self) -> dict:
        """Retourne l'etat complet du simulateur"""
        return {
            'frame_id': self.frame_id,
            'temps_simule_ms': self.temps_simule,
            'running': self.running,
            'paused': self.paused,
            'trajectoire': self.trajectoire_type.value,
            'camera': {
                'x': self.camera.position.x,
                'y': self.camera.position.y,
                'z': self.camera.position.z
            },
            'cortex': self.cortex.get_etat(),
            'config': {
                'fps': self.config.fps,
                'nb_points': self.config.nb_points,
                'grille_size': self.config.grille_size
            }
        }

    def exporter_frame_pour_hardware(self, frame_result: FrameResult) -> dict:
        """
        Exporte une frame au format hardware (FPGA)

        Returns:
            dict avec tous les signaux prets pour le hardware
        """
        signal_frame = self.signal_gen.generer_frame(
            self.trajectoire,
            frame_result.activation_v1,
            self.config.temps_frame_ms / 1000
        )

        return self.signal_gen.exporter_pour_fpga(signal_frame)
