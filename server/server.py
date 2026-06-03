"""Pure Python server for Poker Starej Kuncery.

Dependencies: websockets (pure Python, no C extensions)
Everything else is stdlib.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Any

import websockets
from websockets.server import ServerConnection

from .game.models import Figure, FigureType, GameConfig, Rank, Suit
from .game.room import Room, RoomManager, RoomStatus
from .game.engine import GameEngine

logger = logging.getLogger("poker")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_MESSAGE_SIZE = 4096
PLAYER_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_\-\s]{1,20}$")
ROOM_CODE_PATTERN = re.compile(r"^[A-Z0-9]{6}$")
IDLE_CLEANUP_INTERVAL = 30  # check every 30s, rooms expire after 2min with no players

_FIGURE_TYPE_MAP: dict[str, FigureType] = {
    "high_card": FigureType.HIGH_CARD,
    "pair": FigureType.PAIR,
    "two_pairs": FigureType.TWO_PAIRS,
    "straight": FigureType.STRAIGHT,
    "three_of_kind": FigureType.THREE_OF_KIND,
    "full_house": FigureType.FULL_HOUSE,
    "flush": FigureType.FLUSH,
    "four_of_kind": FigureType.FOUR_OF_KIND,
    "straight_flush": FigureType.STRAIGHT_FLUSH,
}

_SUIT_LAST_TYPES: set[FigureType] = {FigureType.FLUSH, FigureType.STRAIGHT_FLUSH}

# ---------------------------------------------------------------------------
# Globals
# ---------------------------------------------------------------------------

room_manager = RoomManager()
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

# ---------------------------------------------------------------------------
# Figure deserialization
# ---------------------------------------------------------------------------

def _deserialize_figure(data: dict) -> Figure:
    fig_type_str = data.get("type")
    if not isinstance(fig_type_str, str) or fig_type_str not in _FIGURE_TYPE_MAP:
        raise ValueError(f"Unknown figure type: {fig_type_str}")

    fig_type = _FIGURE_TYPE_MAP[fig_type_str]

    raw_params = data.get("params")
    if not isinstance(raw_params, list):
        raise ValueError("Figure params must be a list")

    converted: list[Rank | Suit] = []
    for i, val in enumerate(raw_params):
        if not isinstance(val, int):
            raise ValueError(f"Param at index {i} must be an integer")
        is_last = i == len(raw_params) - 1
        if is_last and fig_type in _SUIT_LAST_TYPES:
            try:
                converted.append(Suit(val))
            except ValueError:
                raise ValueError(f"Invalid suit value: {val}")
        else:
            try:
                converted.append(Rank(val))
            except ValueError:
                raise ValueError(f"Invalid rank value: {val}")

    masquerade = bool(data.get("masquerade", False))
    return Figure(type=fig_type, params=tuple(converted), masquerade=masquerade)


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

def _validate_room_code(code: str) -> str | None:
    upper = code.upper().strip()
    if ROOM_CODE_PATTERN.match(upper):
        return upper
    return None


def _validate_player_name(name: str) -> str | None:
    stripped = name.strip()
    if PLAYER_NAME_PATTERN.match(stripped):
        return stripped
    return None


# ---------------------------------------------------------------------------
# HTTP handler (serves static files + REST API)
# ---------------------------------------------------------------------------

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
}


async def handle_http(connection, request):
    """Handle HTTP requests (static files + REST API).

    For websockets 13+: receives (connection, request), returns Response or None.
    """
    from websockets.http11 import Response

    # If this is a WebSocket upgrade, let it through
    if request.headers.get("Upgrade", "").lower() == "websocket":
        return None

    path = request.path

    # REST API: GET /api/rooms - list room codes (debug)
    if path == "/api/rooms":
        codes = [room.code for room in room_manager.rooms.values()]
        body = json.dumps({"rooms": codes}).encode()
        return Response(200, "OK", websockets.Headers({"Content-Type": "application/json"}), body)

    # REST API: GET /api/rooms/new - create a room
    if path == "/api/rooms/new":
        try:
            room = await room_manager.create_room()
        except RuntimeError as exc:
            body = json.dumps({"error": str(exc)}).encode()
            return Response(503, "Service Unavailable", websockets.Headers({"Content-Type": "application/json"}), body)
        body = json.dumps({"code": room.code}).encode()
        return Response(200, "OK", websockets.Headers({"Content-Type": "application/json"}), body)

    # REST API: GET /api/rooms/{code}
    if path.startswith("/api/rooms/") and len(path) > len("/api/rooms/"):
        code = path[len("/api/rooms/"):]
        clean = _validate_room_code(code)
        if clean is None:
            body = json.dumps({"error": "Invalid room code format"}).encode()
            return Response(400, "Bad Request", websockets.Headers({"Content-Type": "application/json"}), body)
        room = room_manager.get_room(clean)
        if room is None:
            body = json.dumps({"error": "Room not found"}).encode()
            return Response(404, "Not Found", websockets.Headers({"Content-Type": "application/json"}), body)
        body = json.dumps(room.to_info_dict()).encode()
        return Response(200, "OK", websockets.Headers({"Content-Type": "application/json"}), body)

    # Static files
    if path == "/":
        file_path = STATIC_DIR / "index.html"
    elif path.startswith("/static/"):
        relative = path[len("/static/"):]
        if ".." in relative or relative.startswith("/"):
            return Response(403, "Forbidden", websockets.Headers(), b"Forbidden")
        file_path = STATIC_DIR / relative
    else:
        return Response(404, "Not Found", websockets.Headers(), b"Not Found")

    if not file_path.is_file():
        return Response(404, "Not Found", websockets.Headers(), b"Not Found")

    content_type = CONTENT_TYPES.get(file_path.suffix, "application/octet-stream")
    body = file_path.read_bytes()
    return Response(200, "OK", websockets.Headers({"Content-Type": content_type}), body)


# ---------------------------------------------------------------------------
# WebSocket handler
# ---------------------------------------------------------------------------

async def handle_websocket(websocket: ServerConnection) -> None:
    """Handle a WebSocket connection."""
    path = websocket.request.path

    # Parse /ws/{room_code}/{player_name}
    ws_match = re.match(r"^/ws/([^/]+)/([^/]+)$", path)
    if not ws_match:
        await websocket.close(4000, "Invalid WebSocket path")
        return

    raw_code = ws_match.group(1)
    raw_name = ws_match.group(2)

    # URL-decode
    from urllib.parse import unquote
    raw_code = unquote(raw_code)
    raw_name = unquote(raw_name)

    clean_code = _validate_room_code(raw_code)
    if clean_code is None:
        await websocket.close(4001, "Invalid room code")
        return

    clean_name = _validate_player_name(raw_name)
    if clean_name is None:
        await websocket.close(4002, "Invalid player name")
        return

    room = room_manager.get_room(clean_code)
    if room is None:
        await websocket.close(4004, "Room not found")
        return

    # Join room
    player_id = await room.add_player(clean_name, websocket)

    # Notify everyone
    await room.broadcast({
        "type": "player_joined",
        "player_id": player_id,
        "name": clean_name,
        "players": room.player_list_info(),
    })

    # If game in progress, send state to reconnecting player
    if room.status == RoomStatus.PLAYING and room.engine is not None:
        try:
            state = room.engine.get_state_for_player(player_id)
            await room.send_to_player(player_id, {"type": "state", **state})
        except Exception:
            pass

    # Message loop
    try:
        async for raw in websocket:
            if not isinstance(raw, str):
                continue

            if len(raw) > MAX_MESSAGE_SIZE:
                await _send_error(websocket, "Message too large")
                continue

            try:
                msg: dict[str, Any] = json.loads(raw)
            except (json.JSONDecodeError, ValueError):
                await _send_error(websocket, "Invalid JSON")
                continue

            if not isinstance(msg, dict) or "type" not in msg:
                await _send_error(websocket, "Invalid message format")
                continue

            msg_type = msg.get("type")
            if not isinstance(msg_type, str):
                await _send_error(websocket, "Message type must be a string")
                continue

            await _handle_message(room, player_id, msg_type, msg, websocket)

    except websockets.exceptions.ConnectionClosed:
        pass
    except Exception:
        logger.exception("WebSocket error for player %s in room %s", player_id, clean_code)
    finally:
        await room.remove_player(player_id)
        await room.broadcast({
            "type": "player_left",
            "player_id": player_id,
            "name": clean_name,
            "players": room.player_list_info(),
        })


# ---------------------------------------------------------------------------
# Message handlers
# ---------------------------------------------------------------------------

async def _handle_message(
    room: Room, player_id: str, msg_type: str, msg: dict[str, Any], websocket: ServerConnection,
) -> None:
    if msg_type == "start":
        await _handle_start(room, player_id, websocket)
    elif msg_type == "raise":
        await _handle_raise(room, player_id, msg, websocket)
    elif msg_type == "check":
        await _handle_check(room, player_id, websocket)
    elif msg_type == "mate":
        await _handle_mate(room, player_id, websocket)
    else:
        await _send_error(websocket, f"Unknown message type: {msg_type}")


async def _handle_start(room: Room, player_id: str, websocket: ServerConnection) -> None:
    async with room.lock:
        if room.status != RoomStatus.LOBBY:
            await _send_error(websocket, "Game has already started")
            return

        if room.player_count < 2:
            await _send_error(websocket, "Need at least 2 players to start")
            return

        if room.player_order[0] != player_id:
            await _send_error(websocket, "Only the room creator can start the game")
            return

        engine = GameEngine(room.config)
        players = [
            {"id": pid, "name": room.players[pid].name}
            for pid in room.player_order
        ]
        engine.start_game(players)
        room.engine = engine
        room.status = RoomStatus.PLAYING

    await room.send_state_to_all()


async def _handle_raise(
    room: Room, player_id: str, msg: dict[str, Any], websocket: ServerConnection,
) -> None:
    if room.status != RoomStatus.PLAYING or room.engine is None:
        await _send_error(websocket, "Game is not in progress")
        return

    fig_data = msg.get("figure")
    if not isinstance(fig_data, dict):
        await _send_error(websocket, "Missing or invalid 'figure' field")
        return

    try:
        figure = _deserialize_figure(fig_data)
    except ValueError as exc:
        await _send_error(websocket, str(exc))
        return

    async with room.lock:
        try:
            result = room.engine.handle_raise(player_id, figure)
        except Exception as exc:
            await _send_error(websocket, str(exc))
            return

    await _broadcast_result(room, result)
    await room.send_state_to_all()


async def _handle_check(room: Room, player_id: str, websocket: ServerConnection) -> None:
    if room.status != RoomStatus.PLAYING or room.engine is None:
        await _send_error(websocket, "Game is not in progress")
        return

    async with room.lock:
        try:
            result = room.engine.handle_check(player_id)
        except Exception as exc:
            await _send_error(websocket, str(exc))
            return

    await _broadcast_result(room, result)
    await room.send_state_to_all()
    await _check_game_over(room)


async def _handle_mate(room: Room, player_id: str, websocket: ServerConnection) -> None:
    if room.status != RoomStatus.PLAYING or room.engine is None:
        await _send_error(websocket, "Game is not in progress")
        return

    async with room.lock:
        try:
            result = room.engine.handle_mate(player_id)
        except Exception as exc:
            await _send_error(websocket, str(exc))
            return

    await _broadcast_result(room, result)
    await room.send_state_to_all()
    await _check_game_over(room)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _broadcast_result(room: Room, result: dict) -> None:
    if result:
        await room.broadcast({"type": "round_result", **result})


async def _check_game_over(room: Room) -> None:
    if room.engine is None:
        return
    state = room.engine.state
    if hasattr(state, "winner") and state.winner is not None:
        room.status = RoomStatus.FINISHED
        await room.broadcast({
            "type": "game_over",
            "winner": state.winner,
        })


async def _send_error(websocket: ServerConnection, message: str) -> None:
    try:
        await websocket.send(json.dumps({"type": "error", "message": message}))
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Background cleanup
# ---------------------------------------------------------------------------

async def _periodic_cleanup() -> None:
    while True:
        await asyncio.sleep(IDLE_CLEANUP_INTERVAL)
        try:
            removed = await room_manager.cleanup_idle_rooms()
            if removed:
                logger.info("Cleaned up %d idle room(s)", removed)
        except Exception:
            logger.exception("Error during idle room cleanup")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def main(host: str = "0.0.0.0", port: int = 8000) -> None:
    asyncio.create_task(_periodic_cleanup())

    async with websockets.serve(
        handle_websocket,
        host,
        port,
        process_request=handle_http,
        max_size=MAX_MESSAGE_SIZE * 4,
    ) as server:
        print(f"Poker Starej Kuncery running at http://{host}:{port}")
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())
