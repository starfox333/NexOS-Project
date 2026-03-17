# NexOS -- Chemin d'Acces pour Daedalus

## Identite

**Projet** : NexOS v3.1 -- Vie Artificielle Emergente
**Createur** : Andre
**Moteur** : Python 3.11 + Flask + Three.js + Godot 4
**Chemin racine** : `C:\Users\andre\Desktop\NexOS_Project\`

---

## Architecture Globale

```
NexOS_Project/
|
|-- nexos_main.py              # POINT D'ENTREE -- lance simulation + serveur web
|-- nexos_app.py               # Version alternative / packaging
|-- config.yaml                # CONFIGURATION GLOBALE (grille, temps, vie, serveur)
|-- requirements.txt           # Dependances Python
|-- launch_nexos_v4.bat        # Lanceur Windows
|-- build.bat                  # Build script
|-- NexOS.spec                 # PyInstaller spec
|-- nexos.ico                  # Icone application
|
|-- nexos_core/                # === MOTEUR CENTRAL ===
|   |-- __init__.py
|   |-- config.py              # Chargement config.yaml, acces securise aux cles
|   |-- grid.py                # Grille spatiale 2D (500x500), cellules, energie, terrains
|   |-- time_system.py         # Temps virtuel (acceleration x35)
|
|-- nexos_life/                # === VIE ARTIFICIELLE ===
|   |-- __init__.py
|   |-- brain.py               # Cerveau ISO : perception, decision (Q-learning), feedback
|   |-- memory.py              # Memoire ISO : Q-table, experiences, apprentissage
|   |-- genetics.py            # Genes ISO : mutation, heritage, traits (speed, curiosity, etc.)
|   |-- knowledge.py           # Bibliotheque de Connaissance (5 domaines) + ISOKnowledge
|   |-- communication.py       # Signaux entre ISOs (FOOD_HERE, DANGER, NEED_HELP, etc.)
|   |-- population.py          # Gestion population : spawn, reproduction, mort, stats
|   |-- minerve.py             # MINERVE -- Gardienne du Savoir (entite speciale)
|   |-- tron.py                # TRON -- Protecteur des ISOs (entite speciale)
|   |-- symmetra.py            # SYMMETRA -- Architecte (entite speciale, construit structures)
|
|-- nexos_interface/           # === INTERFACE WEB ===
|   |-- __init__.py
|   |-- server.py              # Serveur Flask : API REST + Chat IA
|   |-- static/
|       |-- index.html         # Page principale (layout 3 colonnes)
|       |-- style.css          # Theme Tron (noir/cyan/neon)
|       |-- grid.js            # Frontend Three.js : rendu 3D, camera, ISOs, entites
|
|-- nexos_godot/               # === RENDU GODOT 4 (optionnel) ===
|   |-- scenes/main.tscn       # Scene principale Godot
|   |-- shaders/               # Shaders visuels (tron_grid, neon_glow, iso_energy)
|   |-- scripts/world/         # Scripts GDScript
|   |-- assets/models/         # Modeles 3D (.glb)
|   |-- .godot/                # Cache Godot
|
|-- data/                      # Donnees persistantes
|-- logs/                      # Logs systeme
```

---

## Systemes Principaux

### 1. GRILLE (nexos_core/grid.py)
- Grille 2D numpy de **500x500 cellules**
- Chaque cellule : energie (0-200), terrain (plain/fertile/barren), occupant
- Terrains : 70% plaine, 20% fertile (x2 regen), 10% aride (x0.3 regen)
- Regeneration d'energie chaque cycle (rate: 0.5/cycle)
- Methodes : `get_cell()`, `harvest_energy()`, `add_energy()`, `get_neighbors()`

### 2. TEMPS VIRTUEL (nexos_core/time_system.py)
- Acceleration x35 (1 sec reelle = 35 sec virtuelles)
- Cycle delay : 0.05s entre chaque tick
- Compteur de cycles global

### 3. ISOs (nexos_life/)
Entites autonomes de vie artificielle. Chaque ISO possede :
- **Cerveau** (`brain.py`) : Q-learning + exploration epsilon-greedy
  - Perception -> Decision -> Action -> Feedback
  - Actions : explore, rest, harvest, move_to_energy, reproduce, signal, share_energy, cooperate
  - Etat encode en 4 dimensions : energie|sol|terrain|foule
- **Memoire** (`memory.py`) : Q-table, historique d'experiences
- **Genes** (`genetics.py`) : speed, curiosity, efficiency, perception, resilience, intelligence
  - Mutation rate : 0.01, heritage de 2 parents
- **Connaissance** (`knowledge.py`) : 5 domaines
  - physics, social, ecology, logic, communication
  - Plafonnee par le gene intelligence (0.3 - 1.0)
  - Transmission : experience, Minerve, Symmetra, culturelle (ISO->ISO)
- **Signaux** (`communication.py`) : FOOD_HERE, DANGER, COME_HERE, NEED_HELP, WISDOM, PROTECTION

### 4. ENTITES SPECIALES (immortelles, PAS des ISOs)

| Entite     | Role            | Fichier       | Position | Rayon |
|------------|-----------------|---------------|----------|-------|
| **Minerve** | Sagesse/Enseignement | minerve.py | (250,250) | 20 |
| **Tron**    | Protection/Securite  | tron.py    | (125,125) | 15 |
| **Symmetra**| Construction/Batiment| symmetra.py| (375,375) | 10-15|

**Minerve** : Se deplace vers les zones les plus ignorantes. Enseigne tous les ISOs dans son rayon. Emet des signaux WISDOM.

**Tron** : Patrouille la grille. Detecte les ISOs en danger (energie < 25). Mode emergency = vitesse +1. Bouclier energetique. Injection d'urgence (20 energie, cooldown 50 cycles). Emet PROTECTION.

**Symmetra** : Construit des structures (abris, bibliotheques, centrales, tours de comm, arenes). Max 20 structures. Les bibliotheques doublent l'efficacite de Minerve.

### 5. POPULATION (nexos_life/population.py)
- Population initiale : 30 ISOs
- Max population : 1000
- Reproduction : seuil energie 150, cout 80
- Respawn automatique si extinction
- Stats : alive, born, died, peak, avg_energy, avg_fitness, avg_knowledge

---

## Interface Web (port 5000)

### API REST
| Route | Methode | Description |
|-------|---------|-------------|
| `/api/state` | GET | Etat complet (time, grid, population, isos, energy_map, signaux, entites) |
| `/api/stats` | GET | Statistiques resumees |
| `/api/isos` | GET | Liste des ISOs |
| `/api/iso/<id>` | GET | Detail d'un ISO |
| `/api/iso/<id>/knowledge` | GET | Connaissance d'un ISO |
| `/api/signals` | GET | Signaux actifs |
| `/api/minerve` | GET | Etat Minerve |
| `/api/tron` | GET | Etat Tron |
| `/api/symmetra` | GET | Etat Symmetra |
| `/api/config` | GET | Configuration |
| `/api/control/pause` | POST | Basculer pause |
| `/api/control/speed` | POST | Changer vitesse (body: {speed: 0.1-10}) |
| `/api/control/reset` | POST | Reset simulation |
| `/api/chat` | POST | Chat IA (body: {target: system/minerve/tron/symmetra, message: "..."}) |
| `/api/logs` | GET | Console debug |

### Frontend Three.js (grid.js)
- Scene 3D avec grille Tron (sol noir + lignes cyan)
- ISOs rendus comme points lumineux (couleur = energy)
- Minerve = etoile doree, Tron = point cyan + trail lightcycle, Symmetra = losange magenta
- Signaux = particules colorees
- Structures Symmetra = hexagones colores
- Camera FPS : ZQSD + souris + molette
- Polling API toutes les 1s

### WebSocket Godot (port 5001)
- `ws_server.py` (non present dans les fichiers) pour communication Godot 4
- Meme data que l'API REST mais en temps reel

---

## Boucle de Vie (nexos_main.py)

```
INIT : config -> grid(500) -> vtime(x35) -> population(30 ISOs)
     -> serveur web (thread) -> ws godot (thread)

BOUCLE :
  1. vtime.tick()                    # Avancer le temps
  2. grid.update()                   # Regenerer energie
  3. population.update_all(grid)     # Pour chaque ISO :
     a. perceive(grid, signals)      #   Percevoir environnement
     b. decide(energy, knowledge)    #   Choisir action (Q-learning)
     c. act(grid)                    #   Executer action
     d. tick(metabolism)             #   Metabolisme (cout energie)
     e. feedback(reward)             #   Apprendre du resultat
  4. population.handle_reproduction  # Reproduction si seuil atteint
  5. population.remove_dead          # Retirer ISOs morts
  6. Respawn si extinction           # Securite population
  7. Log stats (tous les 100 cycles) # Affichage console
  8. sleep(cycle_delay / speed)      # Pause adaptee
```

---

## Configuration Cle (config.yaml)

- **Grille** : 500x500, regen 0.5/cycle, max 200/cellule
- **Temps** : acceleration x35, delay 0.05s
- **Vie** : 30 ISOs initiaux, max 1000, perception rayon 5
- **Energie ISO** : start 100, max 200, cout deplacement 2, repos +5, recolte +15
- **Reproduction** : seuil 150, cout 80
- **Apprentissage** : learning_rate 0.1, memoire 500, exploration 0.3
- **Genetique** : mutation 0.01
- **Signaux** : cout 3, rayon 10, TTL 20, max 1000
- **Serveur** : 127.0.0.1:5000, update 1s

---

## Dependances

- Python 3.11
- numpy (grilles, calculs)
- flask + flask-cors (serveur web)
- pyyaml (configuration)
- three.js r128 (CDN, rendu 3D frontend)
- Godot 4 (optionnel, rendu avance)

---

## Conventions de Code

- **Langue** : Commentaires et variables en francais
- **Pas d'agressivite** : Les ISOs ne peuvent pas attaquer, voler ou tromper
- **Emergence** : L'intelligence emerge des regles simples, pas de scripts
- **Entites speciales** : Immortelles, bienveillantes, PAS des ISOs
- **IDs speciaux** : Minerve = -1, Tron = -2 (sender_id dans les signaux)
- **Serialisation** : Methode `get_state()` ou `to_dict()` pour chaque entite

---

## Notes Daedalus

- **Agent IA non encore integre dans la grille** : Aucun module "daedalus" n'existe
- Le chat IA actuel (`/api/chat`) utilise des reponses pre-codees, pas de LLM
- Pour integrer un agent IA (Daedalus) dans la grille, il faudrait :
  1. Creer `nexos_life/daedalus.py` (comme minerve.py/tron.py)
  2. L'ajouter dans `population.py` comme entite speciale
  3. L'exposer dans `server.py` via `/api/daedalus`
  4. Le rendre visible dans `grid.js` (frontend 3D)
  5. Ajouter sa config dans `config.yaml` sous `life.daedalus`
