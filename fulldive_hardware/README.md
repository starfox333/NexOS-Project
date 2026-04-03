# Full-Dive Headset - Modèles 3D Hardware

## Vue d'ensemble

Modèles 3D FreeCAD pour le casque Full-Dive à stimulation corticale directe.

```
┌─────────────────────────────────────────────────────────────┐
│                    CASQUE FULL-DIVE                         │
│                                                             │
│                    ╭───────────────╮                        │
│                   ╱   COQUE (R=140mm)                       │
│                  ╱  ╭─────────────╮ ╲                       │
│                 │  ╱ R3 ÉMISSION  ╲ │  10 000 transducteurs │
│                 │ │  ╭─────────╮  │ │                       │
│                 │ │ │R2 LENTILLE│ │ │  Focalisation         │
│                 │ │ │  ╭─────╮ │ │ │                       │
│                 │ │ │ │ GEL  │ │ │ │  Contact crâne        │
│                 │ │ │ │CRÂNE │ │ │ │                       │
│                 │ │ │  ╰─────╯ │ │ │                       │
│                 │ │  ╰─────────╯  │ │                       │
│                 │  ╲             ╱  │                       │
│                  ╲  ╰───────────╯  ╱                        │
│                   ╲   ÉLECTRONIQUE                          │
│                    ╰───────────────╯                        │
└─────────────────────────────────────────────────────────────┘
```

## Fichiers

| Fichier | Description |
|---------|-------------|
| `fulldive_casque_freecad.py` | Modèle complet du casque |
| `module_transducteur_freecad.py` | Module transducteur unitaire détaillé |

## Installation

### Prérequis
- [FreeCAD 0.20+](https://www.freecad.org/downloads.php)
- Python 3.8+

### Utilisation dans FreeCAD

1. Ouvrir FreeCAD
2. Menu: **Macro > Macros...**
3. Cliquer **Créer** ou naviguer vers le fichier
4. Sélectionner `fulldive_casque_freecad.py`
5. Cliquer **Exécuter**

### Utilisation en ligne de commande

```bash
# Lancer FreeCAD avec le script
freecad fulldive_casque_freecad.py

# Ou en mode console
freecadcmd fulldive_casque_freecad.py
```

## Spécifications Techniques

### Dimensions du Casque

| Composant | Rayon (mm) | Épaisseur (mm) |
|-----------|-----------|----------------|
| Coque externe | 140 | 3 |
| R3 Émission | 120 | 15 |
| R2 Focalisation | 100 | 8 |
| Gel contact | 90 | 10 |

### Module Transducteur

```
    ┌───────────────────┐
    │   LED RGB Ø2mm    │  ← Calibration
    ├───────────────────┤
    │  Perforation Ø3mm │  ← Fenêtre acoustique
    ├───────────────────┤
    │  ┌───┐    ┌───┐  │
    │  │ A │    │ B │  │  ← Réseau piézo 2×2
    │  └───┘    └───┘  │    (déflexion ±15°)
    │  ┌───┐    ┌───┐  │
    │  │ C │    │ D │  │
    │  └───┘    └───┘  │
    ├───────────────────┤
    │  Circuit ASIC     │  ← Contrôle local
    ├───────────────────┤
    │  ○ ○ ○ ○ ○ ○     │  ← 6 pins connecteur
    └───────────────────┘
         Ø 8mm
```

### Paramètres Ajustables

Dans `fulldive_casque_freecad.py`, modifier la classe `ParametresCasque`:

```python
class ParametresCasque:
    COQUE_RAYON = 140.0           # Ajuster selon morphologie
    R3_ANGLE_COUVERTURE = 120.0   # Zone occipitale couverte
    TRANSDUCTEUR_NB_TOTAL = 10000 # Résolution de stimulation
```

## Export

### STL (pour impression 3D)
```python
# Dans FreeCAD après exécution du script
import Mesh
Mesh.export([doc.getObject("coque_externe")], "coque.stl")
```

### STEP (pour CAO)
```python
import Part
Part.export([doc.getObject("coque_externe")], "coque.step")
```

## Architecture des Couches

```
Extérieur → Intérieur

1. COQUE EXTERNE (ABS/Carbone)
   Protection mécanique, esthétique

2. COURONNE ÉLECTRONIQUE (PCB + FPGA)
   Traitement signal, alimentation

3. DEMI-SPHÈRE R3 - ÉMISSION (Céramique PZT)
   10 000 transducteurs orientables
   Génération ultrasons 500kHz

4. DEMI-SPHÈRE R2 - FOCALISATION (PDMS/Silicone)
   Lentille acoustique Fresnel
   Focalisation sur V1

5. COUSSIN GEL (Hydrogel)
   Couplage acoustique
   Confort utilisateur

6. CRÂNE + CORTEX V1
   Cible de stimulation
```

## Licence

Ce projet est fourni à des fins de recherche et d'éducation.
