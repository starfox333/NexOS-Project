#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================================
# FULL-DIVE HEADSET - STYLE AMUSPHERE (SAO)
# Design inspiré du casque AmuSphere de Sword Art Online
# ============================================================
#
#  Vue de face:
#                 ╭─────────────────────╮
#                ╱    BANDEAU FRONTAL    ╲
#               ╱   ┌─────────────────┐   ╲
#    MODULE    │    │  ZONE CENTRALE  │    │    MODULE
#    TEMPORAL ◀│    │   (transducteurs)│    │▶  TEMPORAL
#    GAUCHE    │    └─────────────────┘    │    DROIT
#               ╲                         ╱
#                ╲    BANDEAU ARRIÈRE   ╱
#                 ╰──────────╥─────────╯
#                            ║
#                      CONNECTEUR
#
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


# ============================================================
# PARAMÈTRES STYLE AMUSPHERE
# ============================================================

class ParametresAmuSphere:
    """Paramètres du casque style AmuSphere"""

    # === DIMENSIONS TÊTE ===
    TETE_RAYON = 95.0              # Rayon moyen tête
    TETE_LARGEUR = 150.0           # Largeur tête (oreille à oreille)
    TETE_PROFONDEUR = 195.0        # Profondeur (front à occiput)

    # === BANDEAU PRINCIPAL ===
    BANDEAU_LARGEUR = 35.0         # Largeur du bandeau
    BANDEAU_EPAISSEUR = 12.0       # Épaisseur (contient l'électronique)
    BANDEAU_RAYON_INT = 100.0      # Rayon intérieur
    BANDEAU_RAYON_EXT = 112.0      # Rayon extérieur

    # === MODULES TEMPORAUX (côtés) ===
    TEMPORAL_LONGUEUR = 80.0       # Longueur module temporal
    TEMPORAL_LARGEUR = 45.0        # Largeur
    TEMPORAL_EPAISSEUR = 25.0      # Épaisseur (contient transducteurs)
    TEMPORAL_RAYON_ARRONDI = 15.0  # Arrondi des bords

    # === MODULE OCCIPITAL (arrière) ===
    OCCIPITAL_LARGEUR = 120.0      # Largeur zone occipitale
    OCCIPITAL_HAUTEUR = 80.0       # Hauteur
    OCCIPITAL_EPAISSEUR = 20.0     # Épaisseur
    OCCIPITAL_COURBURE = 85.0      # Rayon de courbure

    # === MODULE FRONTAL ===
    FRONTAL_LARGEUR = 60.0         # Largeur pièce frontale
    FRONTAL_HAUTEUR = 25.0         # Hauteur
    FRONTAL_EPAISSEUR = 15.0       # Épaisseur

    # === TRANSDUCTEURS ===
    TRANS_NB_TEMPORAL = 1500       # Par module temporal
    TRANS_NB_OCCIPITAL = 6000      # Module occipital
    TRANS_NB_FRONTAL = 1000        # Module frontal
    TRANS_DIAMETRE = 6.0           # Diamètre unitaire
    TRANS_ESPACEMENT = 7.0         # Espacement

    # === ÉCLAIRAGE (LED décoratives) ===
    LED_LARGEUR = 3.0              # Largeur bande LED
    LED_COULEUR = (0.0, 0.8, 1.0)  # Cyan (style SAO)

    # === COUSSINETS ===
    COUSSINET_EPAISSEUR = 8.0      # Épaisseur mousse
    COUSSINET_MATERIAU = "gel"     # gel ou mousse

    # === CONNECTEUR ===
    CONNECTEUR_DIAMETRE = 8.0      # Connecteur magnétique
    CONNECTEUR_POSITION = "nuque"  # nuque ou temporal


# ============================================================
# FONCTIONS DE CRÉATION - STYLE AMUSPHERE
# ============================================================

def creer_bandeau_principal(params):
    """
    Crée le bandeau principal qui fait le tour de la tête
    Style fin et élégant comme l'AmuSphere
    """
    if not FREECAD_AVAILABLE:
        print(f"[APERÇU] Bandeau principal: R={params.BANDEAU_RAYON_INT}mm")
        return None

    # Tore pour le bandeau (anneau)
    # On utilise une révolution d'un rectangle arrondi

    # Profil du bandeau (section)
    profil_pts = [
        Vector(params.BANDEAU_RAYON_INT, 0, -params.BANDEAU_LARGEUR/2),
        Vector(params.BANDEAU_RAYON_EXT, 0, -params.BANDEAU_LARGEUR/2),
        Vector(params.BANDEAU_RAYON_EXT, 0, params.BANDEAU_LARGEUR/2),
        Vector(params.BANDEAU_RAYON_INT, 0, params.BANDEAU_LARGEUR/2),
    ]

    # Créer le profil fermé
    lignes = []
    for i in range(len(profil_pts)):
        lignes.append(Part.LineSegment(
            profil_pts[i],
            profil_pts[(i+1) % len(profil_pts)]
        ))

    profil = Part.Wire([l.toShape() for l in lignes])
    face = Part.Face(profil)

    # Révolution partielle (pas un cercle complet - ouvert devant)
    # De -150° à +150° (ouverture de 60° devant pour les yeux)
    bandeau = face.revolve(
        Vector(0, 0, 0),
        Vector(0, 0, 1),
        300  # 300° de révolution
    )

    # Rotation pour centrer l'ouverture devant
    bandeau.rotate(Vector(0, 0, 0), Vector(0, 0, 1), 30)

    return bandeau


def creer_module_temporal(params, cote="gauche"):
    """
    Crée un module temporal (côté de la tête)
    Contient les transducteurs pour les zones temporales du cerveau
    """
    if not FREECAD_AVAILABLE:
        print(f"[APERÇU] Module temporal {cote}: {params.TEMPORAL_LONGUEUR}x{params.TEMPORAL_LARGEUR}mm")
        return None

    # Forme de base : boîte arrondie
    longueur = params.TEMPORAL_LONGUEUR
    largeur = params.TEMPORAL_LARGEUR
    epaisseur = params.TEMPORAL_EPAISSEUR

    # Position selon le côté
    signe = -1 if cote == "gauche" else 1
    offset_x = signe * (params.TETE_LARGEUR / 2 + epaisseur / 2)

    # Créer une forme ellipsoïdale aplatie
    module = Part.makeBox(
        epaisseur,
        longueur,
        largeur,
        Vector(offset_x - epaisseur/2, -longueur/2, -largeur/2)
    )

    # Arrondir avec une sphère (simplification)
    # Dans FreeCAD complet, on utiliserait Fillet

    # Surface interne concave (épouse la tête)
    sphere_int = Part.makeSphere(
        params.TETE_RAYON + 5,
        Vector(0, 0, 0)
    )

    if cote == "gauche":
        module = module.cut(sphere_int)
    else:
        module = module.cut(sphere_int)

    return module


def creer_module_occipital(params):
    """
    Crée le module occipital (arrière de la tête)
    Zone principale de stimulation du cortex visuel V1
    """
    if not FREECAD_AVAILABLE:
        print(f"[APERÇU] Module occipital: {params.OCCIPITAL_LARGEUR}x{params.OCCIPITAL_HAUTEUR}mm")
        return None

    largeur = params.OCCIPITAL_LARGEUR
    hauteur = params.OCCIPITAL_HAUTEUR
    epaisseur = params.OCCIPITAL_EPAISSEUR
    courbure = params.OCCIPITAL_COURBURE

    # Position à l'arrière de la tête
    offset_y = params.TETE_PROFONDEUR / 2

    # Section du module (forme de haricot/croissant)
    # Utiliser une extrusion le long d'une courbe

    # Créer un arc de cercle pour la forme
    arc = Part.makeCircle(
        courbure,
        Vector(0, offset_y - courbure + epaisseur, 0),
        Vector(1, 0, 0),  # Axe X
        -60, 60  # Arc de 120°
    )

    # Profil rectangulaire à extruder
    profil = Part.makeCircle(epaisseur/2)

    # Pour simplifier, on fait une forme ellipsoïdale
    module = Part.makeEllipsoid(
        largeur / 2,       # Rayon X
        epaisseur / 2,     # Rayon Y
        hauteur / 2,       # Rayon Z
        Vector(0, offset_y, 0)
    )

    # Couper la partie interne (contre la tête)
    sphere_tete = Part.makeSphere(
        params.TETE_RAYON,
        Vector(0, 0, 0)
    )
    module = module.cut(sphere_tete)

    return module


def creer_module_frontal(params):
    """
    Crée le module frontal (front)
    Design élégant avec indicateurs LED
    """
    if not FREECAD_AVAILABLE:
        print(f"[APERÇU] Module frontal: {params.FRONTAL_LARGEUR}x{params.FRONTAL_HAUTEUR}mm")
        return None

    largeur = params.FRONTAL_LARGEUR
    hauteur = params.FRONTAL_HAUTEUR
    epaisseur = params.FRONTAL_EPAISSEUR

    # Position devant
    offset_y = -params.BANDEAU_RAYON_INT - epaisseur/2

    # Forme elliptique plate
    module = Part.makeEllipsoid(
        largeur / 2,
        epaisseur / 2,
        hauteur / 2,
        Vector(0, offset_y, params.BANDEAU_LARGEUR/4)
    )

    return module


def creer_bande_led(params, position="bandeau"):
    """
    Crée les bandes LED décoratives (style SAO cyan glow)
    """
    if not FREECAD_AVAILABLE:
        print(f"[APERÇU] Bande LED: position={position}")
        return None

    largeur_led = params.LED_LARGEUR

    if position == "bandeau":
        # LED sur le bord du bandeau
        rayon = params.BANDEAU_RAYON_EXT + 0.5

        # Tore fin pour la LED
        led = Part.makeTorus(
            rayon,
            largeur_led / 2,
            Vector(0, 0, params.BANDEAU_LARGEUR/2 - largeur_led)
        )

        # Couper pour correspondre au bandeau (300°)
        boite = Part.makeBox(
            rayon * 3, rayon * 3, 50,
            Vector(-rayon * 1.5, 0, -25)
        )
        led = led.cut(boite)

    elif position == "temporal":
        # LED autour du module temporal
        led = Part.makeTorus(
            params.TEMPORAL_LARGEUR / 2,
            largeur_led / 2,
            Vector(-params.TETE_LARGEUR/2 - params.TEMPORAL_EPAISSEUR/2, 0, 0)
        )

    return led


def creer_coussinet(params, zone="occipital"):
    """
    Crée les coussinets de confort (contact avec la tête)
    """
    if not FREECAD_AVAILABLE:
        print(f"[APERÇU] Coussinet: zone={zone}")
        return None

    epaisseur = params.COUSSINET_EPAISSEUR

    if zone == "occipital":
        # Coussinet courbe pour l'arrière
        coussinet = Part.makeEllipsoid(
            params.OCCIPITAL_LARGEUR / 2 - 5,
            epaisseur / 2,
            params.OCCIPITAL_HAUTEUR / 2 - 5,
            Vector(0, params.TETE_PROFONDEUR / 2 - epaisseur, 0)
        )

    elif zone == "temporal":
        # Petit coussinet pour les tempes
        coussinet = Part.makeCylinder(
            20,
            epaisseur,
            Vector(-params.TETE_LARGEUR/2 - epaisseur, 0, 0),
            Vector(1, 0, 0)
        )

    elif zone == "frontal":
        # Coussinet frontal
        coussinet = Part.makeEllipsoid(
            params.FRONTAL_LARGEUR / 2 - 5,
            epaisseur / 2,
            params.FRONTAL_HAUTEUR / 2 - 5,
            Vector(0, -params.BANDEAU_RAYON_INT + epaisseur, params.BANDEAU_LARGEUR/4)
        )

    return coussinet


def creer_connecteur_magnetique(params):
    """
    Crée le connecteur magnétique à la nuque
    Design discret et élégant
    """
    if not FREECAD_AVAILABLE:
        print(f"[APERÇU] Connecteur magnétique: Ø{params.CONNECTEUR_DIAMETRE}mm")
        return None

    diametre = params.CONNECTEUR_DIAMETRE
    position_y = params.TETE_PROFONDEUR / 2 + params.OCCIPITAL_EPAISSEUR

    # Base cylindrique
    base = Part.makeCylinder(
        diametre,
        15,
        Vector(0, position_y, -params.BANDEAU_LARGEUR/2),
        Vector(0, 1, 0)
    )

    # Anneau magnétique
    anneau = Part.makeTorus(
        diametre - 2,
        1.5,
        Vector(0, position_y + 10, -params.BANDEAU_LARGEUR/2),
        Vector(0, 1, 0)
    )

    return base.fuse(anneau)


def generer_positions_transducteurs_amusphere(params):
    """
    Génère les positions des transducteurs sur les différentes zones
    """
    positions = {
        'occipital': [],
        'temporal_gauche': [],
        'temporal_droit': [],
        'frontal': []
    }

    # === ZONE OCCIPITALE (principale - V1) ===
    nb_occ = min(params.TRANS_NB_OCCIPITAL, 2000)  # Limiter pour perf
    largeur = params.OCCIPITAL_LARGEUR
    hauteur = params.OCCIPITAL_HAUTEUR
    offset_y = params.TETE_PROFONDEUR / 2

    for i in range(nb_occ):
        # Distribution Fibonacci sur ellipse
        golden = (1 + math.sqrt(5)) / 2
        theta = 2 * math.pi * i / golden
        r = math.sqrt(i / nb_occ)

        x = r * (largeur/2 - 10) * math.cos(theta)
        z = r * (hauteur/2 - 10) * math.sin(theta)
        y = offset_y - 5  # Légèrement à l'intérieur

        positions['occipital'].append({
            'pos': (x, y, z),
            'normal': (0, 1, 0),
            'index': i
        })

    # === ZONES TEMPORALES ===
    nb_temp = min(params.TRANS_NB_TEMPORAL, 500)

    for cote in ['gauche', 'droit']:
        signe = -1 if cote == 'gauche' else 1
        offset_x = signe * (params.TETE_LARGEUR / 2)

        for i in range(nb_temp):
            golden = (1 + math.sqrt(5)) / 2
            theta = 2 * math.pi * i / golden
            r = math.sqrt(i / nb_temp)

            y = r * (params.TEMPORAL_LONGUEUR/2 - 10) * math.cos(theta)
            z = r * (params.TEMPORAL_LARGEUR/2 - 10) * math.sin(theta)
            x = offset_x

            key = f'temporal_{cote}'
            positions[key].append({
                'pos': (x, y, z),
                'normal': (signe, 0, 0),
                'index': i
            })

    # === ZONE FRONTALE ===
    nb_front = min(params.TRANS_NB_FRONTAL, 300)
    offset_y_front = -params.BANDEAU_RAYON_INT

    for i in range(nb_front):
        golden = (1 + math.sqrt(5)) / 2
        theta = 2 * math.pi * i / golden
        r = math.sqrt(i / nb_front)

        x = r * (params.FRONTAL_LARGEUR/2 - 5) * math.cos(theta)
        z = r * (params.FRONTAL_HAUTEUR/2 - 5) * math.sin(theta) + params.BANDEAU_LARGEUR/4
        y = offset_y_front

        positions['frontal'].append({
            'pos': (x, y, z),
            'normal': (0, -1, 0),
            'index': i
        })

    return positions


# ============================================================
# ASSEMBLAGE COMPLET STYLE AMUSPHERE
# ============================================================

def assembler_amusphere(params=None, detail_level="medium"):
    """
    Assemble le casque complet style AmuSphere

    Args:
        params: ParametresAmuSphere
        detail_level: "low", "medium", "high"
    """
    if params is None:
        params = ParametresAmuSphere()

    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║     █████╗ ███╗   ███╗██╗   ██╗███████╗██████╗ ██╗  ██╗  ║
    ║    ██╔══██╗████╗ ████║██║   ██║██╔════╝██╔══██╗██║  ██║  ║
    ║    ███████║██╔████╔██║██║   ██║███████╗██████╔╝███████║  ║
    ║    ██╔══██║██║╚██╔╝██║██║   ██║╚════██║██╔═══╝ ██╔══██║  ║
    ║    ██║  ██║██║ ╚═╝ ██║╚██████╔╝███████║██║     ██║  ██║  ║
    ║    ╚═╝  ╚═╝╚═╝     ╚═╝ ╚═════╝ ╚══════╝╚═╝     ╚═╝  ╚═╝  ║
    ║                                                           ║
    ║              FULL-DIVE HEADSET - STYLE SAO               ║
    ╚═══════════════════════════════════════════════════════════╝
    """)

    composants = {}

    # 1. BANDEAU PRINCIPAL
    print("[1/8] Création bandeau principal...")
    composants['bandeau'] = creer_bandeau_principal(params)

    # 2. MODULE OCCIPITAL (arrière - V1)
    print("[2/8] Création module occipital (zone V1)...")
    composants['occipital'] = creer_module_occipital(params)

    # 3. MODULES TEMPORAUX
    print("[3/8] Création modules temporaux...")
    composants['temporal_gauche'] = creer_module_temporal(params, "gauche")
    composants['temporal_droit'] = creer_module_temporal(params, "droit")

    # 4. MODULE FRONTAL
    print("[4/8] Création module frontal...")
    composants['frontal'] = creer_module_frontal(params)

    # 5. BANDES LED
    print("[5/8] Création bandes LED (style SAO)...")
    composants['led_bandeau'] = creer_bande_led(params, "bandeau")

    # 6. COUSSINETS
    print("[6/8] Création coussinets confort...")
    composants['coussinet_occipital'] = creer_coussinet(params, "occipital")
    composants['coussinet_frontal'] = creer_coussinet(params, "frontal")

    # 7. CONNECTEUR
    print("[7/8] Création connecteur magnétique...")
    composants['connecteur'] = creer_connecteur_magnetique(params)

    # 8. POSITIONS TRANSDUCTEURS
    print("[8/8] Calcul positions transducteurs...")
    composants['positions_transducteurs'] = generer_positions_transducteurs_amusphere(params)

    total_trans = sum(len(v) for v in composants['positions_transducteurs'].values())
    print(f"       -> {total_trans} transducteurs positionnés")

    print("\n" + "=" * 60)
    print("ASSEMBLAGE AMUSPHERE TERMINÉ")
    print("=" * 60)

    return composants


def creer_document_amusphere(composants, nom="FullDive_AmuSphere"):
    """Crée le document FreeCAD avec style AmuSphere"""

    if not FREECAD_AVAILABLE:
        print("[!] FreeCAD non disponible")
        return None

    doc = FreeCAD.newDocument(nom)

    # Palette de couleurs style AmuSphere (blanc/argent/cyan)
    couleurs = {
        'bandeau': (0.95, 0.95, 0.97),           # Blanc nacré
        'occipital': (0.9, 0.9, 0.92),           # Blanc légèrement gris
        'temporal_gauche': (0.9, 0.9, 0.92),
        'temporal_droit': (0.9, 0.9, 0.92),
        'frontal': (0.85, 0.85, 0.9),            # Légèrement plus sombre
        'led_bandeau': (0.0, 0.9, 1.0),          # Cyan lumineux (SAO)
        'coussinet_occipital': (0.3, 0.3, 0.35), # Gris foncé (mousse)
        'coussinet_frontal': (0.3, 0.3, 0.35),
        'connecteur': (0.6, 0.6, 0.65),          # Argent
    }

    for nom_comp, shape in composants.items():
        if shape is None or nom_comp == 'positions_transducteurs':
            continue

        obj = doc.addObject("Part::Feature", nom_comp)
        obj.Shape = shape

        if nom_comp in couleurs:
            obj.ViewObject.ShapeColor = couleurs[nom_comp]

            # Transparence pour certains éléments
            if 'led' in nom_comp:
                obj.ViewObject.Transparency = 30

    # Visualiser quelques transducteurs
    if 'positions_transducteurs' in composants:
        groupe = doc.addObject("App::DocumentObjectGroup", "Transducteurs_Preview")

        for zone, positions in composants['positions_transducteurs'].items():
            for i, trans in enumerate(positions[:50]):  # 50 par zone max
                pos = trans['pos']
                sphere = Part.makeSphere(2, Vector(pos[0], pos[1], pos[2]))
                obj = doc.addObject("Part::Feature", f"T_{zone}_{i}")
                obj.Shape = sphere
                obj.ViewObject.ShapeColor = (0.0, 0.5, 0.8)
                groupe.addObject(obj)

    doc.recompute()
    print(f"\n[OK] Document '{nom}' créé!")

    return doc


# ============================================================
# MAIN
# ============================================================

def main():
    params = ParametresAmuSphere()

    print("\nSPÉCIFICATIONS AMUSPHERE:")
    print(f"  Bandeau: R={params.BANDEAU_RAYON_INT}-{params.BANDEAU_RAYON_EXT}mm")
    print(f"  Module occipital: {params.OCCIPITAL_LARGEUR}x{params.OCCIPITAL_HAUTEUR}mm")
    print(f"  Modules temporaux: {params.TEMPORAL_LONGUEUR}x{params.TEMPORAL_LARGEUR}mm")
    print(f"  Transducteurs: ~{params.TRANS_NB_OCCIPITAL + 2*params.TRANS_NB_TEMPORAL + params.TRANS_NB_FRONTAL}")

    composants = assembler_amusphere(params)

    if FREECAD_AVAILABLE:
        doc = creer_document_amusphere(composants)
        print("\nModèle AmuSphere prêt dans FreeCAD!")
    else:
        print("\n" + "=" * 60)
        print("MODE APERÇU")
        print("=" * 60)
        print("Ouvrez ce fichier dans FreeCAD pour générer le modèle 3D")

    return composants


if __name__ == "__main__":
    main()
