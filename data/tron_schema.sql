-- =============================================================================
-- NexOS -- BASE DE DONNEES TRON GRID
-- Schema inspire de l'univers du film Tron (1982 / Legacy 2010)
--
-- "I fight for the Users." -- Tron
--
-- Terminologie :
--   THE_GRID      = le monde numerique (simulation)
--   PROGRAMS      = les ISOs (algorithmes isomorphiques)
--   IDENTITY_DISCS= memoires/connaissances des programmes
--   GUARDIANS     = entites speciales immortelles
--   LIGHT_TRAILS  = historique de deplacements (sillons de lightcycle)
--   SIGNAL_BEACONS= communications entre programmes
--   STRUCTURES    = constructions de Symmetra
--   ENERGY_SECTORS= carte energetique du Grid par secteur
--   DEREZZED_LOG  = archive des programmes morts (de-rezzes)
--   RECOGNITION_EVENTS = journal des evenements marquants
--   POPULATION_STATS   = statistiques periodiques de la population
-- =============================================================================

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;
PRAGMA encoding = 'UTF-8';

-- =============================================================================
-- THE_GRID : sessions de simulation (le monde lui-meme)
-- Chaque simulation = une instance du Grid
-- =============================================================================
CREATE TABLE IF NOT EXISTS THE_GRID (
    grid_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    session_name  TEXT    NOT NULL DEFAULT 'NexOS_Grid',
    grid_size     INTEGER NOT NULL DEFAULT 200,
    status        TEXT    NOT NULL DEFAULT 'ACTIVE'   -- ACTIVE | SUSPENDED | ARCHIVED
                          CHECK (status IN ('ACTIVE', 'SUSPENDED', 'ARCHIVED')),
    created_at    DATETIME DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now')),
    last_active   DATETIME DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now'))
);

-- =============================================================================
-- CYCLES : unite de temps virtuelle du Grid (comme les cycles Tron)
-- Sauvegarde periodique de l'etat temporel
-- =============================================================================
CREATE TABLE IF NOT EXISTS CYCLES (
    cycle_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    grid_id        INTEGER NOT NULL REFERENCES THE_GRID(grid_id) ON DELETE CASCADE,
    cycle_number   INTEGER NOT NULL,
    virtual_time   REAL    NOT NULL DEFAULT 0.0,   -- secondes de temps virtuel
    real_time      REAL    NOT NULL DEFAULT 0.0,   -- secondes de temps reel
    speed_factor   REAL    NOT NULL DEFAULT 35.0,  -- acceleration (x35 par defaut)
    recorded_at    DATETIME DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now')),
    UNIQUE (grid_id, cycle_number)
);

CREATE INDEX IF NOT EXISTS idx_cycles_grid ON CYCLES (grid_id, cycle_number DESC);

-- =============================================================================
-- PROGRAMS : ISOs (Algorithmes Isomorphiques)
-- Les entites vivantes du Grid -- "les programmes qui ont emerge naturellement"
-- =============================================================================
CREATE TABLE IF NOT EXISTS PROGRAMS (
    program_id     INTEGER PRIMARY KEY,            -- = ISO.id
    grid_id        INTEGER NOT NULL REFERENCES THE_GRID(grid_id) ON DELETE CASCADE,
    designation    TEXT    NOT NULL DEFAULT 'ISO', -- ISO | RECOM | EVOLVED
    pos_x          INTEGER NOT NULL,
    pos_z          INTEGER NOT NULL,
    energy_level   REAL    NOT NULL DEFAULT 100.0,
    max_energy     REAL    NOT NULL DEFAULT 200.0,
    status         TEXT    NOT NULL DEFAULT 'ACTIVE'
                           CHECK (status IN ('ACTIVE', 'DEREZZED', 'DORMANT')),
    -- Identite
    generation     INTEGER NOT NULL DEFAULT 0,
    age            INTEGER NOT NULL DEFAULT 0,
    children_count INTEGER NOT NULL DEFAULT 0,
    mood           REAL    NOT NULL DEFAULT 50.0,
    -- Genome (codex genetique)
    gene_speed         REAL NOT NULL DEFAULT 1.0,
    gene_curiosity     REAL NOT NULL DEFAULT 1.0,
    gene_efficiency    REAL NOT NULL DEFAULT 1.0,
    gene_perception    REAL NOT NULL DEFAULT 1.0,
    gene_resilience    REAL NOT NULL DEFAULT 1.0,
    gene_intelligence  REAL NOT NULL DEFAULT 0.5,
    -- Statistiques de vie
    total_harvested    REAL NOT NULL DEFAULT 0.0,
    distance_traveled  REAL NOT NULL DEFAULT 0.0,
    -- Filiation (lignee)
    parent_alpha_id    INTEGER REFERENCES PROGRAMS(program_id),  -- parent 1
    parent_beta_id     INTEGER REFERENCES PROGRAMS(program_id),  -- parent 2
    -- Horodatages
    compiled_at        DATETIME DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now')),  -- naissance
    derezzed_at        DATETIME,                                                   -- mort
    last_cycle         INTEGER  NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_programs_grid   ON PROGRAMS (grid_id, status);
CREATE INDEX IF NOT EXISTS idx_programs_pos    ON PROGRAMS (pos_x, pos_z);
CREATE INDEX IF NOT EXISTS idx_programs_parent ON PROGRAMS (parent_alpha_id, parent_beta_id);

-- =============================================================================
-- IDENTITY_DISCS : memoires et connaissances des programmes
-- "Ton disque est ta vie" -- CLU
-- Chaque programme possede un disque unique contenant son savoir et sa Q-table
-- =============================================================================
CREATE TABLE IF NOT EXISTS IDENTITY_DISCS (
    disc_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    program_id     INTEGER NOT NULL REFERENCES PROGRAMS(program_id) ON DELETE CASCADE,
    -- Domaines de connaissance (0.0 - 1.0)
    know_physics       REAL NOT NULL DEFAULT 0.0,
    know_social        REAL NOT NULL DEFAULT 0.0,
    know_ecology       REAL NOT NULL DEFAULT 0.0,
    know_logic         REAL NOT NULL DEFAULT 0.0,
    know_communication REAL NOT NULL DEFAULT 0.0,
    -- Q-table compresse (JSON -- entrees les plus significatives)
    q_table_json   TEXT,
    -- Besoins (systeme de besoins Sims-like)
    need_hunger    REAL NOT NULL DEFAULT 80.0,
    need_social    REAL NOT NULL DEFAULT 70.0,
    need_fun       REAL NOT NULL DEFAULT 60.0,
    need_comfort   REAL NOT NULL DEFAULT 75.0,
    need_hygiene   REAL NOT NULL DEFAULT 85.0,
    -- Metadata
    last_updated   DATETIME DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now')),
    cycle_recorded INTEGER NOT NULL DEFAULT 0,
    UNIQUE (program_id)  -- un seul disque par programme
);

CREATE INDEX IF NOT EXISTS idx_discs_program ON IDENTITY_DISCS (program_id);

-- =============================================================================
-- GUARDIANS : entites speciales immortelles du Grid
-- TRON = Protecteur | MINERVE = Sage | SYMMETRA = Architecte | DAEDALUS = Navigateur
-- =============================================================================
CREATE TABLE IF NOT EXISTS GUARDIANS (
    guardian_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    grid_id        INTEGER NOT NULL REFERENCES THE_GRID(grid_id) ON DELETE CASCADE,
    name           TEXT    NOT NULL,       -- TRON | MINERVE | SYMMETRA | DAEDALUS
    designation    TEXT    NOT NULL,       -- PROTECTOR | SAGE | ARCHITECT | NAVIGATOR
    pos_x          INTEGER NOT NULL,
    pos_z          INTEGER NOT NULL,
    mode           TEXT    NOT NULL DEFAULT 'PATROL',
    enabled        INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
    cycles_active  INTEGER NOT NULL DEFAULT 0,
    -- Statistiques specifiques (JSON flexible)
    stats_json     TEXT,
    last_updated   DATETIME DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now')),
    UNIQUE (grid_id, name)
);

-- =============================================================================
-- LIGHT_TRAILS : sillons de deplacement (comme les trails de lightcycle)
-- Historique de positions pour chaque entite (programmes + gardiens)
-- =============================================================================
CREATE TABLE IF NOT EXISTS LIGHT_TRAILS (
    trail_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id     INTEGER NOT NULL,   -- program_id ou guardian_id
    entity_type   TEXT    NOT NULL    -- PROGRAM | GUARDIAN
                          CHECK (entity_type IN ('PROGRAM', 'GUARDIAN')),
    pos_x         INTEGER NOT NULL,
    pos_z         INTEGER NOT NULL,
    cycle_number  INTEGER NOT NULL,
    action        TEXT,               -- action executee a cette position
    energy_level  REAL,               -- energie au moment du deplacement
    recorded_at   DATETIME DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_trails_entity ON LIGHT_TRAILS (entity_id, entity_type, cycle_number DESC);
CREATE INDEX IF NOT EXISTS idx_trails_cycle  ON LIGHT_TRAILS (cycle_number);

-- =============================================================================
-- SIGNAL_BEACONS : phares de communication entre programmes
-- Types : FOOD_HERE | DANGER | COME_HERE | NEED_HELP | WISDOM | PROTECTION
-- =============================================================================
CREATE TABLE IF NOT EXISTS SIGNAL_BEACONS (
    beacon_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    grid_id        INTEGER NOT NULL REFERENCES THE_GRID(grid_id) ON DELETE CASCADE,
    -- Emetteur : -1=MINERVE, -2=TRON, -3=SYMMETRA, -4=DAEDALUS, >0=ISO
    sender_id      INTEGER NOT NULL,
    signal_type    TEXT    NOT NULL
                           CHECK (signal_type IN (
                               'FOOD_HERE', 'DANGER', 'COME_HERE',
                               'NEED_HELP', 'WISDOM', 'PROTECTION',
                               'BUILD_HERE', 'EXPLORE'
                           )),
    pos_x          INTEGER NOT NULL,
    pos_z          INTEGER NOT NULL,
    radius         INTEGER NOT NULL DEFAULT 10,
    intensity      REAL    NOT NULL DEFAULT 1.0,
    ttl            INTEGER NOT NULL DEFAULT 20,   -- time-to-live en cycles
    cycle_emitted  INTEGER NOT NULL,
    cycle_expired  INTEGER,
    recorded_at    DATETIME DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_beacons_grid   ON SIGNAL_BEACONS (grid_id, cycle_emitted DESC);
CREATE INDEX IF NOT EXISTS idx_beacons_type   ON SIGNAL_BEACONS (signal_type);
CREATE INDEX IF NOT EXISTS idx_beacons_sender ON SIGNAL_BEACONS (sender_id);

-- =============================================================================
-- STRUCTURES : batiments construits par Symmetra l'Architecte
-- shelter | library | power_plant | comm_tower | arena | hex_monolith
-- =============================================================================
CREATE TABLE IF NOT EXISTS STRUCTURES (
    structure_id   INTEGER PRIMARY KEY,           -- = Structure.id
    grid_id        INTEGER NOT NULL REFERENCES THE_GRID(grid_id) ON DELETE CASCADE,
    structure_type TEXT    NOT NULL,
    pos_x          INTEGER NOT NULL,
    pos_z          INTEGER NOT NULL,
    radius         INTEGER NOT NULL DEFAULT 8,
    durability     REAL    NOT NULL DEFAULT 100.0,
    level          INTEGER NOT NULL DEFAULT 1,
    age            INTEGER NOT NULL DEFAULT 0,
    total_usage    INTEGER NOT NULL DEFAULT 0,
    built_at_cycle INTEGER NOT NULL DEFAULT 0,
    built_at       DATETIME DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now')),
    demolished_at  DATETIME
);

CREATE INDEX IF NOT EXISTS idx_structures_grid ON STRUCTURES (grid_id, structure_type);
CREATE INDEX IF NOT EXISTS idx_structures_pos  ON STRUCTURES (pos_x, pos_z);

-- =============================================================================
-- ENERGY_SECTORS : instantanes periodiques de la carte d'energie
-- Le Grid divise en secteurs (10x10 par defaut) pour suivre la repartition
-- =============================================================================
CREATE TABLE IF NOT EXISTS ENERGY_SECTORS (
    snapshot_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    grid_id       INTEGER NOT NULL REFERENCES THE_GRID(grid_id) ON DELETE CASCADE,
    cycle_number  INTEGER NOT NULL,
    sector_x      INTEGER NOT NULL,  -- coordonnee de secteur (pas de cellule)
    sector_z      INTEGER NOT NULL,
    avg_energy    REAL    NOT NULL DEFAULT 0.0,
    max_energy    REAL    NOT NULL DEFAULT 0.0,
    min_energy    REAL    NOT NULL DEFAULT 0.0,
    terrain_type  TEXT    NOT NULL DEFAULT 'plain'
                          CHECK (terrain_type IN ('plain', 'fertile', 'barren', 'mixed')),
    iso_count     INTEGER NOT NULL DEFAULT 0,
    recorded_at   DATETIME DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_sectors_grid  ON ENERGY_SECTORS (grid_id, cycle_number DESC);
CREATE INDEX IF NOT EXISTS idx_sectors_coord ON ENERGY_SECTORS (sector_x, sector_z);

-- =============================================================================
-- DEREZZED_LOG : archive des programmes morts (de-rezzes)
-- Conserver toute l'histoire de vie d'un programme apres sa mort
-- =============================================================================
CREATE TABLE IF NOT EXISTS DEREZZED_LOG (
    log_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    program_id       INTEGER NOT NULL,
    grid_id          INTEGER REFERENCES THE_GRID(grid_id),
    derez_cause      TEXT    NOT NULL DEFAULT 'starvation'
                             CHECK (derez_cause IN ('starvation', 'old_age', 'energy_drain', 'unknown')),
    derez_cycle      INTEGER,
    -- Position finale
    final_pos_x      INTEGER,
    final_pos_z      INTEGER,
    -- Stats finales
    final_energy     REAL,
    final_age        INTEGER,
    generation       INTEGER,
    children_count   INTEGER,
    total_harvested  REAL,
    distance_traveled REAL,
    -- Connaissance finale
    know_physics       REAL,
    know_social        REAL,
    know_ecology       REAL,
    know_logic         REAL,
    know_communication REAL,
    -- Genome final
    gene_speed         REAL,
    gene_curiosity     REAL,
    gene_efficiency    REAL,
    gene_perception    REAL,
    gene_resilience    REAL,
    gene_intelligence  REAL,
    -- Horodatage
    derezzed_at      DATETIME DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_derez_grid  ON DEREZZED_LOG (grid_id, derez_cycle DESC);
CREATE INDEX IF NOT EXISTS idx_derez_cause ON DEREZZED_LOG (derez_cause);

-- =============================================================================
-- RECOGNITION_EVENTS : journal des evenements importants du Grid
-- Comme les "Recognizers" du film -- detectent et enregistrent les anomalies
-- =============================================================================
CREATE TABLE IF NOT EXISTS RECOGNITION_EVENTS (
    event_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    grid_id       INTEGER REFERENCES THE_GRID(grid_id) ON DELETE CASCADE,
    cycle_number  INTEGER NOT NULL,
    event_type    TEXT    NOT NULL
                          CHECK (event_type IN (
                              'BIRTH', 'DEATH', 'REPRODUCTION',
                              'STRUCTURE_BUILT', 'STRUCTURE_DEMOLISHED',
                              'GUARDIAN_ACTION', 'KNOWLEDGE_PEAK',
                              'POPULATION_MILESTONE', 'EXTINCTION_RISK',
                              'ENERGY_CRISIS', 'EVOLUTION_LEAP',
                              'SIGNAL_CASCADE', 'SIMULATION_START',
                              'SIMULATION_PAUSE', 'SIMULATION_RESET'
                          )),
    entity_id     INTEGER,   -- ISO id, guardian id, structure id...
    entity_type   TEXT,      -- PROGRAM | GUARDIAN | STRUCTURE | SIMULATION
    description   TEXT,
    data_json     TEXT,      -- donnees supplementaires (JSON)
    recorded_at   DATETIME DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_events_grid ON RECOGNITION_EVENTS (grid_id, cycle_number DESC);
CREATE INDEX IF NOT EXISTS idx_events_type ON RECOGNITION_EVENTS (event_type);

-- =============================================================================
-- POPULATION_STATS : instantanes periodiques des statistiques de population
-- Sauvegarde toutes les N cycles pour visualiser l'evolution
-- =============================================================================
CREATE TABLE IF NOT EXISTS POPULATION_STATS (
    stat_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    grid_id          INTEGER NOT NULL REFERENCES THE_GRID(grid_id) ON DELETE CASCADE,
    cycle_number     INTEGER NOT NULL,
    alive_count      INTEGER NOT NULL DEFAULT 0,
    total_born       INTEGER NOT NULL DEFAULT 0,
    total_died       INTEGER NOT NULL DEFAULT 0,
    peak_population  INTEGER NOT NULL DEFAULT 0,
    avg_energy       REAL    NOT NULL DEFAULT 0.0,
    avg_age          REAL    NOT NULL DEFAULT 0.0,
    avg_generation   REAL    NOT NULL DEFAULT 0.0,
    avg_fitness      REAL    NOT NULL DEFAULT 0.0,
    avg_knowledge    REAL    NOT NULL DEFAULT 0.0,
    structure_count  INTEGER NOT NULL DEFAULT 0,
    recorded_at      DATETIME DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now')),
    UNIQUE (grid_id, cycle_number)
);

CREATE INDEX IF NOT EXISTS idx_stats_grid ON POPULATION_STATS (grid_id, cycle_number DESC);

-- =============================================================================
-- VUES ANALYTIQUES
-- "Regarde le Grid, il te dira tout." -- Rinzler
-- =============================================================================

-- Vue : programmes actifs avec leurs connaissances
CREATE VIEW IF NOT EXISTS v_active_programs AS
SELECT
    p.program_id,
    p.designation,
    p.pos_x,
    p.pos_z,
    p.energy_level,
    p.generation,
    p.age,
    p.gene_speed,
    p.gene_intelligence,
    COALESCE(d.know_physics, 0) + COALESCE(d.know_social, 0) +
    COALESCE(d.know_ecology, 0) + COALESCE(d.know_logic, 0) +
    COALESCE(d.know_communication, 0) AS total_knowledge,
    p.last_cycle
FROM PROGRAMS p
LEFT JOIN IDENTITY_DISCS d ON p.program_id = d.program_id
WHERE p.status = 'ACTIVE';

-- Vue : derniere position des gardiens
CREATE VIEW IF NOT EXISTS v_guardians_status AS
SELECT
    g.name,
    g.designation,
    g.pos_x,
    g.pos_z,
    g.mode,
    g.enabled,
    g.cycles_active,
    g.stats_json
FROM GUARDIANS g;

-- Vue : top 10 ISOs les plus savants
CREATE VIEW IF NOT EXISTS v_knowledge_elite AS
SELECT
    p.program_id,
    p.generation,
    p.age,
    p.energy_level,
    d.know_physics,
    d.know_social,
    d.know_ecology,
    d.know_logic,
    d.know_communication,
    (d.know_physics + d.know_social + d.know_ecology +
     d.know_logic + d.know_communication) / 5.0 AS avg_knowledge
FROM PROGRAMS p
JOIN IDENTITY_DISCS d ON p.program_id = d.program_id
WHERE p.status = 'ACTIVE'
ORDER BY avg_knowledge DESC
LIMIT 10;

-- Vue : evolution de la population (derniers 100 snapshots)
CREATE VIEW IF NOT EXISTS v_population_history AS
SELECT
    cycle_number,
    alive_count,
    total_born,
    total_died,
    avg_energy,
    avg_knowledge,
    structure_count
FROM POPULATION_STATS
ORDER BY cycle_number DESC
LIMIT 100;

-- Vue : signaux recents (derniers 50 cycles)
CREATE VIEW IF NOT EXISTS v_recent_signals AS
SELECT
    b.beacon_id,
    b.sender_id,
    b.signal_type,
    b.pos_x,
    b.pos_z,
    b.radius,
    b.intensity,
    b.cycle_emitted,
    b.ttl
FROM SIGNAL_BEACONS b
ORDER BY b.cycle_emitted DESC
LIMIT 200;

-- Vue : statistiques de de-rez par cause
CREATE VIEW IF NOT EXISTS v_derez_stats AS
SELECT
    derez_cause,
    COUNT(*)            AS total_derezed,
    AVG(final_age)      AS avg_age_at_death,
    AVG(final_energy)   AS avg_energy_at_death,
    AVG(children_count) AS avg_children
FROM DEREZZED_LOG
GROUP BY derez_cause;

-- =============================================================================
-- FIN DU SCHEMA
-- "End of line." -- MCP
-- =============================================================================
