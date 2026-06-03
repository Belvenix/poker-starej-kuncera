"""Game engine - state machine for Poker Starej Kuncery.

Manages the full game loop: dealing, declaring, checking, mate, elimination.
All public methods return dicts suitable for JSON serialization (WebSocket messages).
"""
from __future__ import annotations

import random
from typing import Optional

from .models import (
    Card,
    Deck,
    Figure,
    GameConfig,
    GamePhase,
    GameState,
    Player,
    RoundState,
)
from .figures import figure_exists, find_highest_figure, is_valid_figure, is_valid_raise, mate_succeeds


class GameError(Exception):
    """Raised when a game action is invalid."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)

    def to_dict(self) -> dict:
        return {"error": self.code, "message": self.message}


class GameEngine:
    """State machine driving a single game of Poker Starej Kuncery."""

    def __init__(self, config: Optional[GameConfig] = None) -> None:
        self.state = GameState(config=config or GameConfig())

    # ------------------------------------------------------------------
    # Properties / helpers
    # ------------------------------------------------------------------

    @property
    def config(self) -> GameConfig:
        return self.state.config

    @property
    def players(self) -> list[Player]:
        return self.state.players

    @property
    def phase(self) -> GamePhase:
        return self.state.phase

    @property
    def round(self) -> RoundState:
        assert self.state.round is not None
        return self.state.round

    @property
    def alive_players(self) -> list[Player]:
        return [p for p in self.players if p.alive]

    def _player_idx(self, player_id: str) -> int:
        for i, p in enumerate(self.players):
            if p.id == player_id:
                return i
        raise GameError("player_not_found", f"No player with id {player_id}")

    def _current_player(self) -> Player:
        return self.players[self.round.current_player_idx]

    def _validate_turn(self, player_id: str) -> int:
        """Validate it is the given player's turn. Return their index."""
        if self.state.phase != GamePhase.DECLARING:
            raise GameError("wrong_phase", "Game is not in declaring phase")
        idx = self._player_idx(player_id)
        if idx != self.round.current_player_idx:
            raise GameError(
                "not_your_turn",
                f"It is {self._current_player().name}'s turn",
            )
        if not self.players[idx].alive:
            raise GameError("player_eliminated", "You have been eliminated")
        return idx

    def _all_cards_in_play(self) -> list[Card]:
        """Collect every card currently held by alive players."""
        cards: list[Card] = []
        for p in self.players:
            if p.alive:
                cards.extend(p.hand)
        return cards

    def _card_to_dict(self, card: Card) -> dict:
        return {"rank": card.rank.value, "suit": card.suit.value}

    # ------------------------------------------------------------------
    # 1. start_game
    # ------------------------------------------------------------------

    def start_game(self, players: list[dict]) -> dict:
        """Initialize and start the game.

        Args:
            players: list of {"id": str, "name": str} dicts.

        Returns:
            Event dict describing game start.
        """
        if self.state.phase != GamePhase.LOBBY:
            raise GameError("wrong_phase", "Game already started")
        if len(players) < 2:
            raise GameError("not_enough_players", "Need at least 2 players")

        # Build player objects
        self.state.players = [
            Player(id=p["id"], name=p["name"], card_count=1) for p in players
        ]

        # Auto-adjust deck range for player count
        self.config.auto_adjust_rank(len(self.state.players))

        # Build and shuffle deck
        self.state.deck = Deck(min_rank=self.config.min_rank)
        self.state.deck.shuffle()

        # Deal 1 card to each player
        for p in self.state.players:
            p.card_count = 1
            p.hand = self.state.deck.deal(1)

        # Pick random starting player
        starting_idx = random.randint(0, len(self.state.players) - 1)

        # Init round state
        self.state.round = RoundState(current_player_idx=starting_idx)
        self.state.phase = GamePhase.DECLARING

        return {
            "event": "game_started",
            "starting_player": self.players[starting_idx].name,
            "starting_player_id": self.players[starting_idx].id,
            "player_count": len(self.players),
            "min_rank": self.config.min_rank.value,
            "elimination_limit": self.config.elimination_limit,
        }

    # ------------------------------------------------------------------
    # 2. handle_raise
    # ------------------------------------------------------------------

    def handle_raise(self, player_id: str, figure: Figure) -> dict:
        """Player declares (raises to) a new figure.

        Returns:
            Event dict describing the raise.
        """
        idx = self._validate_turn(player_id)
        player = self.players[idx]

        # Validate figure structure
        if not is_valid_figure(figure, self.config):
            raise GameError("invalid_figure", "Figure is not valid for this game config")

        # Validate it is strictly higher than last
        if not is_valid_raise(figure, self.round.last_figure):
            raise GameError(
                "figure_not_higher",
                "Declared figure must be higher than the current one",
            )

        # Record
        self.round.last_figure = figure
        self.round.last_declarer_idx = idx

        history_entry = {
            "action": "raise",
            "player": player.name,
            "figure": figure.describe(self.config.lang),
        }
        self.round.history.append(history_entry)

        # Advance to next alive player
        self.round.current_player_idx = self._next_alive_player(idx)

        return {
            "event": "raise",
            "player": player.name,
            "player_id": player.id,
            "figure": figure.describe(self.config.lang),
            "next_player": self._current_player().name,
            "next_player_id": self._current_player().id,
        }

    # ------------------------------------------------------------------
    # 3. handle_check
    # ------------------------------------------------------------------

    def handle_check(self, player_id: str) -> dict:
        """Player challenges the last declared figure.

        Returns:
            Event dict describing the check result.
        """
        idx = self._validate_turn(player_id)
        checker = self.players[idx]

        if self.round.last_figure is None or self.round.last_declarer_idx is None:
            raise GameError("nothing_to_check", "No figure has been declared yet")

        declarer_idx = self.round.last_declarer_idx
        declarer = self.players[declarer_idx]
        declared_figure = self.round.last_figure

        # Gather all cards in play
        all_cards = self._all_cards_in_play()
        cards_revealed = [self._card_to_dict(c) for c in all_cards]

        exists = figure_exists(declared_figure, all_cards)

        if exists:
            # Figure exists -> checker loses (gets +1 card)
            loser_idx = idx
            loser = checker
            winner_idx = declarer_idx
            success = False  # check was not successful for the checker
        else:
            # Figure doesn't exist -> declarer loses (gets +1 card)
            loser_idx = declarer_idx
            loser = declarer
            winner_idx = idx
            success = True  # check was successful for the checker

        # Penalty: loser gets +1 card
        loser.card_count += 1

        history_entry = {
            "action": "check",
            "player": checker.name,
            "target": declarer.name,
            "success": success,
            "cards_revealed": cards_revealed,
        }
        self.round.history.append(history_entry)

        # Check for elimination
        eliminated = False
        eliminated_name = None
        if loser.card_count >= self.config.elimination_limit:
            eliminated = True
            eliminated_name = loser.name
            self._eliminate_player(loser_idx)

        # Determine who starts next round
        # "The person that took the card starts" = the loser starts
        if eliminated:
            # If the loser was eliminated, the eliminator (winner) starts
            starter_idx = winner_idx
        else:
            starter_idx = loser_idx

        # Check if game is over
        if self.state.phase == GamePhase.GAME_OVER:
            return {
                "event": "check",
                "player": checker.name,
                "player_id": checker.id,
                "target": declarer.name,
                "target_id": declarer.id,
                "figure": declared_figure.describe(self.config.lang),
                "figure_exists": exists,
                "success": success,
                "loser": loser.name,
                "cards_revealed": cards_revealed,
                "eliminated": eliminated_name,
                "game_over": True,
                "winner": self.state.winner,
            }

        # Start new round
        self._new_round(starter_idx)

        return {
            "event": "check",
            "player": checker.name,
            "player_id": checker.id,
            "target": declarer.name,
            "target_id": declarer.id,
            "figure": declared_figure.describe(self.config.lang),
            "figure_exists": exists,
            "success": success,
            "loser": loser.name,
            "cards_revealed": cards_revealed,
            "eliminated": eliminated_name,
            "game_over": False,
            "new_round_starter": self.players[starter_idx].name,
            "new_round_starter_id": self.players[starter_idx].id,
        }

    # ------------------------------------------------------------------
    # 4. handle_mate
    # ------------------------------------------------------------------

    def handle_mate(self, player_id: str) -> dict:
        """Player claims the last declared figure is the highest possible.

        Returns:
            Event dict describing the mate result.
        """
        idx = self._validate_turn(player_id)
        caller = self.players[idx]

        if self.round.last_figure is None or self.round.last_declarer_idx is None:
            raise GameError("nothing_to_mate", "No figure has been declared yet")

        declared_figure = self.round.last_figure

        # Gather all cards in play
        all_cards = self._all_cards_in_play()
        cards_revealed = [self._card_to_dict(c) for c in all_cards]

        # Mate succeeds if declared figure exists AND no higher figure exists
        declared_exists = figure_exists(declared_figure, all_cards)
        highest = find_highest_figure(all_cards, self.config)
        success = declared_exists and (highest is None or highest <= declared_figure)

        # Build failure reason
        mate_fail_reason = None
        if not success:
            if not declared_exists:
                mate_fail_reason = "not_found"
            elif highest is not None and highest > declared_figure:
                mate_fail_reason = "higher_exists"

        if success:
            # Mate successful -> caller gets -1 card (min 0)
            caller.card_count = max(0, caller.card_count - 1)
        else:
            # Mate failed -> caller gets +1 card
            caller.card_count += 1

        history_entry = {
            "action": "mate",
            "player": caller.name,
            "success": success,
            "cards_revealed": cards_revealed,
        }
        self.round.history.append(history_entry)

        # Check for elimination (only on failure)
        eliminated = False
        eliminated_name = None
        if not success and caller.card_count >= self.config.elimination_limit:
            eliminated = True
            eliminated_name = caller.name
            self._eliminate_player(idx)

        # Mate caller always starts next round
        starter_idx = idx

        # If the caller was eliminated, the next alive player starts
        if eliminated:
            starter_idx = self._next_alive_player(idx)

        # Common mate result fields
        mate_result: dict = {
            "event": "mate",
            "player": caller.name,
            "player_id": caller.id,
            "figure": declared_figure.describe(self.config.lang),
            "success": success,
            "mate_fail_reason": mate_fail_reason,
            "highest_figure": highest.describe(self.config.lang) if highest else None,
            "cards_revealed": cards_revealed,
            "eliminated": eliminated_name,
        }

        # Check if game is over
        if self.state.phase == GamePhase.GAME_OVER:
            return {**mate_result, "game_over": True, "winner": self.state.winner}

        # Start new round
        self._new_round(starter_idx)

        return {
            **mate_result,
            "game_over": False,
            "new_round_starter": self.players[starter_idx].name,
            "new_round_starter_id": self.players[starter_idx].id,
        }

    # ------------------------------------------------------------------
    # 5. new_round
    # ------------------------------------------------------------------

    def _new_round(self, starting_player_idx: int) -> None:
        """Return all cards, rebuild deck, shuffle, deal, reset round state."""
        assert self.state.deck is not None

        # Return all cards from all players
        for p in self.players:
            p.hand.clear()

        # Rebuild and shuffle deck
        self.state.deck.rebuild()
        self.state.deck.shuffle()

        # Deal card_count cards to each alive player
        for p in self.players:
            if p.alive:
                p.hand = self.state.deck.deal(p.card_count)

        # Reset round state
        self.state.round = RoundState(current_player_idx=starting_player_idx)
        self.state.phase = GamePhase.DECLARING

    # ------------------------------------------------------------------
    # 6. eliminate_player
    # ------------------------------------------------------------------

    def _eliminate_player(self, player_idx: int) -> None:
        """Mark player as dead, return their cards. Check for game over."""
        player = self.players[player_idx]
        player.alive = False
        player.hand.clear()
        player.card_count = 0

        # Check if only 1 alive player remains
        alive = self.alive_players
        if len(alive) == 1:
            self.state.phase = GamePhase.GAME_OVER
            self.state.winner = alive[0].id

    # ------------------------------------------------------------------
    # 7. next_alive_player
    # ------------------------------------------------------------------

    def _next_alive_player(self, current_idx: int) -> int:
        """Return the index of the next alive player after current_idx."""
        n = len(self.players)
        idx = (current_idx + 1) % n
        while idx != current_idx:
            if self.players[idx].alive:
                return idx
            idx = (idx + 1) % n
        # Should not happen if game is not over (at least 2 alive)
        return current_idx

    # ------------------------------------------------------------------
    # 8. get_state_for_player
    # ------------------------------------------------------------------

    def get_state_for_player(self, player_id: str) -> dict:
        """Return sanitized game state visible to a specific player.

        Only shows that player's own cards; other players show card counts only.
        """
        player_idx = self._player_idx(player_id)
        player = self.players[player_idx]

        players_info = []
        for p in self.players:
            info: dict = {
                "id": p.id,
                "name": p.name,
                "card_count": p.card_count,
                "alive": p.alive,
            }
            if p.id == player_id:
                info["hand"] = [self._card_to_dict(c) for c in p.hand]
            players_info.append(info)

        result: dict = {
            "phase": self.state.phase.name,
            "players": players_info,
            "your_id": player_id,
            "your_name": player.name,
            "config": {
                "elimination_limit": self.config.elimination_limit,
                "min_rank": self.config.min_rank.value,
                "lang": self.config.lang,
            },
        }

        if self.state.round is not None:
            current = self._current_player()
            result["round"] = {
                "current_player": current.name,
                "current_player_id": current.id,
                "is_your_turn": current.id == player_id,
                "last_figure": (
                    self.round.last_figure.describe(self.config.lang)
                    if self.round.last_figure
                    else None
                ),
                "last_figure_raw": (
                    {
                        "type": self.round.last_figure.type.name.lower(),
                        "params": [v.value if hasattr(v, 'value') else v for v in self.round.last_figure.params],
                        "masquerade": self.round.last_figure.masquerade,
                    }
                    if self.round.last_figure
                    else None
                ),
                "last_declarer": (
                    self.players[self.round.last_declarer_idx].name
                    if self.round.last_declarer_idx is not None
                    else None
                ),
                "history": self.round.history,
            }

        if self.state.phase == GamePhase.GAME_OVER:
            result["winner"] = self.state.winner

        return result
