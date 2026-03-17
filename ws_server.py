"""
NexOS v4 -- Serveur WebSocket pour communication avec Godot 4
Port 5001 : push d'etat temps-reel + reception de commandes
"""

import asyncio
import json
import threading
import traceback

try:
    import websockets
    import websockets.server
    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False
    print("  [WS] Module 'websockets' non trouve. pip install websockets")


class NexOSWebSocket:
    """Serveur WebSocket pour le client Godot 4."""

    def __init__(self):
        self.clients = set()
        self._grid = None
        self._vtime = None
        self._population = None
        self._config = None
        self._control = None
        self._loop = None
        self._chat_handler = None  # Fonction de chat depuis server.py
        self._broadcast_count = 0  # Compteur pour envoyer energy_map moins souvent
        self._terrain_cache = None  # Cache terrain (statique, envoye une fois)

    def configure(self, config, grid, vtime, population, control, chat_handler=None):
        self._config = config
        self._grid = grid
        self._vtime = vtime
        self._population = population
        self._control = control
        self._chat_handler = chat_handler

    # ------------------------------------------------------------------
    #  Gestion des connexions
    # ------------------------------------------------------------------

    async def _handler(self, websocket):
        """Gere une connexion WebSocket entrante."""
        self.clients.add(websocket)
        remote = websocket.remote_address
        print(f"  [WS] Client connecte : {remote}")
        if self._control:
            self._control.log(f"Godot connecte ({remote[0]}:{remote[1]})", "info")
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self._handle_message(data, websocket)
                except json.JSONDecodeError:
                    pass
                except Exception as e:
                    print(f"  [WS] Erreur message : {e}")
        except Exception:
            pass
        finally:
            self.clients.discard(websocket)
            print(f"  [WS] Client deconnecte : {remote}")

    # ------------------------------------------------------------------
    #  Traitement des commandes du client
    # ------------------------------------------------------------------

    async def _handle_message(self, data, ws):
        msg_type = data.get('type', '')

        if msg_type == 'command':
            action = data.get('action', '')
            payload = data.get('data', {})

            if action == 'pause':
                if self._control:
                    self._control.paused = not self._control.paused
                    self._control.log(
                        f"{'PAUSE' if self._control.paused else 'PLAY'} (Godot)", 'warn')
                    await ws.send(json.dumps({
                        'type': 'command_ack',
                        'action': 'pause',
                        'paused': self._control.paused
                    }))

            elif action == 'speed':
                if self._control:
                    speed = float(payload.get('speed', 1.0))
                    self._control.speed = max(0.1, min(10.0, speed))
                    self._control.log(f"Vitesse: x{self._control.speed} (Godot)", 'info')
                    await ws.send(json.dumps({
                        'type': 'command_ack',
                        'action': 'speed',
                        'speed': self._control.speed
                    }))

            elif action == 'reset':
                if self._control:
                    self._control.reset_requested = True
                    self._control.log("RESET demande (Godot)", 'warn')

            elif action == 'select_iso':
                iso_id = int(payload.get('id', 0))
                iso_data = None
                if self._population:
                    iso_obj = self._population._iso_by_id.get(iso_id)
                    if iso_obj and iso_obj.alive:
                        iso_data = iso_obj.to_dict()
                await ws.send(json.dumps({
                    'type': 'iso_detail',
                    'data': iso_data
                }))

            elif action == 'place_structure':
                stype = payload.get('structure_type', 'shelter')
                sx = int(payload.get('x', 0))
                sz = int(payload.get('z', 0))
                if self._population and self._population.symmetra:
                    self._population.symmetra.force_build(sx, sz, stype)
                    await ws.send(json.dumps({
                        'type': 'command_ack',
                        'action': 'place_structure',
                        'success': True
                    }))

            elif action == 'chat':
                target = payload.get('target', 'system')
                message = payload.get('message', '')
                response = self._process_chat(target, message)
                await ws.send(json.dumps({
                    'type': 'chat_response',
                    'target': target,
                    'data': response
                }))

        elif msg_type == 'ping':
            await ws.send(json.dumps({'type': 'pong'}))

    def _process_chat(self, target, message):
        """Traite un message de chat (delegue a server.py si possible)."""
        if self._chat_handler:
            try:
                return self._chat_handler(target, message)
            except Exception as e:
                return {'response': f'Erreur chat: {e}'}

        # Fallback basique
        return {'response': f'[{target}] Message recu.', 'target': target}

    # ------------------------------------------------------------------
    #  Construction de l'etat JSON
    # ------------------------------------------------------------------

    def _get_iso_light(self, iso):
        """Version allegee de to_dict() pour le WebSocket -- pas de brain/knowledge details."""
        try:
            return {
                'id': iso.id,
                'x': iso.x, 'z': iso.z,
                'energy': round(iso.energy, 1),
                'max_energy': iso.max_energy,
                'age': iso.age,
                'generation': iso.generation,
                'alive': iso.alive,
                'last_action': iso.last_action,
                'needs': {k: round(v, 1) for k, v in iso.needs.items()} if hasattr(iso, 'needs') else {},
                'mood': round(iso.mood, 1) if hasattr(iso, 'mood') else 0,
                'mood_label': iso.mood_label if hasattr(iso, 'mood_label') else 'neutral',
            }
        except Exception:
            return {'id': getattr(iso, 'id', 0), 'x': 0, 'z': 0, 'energy': 0}

    def _get_state(self, include_energy_map: bool = True):
        """Construit le dictionnaire d'etat pour Godot.
        Version allegee : ISOs light (pas de brain/knowledge), energy_map optionnel.
        Chaque section protegee individuellement."""
        state = {}
        try:
            state['time'] = self._vtime.get_state() if self._vtime else {
                'cycles': 0, 'virtual_formatted': '??:??', 'acceleration': 0}
        except Exception as e:
            state['time'] = {'cycles': 0, 'virtual_formatted': 'ERR', 'error': str(e)}

        try:
            state['grid'] = self._grid.get_stats() if self._grid else {}
        except Exception as e:
            state['grid'] = {'error': str(e)}

        try:
            state['population'] = self._population.get_stats() if self._population else {}
        except Exception as e:
            state['population'] = {'alive': 0, 'error': str(e)}

        # ISOs -- version allegee (sans brain stats ni knowledge details)
        try:
            if self._population:
                state['isos'] = [self._get_iso_light(iso) for iso in self._population.isos if iso.alive]
            else:
                state['isos'] = []
        except Exception as e:
            state['isos'] = []
            print(f"  [WS] Erreur isos: {e}")

        # Energy map -- seulement tous les N broadcasts (downsample 50 pour WS)
        if include_energy_map:
            try:
                state['energy_map'] = self._grid.get_energy_map(downsample=50) if self._grid else []
            except Exception:
                state['energy_map'] = []
        else:
            state['energy_map'] = []

        # Signaux -- max 100
        try:
            if self._population and self._population.signal_board:
                all_signals = self._population.signal_board.get_all_signals()
                state['signals'] = all_signals[:100]  # Limiter
        except Exception:
            pass

        # Entites speciales -- chacune protegee
        try:
            if self._population and self._population.minerve:
                state['minerve'] = self._population.minerve.get_state()
        except Exception as e:
            print(f"  [WS] Erreur minerve.get_state: {e}")

        try:
            if self._population and self._population.tron:
                state['tron'] = self._population.tron.get_state()
        except Exception as e:
            print(f"  [WS] Erreur tron.get_state: {e}")

        try:
            if self._population and self._population.symmetra:
                state['symmetra'] = self._population.symmetra.get_state()
        except Exception as e:
            print(f"  [WS] Erreur symmetra.get_state: {e}")

        try:
            if self._population and hasattr(self._population, 'daedalus') and self._population.daedalus:
                state['daedalus'] = self._population.daedalus.get_state()
        except Exception as e:
            print(f"  [WS] Erreur daedalus.get_state: {e}")

        try:
            if self._population and hasattr(self._population, 'vehicle_manager') and self._population.vehicle_manager:
                state['vehicles'] = self._population.vehicle_manager.get_all_states()
        except Exception:
            pass

        # Terrain (statique -- envoye au premier broadcast puis cache)
        if self._broadcast_count <= 1:
            try:
                if self._terrain_cache is None and self._grid:
                    self._terrain_cache = self._grid.get_terrain_map(downsample=50)
                    print(f"  [WS] Terrain cache: res={self._terrain_cache.get('resolution')}x{self._terrain_cache.get('resolution')}")
                if self._terrain_cache:
                    state['terrain'] = self._terrain_cache
            except Exception as e:
                print(f"  [WS] Erreur terrain_map: {e}")

        # Controle
        if self._control:
            state['control'] = {
                'paused': self._control.paused,
                'speed': self._control.speed,
            }

        return state

    # ------------------------------------------------------------------
    #  Boucle de broadcast
    # ------------------------------------------------------------------

    async def _broadcast_loop(self):
        """Envoie l'etat a tous les clients toutes les 200ms (5 fps).
        Energy map envoyee seulement 1 fois sur 5 (toutes les ~1s)."""
        while True:
            if self.clients and self._vtime:
                try:
                    self._broadcast_count += 1
                    # Energy map seulement 1x/s (tous les 5 broadcasts)
                    include_map = (self._broadcast_count % 5 == 0)
                    state = self._get_state(include_energy_map=include_map)
                    message = json.dumps(state)  # PAS de wrapper {type, data}
                    # Debug taille une fois
                    if self._broadcast_count == 1:
                        size_kb = len(message) / 1024
                        iso_count = len(state.get('isos', []))
                        map_count = len(state.get('energy_map', []))
                        print(f"  [WS] Premier broadcast: {size_kb:.1f} KB, {iso_count} ISOs, {map_count} energy points")
                    # Envoyer en tant que {type: state, data: ...}
                    full_msg = json.dumps({'type': 'state', 'data': state})
                    dead = set()
                    for client in self.clients.copy():
                        try:
                            await client.send(full_msg)
                        except Exception:
                            dead.add(client)
                    self.clients -= dead
                except Exception as e:
                    if self._broadcast_count <= 3:
                        print(f"  [WS] Erreur broadcast: {e}")
                        import traceback
                        traceback.print_exc()
            await asyncio.sleep(0.2)  # 5 fps au lieu de 10 -- plus stable

    # ------------------------------------------------------------------
    #  Demarrage du serveur
    # ------------------------------------------------------------------

    async def _run_server(self, host, port):
        async with websockets.server.serve(
            self._handler, host, port,
            compression=None,
            ping_interval=20,
            ping_timeout=40,
            max_size=2 * 1024 * 1024,      # 2 MB max (state allege)
            write_limit=2 ** 18,            # 256 KB write buffer
        ):
            print(f"  [WS] Serveur demarre : ws://{host}:{port}")
            await self._broadcast_loop()

    def start(self, host='127.0.0.1', port=5001):
        """Demarre le serveur WebSocket dans un thread separe."""
        if not HAS_WEBSOCKETS:
            print("  [WS] Impossible de demarrer -- module websockets manquant")
            return

        def _run():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._loop = loop
            try:
                loop.run_until_complete(self._run_server(host, port))
            except Exception as e:
                print(f"  [WS] Erreur serveur: {e}")
                traceback.print_exc()

        thread = threading.Thread(target=_run, daemon=True, name='NexOS-WS')
        thread.start()
        return thread


# Instance singleton
ws_server = NexOSWebSocket()
