"""
NexOS -- Systeme de Communication ISO
Signaux veridiques entre ISOs. Pas de deception possible.
"""

from dataclasses import dataclass
from typing import List, Optional


# Types de signaux -- toujours veridiques
SIGNAL_TYPES = {
    'FOOD_HERE':  {'color': '#00ff00', 'description': 'Nourriture ici'},
    'DANGER':     {'color': '#ff4444', 'description': 'Danger (energie basse)'},
    'COME_HERE':  {'color': '#00aaff', 'description': 'Viens ici'},
    'NEED_HELP':  {'color': '#ff8800', 'description': "Besoin d'aide"},
    'WISDOM':     {'color': '#ffd700', 'description': 'Sagesse de Minerve'},
    'PROTECTION': {'color': '#00e5ff', 'description': 'Protection de Tron'},
}


@dataclass
class Signal:
    """Un signal emis par un ISO ou par Minerve."""
    x: int
    z: int
    signal_type: str
    sender_id: int
    radius: int = 10
    ttl: int = 20
    cycle_created: int = 0

    def to_dict(self) -> dict:
        return {
            'x': self.x, 'z': self.z,
            'type': self.signal_type,
            'sender_id': self.sender_id,
            'radius': self.radius,
            'ttl': self.ttl
        }


class SignalBoard:
    """
    Tableau de signaux global. Stocke les signaux actifs, gere la decroissance,
    et fournit les signaux perceptibles par position.
    """

    def __init__(self, grid_size: int = 200, config: dict = None):
        self.grid_size = grid_size
        self.config = config or {}

        comm_cfg = self.config.get('life', {}).get('communication', {})
        self.signal_cost = comm_cfg.get('signal_cost', 3.0)
        self.default_radius = comm_cfg.get('signal_radius', 10)
        self.default_ttl = comm_cfg.get('signal_ttl', 20)
        self.max_signals = comm_cfg.get('max_signals', 1000)

        self.signals: List[Signal] = []

    def emit(self, x: int, z: int, signal_type: str, sender_id: int,
             cycle: int = 0, radius: int = None) -> Optional[Signal]:
        """Emet un nouveau signal."""
        if signal_type not in SIGNAL_TYPES:
            return None
        if len(self.signals) >= self.max_signals:
            return None

        signal = Signal(
            x=x, z=z,
            signal_type=signal_type,
            sender_id=sender_id,
            radius=radius or self.default_radius,
            ttl=self.default_ttl,
            cycle_created=cycle
        )
        self.signals.append(signal)
        return signal

    def get_nearby_signals(self, x: int, z: int,
                           perception_radius: int = 10) -> List[Signal]:
        """Retourne les signaux perceptibles depuis (x, z)."""
        nearby = []
        for sig in self.signals:
            dx = abs(sig.x - x)
            dz = abs(sig.z - z)
            max_range = max(sig.radius, perception_radius)
            if dx <= max_range and dz <= max_range:
                nearby.append(sig)
        return nearby

    def tick(self):
        """Decroit le TTL et retire les signaux expires."""
        for sig in self.signals:
            sig.ttl -= 1
        self.signals = [s for s in self.signals if s.ttl > 0]

    def get_all_signals(self) -> List[dict]:
        return [s.to_dict() for s in self.signals]

    def get_stats(self) -> dict:
        type_counts = {}
        for sig in self.signals:
            type_counts[sig.signal_type] = type_counts.get(sig.signal_type, 0) + 1
        return {
            'active_signals': len(self.signals),
            'by_type': type_counts
        }
