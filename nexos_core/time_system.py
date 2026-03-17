"""
NexOS — Systeme de temps virtuel accelere
1 seconde reelle = N secondes virtuelles
"""

import time


class VirtualTime:
    """
    Temps virtuel accelere.
    Permet aux ISOs d'evoluer rapidement dans un temps compresse.
    """

    def __init__(self, acceleration: float = 35.0):
        self.acceleration = acceleration
        self.start_real = time.time()
        self.cycles = 0

    def get_real_elapsed(self) -> float:
        """Temps reel ecoule en secondes"""
        return time.time() - self.start_real

    def get_virtual_elapsed(self) -> float:
        """Temps virtuel ecoule en secondes"""
        return self.get_real_elapsed() * self.acceleration

    def get_virtual_days(self) -> float:
        """Jours virtuels ecoules"""
        return self.get_virtual_elapsed() / 86400.0

    def tick(self):
        """Avance d'un cycle"""
        self.cycles += 1

    def get_cycles(self) -> int:
        return self.cycles

    def format_virtual(self) -> str:
        """Affichage lisible : Xj Xh Xm Xs"""
        total = self.get_virtual_elapsed()
        days = int(total // 86400)
        hours = int((total % 86400) // 3600)
        mins = int((total % 3600) // 60)
        secs = int(total % 60)

        parts = []
        if days > 0:
            parts.append(f"{days}j")
        if hours > 0 or days > 0:
            parts.append(f"{hours:02d}h")
        parts.append(f"{mins:02d}m")
        parts.append(f"{secs:02d}s")
        return ' '.join(parts)

    def format_real(self) -> str:
        """Temps reel ecoule formate"""
        total = int(self.get_real_elapsed())
        mins = total // 60
        secs = total % 60
        return f"{mins}m {secs:02d}s"

    def get_state(self) -> dict:
        return {
            'cycles': self.cycles,
            'real_elapsed': round(self.get_real_elapsed(), 1),
            'virtual_elapsed': round(self.get_virtual_elapsed(), 1),
            'virtual_formatted': self.format_virtual(),
            'acceleration': self.acceleration
        }
