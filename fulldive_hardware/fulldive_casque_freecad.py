#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================================
# FULL-DIVE HEADSET - MODÈLE 3D FREECAD
# Casque de réalité virtuelle à stimulation corticale directe
# ============================================================
# Usage dans FreeCAD:
#   1. Ouvrir FreeCAD
#   2. Menu: Macro > Macros...
#   3. Sélectionner ce fichier et exécuter
#
# Ou en ligne de commande:
#   freecad -c fulldive_casque_freecad.py
# ============================================================

import math

# Essayer d'importer FreeCAD, sinon mode standalone pour test
try:
    import FreeCAD
    import Part
    from FreeCAD import Base, Vector
    FREECAD_AVAILABLE = True
except ImportError:
    print("FreeCAD non disponible - Mode aperçu uniquement")
    FREECAD_AVAILABLE = False


# ============================================================
# PARAMÈTRES DU CASQUE (tous en mm)
# ============================================================

class ParametresCasque:
    """Paramètres configurables du casque Full-Dive"""

    # Dimensions globales
    RAYON_TETE = 95.0              # Rayon moyen tête humaine
    RAYON_CRANE_OCCIPITAL = 85.0  # Rayon zone occipitale

    # Coque externe
    COQUE_RAYON = 140.0           # Rayon externe du casque
    COQUE_EPAISSEUR = 3.0         # Épaisseur coque

    # Demi-sphère R3 (Émission - transducteurs)
    R3_RAYON = 120.0              # Rayon demi-sphère émission
    R3_EPAISSEUR = 15.0           # Épaisseur (inclut électronique)
    R3_ANGLE_COUVERTURE = 120.0   # Angle de couverture (degrés)

    # Demi-sphère R2 (Focalisation - lentille acoustique)
    R2_RAYON = 100.0              # Rayon lentille
    R2_EPAISSEUR = 8.0            # Épaisseur lentille

    # Coussin gel (contact crâne)
    GEL_RAYON = 90.0              # Rayon interne
    GEL_EPAISSEUR = 10.0          # Épaisseur gel

    # Transducteurs
    TRANSDUCTEUR_DIAMETRE = 8.0   # Diamètre d'un module
    TRANSDUCTEUR_NB_TOTAL = 10000 # Nombre total visé
    TRANSDUCTEUR_ESPACEMENT = 9.5 # Espacement entre centres

    # Perforations (fenêtres acoustiques)
    PERFORATION_DIAMETRE = 3.0    # Diamètre des trous

    # Électronique (couronne)
    ELECTRONIQUE_HAUTEUR = 30.0   # Hauteur de la couronne
    ELECTRONIQUE_EPAISSEUR = 15.0 # Épaisseur

    # Sangle
    SANGLE_LARGEUR = 25.0         # Largeur sangle
    SANGLE_EPAISSEUR = 3.0        # Épaisseur


# ============================================================
# FONCTIONS DE CRÉATION DES COMPOSANTS
# ============================================================

def creer_demi_sphere(rayon, epaisseur, angle_deg=180, nom="DemiSphere"):
    """
    Crée une demi-sphère creuse (coque sphérique)

    Args:
        rayon: Rayon extérieur
        epaisseur: Épaisseur de la paroi
        angle_deg: Angle d'ouverture (180 = demi-sphère complète)
        nom: Nom de l'objet

    Returns:
        Part.Shape ou None
    """
    if not FREECAD_AVAILABLE:
        print(f"[APERÇU] Demi-sphère: R={rayon}mm, ép={epaisseur}mm, angle={angle_deg}°")
        return None

    # Sphère externe
    sphere_ext = Part.makeSphere(rayon)

    # Sphère interne (pour creuser)
    sphere_int = Part.makeSphere(rayon - epaisseur)

    # Soustraire pour obtenir la coque
    coque = sphere_ext.cut(sphere_int)

    # Couper pour obtenir la demi-sphère (partie inférieure)
    # On garde la partie Z < 0 pour l'arrière de la tête
    if angle_deg < 180:
        # Calculer la hauteur de coupe
        angle_rad = math.radians(angle_deg / 2)
        z_coupe = -rayon * math.cos(angle_rad)

        # Boîte de coupe
        boite = Part.makeBox(
            rayon * 3, rayon * 3, rayon * 2,
            Vector(-rayon * 1.5, -rayon * 1.5, z_coupe)
        )
        coque = coque.common(boite)
    else:
        # Demi-sphère standard (Z < 0)
        boite = Part.makeBox(
            rayon * 3, rayon * 3, rayon,
            Vector(-rayon * 1.5, -rayon * 1.5, -rayon)
        )
        coque = coque.common(boite)

    return coque


def creer_reseau_transducteurs(rayon, nb_points, diametre, angle_couverture=120):
    """
    Crée le réseau de transducteurs sur une demi-sphère
    Distribution de Fibonacci pour uniformité

    Args:
        rayon: Rayon de la sphère
        nb_points: Nombre de transducteurs
        diametre: Diamètre de chaque transducteur
        angle_couverture: Angle de couverture en degrés

    Returns:
        Liste de positions (x, y, z) et normales
    """
    positions = []
    golden_ratio = (1 + math.sqrt(5)) / 2
    angle_max = math.radians(angle_couverture / 2)

    # Distribution de Fibonacci sur la sphère
    for i in range(nb_points):
        # Latitude (theta) - distribution uniforme en cos(theta)
        theta = math.acos(1 - 2 * (i + 0.5) / nb_points)

        # Limiter à l'angle de couverture (zone occipitale)
        if theta > angle_max:
            continue

        # Longitude (phi) - spirale dorée
        phi = 2 * math.pi * i / golden_ratio

        # Coordonnées cartésiennes
        x = rayon * math.sin(theta) * math.cos(phi)
        y = rayon * math.sin(theta) * math.sin(phi)
        z = -rayon * math.cos(theta)  # Négatif pour l'arrière

        # Normale (pointe vers le centre)
        nx, ny, nz = -x/rayon, -y/rayon, -z/rayon

        positions.append({
            'pos': (x, y, z),
            'normal': (nx, ny, nz),
            'index': i
        })

    return positions


def creer_perforations(coque, positions, diametre):
    """
    Crée les perforations (fenêtres acoustiques) dans la coque

    Args:
        coque: Shape de la coque à perforer
        positions: Liste des positions de transducteurs
        diametre: Diamètre des perforations

    Returns:
        Part.Shape avec perforations
    """
    if not FREECAD_AVAILABLE:
        print(f"[APERÇU] Perforations: {len(positions)} trous de Ø{diametre}mm")
        return None

    resultat = coque

    for i, trans in enumerate(positions):
        if i % 500 == 0:
            print(f"  Perforation {i}/{len(positions)}...")

        pos = trans['pos']
        normal = trans['normal']

        # Créer un cylindre orienté selon la normale
        cylindre = Part.makeCylinder(
            diametre / 2,  # rayon
            50,  # longueur (traverse la coque)
            Vector(pos[0] + normal[0] * 25,
                   pos[1] + normal[1] * 25,
                   pos[2] + normal[2] * 25),
            Vector(-normal[0], -normal[1], -normal[2])
        )

        # Soustraire le cylindre
        try:
            resultat = resultat.cut(cylindre)
        except:
            pass  # Ignorer les erreurs de géométrie

    return resultat


def creer_couronne_electronique(rayon_int, rayon_ext, hauteur, position_z):
    """
    Crée la couronne contenant l'électronique (FPGA, alimentation)

    Args:
        rayon_int: Rayon intérieur
        rayon_ext: Rayon extérieur
        hauteur: Hauteur de la couronne
        position_z: Position Z du bas de la couronne

    Returns:
        Part.Shape
    """
    if not FREECAD_AVAILABLE:
        print(f"[APERÇU] Couronne électronique: Rint={rayon_int}mm, Rext={rayon_ext}mm, H={hauteur}mm")
        return None

    # Cylindre externe
    cyl_ext = Part.makeCylinder(rayon_ext, hauteur, Vector(0, 0, position_z))

    # Cylindre interne (pour creuser)
    cyl_int = Part.makeCylinder(rayon_int, hauteur + 2, Vector(0, 0, position_z - 1))

    # Soustraire
    couronne = cyl_ext.cut(cyl_int)

    return couronne


def creer_supports_sangle(rayon, largeur, epaisseur):
    """
    Crée les supports pour la sangle de maintien

    Args:
        rayon: Rayon du casque
        largeur: Largeur des supports
        epaisseur: Épaisseur

    Returns:
        Part.Shape
    """
    if not FREECAD_AVAILABLE:
        print(f"[APERÇU] Supports sangle: largeur={largeur}mm")
        return None

    supports = []

    # Support gauche
    support_g = Part.makeBox(
        epaisseur, largeur, 40,
        Vector(-rayon - epaisseur, -largeur/2, -20)
    )
    supports.append(support_g)

    # Support droit
    support_d = Part.makeBox(
        epaisseur, largeur, 40,
        Vector(rayon, -largeur/2, -20)
    )
    supports.append(support_d)

    # Support arrière (haut)
    support_arr = Part.makeBox(
        largeur, epaisseur, 40,
        Vector(-largeur/2, rayon, -20)
    )
    supports.append(support_arr)

    # Fusionner tous les supports
    resultat = supports[0]
    for s in supports[1:]:
        resultat = resultat.fuse(s)

    return resultat


def creer_connecteur_arriere(position, largeur=40, hauteur=20, profondeur=15):
    """
    Crée le connecteur arrière (alimentation + données)

    Returns:
        Part.Shape
    """
    if not FREECAD_AVAILABLE:
        print(f"[APERÇU] Connecteur arrière: {largeur}x{hauteur}x{profondeur}mm")
        return None

    # Boîtier du connecteur
    boitier = Part.makeBox(
        largeur, profondeur, hauteur,
        Vector(-largeur/2, position - profondeur, -hauteur/2)
    )

    # Arrondir les bords (chanfrein simple)
    # Note: FreeCAD permet des opérations plus complexes

    return boitier


# ============================================================
# ASSEMBLAGE COMPLET DU CASQUE
# ============================================================

def assembler_casque_complet(params=None, simplifier=False, nb_transducteurs=500):
    """
    Assemble tous les composants du casque Full-Dive

    Args:
        params: ParametresCasque ou None pour défaut
        simplifier: Si True, réduit le nombre de détails
        nb_transducteurs: Nombre de transducteurs (réduit pour test)

    Returns:
        dict avec tous les composants Part.Shape
    """
    if params is None:
        params = ParametresCasque()

    print("=" * 60)
    print("ASSEMBLAGE CASQUE FULL-DIVE")
    print("=" * 60)

    composants = {}

    # 1. COQUE EXTERNE
    print("\n[1/7] Création coque externe...")
    composants['coque_externe'] = creer_demi_sphere(
        params.COQUE_RAYON,
        params.COQUE_EPAISSEUR,
        angle_deg=150,
        nom="Coque_Externe"
    )

    # 2. DEMI-SPHÈRE R3 (Émission)
    print("[2/7] Création demi-sphère R3 (transducteurs)...")
    composants['r3_emission'] = creer_demi_sphere(
        params.R3_RAYON,
        params.R3_EPAISSEUR,
        angle_deg=params.R3_ANGLE_COUVERTURE,
        nom="R3_Emission"
    )

    # 3. RÉSEAU DE TRANSDUCTEURS
    print(f"[3/7] Calcul positions transducteurs ({nb_transducteurs})...")
    positions_trans = creer_reseau_transducteurs(
        params.R3_RAYON - params.R3_EPAISSEUR / 2,
        nb_transducteurs,
        params.TRANSDUCTEUR_DIAMETRE,
        params.R3_ANGLE_COUVERTURE
    )
    composants['positions_transducteurs'] = positions_trans
    print(f"       -> {len(positions_trans)} transducteurs positionnés")

    # 4. PERFORATIONS (optionnel, long à calculer)
    if not simplifier and FREECAD_AVAILABLE and composants['r3_emission']:
        print("[4/7] Création perforations (peut être long)...")
        # Limiter le nombre pour le test
        positions_limitees = positions_trans[:min(200, len(positions_trans))]
        composants['r3_perfore'] = creer_perforations(
            composants['r3_emission'],
            positions_limitees,
            params.PERFORATION_DIAMETRE
        )
    else:
        print("[4/7] Perforations ignorées (mode simplifié)")
        composants['r3_perfore'] = composants['r3_emission']

    # 5. DEMI-SPHÈRE R2 (Focalisation)
    print("[5/7] Création demi-sphère R2 (lentille)...")
    composants['r2_focalisation'] = creer_demi_sphere(
        params.R2_RAYON,
        params.R2_EPAISSEUR,
        angle_deg=params.R3_ANGLE_COUVERTURE - 10,
        nom="R2_Focalisation"
    )

    # 6. COURONNE ÉLECTRONIQUE
    print("[6/7] Création couronne électronique...")
    composants['electronique'] = creer_couronne_electronique(
        params.R3_RAYON - 5,
        params.COQUE_RAYON,
        params.ELECTRONIQUE_HAUTEUR,
        -10  # Position Z
    )

    # 7. SUPPORTS ET CONNECTEUR
    print("[7/7] Création supports et connecteur...")
    composants['supports_sangle'] = creer_supports_sangle(
        params.COQUE_RAYON,
        params.SANGLE_LARGEUR,
        params.SANGLE_EPAISSEUR
    )
    composants['connecteur'] = creer_connecteur_arriere(
        params.COQUE_RAYON + 5
    )

    print("\n" + "=" * 60)
    print("ASSEMBLAGE TERMINÉ")
    print("=" * 60)

    return composants


# ============================================================
# CRÉATION DU DOCUMENT FREECAD
# ============================================================

def creer_document_freecad(composants, nom_doc="FullDive_Casque"):
    """
    Crée un document FreeCAD avec tous les composants

    Args:
        composants: dict retourné par assembler_casque_complet()
        nom_doc: Nom du document

    Returns:
        FreeCAD.Document
    """
    if not FREECAD_AVAILABLE:
        print("\n[!] FreeCAD non disponible - Export impossible")
        print("    Exécutez ce script dans FreeCAD pour générer le modèle 3D")
        return None

    # Créer le document
    doc = FreeCAD.newDocument(nom_doc)

    # Couleurs pour chaque composant
    couleurs = {
        'coque_externe': (0.2, 0.2, 0.2),      # Gris foncé
        'r3_emission': (0.0, 0.5, 0.8),        # Bleu
        'r3_perfore': (0.0, 0.5, 0.8),         # Bleu
        'r2_focalisation': (0.8, 0.6, 0.0),    # Orange
        'electronique': (0.0, 0.8, 0.0),       # Vert
        'supports_sangle': (0.3, 0.3, 0.3),    # Gris
        'connecteur': (0.1, 0.1, 0.1),         # Noir
    }

    # Ajouter chaque composant au document
    for nom, shape in composants.items():
        if shape is None:
            continue
        if nom == 'positions_transducteurs':
            continue  # Pas une shape

        # Créer l'objet
        obj = doc.addObject("Part::Feature", nom)
        obj.Shape = shape

        # Appliquer la couleur
        if nom in couleurs:
            obj.ViewObject.ShapeColor = couleurs[nom]

    # Ajouter des sphères pour visualiser les transducteurs
    if 'positions_transducteurs' in composants:
        print("Ajout visualisation transducteurs...")
        groupe = doc.addObject("App::DocumentObjectGroup", "Transducteurs")

        for i, trans in enumerate(composants['positions_transducteurs'][:100]):  # Limiter
            pos = trans['pos']
            sphere = Part.makeSphere(2, Vector(pos[0], pos[1], pos[2]))
            obj = doc.addObject("Part::Feature", f"Trans_{i}")
            obj.Shape = sphere
            obj.ViewObject.ShapeColor = (1.0, 0.0, 0.0)  # Rouge
            groupe.addObject(obj)

    # Recalculer
    doc.recompute()

    print(f"\nDocument '{nom_doc}' créé avec succès!")

    return doc


def exporter_stl(doc, chemin="fulldive_casque.stl"):
    """
    Exporte le modèle au format STL

    Args:
        doc: Document FreeCAD
        chemin: Chemin du fichier de sortie
    """
    if not FREECAD_AVAILABLE:
        print(f"[!] Export STL impossible sans FreeCAD")
        return

    import Mesh

    # Fusionner toutes les shapes
    shapes = []
    for obj in doc.Objects:
        if hasattr(obj, 'Shape'):
            shapes.append(obj.Shape)

    if shapes:
        fusion = shapes[0]
        for s in shapes[1:]:
            try:
                fusion = fusion.fuse(s)
            except:
                pass

        # Convertir en mesh et exporter
        mesh = Mesh.Mesh(fusion.tessellate(1))
        mesh.write(chemin)
        print(f"Exporté: {chemin}")


# ============================================================
# FONCTION PRINCIPALE
# ============================================================

def main():
    """Point d'entrée principal"""

    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║   FULL-DIVE HEADSET - MODÈLE 3D                          ║
    ║   Casque de Réalité Virtuelle                            ║
    ║   à Stimulation Corticale Directe                        ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """)

    # Paramètres
    params = ParametresCasque()

    print("PARAMÈTRES DU CASQUE:")
    print(f"  - Rayon coque externe:    {params.COQUE_RAYON} mm")
    print(f"  - Rayon R3 (émission):    {params.R3_RAYON} mm")
    print(f"  - Rayon R2 (lentille):    {params.R2_RAYON} mm")
    print(f"  - Transducteurs visés:    {params.TRANSDUCTEUR_NB_TOTAL}")
    print(f"  - Diamètre transducteur:  {params.TRANSDUCTEUR_DIAMETRE} mm")
    print(f"  - Angle couverture:       {params.R3_ANGLE_COUVERTURE}°")

    # Assembler le casque
    # Mode simplifié pour test (moins de transducteurs)
    composants = assembler_casque_complet(
        params,
        simplifier=True,  # True pour test rapide
        nb_transducteurs=500  # Réduit pour test
    )

    # Créer le document FreeCAD
    if FREECAD_AVAILABLE:
        doc = creer_document_freecad(composants)

        # Exporter en STL
        # exporter_stl(doc, "fulldive_casque.stl")

        print("\n[OK] Modèle prêt dans FreeCAD!")
        print("     Utilisez Fichier > Exporter pour sauvegarder")
    else:
        print("\n" + "=" * 60)
        print("MODE APERÇU (FreeCAD non disponible)")
        print("=" * 60)
        print(f"Transducteurs calculés: {len(composants['positions_transducteurs'])}")
        print("\nPour générer le modèle 3D:")
        print("  1. Installer FreeCAD: https://www.freecad.org/")
        print("  2. Ouvrir FreeCAD")
        print("  3. Macro > Macros > Sélectionner ce fichier")
        print("  4. Exécuter")

    return composants


# ============================================================
# EXÉCUTION
# ============================================================

if __name__ == "__main__":
    composants = main()
