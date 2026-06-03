"""Room and session management for Poker Starej Kuncery.

No external dependencies - websocket objects are duck-typed (any object with
a .send(str) coroutine works).
"""
from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from .models import GameConfig, generate_room_code

IDLE_TIMEOUT_SECONDS = 120  # 2 minutes with no connected players


class RoomStatus(str, Enum):
    LOBBY = "lobby"
    PLAYING = "playing"
    FINISHED = "finished"


@dataclass
class ConnectedPlayer:
    player_id: str
    name: str
    websocket: Any = None  # duck-typed: needs .send(str)
    connected: bool = True


class Room:
    """A single game room that holds players and an engine instance."""

    def __init__(self, code: str, config: GameConfig | None = None) -> None:
        self.code: str = code
        self.config: GameConfig = config or GameConfig()
        self.status: RoomStatus = RoomStatus.LOBBY
        self.players: dict[str, ConnectedPlayer] = {}
        self.player_order: list[str] = []
        self.engine: Any = None
        self.lock: asyncio.Lock = asyncio.Lock()
        self.last_activity: float = time.monotonic()
        self._next_id: int = 0

    def _generate_player_id(self) -> str:
        self._next_id += 1
        return f"p{self._next_id}"

    async def add_player(self, name: str, websocket: Any) -> str:
        async with self.lock:
            for pid, cp in self.players.items():
                if cp.name == name and not cp.connected:
                    cp.websocket = websocket
                    cp.connected = True
                    self._touch()
                    return pid

            player_id = self._generate_player_id()
            self.players[player_id] = ConnectedPlayer(
                player_id=player_id,
                name=name,
                websocket=websocket,
                connected=True,
            )
            self.player_order.append(player_id)
            self._touch()
            return player_id

    async def remove_player(self, player_id: str) -> None:
        async with self.lock:
            cp = self.players.get(player_id)
            if cp is not None:
                cp.connected = False
                cp.websocket = None
            self._touch()

    def get_connected_websockets(self) -> list[tuple[str, Any]]:
        return [
            (pid, cp.websocket)
            for pid, cp in self.players.items()
            if cp.connected and cp.websocket is not None
        ]

    def player_list_info(self) -> list[dict]:
        return [
            {
                "player_id": cp.player_id,
                "name": cp.name,
                "connected": cp.connected,
            }
            for cp in (self.players[pid] for pid in self.player_order)
        ]

    async def broadcast(self, message: dict) -> None:
        data = json.dumps(message)
        for _pid, ws in self.get_connected_websockets():
            try:
                await ws.send(data)
            except Exception:
                pass

    async def send_state_to_all(self) -> None:
        if self.engine is None:
            return
        for pid, ws in self.get_connected_websockets():
            try:
                state = self.engine.get_state_for_player(pid)
                await ws.send(json.dumps({"type": "state", **state}))
            except Exception:
                pass

    async def send_to_player(self, player_id: str, message: dict) -> None:
        cp = self.players.get(player_id)
        if cp and cp.connected and cp.websocket:
            try:
                await cp.websocket.send(json.dumps(message))
            except Exception:
                pass

    def _touch(self) -> None:
        self.last_activity = time.monotonic()

    def has_connected_players(self) -> bool:
        return any(cp.connected for cp in self.players.values())

    def is_idle(self, timeout: float = IDLE_TIMEOUT_SECONDS) -> bool:
        if self.has_connected_players():
            return False
        return (time.monotonic() - self.last_activity) > timeout

    @property
    def player_count(self) -> int:
        return len(self.players)

    def to_info_dict(self) -> dict:
        return {
            "code": self.code,
            "status": self.status.value,
            "players": self.player_list_info(),
            "player_count": self.player_count,
        }


class RoomManager:
    def __init__(self, max_rooms: int = 100) -> None:
        self.rooms: dict[str, Room] = {}
        self.max_rooms: int = max_rooms
        self._lock: asyncio.Lock = asyncio.Lock()

    async def create_room(self, config: GameConfig | None = None) -> Room:
        async with self._lock:
            if len(self.rooms) >= self.max_rooms:
                raise RuntimeError("Maximum number of rooms reached")
            for _ in range(100):
                code = generate_room_code(6)
                if code not in self.rooms:
                    break
            else:
                raise RuntimeError("Could not generate unique room code")
            room = Room(code=code, config=config)
            self.rooms[code] = room
            return room

    def get_room(self, code: str) -> Room | None:
        return self.rooms.get(code.upper())

    async def remove_room(self, code: str) -> None:
        async with self._lock:
            self.rooms.pop(code.upper(), None)

    def list_rooms(self) -> list[dict]:
        return [room.to_info_dict() for room in self.rooms.values()]

    async def cleanup_idle_rooms(self, timeout: float = IDLE_TIMEOUT_SECONDS) -> int:
        async with self._lock:
            idle_codes = [
                code for code, room in self.rooms.items() if room.is_idle(timeout)
            ]
            for code in idle_codes:
                del self.rooms[code]
            return len(idle_codes)
