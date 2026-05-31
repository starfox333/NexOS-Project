# ============================================================
# GENERATEUR DE SCENE 3D
# Monde virtuel a projeter dans le cortex visuel
# ============================================================

import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Optional


@dataclass
class Vec3:
    """Vecteur 3D simple"""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def __add__(self, other):
        return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other):
        return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar):
        return Vec3(self.x * scalar, self.y * scalar, self.z * scalar)

    def to_array(self):
        return np.array([self.x, self.y, self.z])

    def norm(self):
        return np.sqrt(self.x**2 + self.y**2 + self.z**2)

    def normalize(self):
        n = self.norm()
        if n > 0:
            return Vec3(self.x/n, self.y/n, self.z/n)
        return Vec3(0, 0, 0)


@dataclass
class Camera:
    """Camera stereoscopique pour vision binoculaire"""
    position: Vec3 = field(default_factory=Vec3)
    direction: Vec3 = field(default_factory=lambda: Vec3(0, 0, 1))
    up: Vec3 = field(default_factory=lambda: Vec3(0, 1, 0))
    fov_deg: float = 90.0
    ipd_mm: float = 63.0  # Distance inter-pupillaire

    # Donnees IMU simulees
    vitesse: Vec3 = field(default_factory=Vec3)
    acceleration: Vec3 = field(default_factory=Vec3)

    def get_eye_positions(self) -> Tuple[Vec3, Vec3]:
        """Retourne les positions des deux yeux virtuels"""
        # Vecteur lateral (perpendiculaire a direction et up)
        lateral = Vec3(
            self.direction.y * self.up.z - self.direction.z * self.up.y,
            self.direction.z * self.up.x - self.direction.x * self.up.z,
            self.direction.x * self.up.y - self.direction.y * self.up.x
        ).normalize()

        offset = lateral * (self.ipd_mm / 2.0 / 1000.0)  # Conversion mm -> m
        oeil_gauche = self.position - offset
        oeil_droit = self.position + offset

        return oeil_gauche, oeil_droit

    def update_from_imu(self, dt: float, accel: Vec3, gyro: Vec3):
        """Met a jour la position/orientation depuis les donnees IMU"""
        self.acceleration = accel
        self.vitesse = self.vitesse + accel * dt
        self.position = self.position + self.vitesse * dt
        # Rotation simplifiee (a ameliorer avec quaternions)
        # Pour l'instant on ignore la rotation


@dataclass
class Objet3D:
    """Objet simple dans la scene"""
    position: Vec3
    taille: float
    couleur: Tuple[float, float, float]  # RGB 0-1
    forme: str = "sphere"  # sphere, cube, plan


class Scene3D:
    """Scene 3D complete avec objets et rendu"""

    def __init__(self, resolution: Tuple[int, int] = (256, 256)):
        self.resolution = resolution
        self.objets: List[Objet3D] = []
        self.couleur_fond = (0.0, 0.0, 0.1)  # Bleu fonce

    def ajouter_objet(self, objet: Objet3D):
        """Ajoute un objet a la scene"""
        self.objets.append(objet)

    def generer_scene_test(self):
        """Genere une scene de test avec plusieurs objets"""
        self.objets.clear()

        # Sol (plan)
        self.objets.append(Objet3D(
            position=Vec3(0, -2, 0),
            taille=20.0,
            couleur=(0.2, 0.3, 0.2),
            forme="plan"
        ))

        # Spheres a differentes distances
        self.objets.append(Objet3D(
            position=Vec3(-2, 0, 5),
            taille=1.0,
            couleur=(1.0, 0.2, 0.2),  # Rouge
            forme="sphere"
        ))

        self.objets.append(Objet3D(
            position=Vec3(2, 0, 8),
            taille=1.5,
            couleur=(0.2, 1.0, 0.2),  # Vert
            forme="sphere"
        ))

        self.objets.append(Objet3D(
            position=Vec3(0, 1, 15),
            taille=2.0,
            couleur=(0.2, 0.2, 1.0),  # Bleu
            forme="sphere"
        ))

        # Cube
        self.objets.append(Objet3D(
            position=Vec3(-3, 0, 10),
            taille=1.2,
            couleur=(1.0, 1.0, 0.2),  # Jaune
            forme="cube"
        ))

    def render_mono(self, camera: Camera) -> np.ndarray:
        """Rendu monoculaire simple (raymarching basique)"""
        w, h = self.resolution
        image = np.zeros((h, w, 3), dtype=np.float32)

        fov_rad = np.radians(camera.fov_deg)
        aspect = w / h

        for y in range(h):
            for x in range(w):
                # Direction du rayon
                u = (2 * x / w - 1) * np.tan(fov_rad / 2) * aspect
                v = (1 - 2 * y / h) * np.tan(fov_rad / 2)

                ray_dir = Vec3(u, v, 1).normalize()

                # Intersection avec les objets
                couleur = self._trace_ray(camera.position, ray_dir)
                image[y, x] = couleur

        return image

    def render_stereo(self, camera: Camera) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Rendu stereoscopique (deux yeux)
        Retourne: (image_gauche, image_droite, carte_profondeur)
        """
        oeil_g, oeil_d = camera.get_eye_positions()

        # Rendu pour chaque oeil
        cam_g = Camera(position=oeil_g, direction=camera.direction,
                       fov_deg=camera.fov_deg)
        cam_d = Camera(position=oeil_d, direction=camera.direction,
                       fov_deg=camera.fov_deg)

        image_g = self.render_mono(cam_g)
        image_d = self.render_mono(cam_d)

        # Carte de profondeur (depuis position centrale)
        depth = self._render_depth(camera)

        return image_g, image_d, depth

    def _trace_ray(self, origin: Vec3, direction: Vec3) -> Tuple[float, float, float]:
        """Trace un rayon et retourne la couleur"""
        t_min = float('inf')
        couleur_hit = self.couleur_fond

        for obj in self.objets:
            t = self._intersect(origin, direction, obj)
            if t is not None and t < t_min:
                t_min = t
                # Shading simple (distance -> intensite)
                intensite = max(0.3, 1.0 - t / 20.0)
                couleur_hit = tuple(c * intensite for c in obj.couleur)

        return couleur_hit

    def _intersect(self, origin: Vec3, direction: Vec3, obj: Objet3D) -> Optional[float]:
        """Calcule l'intersection rayon-objet"""
        if obj.forme == "sphere":
            return self._intersect_sphere(origin, direction, obj.position, obj.taille)
        elif obj.forme == "plan":
            return self._intersect_plan(origin, direction, obj.position.y)
        elif obj.forme == "cube":
            return self._intersect_sphere(origin, direction, obj.position, obj.taille * 0.7)
        return None

    def _intersect_sphere(self, origin: Vec3, direction: Vec3,
                          centre: Vec3, rayon: float) -> Optional[float]:
        """Intersection rayon-sphere"""
        oc = origin - centre
        a = direction.x**2 + direction.y**2 + direction.z**2
        b = 2 * (oc.x * direction.x + oc.y * direction.y + oc.z * direction.z)
        c = oc.x**2 + oc.y**2 + oc.z**2 - rayon**2

        discriminant = b**2 - 4*a*c
        if discriminant < 0:
            return None

        t = (-b - np.sqrt(discriminant)) / (2*a)
        if t > 0.001:
            return t
        return None

    def _intersect_plan(self, origin: Vec3, direction: Vec3, y_plan: float) -> Optional[float]:
        """Intersection rayon-plan horizontal"""
        if abs(direction.y) < 0.0001:
            return None
        t = (y_plan - origin.y) / direction.y
        if t > 0.001:
            return t
        return None

    def _render_depth(self, camera: Camera) -> np.ndarray:
        """Rendu de la carte de profondeur"""
        w, h = self.resolution
        depth = np.zeros((h, w), dtype=np.float32)

        fov_rad = np.radians(camera.fov_deg)
        aspect = w / h

        for y in range(h):
            for x in range(w):
                u = (2 * x / w - 1) * np.tan(fov_rad / 2) * aspect
                v = (1 - 2 * y / h) * np.tan(fov_rad / 2)

                ray_dir = Vec3(u, v, 1).normalize()

                # Trouver la distance minimale
                t_min = 100.0  # Distance max
                for obj in self.objets:
                    t = self._intersect(camera.position, ray_dir, obj)
                    if t is not None and t < t_min:
                        t_min = t

                depth[y, x] = t_min

        return depth

    def calculer_flux_optique(self, depth: np.ndarray,
                               mouvement: Vec3) -> np.ndarray:
        """
        Calcule le flux optique a partir de la carte de profondeur
        et du mouvement de la camera
        """
        h, w = depth.shape
        flux = np.zeros((h, w, 2), dtype=np.float32)

        # Flux optique simplifie: objets proches bougent plus vite
        for y in range(h):
            for x in range(w):
                z = max(depth[y, x], 0.1)
                # Deplacement apparent inversement proportionnel a la profondeur
                flux[y, x, 0] = -mouvement.x / z  # Flux horizontal
                flux[y, x, 1] = -mouvement.y / z  # Flux vertical

        return flux
