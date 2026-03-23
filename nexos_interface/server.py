"""
NexOS -- Serveur Flask pour l'interface web
API REST : etat, ISOs, controles, chat IA, debug.
"""

import os
import random
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

_STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
_MODELS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'modèle de construction pour symmetra'
)

_grid = None
_vtime = None
_population = None
_config = None
_control = None


def create_app(config, grid, vtime, population, control=None):
    global _grid, _vtime, _population, _config, _control
    _grid = grid
    _vtime = vtime
    _population = population
    _config = config
    _control = control

    app = Flask(__name__, static_folder=_STATIC_DIR)
    CORS(app)

    # --- Routes statiques ---
    @app.route('/')
    def index():
        return send_from_directory(_STATIC_DIR, 'index.html')

    @app.route('/style.css')
    def style():
        return send_from_directory(_STATIC_DIR, 'style.css')

    @app.route('/grid.js')
    def grid_js():
        return send_from_directory(_STATIC_DIR, 'grid.js')

    @app.route('/models/<path:filename>')
    def serve_model(filename):
        """Sert les modeles 3D GLB pour le frontend Three.js."""
        return send_from_directory(_MODELS_DIR, filename)

    # --- API REST : Etat ---
    @app.route('/api/state')
    def api_state():
        state = {}
        try:
            state['time'] = _vtime.get_state()
        except Exception:
            state['time'] = {'cycles': 0, 'virtual_formatted': '??:??'}
        try:
            state['grid'] = _grid.get_stats()
        except Exception:
            state['grid'] = {}
        try:
            state['physics'] = _grid.get_physics_state()
        except Exception:
            state['physics'] = {}
        try:
            state['population'] = _population.get_stats()
        except Exception:
            state['population'] = {'alive': 0}
        try:
            state['isos'] = _population.get_isos_data()
        except Exception:
            state['isos'] = []
        try:
            state['energy_map'] = _grid.get_energy_map()
        except Exception:
            state['energy_map'] = []
        try:
            if _population.signal_board:
                state['signals'] = _population.signal_board.get_all_signals()
        except Exception:
            pass
        try:
            if _population.minerve:
                state['minerve'] = _population.minerve.get_state()
        except Exception:
            pass
        try:
            if _population.tron:
                state['tron'] = _population.tron.get_state()
        except Exception:
            pass
        try:
            if _population.symmetra:
                state['symmetra'] = _population.symmetra.get_state()
        except Exception:
            pass
        try:
            if hasattr(_population, 'daedalus') and _population.daedalus:
                state['daedalus'] = _population.daedalus.get_state()
        except Exception:
            pass
        # Controles
        if _control:
            state['control'] = {
                'paused': _control.paused,
                'speed': _control.speed,
            }
        return jsonify(state)

    @app.route('/api/stats')
    def api_stats():
        return jsonify({
            'time': _vtime.get_state(),
            'grid': _grid.get_stats(),
            'population': _population.get_stats()
        })

    @app.route('/api/isos')
    def api_isos():
        return jsonify(_population.get_isos_data())

    @app.route('/api/iso/<int:iso_id>')
    def api_iso(iso_id):
        for iso in _population.isos:
            if iso.id == iso_id:
                return jsonify(iso.to_dict())
        return jsonify({'error': 'ISO not found'}), 404

    @app.route('/api/iso/<int:iso_id>/knowledge')
    def api_iso_knowledge(iso_id):
        for iso in _population.isos:
            if iso.id == iso_id:
                return jsonify(iso.knowledge.to_dict())
        return jsonify({'error': 'ISO not found'}), 404

    @app.route('/api/signals')
    def api_signals():
        if _population.signal_board:
            return jsonify({
                'signals': _population.signal_board.get_all_signals(),
                'stats': _population.signal_board.get_stats()
            })
        return jsonify({'signals': [], 'stats': {}})

    @app.route('/api/minerve')
    def api_minerve():
        if _population.minerve:
            return jsonify(_population.minerve.get_state())
        return jsonify({'enabled': False})

    @app.route('/api/tron')
    def api_tron():
        if _population.tron:
            return jsonify(_population.tron.get_state())
        return jsonify({'enabled': False})

    @app.route('/api/symmetra')
    def api_symmetra():
        if _population.symmetra:
            return jsonify(_population.symmetra.get_state())
        return jsonify({'enabled': False})

    @app.route('/api/daedalus')
    def api_daedalus():
        if _population.daedalus:
            return jsonify(_population.daedalus.get_state())
        return jsonify({'enabled': False})

    @app.route('/api/config')
    def api_config():
        return jsonify(_config)

    # --- API : Controles ---
    @app.route('/api/control/pause', methods=['POST'])
    def api_pause():
        if _control:
            _control.paused = not _control.paused
            _control.log(f"{'PAUSE' if _control.paused else 'PLAY'}", 'warn')
            return jsonify({'paused': _control.paused})
        return jsonify({'error': 'No control'}), 500

    @app.route('/api/control/speed', methods=['POST'])
    def api_speed():
        if _control:
            data = request.get_json(silent=True) or {}
            _control.speed = max(0.1, min(10.0, float(data.get('speed', 1.0))))
            _control.log(f"Vitesse: x{_control.speed}", 'info')
            return jsonify({'speed': _control.speed})
        return jsonify({'error': 'No control'}), 500

    @app.route('/api/control/reset', methods=['POST'])
    def api_reset():
        if _control:
            _control.reset_requested = True
            return jsonify({'ok': True})
        return jsonify({'error': 'No control'}), 500

    @app.route('/api/control/save', methods=['POST'])
    def api_save():
        """Sauvegarde manuelle de la simulation."""
        try:
            from nexos_core.save_manager import save_state
            ok = save_state(_grid, _vtime, _population, _config)
            if ok:
                return jsonify({'ok': True, 'message': 'Sauvegarde reussie'})
            return jsonify({'ok': False, 'error': 'Echec sauvegarde'}), 500
        except Exception as e:
            return jsonify({'ok': False, 'error': str(e)}), 500

    # --- API : Console Debug ---
    @app.route('/api/logs')
    def api_logs():
        if _control:
            return jsonify(_control.logs[-50:])
        return jsonify([])

    # --- API : Chat IA ---
    @app.route('/api/chat', methods=['POST'])
    def api_chat():
        data = request.get_json(silent=True) or {}
        target = data.get('target', 'system')  # minerve, symmetra, tron, system
        msg = data.get('message', '').lower().strip()

        if not msg:
            return jsonify({'response': '...'})

        response = _generate_chat_response(target, msg)
        if _control:
            _control.log(f"Chat [{target}]: {msg[:50]}", 'info')
        return jsonify({'response': response, 'target': target})

    return app


def _generate_chat_response(target, msg):
    """Genere une reponse contextuelle basee sur l'etat reel de la simulation."""
    stats = _population.get_stats()
    alive = stats.get('alive', 0)
    avg_k = stats.get('avg_knowledge', 0)
    gen = stats.get('max_generation', 0)
    cycles = _vtime.get_cycles()

    if target == 'minerve':
        m = _population.minerve
        if not m:
            return "Minerve n'est pas active."
        s = m.get_state()
        responses = [
            f"Je suis Minerve, gardienne du savoir. J'enseigne actuellement a {s['current_students']} ISOs.",
            f"La connaissance moyenne de la population est de {avg_k:.2f}. {'Ils progressent bien.' if avg_k > 0.3 else 'Il y a encore beaucoup a apprendre.'}",
            f"Depuis mon eveil, j'ai enseigne {s['total_taught']} fois et transmis {s['total_knowledge_given']:.0f} unites de savoir.",
            f"Je me trouve en position ({s['x']}, {s['z']}), guidant les ISOs vers la sagesse.",
            f"Les 5 domaines du savoir -- physique, social, ecologie, logique, communication -- sont les piliers de l'intelligence ISO.",
        ]
        if 'connaissance' in msg or 'savoir' in msg or 'knowledge' in msg:
            return f"La connaissance moyenne est de {avg_k:.3f} sur 5 domaines. Les ISOs les plus intelligents atteignent des niveaux remarquables."
        if 'eleve' in msg or 'etudiant' in msg or 'student' in msg:
            return f"J'ai {s['current_students']} eleves autour de moi en ce moment. Mon rayon d'enseignement est de {s['teaching_radius']} unites."
        if 'biblio' in msg or 'library' in msg:
            in_lib = "Oui, j'enseigne depuis une bibliotheque ! Mon efficacite est doublee." if s['teaching_rate'] > m._base_teaching_rate else "Je ne suis pas dans une bibliotheque en ce moment. Si Symmetra en construit une, j'y enseignerai avec une efficacite doublee."
            return in_lib
        return random.choice(responses)

    elif target == 'symmetra':
        sym = _population.symmetra
        if not sym:
            return "Symmetra n'est pas active."
        s = sym.get_state()
        builds = s.get('builds_by_type', {})
        total = s['total_built']
        active = s['active_structures']
        mx = s['max_shelters']

        # Detail des types construits
        details = []
        for t, count in builds.items():
            if count > 0:
                from nexos_life.symmetra import STRUCTURE_TYPES
                name = STRUCTURE_TYPES.get(t, {}).get('name', t)
                details.append(f"{count} {name}")
        detail_str = ', '.join(details) if details else 'rien encore'

        responses = [
            f"Je suis Symmetra, architecte de la grille. J'ai construit {total} structures : {detail_str}.",
            f"Actuellement {active}/{mx} structures actives. Je batis selon les besoins : abris, bibliotheques, centrales, tours, arenes.",
            f"J'enseigne la construction a {s['current_students']} ISOs. Les plus doues reparent mes structures.",
            f"Chaque structure a un role : les BIBLIO boostent le savoir, les CENTRALES regenerent l'energie, les ARENES ameliorent le fitness.",
            f"Je me trouve en ({s['x']}, {s['z']}), en mode {s['mode']}. Mon objectif : une cite prospere pour les ISOs.",
        ]
        if 'abri' in msg or 'shelter' in msg:
            n_shelters = builds.get('shelter', 0)
            return f"J'ai construit {n_shelters} abris. Ils protegent les ISOs et leur donnent un bonus d'energie."
        if 'biblio' in msg or 'library' in msg or 'livre' in msg:
            n_lib = builds.get('library', 0)
            return f"J'ai construit {n_lib} bibliotheques. Quand Minerve y enseigne, son efficacite double ! Les ISOs y apprennent 2.5x plus vite."
        if 'central' in msg or 'energie' in msg or 'energy' in msg:
            n_plant = builds.get('energy_plant', 0)
            return f"J'ai construit {n_plant} centrales d'energie. Elles regenerent l'energie des cellules environnantes."
        if 'tour' in msg or 'comm' in msg or 'signal' in msg:
            n_tower = builds.get('comm_tower', 0)
            return f"J'ai construit {n_tower} tours de communication. Elles amplifient la portee des signaux ISO."
        if 'arene' in msg or 'arena' in msg or 'fitness' in msg:
            n_arena = builds.get('arena', 0)
            return f"J'ai construit {n_arena} arenes. Les ISOs y ameliorent leur resilience et leur efficacite."
        if 'construi' in msg or 'batiment' in msg or 'structure' in msg:
            return f"J'ai construit {total} structures au total : {detail_str}. {active} sont actives sur {mx} possibles."
        return random.choice(responses)

    elif target == 'tron':
        t = _population.tron
        if not t:
            return "Tron n'est pas actif."
        s = t.get_state()
        responses = [
            f"Je suis Tron, protecteur des ISOs. Mode actuel : {s['mode'].upper()}. {s['current_protected']} ISOs sous ma protection.",
            f"J'ai sauve {s['total_saved']} ISOs de la mort et injecte {s['total_energy_given']:.0f} unites d'energie d'urgence.",
            f"Ma mission : qu'aucun ISO ne meurt si je peux l'empecher. Je patrouille la grille sans relache.",
            f"Bouclier actif -- je reduis le cout metabolique des ISOs proches de {s['shield_factor']*100:.0f}%.",
            f"Position ({s['x']}, {s['z']}). {s['current_emergencies']} urgences detectees.",
        ]
        if 'proteg' in msg or 'sauv' in msg or 'danger' in msg:
            return f"J'ai {s['current_emergencies']} urgences en cours. {s['current_protected']} ISOs proteges. Total sauves : {s['total_saved']}."
        return random.choice(responses)

    elif target == 'daedalus':
        d = _population.daedalus
        if not d:
            return "Daedalus n'est pas actif."
        s = d.get_state()
        responses = [
            f"Je suis Daedalus, catalyseur d'innovation. J'inspire actuellement {s['current_seekers']} ISOs a explorer et creer.",
            f"J'ai inspire {s['total_inspired']} ISOs et pose {s['total_questions_asked']} questions qui stimulent la reflexion.",
            f"Je ne transmets pas le savoir -- je catalyse l'innovation en encourageant l'exploration et l'experimentation.",
            f"Je me trouve en ({s['x']}, {s['z']}), me deplacant vers les zones les plus stagnantes pour y semer les graines de changement.",
            f"Mon rayon d'influence : {s['influence_radius']} unites. Les ISOs proches gagnent en curiosite et en tendance a l'exploration.",
        ]
        if 'explor' in msg or 'curieux' in msg or 'curiosity' in msg or 'innov' in msg:
            return f"J'ai inspire {s['total_inspired']} ISOs a explorer. La curiosite est la base de l'innovation. Les ISOs les plus curieux font les plus belles decouvertes."
        if 'question' in msg or 'penser' in msg or 'think' in msg:
            return f"J'ai pose {s['total_questions_asked']} questions pour stimuler la reflexion. Chaque question ouvre de nouvelles possibilites."
        if 'pos' in msg or 'position' in msg or 'ou' in msg:
            return f"Je suis en ({s['x']}, {s['z']}), a la recherche des zones d'ignorance pour y apporter le changement."
        return random.choice(responses)

    else:  # system
        responses = [
            f"NexOS v3.1 -- {alive} ISOs actifs, generation {gen}, cycle {cycles}.",
            f"Population: {alive} vivants, {stats.get('total_born',0)} nes, {stats.get('total_died',0)} morts.",
            f"Energie moyenne: {stats.get('avg_energy',0):.0f}, Fitness: {stats.get('avg_fitness',0):.1f}.",
            f"Grille {_grid.size}x{_grid.size}. Connaissance moy: {avg_k:.3f}. Intelligence moy: {stats.get('avg_intelligence',0):.3f}.",
        ]
        if 'stat' in msg or 'status' in msg or 'etat' in msg:
            return f"Cycle {cycles} | {alive} ISOs | Gen {gen} | Energie {stats.get('avg_energy',0):.0f} | Connaissance {avg_k:.3f}"
        if 'population' in msg or 'iso' in msg:
            return f"{alive} ISOs vivants. {stats.get('total_born',0)} nes au total. Record: {stats.get('peak',0)}."
        return random.choice(responses)


def start_server(app, config):
    host = config.get('server', {}).get('host', '127.0.0.1')
    port = config.get('server', {}).get('port', 5000)
    app.run(host=host, port=port, debug=False, use_reloader=False)
