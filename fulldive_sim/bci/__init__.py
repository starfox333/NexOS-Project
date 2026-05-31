#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================================
# MODULE BCI (Brain-Computer Interface) - VERSION ACCESSIBLE
# Contrôle cérébral simple et abordable
# ============================================================
#
# PHILOSOPHIE : Peu de capteurs, algorithmes malins
# Budget cible : < 200€ pour le prototype
#
# ============================================================

from .config_bci import ConfigBCI
from .capteurs import CapteurEEG, CapteurIMU, FusionCapteurs
from .decodeur import DecodeurMoteur
from .predicteur import PredicteurMouvement
from .calibration import CalibreurBCI
from .controleur import ControleurAvatar

__version__ = "0.1.0"
