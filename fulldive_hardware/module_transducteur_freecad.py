#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================================
# MODULE TRANSDUCTEUR DÉTAILLÉ - FREECAD
# Un module unitaire du réseau de 10 000 transducteurs
# ============================================================

import math

try:
    import FreeCAD
    import Part
    from FreeCAD import Vector
    FREECAD_AVAILABLE = True
except ImportError:
    print("FreeCAD non disponible - Mode aperçu")
    FREECAD_AVAILABLE = False


class ParametresTransducteur:
    """Paramètres d'un module transducteur unitaire"""

    # Dimensions du module (mm)
    DIAMETRE_TOTAL = 8.0
    HAUTEUR_TOTALE = 12.0

    # LED RGB (calibration)
    LED_DIAMETRE = 2.0
    LED_HAUTEUR = 1.5
    LED_POSITION_Z = 11.0

    # Perforation acoustique
    PERFORATION_DIAMETRE = 3.0
    PERFORATION_POSITION_Z = 9.0

    # Réseau piézo (4 éléments)
    PIEZO_TAILLE = 2.5          # Taille d'un élément
    PIEZO_ESPACEMENT = 0.3      # Espace entre éléments
    PIEZO_HAUTEUR = 3.0
    PIEZO_POSITION_Z = 5.0

    # Circuit de contrôle (ASIC)
    CIRCUIT_DIAMETRE = 7.0
    CIRCUIT_HAUTEUR = 2.0
    CIRCUIT_POSITION_Z = 0.0

    # Boîtier
    BOITIER_EPAISSEUR = 0.5


def creer_led_rgb(params):
    """Crée la LED RGB de calibration"""
    if not FREECAD_AVAILABLE:
        return None

    # Corps principal (dôme)
    dome = Part.makeSphere(
        params.LED_DIAMETRE / 2,
        Vector(0, 0, params.LED_POSITION_Z)
    )

    # Couper le bas pour faire un dôme
    boite = Part.makeBox(
        params.LED_DIAMETRE * 2,
        params.LED_DIAMETRE * 2,
        params.LED_DIAMETRE,
        Vector(-params.LED_DIAMETRE, -params.LED_DIAMETRE,
               params.LED_POSITION_Z - params.LED_DIAMETRE)
    )
    dome = dome.cut(boite)

    # Base cylindrique
    base = Part.makeCylinder(
        params.LED_DIAMETRE / 2,
        params.LED_HAUTEUR / 2,
        Vector(0, 0, params.LED_POSITION_Z - params.LED_HAUTEUR / 2)
    )

    return dome.fuse(base)


def creer_perforation(params):
    """Crée la fenêtre acoustique (perforation)"""
    if not FREECAD_AVAILABLE:
        return None

    # Cylindre de perforation
    perforation = Part.makeCylinder(
        params.PERFORATION_DIAMETRE / 2,
        3.0,  # Traverse le boîtier
        Vector(0, 0, params.PERFORATION_POSITION_Z - 1)
    )

    return perforation


def creer_reseau_piezo(params):
    """Crée le réseau de 4 éléments piézoélectriques (2x2)"""
    if not FREECAD_AVAILABLE:
        return None

    elements = []
    taille = params.PIEZO_TAILLE
    esp = params.PIEZO_ESPACEMENT
    offset = (taille + esp) / 2

    positions = [
        (-offset, -offset),  # A
        (offset, -offset),   # B
        (-offset, offset),   # C
        (offset, offset),    # D
    ]

    for i, (px, py) in enumerate(positions):
        # Élément piézo (rectangulaire)
        elem = Part.makeBox(
            taille, taille, params.PIEZO_HAUTEUR,
            Vector(px - taille/2, py - taille/2, params.PIEZO_POSITION_Z)
        )
        elements.append(elem)

    # Fusionner tous les éléments
    resultat = elements[0]
    for e in elements[1:]:
        resultat = resultat.fuse(e)

    return resultat


def creer_circuit_controle(params):
    """Crée le circuit de contrôle (ASIC)"""
    if not FREECAD_AVAILABLE:
        return None

    # PCB circulaire
    pcb = Part.makeCylinder(
        params.CIRCUIT_DIAMETRE / 2,
        params.CIRCUIT_HAUTEUR,
        Vector(0, 0, params.CIRCUIT_POSITION_Z)
    )

    # Chip central (carré)
    chip_taille = 3.0
    chip = Part.makeBox(
        chip_taille, chip_taille, 0.5,
        Vector(-chip_taille/2, -chip_taille/2,
               params.CIRCUIT_POSITION_Z + params.CIRCUIT_HAUTEUR)
    )

    return pcb.fuse(chip)


def creer_boitier(params):
    """Crée le boîtier cylindrique du module"""
    if not FREECAD_AVAILABLE:
        return None

    # Cylindre externe
    ext = Part.makeCylinder(
        params.DIAMETRE_TOTAL / 2,
        params.HAUTEUR_TOTALE,
        Vector(0, 0, 0)
    )

    # Cylindre interne (creux)
    int_rayon = params.DIAMETRE_TOTAL / 2 - params.BOITIER_EPAISSEUR
    int_cyl = Part.makeCylinder(
        int_rayon,
        params.HAUTEUR_TOTALE - params.BOITIER_EPAISSEUR,
        Vector(0, 0, params.BOITIER_EPAISSEUR)
    )

    boitier = ext.cut(int_cyl)

    return boitier


def creer_connecteurs(params):
    """Crée les connecteurs électriques (pins)"""
    if not FREECAD_AVAILABLE:
        return None

    pins = []
    nb_pins = 6
    rayon_cercle = params.DIAMETRE_TOTAL / 2 - 1.5
    pin_rayon = 0.3
    pin_hauteur = 2.0

    for i in range(nb_pins):
        angle = 2 * math.pi * i / nb_pins
        x = rayon_cercle * math.cos(angle)
        y = rayon_cercle * math.sin(angle)

        pin = Part.makeCylinder(
            pin_rayon,
            pin_hauteur,
            Vector(x, y, -pin_hauteur)
        )
        pins.append(pin)

    resultat = pins[0]
    for p in pins[1:]:
        resultat = resultat.fuse(p)

    return resultat


def assembler_module_transducteur(params=None):
    """Assemble un module transducteur complet"""

    if params is None:
        params = ParametresTransducteur()

    print("=" * 50)
    print("MODULE TRANSDUCTEUR FULL-DIVE")
    print("=" * 50)

    composants = {}

    # 1. Boîtier
    print("[1/6] Création boîtier...")
    composants['boitier'] = creer_boitier(params)

    # 2. LED RGB
    print("[2/6] Création LED RGB...")
    composants['led'] = creer_led_rgb(params)

    # 3. Réseau piézo
    print("[3/6] Création réseau piézoélectrique 2x2...")
    composants['piezo'] = creer_reseau_piezo(params)

    # 4. Circuit contrôle
    print("[4/6] Création circuit de contrôle...")
    composants['circuit'] = creer_circuit_controle(params)

    # 5. Connecteurs
    print("[5/6] Création connecteurs...")
    composants['connecteurs'] = creer_connecteurs(params)

    # 6. Perforation (à soustraire)
    print("[6/6] Création perforation acoustique...")
    composants['perforation'] = creer_perforation(params)

    print("\n[OK] Module assemblé!")

    return composants


def creer_document_module(composants, nom="Module_Transducteur"):
    """Crée le document FreeCAD pour le module"""

    if not FREECAD_AVAILABLE:
        print("[!] FreeCAD non disponible")
        return None

    doc = FreeCAD.newDocument(nom)

    couleurs = {
        'boitier': (0.3, 0.3, 0.3),       # Gris
        'led': (1.0, 0.0, 0.0),           # Rouge (RGB)
        'piezo': (0.8, 0.7, 0.0),         # Doré (céramique)
        'circuit': (0.0, 0.5, 0.0),       # Vert (PCB)
        'connecteurs': (0.8, 0.8, 0.8),   # Argent
    }

    for nom_comp, shape in composants.items():
        if shape is None or nom_comp == 'perforation':
            continue

        obj = doc.addObject("Part::Feature", nom_comp)
        obj.Shape = shape

        if nom_comp in couleurs:
            obj.ViewObject.ShapeColor = couleurs[nom_comp]
            obj.ViewObject.Transparency = 20 if nom_comp == 'boitier' else 0

    doc.recompute()
    return doc


def creer_grille_modules(nb_x=5, nb_y=5, espacement=9.5):
    """Crée une grille de modules pour visualisation"""

    if not FREECAD_AVAILABLE:
        print("[!] FreeCAD non disponible")
        return None

    print(f"\nCréation grille {nb_x}x{nb_y} modules...")

    doc = FreeCAD.newDocument("Grille_Modules")
    params = ParametresTransducteur()

    for i in range(nb_x):
        for j in range(nb_y):
            x = i * espacement - (nb_x - 1) * espacement / 2
            y = j * espacement - (nb_y - 1) * espacement / 2

            # Créer un module simplifié (juste le boîtier)
            boitier = creer_boitier(params)
            if boitier:
                boitier.translate(Vector(x, y, 0))
                obj = doc.addObject("Part::Feature", f"Module_{i}_{j}")
                obj.Shape = boitier
                obj.ViewObject.ShapeColor = (0.0, 0.5, 0.8)

    doc.recompute()
    print(f"[OK] Grille créée: {nb_x * nb_y} modules")

    return doc


# ============================================================
# MAIN
# ============================================================

def main():
    print("""
    ╔═════════════════════════════════════════════════════╗
    ║   MODULE TRANSDUCTEUR UNITAIRE                      ║
    ║   Élément de base du réseau Full-Dive              ║
    ╠═════════════════════════════════════════════════════╣
    ║   Composants:                                       ║
    ║   - LED RGB (calibration)                          ║
    ║   - Fenêtre acoustique (Ø3mm)                      ║
    ║   - Réseau piézo 2x2 (déflexion)                   ║
    ║   - Circuit ASIC (contrôle)                        ║
    ║   - Connecteurs (6 pins)                           ║
    ╚═════════════════════════════════════════════════════╝
    """)

    # Créer un module
    composants = assembler_module_transducteur()

    if FREECAD_AVAILABLE:
        # Document du module unique
        doc = creer_document_module(composants)

        # Optionnel: créer une grille de test
        # grille = creer_grille_modules(5, 5)

        print("\nModèle prêt dans FreeCAD!")
    else:
        print("\nPour visualiser, exécutez dans FreeCAD.")

    return composants


if __name__ == "__main__":
    main()
