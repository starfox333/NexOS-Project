# ============================================================
# ENCODEUR RETINOTOPIQUE
# Transformation du champ visuel vers le cortex V1
# ============================================================

import numpy as np
from typing import Tuple
from dataclasses import dataclass


@dataclass
class CarteRetinotopique:
    """Carte personnalisee V1 d'un individu"""
    # Parametres du modele de Schwartz
    k: float = 15.0          # Facteur d'echelle
    a: float = 0.5           # Offset foveal

    # Variations individuelles
    taille_v1_mm2: float = 2500.0
    magnification_foveale: float = 10.0
    rotation_deg: float = 0.0  # Rotation individuelle

    # Position anatomique
    centre_v1_mm: Tuple[float, float, float] = (0, 0, -50)  # Occipital


class RetinotopicEncoder:
    """
    Encode une image du champ visuel vers une carte d'activation V1
    Utilise le modele de Schwartz (transformation log-polaire)
    """

    def __init__(self, grille_size: int = 100, carte: CarteRetinotopique = None):
        self.grille_size = grille_size
        self.carte = carte or CarteRetinotopique()

        # Pre-calculer les tables de correspondance
        self._init_lookup_tables()

    def _init_lookup_tables(self):
        """Initialise les tables de correspondance champ visuel <-> V1"""
        self.lut_visuel_vers_v1 = np.zeros((self.grille_size, self.grille_size, 2))
        self.lut_v1_vers_visuel = np.zeros((self.grille_size, self.grille_size, 2))

        centre = self.grille_size / 2

        for y in range(self.grille_size):
            for x in range(self.grille_size):
                # Position dans le champ visuel (normalise -1 a 1)
                vx = (x - centre) / centre
                vy = (y - centre) / centre

                # Transformation vers V1
                cx, cy = self._schwartz_transform(vx, vy)

                # Stocker dans la LUT
                self.lut_visuel_vers_v1[y, x] = [cx, cy]

        # Calculer la LUT inverse (V1 -> champ visuel)
        self._compute_inverse_lut()

    def _schwartz_transform(self, x: float, y: float) -> Tuple[float, float]:
        """
        Transformation de Schwartz: champ visuel -> cortex V1
        w = k * log(z + a) ou z = x + iy (coordonnees complexes)
        """
        # Conversion en coordonnees polaires
        r = np.sqrt(x**2 + y**2) + 1e-6  # Eviter log(0)
        theta = np.arctan2(y, x)

        # Transformation log-polaire avec magnification foveale
        # Le centre (fovea) est etire, la peripherie compressee
        r_cortex = self.carte.k * np.log(r + self.carte.a)

        # Appliquer la magnification foveale
        if r < 0.1:  # Zone foveale
            r_cortex *= self.carte.magnification_foveale / 5.0

        # Rotation individuelle
        theta_cortex = theta + np.radians(self.carte.rotation_deg)

        # Conversion retour en cartesien (normalise 0-1)
        cx = 0.5 + 0.3 * r_cortex * np.cos(theta_cortex)
        cy = 0.5 + 0.3 * r_cortex * np.sin(theta_cortex)

        return np.clip(cx, 0, 1), np.clip(cy, 0, 1)

    def _compute_inverse_lut(self):
        """Calcule la table inverse par interpolation"""
        # Methode simple: pour chaque point V1, trouver le point visuel le plus proche
        for cy in range(self.grille_size):
            for cx in range(self.grille_size):
                # Position V1 normalisee
                target = np.array([cx / self.grille_size, cy / self.grille_size])

                # Trouver le point visuel correspondant
                min_dist = float('inf')
                best_vx, best_vy = 0, 0

                # Recherche dans la LUT directe
                for vy in range(self.grille_size):
                    for vx in range(self.grille_size):
                        v1_pos = self.lut_visuel_vers_v1[vy, vx]
                        dist = np.sum((v1_pos - target)**2)
                        if dist < min_dist:
                            min_dist = dist
                            best_vx, best_vy = vx, vy

                self.lut_v1_vers_visuel[cy, cx] = [best_vx, best_vy]

    def encoder(self, image: np.ndarray) -> np.ndarray:
        """
        Encode une image du champ visuel en carte d'activation V1

        Args:
            image: Image RGB (H, W, 3) ou grayscale (H, W)

        Returns:
            activation_v1: Carte d'activation (grille_size, grille_size)
        """
        if len(image.shape) == 3:
            # Convertir en luminance
            image_gray = 0.299 * image[:,:,0] + 0.587 * image[:,:,1] + 0.114 * image[:,:,2]
        else:
            image_gray = image

        # Redimensionner si necessaire
        h, w = image_gray.shape
        if h != self.grille_size or w != self.grille_size:
            image_gray = self._resize(image_gray, self.grille_size)

        # Appliquer la transformation retinotopique
        activation = np.zeros((self.grille_size, self.grille_size))

        for y in range(self.grille_size):
            for x in range(self.grille_size):
                # Position dans V1 (destination)
                v1_x, v1_y = self.lut_visuel_vers_v1[y, x]

                # Coordonnees discretes
                cx = int(v1_x * (self.grille_size - 1))
                cy = int(v1_y * (self.grille_size - 1))

                # Accumuler l'activation
                activation[cy, cx] += image_gray[y, x]

        # Normaliser
        activation = np.clip(activation / activation.max(), 0, 1) if activation.max() > 0 else activation

        return activation

    def encoder_stereo(self, image_g: np.ndarray, image_d: np.ndarray,
                       depth: np.ndarray) -> dict:
        """
        Encode une paire stereo avec information de profondeur

        Returns:
            dict avec:
                - 'v1_gauche': activation pour oeil gauche
                - 'v1_droite': activation pour oeil droit
                - 'disparite': carte de disparite (pour V2)
                - 'profondeur': signal de profondeur
        """
        # Encoder chaque oeil
        v1_g = self.encoder(image_g)
        v1_d = self.encoder(image_d)

        # Calculer la disparite (difference entre les deux vues)
        disparite = np.abs(v1_g - v1_d)

        # Profondeur normalisee pour V2/V3
        if len(depth.shape) == 2:
            depth_norm = self._resize(depth, self.grille_size)
            depth_norm = 1.0 - np.clip(depth_norm / depth_norm.max(), 0, 1)
        else:
            depth_norm = np.zeros((self.grille_size, self.grille_size))

        return {
            'v1_gauche': v1_g,
            'v1_droite': v1_d,
            'disparite': disparite,
            'profondeur': depth_norm
        }

    def encoder_couleur(self, image_rgb: np.ndarray) -> dict:
        """
        Encode les canaux de couleur separement (pour V4)

        Returns:
            dict avec canaux R, G, B encodes + luminance
        """
        if len(image_rgb.shape) != 3:
            raise ValueError("Image RGB requise")

        return {
            'luminance': self.encoder(image_rgb),
            'rouge': self.encoder(image_rgb[:,:,0]),
            'vert': self.encoder(image_rgb[:,:,1]),
            'bleu': self.encoder(image_rgb[:,:,2]),
            'rouge_vert': self.encoder(image_rgb[:,:,0] - image_rgb[:,:,1]),
            'bleu_jaune': self.encoder(image_rgb[:,:,2] - (image_rgb[:,:,0] + image_rgb[:,:,1])/2)
        }

    def encoder_mouvement(self, flux_optique: np.ndarray) -> dict:
        """
        Encode le flux optique (pour V5/MT)

        Args:
            flux_optique: (H, W, 2) avec composantes x et y

        Returns:
            dict avec direction et magnitude du mouvement
        """
        if len(flux_optique.shape) != 3 or flux_optique.shape[2] != 2:
            raise ValueError("Flux optique (H, W, 2) requis")

        fx = flux_optique[:,:,0]
        fy = flux_optique[:,:,1]

        magnitude = np.sqrt(fx**2 + fy**2)
        direction = np.arctan2(fy, fx)

        return {
            'magnitude': self.encoder(magnitude),
            'direction': self.encoder((direction + np.pi) / (2 * np.pi)),  # Normalise 0-1
            'horizontal': self.encoder(np.abs(fx)),
            'vertical': self.encoder(np.abs(fy))
        }

    def _resize(self, image: np.ndarray, size: int) -> np.ndarray:
        """Redimensionnement simple par interpolation bilineaire"""
        h, w = image.shape
        new_image = np.zeros((size, size))

        for y in range(size):
            for x in range(size):
                src_x = x * (w - 1) / (size - 1)
                src_y = y * (h - 1) / (size - 1)

                x0, y0 = int(src_x), int(src_y)
                x1, y1 = min(x0 + 1, w - 1), min(y0 + 1, h - 1)

                fx, fy = src_x - x0, src_y - y0

                new_image[y, x] = (
                    image[y0, x0] * (1 - fx) * (1 - fy) +
                    image[y0, x1] * fx * (1 - fy) +
                    image[y1, x0] * (1 - fx) * fy +
                    image[y1, x1] * fx * fy
                )

        return new_image

    def decomposer_gabor(self, activation: np.ndarray,
                         nb_orientations: int = 8,
                         nb_frequences: int = 4) -> np.ndarray:
        """
        Decompose l'activation en reponses de filtres de Gabor
        (simule la reponse des neurones V1)

        Returns:
            gabor_responses: (nb_orientations * nb_frequences, grille_size, grille_size)
        """
        responses = []

        for theta in np.linspace(0, np.pi, nb_orientations, endpoint=False):
            for freq in [0.05, 0.1, 0.2, 0.4]:
                # Creer le filtre de Gabor
                filtre = self._gabor_kernel(theta, freq, sigma=2.0)

                # Convolution
                response = self._convolve(activation, filtre)
                responses.append(response)

        return np.array(responses)

    def _gabor_kernel(self, theta: float, freq: float, sigma: float,
                      size: int = 11) -> np.ndarray:
        """Genere un noyau de Gabor"""
        x = np.linspace(-size//2, size//2, size)
        y = np.linspace(-size//2, size//2, size)
        X, Y = np.meshgrid(x, y)

        x_rot = X * np.cos(theta) + Y * np.sin(theta)
        y_rot = -X * np.sin(theta) + Y * np.cos(theta)

        gaussienne = np.exp(-(x_rot**2 + y_rot**2) / (2 * sigma**2))
        sinusoide = np.cos(2 * np.pi * freq * x_rot)

        return gaussienne * sinusoide

    def _convolve(self, image: np.ndarray, kernel: np.ndarray) -> np.ndarray:
        """Convolution 2D simple"""
        h, w = image.shape
        kh, kw = kernel.shape
        pad_h, pad_w = kh // 2, kw // 2

        # Padding
        padded = np.pad(image, ((pad_h, pad_h), (pad_w, pad_w)), mode='reflect')

        result = np.zeros((h, w))
        for y in range(h):
            for x in range(w):
                region = padded[y:y+kh, x:x+kw]
                result[y, x] = np.sum(region * kernel)

        return result
