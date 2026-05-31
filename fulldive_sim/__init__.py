# ============================================================
# FULL-DIVE HEADSET SIMULATION
# Casque de realite virtuelle a stimulation corticale directe
# ============================================================
# Auteur: Andre (NexOS Project)
# Version: 0.1.0
# ============================================================

from .config import FullDiveConfig
from .scene_3d import Scene3D, Camera
from .retinotopic import RetinotopicEncoder
from .scanner import BalayageCRT, TrajectoireType
from .signal_gen import SignalGenerator
from .brain_model import CortexVisuel
from .simulator import FullDiveSimulator

__version__ = "0.1.0"
__all__ = [
    'FullDiveConfig',
    'Scene3D',
    'Camera',
    'RetinotopicEncoder',
    'BalayageCRT',
    'TrajectoireType',
    'SignalGenerator',
    'CortexVisuel',
    'FullDiveSimulator',
]
