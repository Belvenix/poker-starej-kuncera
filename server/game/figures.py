"""Figure detection, validation and comparison.

Core logic for checking whether a declared figure exists among all dealt cards,
validating raises, and determining the highest possible figure (for mate).
"""
from __future__ import annotations

from collections import Counter

from .models import Card, Figure, FigureType, GameConfig, Rank, Suit

STRAIGHT_LENGTH = 5


def figure_exists(figure: Figure, cards: list[Card]) -> bool:
    """Check if a declared figure exists (with 'at least' semantics) in cards."""
    ft = figure.type
    p = figure.params

    if ft == FigureType.HIGH_CARD:
        return _count_rank(cards, p[0]) >= 1

    if ft == FigureType.PAIR:
        return _count_rank(cards, p[0]) >= 2

    if ft == FigureType.TWO_PAIRS:
        return _count_rank(cards, p[0]) >= 2 and _count_rank(cards, p[1]) >= 2

    if ft == FigureType.STRAIGHT:
        return _straight_exists(cards, p[0])

    if ft == FigureType.THREE_OF_KIND:
        return _count_rank(cards, p[0]) >= 3

    if ft == FigureType.FULL_HOUSE:
        three_rank, pair_rank = p[0], p[1]
        cnt = _rank_counts(cards)
        if figure.masquerade:
            # Swapped: need 2 of "three_rank" and 3 of "pair_rank"
            return cnt[three_rank] >= 2 and cnt[pair_rank] >= 3
        return cnt[three_rank] >= 3 and cnt[pair_rank] >= 2

    if ft == FigureType.FLUSH:
        return _count_suit(cards, p[0]) >= 5

    if ft == FigureType.FOUR_OF_KIND:
        return _count_rank(cards, p[0]) >= 4

    if ft == FigureType.STRAIGHT_FLUSH:
        return _straight_flush_exists(cards, p[0], p[1])

    return False


def is_valid_raise(new_figure: Figure, old_figure: Figure | None) -> bool:
    """Check if new_figure is strictly higher than old_figure."""
    if old_figure is None:
        return True
    return new_figure > old_figure


def is_valid_figure(figure: Figure, config: GameConfig) -> bool:
    """Check if a figure declaration is structurally valid given game config."""
    ft = figure.type
    p = figure.params
    ranks = [r for r in Rank if r >= config.min_rank]
    min_r, max_r = ranks[0], ranks[-1]

    if ft == FigureType.HIGH_CARD:
        return len(p) == 1 and isinstance(p[0], Rank) and min_r <= p[0] <= max_r

    if ft == FigureType.PAIR:
        return len(p) == 1 and isinstance(p[0], Rank) and min_r <= p[0] <= max_r

    if ft == FigureType.TWO_PAIRS:
        if len(p) != 2:
            return False
        high, low = p
        return (isinstance(high, Rank) and isinstance(low, Rank)
                and min_r <= low < high <= max_r)

    if ft == FigureType.STRAIGHT:
        if len(p) != 1 or not isinstance(p[0], Rank):
            return False
        start = p[0]
        return start >= min_r and Rank(start + STRAIGHT_LENGTH - 1) <= max_r

    if ft == FigureType.THREE_OF_KIND:
        return len(p) == 1 and isinstance(p[0], Rank) and min_r <= p[0] <= max_r

    if ft == FigureType.FULL_HOUSE:
        if len(p) != 2:
            return False
        three_r, pair_r = p
        return (isinstance(three_r, Rank) and isinstance(pair_r, Rank)
                and min_r <= three_r <= max_r and min_r <= pair_r <= max_r
                and three_r != pair_r)

    if ft == FigureType.FLUSH:
        return len(p) == 1 and isinstance(p[0], Suit)

    if ft == FigureType.FOUR_OF_KIND:
        return len(p) == 1 and isinstance(p[0], Rank) and min_r <= p[0] <= max_r

    if ft == FigureType.STRAIGHT_FLUSH:
        if len(p) != 2 or not isinstance(p[0], Rank) or not isinstance(p[1], Suit):
            return False
        start = p[0]
        return start >= min_r and Rank(start + STRAIGHT_LENGTH - 1) <= max_r

    return False


def find_highest_figure(cards: list[Card], config: GameConfig) -> Figure | None:
    """Find the highest figure that exists among the given cards.

    Used for mate validation. Iterates from highest type downward.
    Returns None if no figure exists (shouldn't happen if cards are non-empty).
    """
    ranks = [r for r in Rank if r >= config.min_rank]
    min_r, max_r = ranks[0], ranks[-1]
    cnt = _rank_counts(cards)
    suit_cnt = _suit_counts(cards)
    card_set = set(cards)

    # Straight flush (highest first)
    for start in reversed(range(min_r, max_r - STRAIGHT_LENGTH + 2)):
        start_rank = Rank(start)
        for suit in reversed(Suit):
            if _straight_flush_exists_fast(card_set, start_rank, suit):
                return Figure(FigureType.STRAIGHT_FLUSH, (start_rank, suit))

    # Four of a kind
    for rank in reversed(ranks):
        if cnt[rank] >= 4:
            return Figure(FigureType.FOUR_OF_KIND, (rank,))

    # Flush
    for suit in reversed(Suit):
        if suit_cnt[suit] >= 5:
            return Figure(FigureType.FLUSH, (suit,))

    # Full house
    threes = [r for r in reversed(ranks) if cnt[r] >= 3]
    for three_r in threes:
        for pair_r in reversed(ranks):
            if pair_r != three_r and cnt[pair_r] >= 2:
                return Figure(FigureType.FULL_HOUSE, (three_r, pair_r))

    # Three of a kind
    for rank in reversed(ranks):
        if cnt[rank] >= 3:
            return Figure(FigureType.THREE_OF_KIND, (rank,))

    # Straight
    for start in reversed(range(min_r, max_r - STRAIGHT_LENGTH + 2)):
        start_rank = Rank(start)
        if _straight_exists(cards, start_rank):
            return Figure(FigureType.STRAIGHT, (start_rank,))

    # Two pairs
    pairs = [r for r in reversed(ranks) if cnt[r] >= 2]
    if len(pairs) >= 2:
        return Figure(FigureType.TWO_PAIRS, (pairs[0], pairs[1]))

    # Pair
    for rank in reversed(ranks):
        if cnt[rank] >= 2:
            return Figure(FigureType.PAIR, (rank,))

    # High card
    for rank in reversed(ranks):
        if cnt[rank] >= 1:
            return Figure(FigureType.HIGH_CARD, (rank,))

    return None


def mate_succeeds(declared_figure: Figure, cards: list[Card], config: GameConfig) -> bool:
    """Check if mate call succeeds: declared figure exists AND no higher figure exists."""
    if not figure_exists(declared_figure, cards):
        return False
    highest = find_highest_figure(cards, config)
    if highest is None:
        return True
    return highest <= declared_figure


def enumerate_valid_figures(config: GameConfig) -> list[Figure]:
    """Enumerate all valid figures for a given config, sorted ascending.

    Useful for UI: presents all possible declarations.
    """
    ranks = [r for r in Rank if r >= config.min_rank]
    min_r, max_r = ranks[0], ranks[-1]
    figures: list[Figure] = []

    # High cards
    for r in ranks:
        figures.append(Figure(FigureType.HIGH_CARD, (r,)))

    # Pairs
    for r in ranks:
        figures.append(Figure(FigureType.PAIR, (r,)))

    # Two pairs (high > low)
    for i, high in enumerate(ranks):
        for low in ranks[:i]:
            figures.append(Figure(FigureType.TWO_PAIRS, (high, low)))

    # Straights
    for start in range(min_r, max_r - STRAIGHT_LENGTH + 2):
        figures.append(Figure(FigureType.STRAIGHT, (Rank(start),)))

    # Three of a kind
    for r in ranks:
        figures.append(Figure(FigureType.THREE_OF_KIND, (r,)))

    # Full house (three_rank != pair_rank)
    for three_r in ranks:
        for pair_r in ranks:
            if three_r != pair_r:
                figures.append(Figure(FigureType.FULL_HOUSE, (three_r, pair_r)))

    # Flush
    for s in Suit:
        figures.append(Figure(FigureType.FLUSH, (s,)))

    # Four of a kind
    for r in ranks:
        figures.append(Figure(FigureType.FOUR_OF_KIND, (r,)))

    # Straight flush
    for start in range(min_r, max_r - STRAIGHT_LENGTH + 2):
        for s in Suit:
            figures.append(Figure(FigureType.STRAIGHT_FLUSH, (Rank(start), s)))

    figures.sort()
    return figures


# --- helpers ---

def _count_rank(cards: list[Card], rank: Rank) -> int:
    return sum(1 for c in cards if c.rank == rank)


def _count_suit(cards: list[Card], suit: Suit) -> int:
    return sum(1 for c in cards if c.suit == suit)


def _rank_counts(cards: list[Card]) -> Counter:
    return Counter(c.rank for c in cards)


def _suit_counts(cards: list[Card]) -> Counter:
    return Counter(c.suit for c in cards)


def _straight_exists(cards: list[Card], start_rank: Rank) -> bool:
    ranks_present = {c.rank for c in cards}
    return all(
        Rank(start_rank + i) in ranks_present
        for i in range(STRAIGHT_LENGTH)
    )


def _straight_flush_exists(cards: list[Card], start_rank: Rank, suit: Suit) -> bool:
    card_set = set(cards)
    return _straight_flush_exists_fast(card_set, start_rank, suit)


def _straight_flush_exists_fast(card_set: set[Card], start_rank: Rank, suit: Suit) -> bool:
    return all(
        Card(Rank(start_rank + i), suit) in card_set
        for i in range(STRAIGHT_LENGTH)
    )
