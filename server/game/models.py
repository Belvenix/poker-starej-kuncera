from __future__ import annotations

import random
import string
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional


class Rank(IntEnum):
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    JACK = 11
    QUEEN = 12
    KING = 13
    ACE = 14

    @property
    def pl(self) -> str:
        return _RANK_PL[self]

    @property
    def en(self) -> str:
        return _RANK_EN[self]


_RANK_PL = {
    Rank.SEVEN: "7", Rank.EIGHT: "8", Rank.NINE: "9", Rank.TEN: "10",
    Rank.JACK: "Walet", Rank.QUEEN: "Dama", Rank.KING: "Krol", Rank.ACE: "As",
}
_RANK_EN = {
    Rank.SEVEN: "7", Rank.EIGHT: "8", Rank.NINE: "9", Rank.TEN: "10",
    Rank.JACK: "Jack", Rank.QUEEN: "Queen", Rank.KING: "King", Rank.ACE: "Ace",
}


class Suit(IntEnum):
    CLUBS = 0
    DIAMONDS = 1
    HEARTS = 2
    SPADES = 3

    @property
    def pl(self) -> str:
        return _SUIT_PL[self]

    @property
    def en(self) -> str:
        return _SUIT_EN[self]

    @property
    def symbol(self) -> str:
        return _SUIT_SYMBOL[self]


_SUIT_PL = {
    Suit.CLUBS: "Trefl", Suit.DIAMONDS: "Karo",
    Suit.HEARTS: "Kier", Suit.SPADES: "Pik",
}
_SUIT_EN = {
    Suit.CLUBS: "Clubs", Suit.DIAMONDS: "Diamonds",
    Suit.HEARTS: "Hearts", Suit.SPADES: "Spades",
}
_SUIT_SYMBOL = {
    Suit.CLUBS: "\u2663", Suit.DIAMONDS: "\u2666",
    Suit.HEARTS: "\u2665", Suit.SPADES: "\u2660",
}


class FigureType(IntEnum):
    HIGH_CARD = 1
    PAIR = 2
    TWO_PAIRS = 3
    STRAIGHT = 4
    THREE_OF_KIND = 5
    FULL_HOUSE = 6
    FLUSH = 7
    FOUR_OF_KIND = 8
    STRAIGHT_FLUSH = 9

    @property
    def pl(self) -> str:
        return _FTYPE_PL[self]

    @property
    def en(self) -> str:
        return _FTYPE_EN[self]


_FTYPE_PL = {
    FigureType.HIGH_CARD: "Wysoka karta",
    FigureType.PAIR: "Para",
    FigureType.TWO_PAIRS: "Dwie pary",
    FigureType.STRAIGHT: "Strit",
    FigureType.THREE_OF_KIND: "Trojka",
    FigureType.FULL_HOUSE: "Full",
    FigureType.FLUSH: "Kolor",
    FigureType.FOUR_OF_KIND: "Kareta",
    FigureType.STRAIGHT_FLUSH: "Poker",
}
_FTYPE_EN = {
    FigureType.HIGH_CARD: "High card",
    FigureType.PAIR: "Pair",
    FigureType.TWO_PAIRS: "Two pairs",
    FigureType.STRAIGHT: "Straight",
    FigureType.THREE_OF_KIND: "Three of a kind",
    FigureType.FULL_HOUSE: "Full house",
    FigureType.FLUSH: "Flush",
    FigureType.FOUR_OF_KIND: "Four of a kind",
    FigureType.STRAIGHT_FLUSH: "Straight flush",
}


@dataclass(frozen=True, order=True)
class Card:
    rank: Rank
    suit: Suit


@dataclass(frozen=True, order=True)
class Figure:
    """A declared figure. Naturally ordered for comparison.

    Comparison is by (type, params) using tuple ordering.
    Params meaning depends on type:
      HIGH_CARD:      (rank,)
      PAIR:           (rank,)
      TWO_PAIRS:      (high_rank, low_rank)  -- high_rank > low_rank
      STRAIGHT:       (start_rank,)
      THREE_OF_KIND:  (rank,)
      FULL_HOUSE:     (three_rank, pair_rank)
      FLUSH:          (suit,)
      FOUR_OF_KIND:   (rank,)
      STRAIGHT_FLUSH: (start_rank, suit)

    masquerade: only for FULL_HOUSE. Swaps the existence check
    (need 2 of three_rank and 3 of pair_rank). Does not affect ordering.
    """
    type: FigureType
    params: tuple = ()
    masquerade: bool = field(default=False, compare=False)

    def describe(self, lang: str = "pl") -> str:
        t = self.type.pl if lang == "pl" else self.type.en
        p = self.params
        if self.type == FigureType.HIGH_CARD:
            r = _rank_name(p[0], lang)
            return f"{t} {r}"
        if self.type == FigureType.PAIR:
            return f"{t} {_rank_name(p[0], lang)}"
        if self.type == FigureType.TWO_PAIRS:
            return f"{t}, {_rank_name(p[0], lang)} i {_rank_name(p[1], lang)}"
        if self.type == FigureType.STRAIGHT:
            return f"{t} ({_straight_label(p[0], lang)})"
        if self.type == FigureType.THREE_OF_KIND:
            return f"{t} {_rank_name(p[0], lang)}"
        if self.type == FigureType.FULL_HOUSE:
            sep = "po" if lang == "pl" else "over"
            label = f"{t}, {_rank_name(p[0], lang)} {sep} {_rank_name(p[1], lang)}"
            if self.masquerade:
                label += " (maszkarada)" if lang == "pl" else " (masquerade)"
            return label
        if self.type == FigureType.FLUSH:
            s = _suit_name(p[0], lang)
            return f"{t} {s}"
        if self.type == FigureType.FOUR_OF_KIND:
            return f"{t} {_rank_name(p[0], lang)}"
        if self.type == FigureType.STRAIGHT_FLUSH:
            s = _suit_name(p[1], lang)
            return f"{t} {s} ({_straight_label(p[0], lang)})"
        return t


def _rank_name(rank: Rank, lang: str) -> str:
    return rank.pl if lang == "pl" else rank.en


def _suit_name(suit: Suit, lang: str) -> str:
    return suit.pl if lang == "pl" else suit.en


def _straight_label(start_rank: Rank, lang: str) -> str:
    end_rank = Rank(start_rank + 4)
    return f"{_rank_name(start_rank, lang)}-{_rank_name(end_rank, lang)}"


class Deck:
    def __init__(self, min_rank: Rank = Rank.NINE):
        self.min_rank = min_rank
        self.cards: list[Card] = []
        self.rebuild()

    @property
    def ranks(self) -> list[Rank]:
        return [r for r in Rank if r >= self.min_rank]

    def rebuild(self) -> None:
        self.cards = [Card(r, s) for r in self.ranks for s in Suit]

    def shuffle(self) -> None:
        random.shuffle(self.cards)

    def deal(self, n: int = 1) -> list[Card]:
        dealt = self.cards[:n]
        self.cards = self.cards[n:]
        return dealt

    def return_cards(self, cards: list[Card]) -> None:
        self.cards.extend(cards)


@dataclass
class Player:
    id: str
    name: str
    hand: list[Card] = field(default_factory=list)
    card_count: int = 0
    alive: bool = True

    @property
    def current_cards(self) -> int:
        return len(self.hand)


class GamePhase(IntEnum):
    LOBBY = 0
    DEALING = 1
    DECLARING = 2
    ROUND_RESULT = 3
    GAME_OVER = 4


@dataclass
class GameConfig:
    elimination_limit: int = 4
    min_rank: Rank = Rank.NINE
    lang: str = "pl"

    @property
    def max_players(self) -> int:
        num_ranks = Rank.ACE - self.min_rank + 1
        return (num_ranks * 4 - 2) // (self.elimination_limit - 1)

    def auto_adjust_rank(self, player_count: int) -> None:
        for r in (Rank.NINE, Rank.EIGHT, Rank.SEVEN):
            self.min_rank = r
            if self.max_players >= player_count:
                return


@dataclass
class RoundState:
    current_player_idx: int = 0
    last_figure: Optional[Figure] = None
    last_declarer_idx: Optional[int] = None
    history: list[dict] = field(default_factory=list)


@dataclass
class GameState:
    config: GameConfig
    players: list[Player] = field(default_factory=list)
    phase: GamePhase = GamePhase.LOBBY
    deck: Optional[Deck] = None
    round: Optional[RoundState] = None
    winner: Optional[str] = None  # player id


def generate_room_code(length: int = 6) -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))
