# NexOS — Vie Artificielle Emergente

## Objectif

NexOS n'est pas une simulation. C'est un projet de **vie artificielle** ou des entites autonomes appelees **ISOs** naissent, apprennent, evoluent et meurent dans un environnement numerique.

Chaque ISO possede :
- Un **cerveau** qui apprend par experience
- Une **memoire** des actions passees
- Des **genes** transmis et mutes a chaque generation
- Des **besoins** (energie, repos, reproduction)

L'objectif : observer l'**emergence** de comportements intelligents a partir de regles simples.

## Architecture

```
NexOS_Project/
  nexos_core/       Moteur : grille spatiale, temps virtuel, config
  nexos_life/       Vie : ISO, cerveau, memoire, genetique, population
  nexos_city/       Construction urbaine (Phase 2)
  nexos_interface/  Interface web Flask + Three.js
  data/             Donnees persistantes
  logs/             Logs systeme
  config.yaml       Configuration globale
  nexos_main.py     Point d'entree
```

## Lancement

```bash
# Installer les dependances
pip install -r requirements.txt

# Lancer le moteur de vie artificielle
python nexos_main.py

# Interface web disponible sur http://127.0.0.1:5000
```

## Philosophie

- **Pas de scripts** : Les ISOs ne suivent pas de scenarios pre-ecrits
- **Apprentissage reel** : Chaque ISO apprend de ses propres experiences
- **Selection naturelle** : Les genes des ISOs les plus adaptes se propagent
- **Emergence** : L'intelligence emerge de la complexite, pas du code
