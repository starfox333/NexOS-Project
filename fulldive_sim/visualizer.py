# ============================================================
# VISUALISATION
# Outils de visualisation pour le simulateur Full-Dive
# ============================================================

import numpy as np
from typing import List, Optional, Tuple
from .scanner import PointBalayage, TrajectoireType
from .simulator import FrameResult


class ASCIIVisualizer:
    """Visualisation ASCII pour terminal (sans dependances)"""

    CHARS = " .:-=+*#%@"

    def __init__(self, width: int = 60, height: int = 30):
        self.width = width
        self.height = height

    def render_array(self, array: np.ndarray, title: str = "") -> str:
        """Convertit un array 2D en art ASCII"""
        # Normaliser
        arr = np.array(array)
        if arr.max() > arr.min():
            arr = (arr - arr.min()) / (arr.max() - arr.min())
        else:
            arr = np.zeros_like(arr)

        # Redimensionner
        h, w = arr.shape
        result = []

        if title:
            result.append(f"╔{'═' * (self.width + 2)}╗")
            result.append(f"║ {title.center(self.width)} ║")
            result.append(f"╠{'═' * (self.width + 2)}╣")

        for y in range(self.height):
            line = "║ "
            for x in range(self.width):
                # Echantillonner
                sy = int(y * h / self.height)
                sx = int(x * w / self.width)
                val = arr[sy, sx]

                # Convertir en caractere
                idx = int(val * (len(self.CHARS) - 1))
                line += self.CHARS[idx]
            line += " ║"
            result.append(line)

        result.append(f"╚{'═' * (self.width + 2)}╝")

        return "\n".join(result)

    def render_trajectoire(self, trajectoire: List[PointBalayage],
                           nb_points: int = 500) -> str:
        """Visualise une trajectoire de balayage"""
        grille = np.zeros((self.height, self.width))

        # Echantillonner les points
        step = max(1, len(trajectoire) // nb_points)
        for i, point in enumerate(trajectoire[::step]):
            x = int(point.x * (self.width - 1))
            y = int(point.y * (self.height - 1))
            # Intensite basee sur l'ordre (plus recent = plus brillant)
            grille[y, x] = (i * step) / len(trajectoire)

        return self.render_array(grille, "Trajectoire de Balayage")

    def render_frame_result(self, result: FrameResult) -> str:
        """Affiche un resume d'une frame"""
        output = []
        output.append("=" * 64)
        output.append(f"FRAME {result.frame_id}")
        output.append("=" * 64)
        output.append(f"Temps simule: {result.temps_simule_ms:.1f}ms")
        output.append(f"Temps reel:   {result.temps_reel_ms:.2f}ms")
        output.append(f"FPS:          {result.fps_reel:.1f}")
        output.append(f"Latence:      {result.latence_ms:.0f}ms")
        output.append("")

        # Miniatures
        mini_viz = ASCIIVisualizer(width=25, height=12)

        output.append("┌─ Activation V1 ─┬─ Perception ────┐")
        v1_lines = mini_viz.render_array(result.activation_v1).split("\n")[3:-1]
        perc_lines = mini_viz.render_array(result.perception).split("\n")[3:-1]

        for v1, perc in zip(v1_lines, perc_lines):
            output.append(f"{v1} {perc}")

        output.append("")
        output.append(f"Activation moyenne: {np.mean(result.activation_v1):.3f}")
        output.append(f"Perception moyenne: {np.mean(result.perception):.3f}")
        output.append("=" * 64)

        return "\n".join(output)

    def render_statistiques(self, historique: List[FrameResult]) -> str:
        """Affiche les statistiques de simulation"""
        if not historique:
            return "Pas de donnees"

        fps_list = [f.fps_reel for f in historique]
        perc_list = [np.mean(f.perception) for f in historique]

        output = []
        output.append("╔" + "═" * 40 + "╗")
        output.append("║" + " STATISTIQUES SIMULATION ".center(40) + "║")
        output.append("╠" + "═" * 40 + "╣")
        output.append(f"║ Frames:           {len(historique):>20} ║")
        output.append(f"║ FPS moyen:        {np.mean(fps_list):>20.1f} ║")
        output.append(f"║ FPS min:          {min(fps_list):>20.1f} ║")
        output.append(f"║ FPS max:          {max(fps_list):>20.1f} ║")
        output.append(f"║ Perception moy:   {np.mean(perc_list):>20.3f} ║")
        output.append("╚" + "═" * 40 + "╝")

        # Mini graphe FPS (derniers 50)
        output.append("\nFPS (derniers 50 frames):")
        recent_fps = fps_list[-50:]
        max_fps = max(recent_fps) if recent_fps else 1
        for i in range(5, 0, -1):
            line = f"{int(max_fps * i / 5):>4}│"
            for fps in recent_fps:
                if fps >= max_fps * i / 5:
                    line += "█"
                elif fps >= max_fps * (i - 0.5) / 5:
                    line += "▄"
                else:
                    line += " "
            output.append(line)
        output.append("    └" + "─" * len(recent_fps))

        return "\n".join(output)


def generer_rapport_html(historique: List[FrameResult],
                         trajectoire: List[PointBalayage],
                         config: dict) -> str:
    """Genere un rapport HTML de la simulation"""
    html = """<!DOCTYPE html>
<html>
<head>
    <title>Rapport Simulation Full-Dive</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #1a1a2e; color: #eee; }
        h1 { color: #00d4ff; }
        h2 { color: #00ff88; border-bottom: 1px solid #333; }
        .card { background: #16213e; padding: 15px; margin: 10px 0; border-radius: 8px; }
        .metric { display: inline-block; margin: 10px; padding: 15px; background: #0f3460; border-radius: 5px; }
        .metric .value { font-size: 24px; color: #00d4ff; }
        .metric .label { font-size: 12px; color: #888; }
        canvas { background: #0a0a1a; border-radius: 5px; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #333; padding: 8px; text-align: left; }
        th { background: #0f3460; }
    </style>
</head>
<body>
    <h1>🧠 Rapport Simulation Full-Dive</h1>
"""

    if historique:
        fps_moy = np.mean([f.fps_reel for f in historique])
        perc_moy = np.mean([np.mean(f.perception) for f in historique])

        html += f"""
    <div class="card">
        <h2>Metriques Globales</h2>
        <div class="metric">
            <div class="value">{len(historique)}</div>
            <div class="label">Frames</div>
        </div>
        <div class="metric">
            <div class="value">{fps_moy:.1f}</div>
            <div class="label">FPS Moyen</div>
        </div>
        <div class="metric">
            <div class="value">{perc_moy:.3f}</div>
            <div class="label">Perception Moyenne</div>
        </div>
        <div class="metric">
            <div class="value">{config.get('nb_points', 10000)}</div>
            <div class="label">Points de Stimulation</div>
        </div>
    </div>
"""

    html += f"""
    <div class="card">
        <h2>Configuration</h2>
        <table>
            <tr><th>Parametre</th><th>Valeur</th></tr>
            <tr><td>Resolution</td><td>{config.get('grille_size', 100)}x{config.get('grille_size', 100)}</td></tr>
            <tr><td>FPS cible</td><td>{config.get('fps', 60)}</td></tr>
            <tr><td>Points de stimulation</td><td>{config.get('nb_points', 10000)}</td></tr>
            <tr><td>Frequence balayage</td><td>{config.get('nb_points', 10000) * config.get('fps', 60) / 1000:.0f} kHz</td></tr>
        </table>
    </div>

    <div class="card">
        <h2>Trajectoire de Balayage</h2>
        <p>Points: {len(trajectoire)}</p>
        <canvas id="trajCanvas" width="400" height="400"></canvas>
    </div>

    <script>
        // Dessiner la trajectoire
        const canvas = document.getElementById('trajCanvas');
        const ctx = canvas.getContext('2d');
        const points = {[[p.x, p.y] for p in trajectoire[:1000]]};

        ctx.strokeStyle = '#00d4ff';
        ctx.lineWidth = 0.5;
        ctx.beginPath();

        for (let i = 0; i < points.length; i++) {{
            const x = points[i][0] * 400;
            const y = points[i][1] * 400;
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        }}
        ctx.stroke();
    </script>
</body>
</html>
"""
    return html


def sauvegarder_rapport(historique: List[FrameResult],
                        trajectoire: List[PointBalayage],
                        config: dict,
                        chemin: str = "rapport_fulldive.html"):
    """Sauvegarde le rapport HTML"""
    html = generer_rapport_html(historique, trajectoire, config)
    with open(chemin, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"Rapport sauvegarde: {chemin}")
