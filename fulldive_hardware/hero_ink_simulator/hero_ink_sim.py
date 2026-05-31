#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================================
# HERO INK - Simulateur TLP (Tube Lumineux Palpébra)
# Mapping vectoriel XY pour casque Full-Dive
# ============================================================

import pygame
import math
import sys
import time

# === CONFIGURATION ===
WINDOW_W = 800
WINDOW_H = 800
GRID_MIN = -6
GRID_MAX = 6
GRID_RANGE = GRID_MAX - GRID_MIN  # 12 unités

# Marges pour la grille
MARGIN = 80
GRID_W = WINDOW_W - 2 * MARGIN
GRID_H = WINDOW_H - 2 * MARGIN

# Couleurs
BLACK      = (0, 0, 0)
WHITE      = (255, 255, 255)
CYAN       = (0, 200, 255)
GRID_COLOR = (0, 80, 120)
AXIS_COLOR = (200, 200, 200)
TEXT_COLOR = (150, 150, 150)
LEFT_COLOR = (0, 180, 255)    # Bleu - œil gauche
RIGHT_COLOR = (255, 100, 0)   # Orange - œil droit
TRACE_COLOR = (0, 255, 100)

# Position interpupillaire (~3 unités de chaque côté du centre)
LEFT_EYE_X  = -3.0
RIGHT_EYE_X =  3.0
EYES_Y      =  0.0

# === PATTERNS DISPONIBLES ===
PATTERNS = {
    '1': 'cercle',
    '2': 'carre',
    '3': 'balayage_raster',
    '4': 'figure8',
    '5': 'spirale',
    '0': 'stop',
}


def grid_to_screen(gx, gy):
    """Convertit coordonnées grille en pixels écran"""
    sx = MARGIN + (gx - GRID_MIN) / GRID_RANGE * GRID_W
    sy = MARGIN + (GRID_MAX - gy) / GRID_RANGE * GRID_H
    return int(sx), int(sy)


def screen_to_grid(sx, sy):
    """Convertit pixels écran en coordonnées grille"""
    gx = (sx - MARGIN) / GRID_W * GRID_RANGE + GRID_MIN
    gy = GRID_MAX - (sy - MARGIN) / GRID_H * GRID_RANGE
    return round(gx, 2), round(gy, 2)


def draw_grid(surface, font_small):
    """Dessine la grille XY"""
    # Fond
    surface.fill(BLACK)

    # Lignes de grille
    for i in range(GRID_MIN, GRID_MAX + 1):
        # Lignes verticales
        x, _ = grid_to_screen(i, 0)
        pygame.draw.line(surface, GRID_COLOR, (x, MARGIN), (x, WINDOW_H - MARGIN), 1)

        # Lignes horizontales
        _, y = grid_to_screen(0, i)
        pygame.draw.line(surface, GRID_COLOR, (MARGIN, y), (WINDOW_W - MARGIN, y), 1)

        # Labels X
        label = font_small.render(str(i), True, TEXT_COLOR)
        sx, _ = grid_to_screen(i, 0)
        _, sy = grid_to_screen(0, 0)
        surface.blit(label, (sx - 6, sy + 8))

        # Labels Y (sauf 0)
        if i != 0:
            label = font_small.render(str(i), True, TEXT_COLOR)
            sx, _ = grid_to_screen(0, 0)
            _, sy = grid_to_screen(0, i)
            surface.blit(label, (sx - 22, sy - 8))

    # Axes principaux (plus épais)
    x0, _ = grid_to_screen(0, 0)
    _, y0 = grid_to_screen(0, 0)
    pygame.draw.line(surface, AXIS_COLOR, (MARGIN, y0), (WINDOW_W - MARGIN, y0), 2)
    pygame.draw.line(surface, AXIS_COLOR, (x0, MARGIN), (x0, WINDOW_H - MARGIN), 2)

    # Flèches des axes
    pygame.draw.polygon(surface, AXIS_COLOR, [
        (WINDOW_W - MARGIN, y0),
        (WINDOW_W - MARGIN - 10, y0 - 5),
        (WINDOW_W - MARGIN - 10, y0 + 5)
    ])
    pygame.draw.polygon(surface, AXIS_COLOR, [
        (x0, MARGIN),
        (x0 - 5, MARGIN + 10),
        (x0 + 5, MARGIN + 10)
    ])


def draw_eye_zones(surface):
    """Dessine les zones cibles des yeux"""
    for ex, color in [(LEFT_EYE_X, LEFT_COLOR), (RIGHT_EYE_X, RIGHT_COLOR)]:
        cx, cy = grid_to_screen(ex, EYES_Y)
        # Zone œil (ellipse)
        rect = pygame.Rect(cx - 40, cy - 25, 80, 50)
        pygame.draw.ellipse(surface, (*color, 30), rect, 0)
        pygame.draw.ellipse(surface, color, rect, 1)


def draw_points(surface, lx, ly, rx, ry):
    """Dessine les deux points de faisceau"""
    # Point gauche
    lsx, lsy = grid_to_screen(lx, ly)
    pygame.draw.circle(surface, LEFT_COLOR, (lsx, lsy), 8)
    pygame.draw.circle(surface, WHITE, (lsx, lsy), 8, 2)

    # Point droit
    rsx, rsy = grid_to_screen(rx, ry)
    pygame.draw.circle(surface, RIGHT_COLOR, (rsx, rsy), 8)
    pygame.draw.circle(surface, WHITE, (rsx, rsy), 8, 2)


def draw_ui(surface, font, font_small, lx, ly, rx, ry, mode, pattern):
    """Affiche l'interface utilisateur"""
    # Titre
    title = font.render("HERO INK - TLP Simulator", True, CYAN)
    surface.blit(title, (WINDOW_W // 2 - title.get_width() // 2, 10))

    # Coordonnées
    info_l = font_small.render(f"G: ({lx:.1f}, {ly:.1f})", True, LEFT_COLOR)
    info_r = font_small.render(f"D: ({rx:.1f}, {ry:.1f})", True, RIGHT_COLOR)
    surface.blit(info_l, (10, 10))
    surface.blit(info_r, (10, 30))

    # Mode
    mode_txt = font_small.render(f"Mode: {mode} | Pattern: {pattern}", True, CYAN)
    surface.blit(mode_txt, (10, WINDOW_H - 60))

    # Contrôles
    ctrl = font_small.render("ZQSD: G  |  Fleches: D  |  1-5: Patterns  |  0: Stop  |  ESC: Quitter", True, TEXT_COLOR)
    surface.blit(ctrl, (WINDOW_W // 2 - ctrl.get_width() // 2, WINDOW_H - 30))


def pattern_cercle(t, offset_x):
    """Cercle autour de la zone œil"""
    r = 1.5
    x = offset_x + r * math.cos(t * 2)
    y = r * math.sin(t * 2)
    return x, y


def pattern_carre(t, offset_x):
    """Carré vectoriel"""
    phase = (t * 2) % (2 * math.pi)
    size = 1.5
    if phase < math.pi / 2:
        p = phase / (math.pi / 2)
        x, y = offset_x - size + p * 2 * size, size
    elif phase < math.pi:
        p = (phase - math.pi / 2) / (math.pi / 2)
        x, y = offset_x + size, size - p * 2 * size
    elif phase < 3 * math.pi / 2:
        p = (phase - math.pi) / (math.pi / 2)
        x, y = offset_x + size - p * 2 * size, -size
    else:
        p = (phase - 3 * math.pi / 2) / (math.pi / 2)
        x, y = offset_x - size, -size + p * 2 * size
    return x, y


def pattern_raster(t, offset_x):
    """Balayage raster (comme CRT)"""
    lines = 10
    speed = 3.0
    total = lines * speed
    phase = (t * 20) % total
    line = int(phase / speed)
    px = (phase % speed) / speed  # 0 à 1
    if line % 2 == 1:
        px = 1 - px  # Alternance gauche-droite
    x = offset_x - 2.0 + px * 4.0
    y = 2.0 - line * 0.4
    return x, y


def pattern_figure8(t, offset_x):
    """Lemniscate (figure 8)"""
    x = offset_x + 1.8 * math.sin(t * 2)
    y = 1.2 * math.sin(t * 4)
    return x, y


def pattern_spirale(t, offset_x):
    """Spirale entrante"""
    r = max(0, 2.0 - (t % 3.0) * 0.6)
    x = offset_x + r * math.cos(t * 4)
    y = r * math.sin(t * 4)
    return x, y


def get_pattern_pos(pattern, t, offset_x):
    """Retourne la position du point selon le pattern"""
    if pattern == 'cercle':
        return pattern_cercle(t, offset_x)
    elif pattern == 'carre':
        return pattern_carre(t, offset_x)
    elif pattern == 'balayage_raster':
        return pattern_raster(t, offset_x)
    elif pattern == 'figure8':
        return pattern_figure8(t, offset_x)
    elif pattern == 'spirale':
        return pattern_spirale(t, offset_x)
    return offset_x, 0.0


def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
    pygame.display.set_caption("HERO INK - TLP Simulator")

    font = pygame.font.SysFont("monospace", 18, bold=True)
    font_small = pygame.font.SysFont("monospace", 13)

    clock = pygame.time.Clock()

    # Positions initiales
    lx, ly = LEFT_EYE_X, EYES_Y
    rx, ry = RIGHT_EYE_X, EYES_Y

    current_pattern = 'stop'
    mode = 'manuel'
    t = 0.0
    step = 0.1
    trace = []

    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        t += dt

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

                # Contrôle point gauche (ZQSD)
                if event.key == pygame.K_q:
                    lx = max(GRID_MIN, lx - step)
                if event.key == pygame.K_d:
                    lx = min(0, lx + step)
                if event.key == pygame.K_z:
                    ly = min(GRID_MAX, ly + step)
                if event.key == pygame.K_s:
                    ly = max(GRID_MIN, ly - step)

                # Contrôle point droit (flèches)
                if event.key == pygame.K_LEFT:
                    rx = max(0, rx - step)
                if event.key == pygame.K_RIGHT:
                    rx = min(GRID_MAX, rx + step)
                if event.key == pygame.K_UP:
                    ry = min(GRID_MAX, ry + step)
                if event.key == pygame.K_DOWN:
                    ry = max(GRID_MIN, ry - step)

                # Patterns
                for key_char, pat_name in PATTERNS.items():
                    if event.key == getattr(pygame, f'K_{key_char}'):
                        current_pattern = pat_name
                        mode = 'auto' if pat_name != 'stop' else 'manuel'
                        t = 0.0
                        trace = []

        # Mise à jour positions en mode auto
        if current_pattern != 'stop':
            lx, ly = get_pattern_pos(current_pattern, t, LEFT_EYE_X)
            rx, ry = get_pattern_pos(current_pattern, t, RIGHT_EYE_X)

            # Trace
            trace.append((grid_to_screen(lx, ly), grid_to_screen(rx, ry)))
            if len(trace) > 200:
                trace.pop(0)

        # Dessin
        draw_grid(screen, font_small)
        draw_eye_zones(screen)

        # Traces
        for i, (lp, rp) in enumerate(trace):
            alpha = int(255 * i / max(1, len(trace)))
            color = (0, alpha // 2, alpha)
            pygame.draw.circle(screen, color, lp, 2)
            pygame.draw.circle(screen, (alpha, alpha // 3, 0), rp, 2)

        draw_points(screen, lx, ly, rx, ry)
        draw_ui(screen, font, font_small, lx, ly, rx, ry, mode, current_pattern)

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
