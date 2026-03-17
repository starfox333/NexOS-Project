extends Node
## WebSocket client -- connecte Godot au backend Python NexOS (port 5001)
## FALLBACK : si WebSocket echoue apres N tentatives, bascule sur HTTP polling (port 5000)

signal state_received(state: Dictionary)
signal chat_response_received(data: Dictionary)
signal connection_changed(connected: bool)
signal terrain_received(terrain_data: Dictionary)

var _terrain_cache: Dictionary = {}  # Terrain statique, recu une fois

@export var server_url: String = "ws://127.0.0.1:5001"
@export var http_url: String = "http://127.0.0.1:5000"
@export var auto_reconnect: bool = true
@export var reconnect_delay: float = 3.0
@export var max_ws_attempts: int = 5  ## Apres N echecs WS, basculer en HTTP

var _ws := WebSocketPeer.new()
var _connected := false
var _reconnect_timer := 0.0
var _was_connected := false
var _ws_attempts := 0
var _use_http_fallback := false

# HTTP fallback
var _http_request: HTTPRequest
var _http_poll_timer := 0.0
var _http_poll_interval := 0.15  # Poll toutes les 150ms
var _http_busy := false


func _ready() -> void:
	# Creer le HTTPRequest pour le fallback
	_http_request = HTTPRequest.new()
	_http_request.name = "HTTPFallback"
	_http_request.timeout = 3.0
	_http_request.request_completed.connect(_on_http_response)
	add_child(_http_request)


func connect_to_server(url: String = "") -> void:
	if url != "":
		server_url = url
	if _use_http_fallback:
		print("[WS] Mode HTTP fallback actif -- poll %s" % http_url)
		return
	# Buffers larges pour recevoir l'etat complet (ISOs + energy_map)
	_ws = WebSocketPeer.new()
	_ws.inbound_buffer_size = 1024 * 1024  # 1 MB
	_ws.outbound_buffer_size = 256 * 1024   # 256 KB
	_ws.max_queued_packets = 64
	var err := _ws.connect_to_url(server_url)
	if err != OK:
		push_error("[WS] Connexion echouee: " + str(err))
		_ws_attempts += 1
		_check_fallback()
		_reconnect_timer = reconnect_delay
	else:
		print("[WS] Tentative %d -- connexion a %s..." % [_ws_attempts + 1, server_url])


func _check_fallback() -> void:
	if _ws_attempts >= max_ws_attempts and not _use_http_fallback:
		print("")
		print("========================================================")
		print("[WS] WebSocket echoue %d fois -- BASCULE EN HTTP POLLING" % _ws_attempts)
		print("[WS] URL: %s/api/state" % http_url)
		print("[WS] Le backend Python tourne-t-il? (python nexos_main.py)")
		print("========================================================")
		print("")
		_use_http_fallback = true


func _process(delta: float) -> void:
	if _use_http_fallback:
		_process_http_fallback(delta)
		return

	_ws.poll()
	var state := _ws.get_ready_state()

	match state:
		WebSocketPeer.STATE_OPEN:
			if not _connected:
				_connected = true
				_was_connected = true
				_ws_attempts = 0
				_reconnect_timer = 0.0
				print("[WS] Connecte au backend NexOS (WebSocket)")
				connection_changed.emit(true)

			# Lire tous les paquets disponibles
			while _ws.get_available_packet_count() > 0:
				var packet := _ws.get_packet()
				var text := packet.get_string_from_utf8()
				var data = JSON.parse_string(text)
				if data is Dictionary:
					_handle_message(data)

		WebSocketPeer.STATE_CLOSING:
			pass

		WebSocketPeer.STATE_CLOSED:
			if _connected:
				_connected = false
				print("[WS] Deconnecte du backend")
				connection_changed.emit(false)

			# Reconnexion auto
			if auto_reconnect:
				_reconnect_timer -= delta
				if _reconnect_timer <= 0.0:
					_ws_attempts += 1
					_check_fallback()
					if not _use_http_fallback:
						_reconnect_timer = reconnect_delay
						connect_to_server()

		WebSocketPeer.STATE_CONNECTING:
			pass


# ================================================================
#  HTTP FALLBACK -- poll /api/state quand WebSocket indisponible
# ================================================================

func _process_http_fallback(delta: float) -> void:
	_http_poll_timer -= delta
	if _http_poll_timer <= 0.0 and not _http_busy:
		_http_poll_timer = _http_poll_interval
		_http_busy = true
		var url := "%s/api/state" % http_url
		var err := _http_request.request(url)
		if err != OK:
			_http_busy = false
			if not _connected:
				# Tenter de revenir en WS
				_reconnect_timer -= delta


func _on_http_response(result: int, response_code: int, headers: PackedStringArray, body: PackedByteArray) -> void:
	_http_busy = false
	if result != HTTPRequest.RESULT_SUCCESS or response_code != 200:
		if _connected:
			_connected = false
			connection_changed.emit(false)
		return

	var text := body.get_string_from_utf8()
	var data = JSON.parse_string(text)
	if data is Dictionary:
		if not _connected:
			_connected = true
			print("[HTTP] Connecte au backend NexOS (HTTP fallback)")
			connection_changed.emit(true)
		_check_terrain(data)
		state_received.emit(data)


# ================================================================
#  MESSAGE HANDLING
# ================================================================

func _handle_message(data: Dictionary) -> void:
	var msg_type: String = data.get("type", "")
	match msg_type:
		"state":
			var state_data = data.get("data", {})
			if state_data is Dictionary:
				_check_terrain(state_data)
				state_received.emit(state_data)
		"chat_response":
			var chat_data = data.get("data", {})
			if chat_data is Dictionary:
				chat_response_received.emit(chat_data)
		"command_ack":
			pass
		"pong":
			pass


func _check_terrain(state_data: Dictionary) -> void:
	"""Extrait et cache le terrain s'il est present dans le state."""
	if _terrain_cache.is_empty() and state_data.has("terrain"):
		var terrain: Dictionary = state_data.get("terrain", {})
		if terrain.has("data") and terrain.get("resolution", 0) > 0:
			_terrain_cache = terrain
			print("[WS] Terrain recu: %dx%d (grid %d)" % [
				terrain.get("resolution", 0),
				terrain.get("resolution", 0),
				terrain.get("grid_size", 0)])
			terrain_received.emit(terrain)


# ---- Envoi de commandes vers Python ----

func send_command(action: String, data: Dictionary = {}) -> void:
	if _use_http_fallback:
		_send_http_command(action, data)
		return
	if not _connected:
		return
	var msg := JSON.stringify({
		"type": "command",
		"action": action,
		"data": data
	})
	_ws.send_text(msg)


func _send_http_command(action: String, data: Dictionary) -> void:
	"""Envoie une commande via HTTP POST en fallback."""
	var url := ""
	match action:
		"pause":
			url = "%s/api/control/pause" % http_url
		"speed":
			url = "%s/api/control/speed" % http_url
		"reset":
			url = "%s/api/control/reset" % http_url
		"chat":
			url = "%s/api/chat" % http_url
		_:
			return
	# On ne peut pas envoyer body facilement avec HTTPRequest,
	# donc on utilise POST simple pour pause/reset
	var http := HTTPRequest.new()
	http.timeout = 2.0
	add_child(http)
	http.request_completed.connect(func(_r, _c, _h, _b): http.queue_free())
	var body_str := JSON.stringify(data) if not data.is_empty() else "{}"
	http.request(url, ["Content-Type: application/json"], HTTPClient.METHOD_POST, body_str)


func send_pause() -> void:
	send_command("pause")


func send_speed(speed: float) -> void:
	send_command("speed", {"speed": speed})


func send_reset() -> void:
	send_command("reset")


func send_chat(target: String, message: String) -> void:
	send_command("chat", {"target": target, "message": message})


func send_ping() -> void:
	if _connected and not _use_http_fallback:
		_ws.send_text(JSON.stringify({"type": "ping"}))


func is_ws_connected() -> bool:
	return _connected
