"""
NexOS — Chargement de la configuration globale
"""

import os
import yaml

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEFAULT_PATH = os.path.join(_BASE_DIR, 'config.yaml')

_DEFAULT_CONFIG = {
    'grid': {'size': 200, 'energy_regen_rate': 0.5, 'max_cell_energy': 200,
             'initial_energy_min': 50, 'initial_energy_max': 150},
    'time': {'acceleration': 35, 'cycle_delay': 0.05},
    'life': {
        'initial_population': 10, 'emergence_threshold': 50000,
        'max_population': 500, 'perception_radius': 5,
        'energy': {'start': 100, 'max': 200, 'move_cost': 2, 'rest_recovery': 5,
                   'reproduction_cost': 80, 'reproduction_threshold': 150, 'harvest_amount': 15},
        'learning': {'learning_rate': 0.1, 'memory_capacity': 500, 'exploration_rate': 0.3},
        'genetics': {'mutation_rate': 0.01}
    },
    'server': {'host': '127.0.0.1', 'port': 5000, 'update_interval': 1.0},
    'logging': {'level': 'INFO', 'stats_interval': 100, 'save_interval': 1000}
}


def load_config(path: str = None) -> dict:
    """Charge la configuration depuis config.yaml"""
    path = path or _DEFAULT_PATH
    try:
        with open(path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        if not isinstance(config, dict):
            raise ValueError("config.yaml invalide")
        return config
    except FileNotFoundError:
        print(f"[CONFIG] {path} introuvable — valeurs par defaut")
        return _DEFAULT_CONFIG
    except Exception as e:
        print(f"[CONFIG] Erreur lecture : {e} — valeurs par defaut")
        return _DEFAULT_CONFIG


def get(config: dict, *keys, default=None):
    """Accès sécurisé aux clés imbriquées : get(cfg, 'life', 'energy', 'max')"""
    node = config
    for key in keys:
        if isinstance(node, dict):
            node = node.get(key)
        else:
            return default
        if node is None:
            return default
    return node
