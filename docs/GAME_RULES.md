# Poker Starej Kuncery - Zasady Gry / Game Rules

## PL - Zasady

### Opis
Poker Starej Kuncery to gra karciana oparta na blefie. Gracze deklaruja uklady (figury) ktore ich zdaniem istnieja wsrod WSZYSTKICH kart rozdanych graczom. Mozna klamac.

### Talia
- Standardowa talia (4 kolory: pik, kier, karo, trefl)
- Domyslny zakres: 9 do Asa (24 karty)
- Dla 6+ graczy: od 8 (28 kart)
- Dla 9+ graczy: od 7 (32 karty)
- Formula: max_graczy = floor((ilosc_rang * 4 - 2) / (limit_eliminacji - 1))
- Zawsze minimum 2 karty pozostaja nierozdane (element niepewnosci)

### Poczatek gry
- Kazdy gracz dostaje 1 karte
- Pierwszy gracz: losowy, zglaszajacy sie lub zwyciezca poprzedniej gry

### Figury (od najslabszej do najsilniejszej)
1. **Wysoka karta** - np. "wysoka karta as" (kolor nieistotny, liczy sie rang)
2. **Para** - np. "para krolow"
3. **Dwie pary** - np. "dwie pary, krolowie i dziesiatki" (porownanie: najwyzsza para, potem druga)
4. **Strit maly** - najnizsze 5 kolejnych kart w talii (np. 9-10-J-Q-K)
5. **Strit duzy** - najwyzsze 5 kolejnych kart w talii (np. 10-J-Q-K-A)
6. **Strit sredni** - tylko gdy gra z 8 lub nizej (np. 8-9-10-J-Q przy talii od 7)
7. **Trojka** - np. "trojka krolow"
8. **Full** - np. "full, krolowie po dziesiatki" (trojka + para)
9. **Kolor** - np. "kolor w kierach" (5 kart w jednym kolorze, nie podajemy jakie)
10. **Kareta** - np. "kareta krolow"
11. **Poker** - strit w jednym kolorze, np. "poker w kierach, maly"

### Akcje gracza
Gracz moze wykonac jedna z trzech akcji:

#### Podbicie (Raise)
- Deklaracja wyzszej figury niz poprzednia
- Mozna podbijac w ramach tego samego typu (para dziesiatek -> para krolow)
- Lub przejsc na wyzszy typ figury

#### Sprawdzenie (Check)
- Podwazenie deklaracji poprzedniego gracza
- Jesli figura (lub lepsza) ISTNIEJE wsrod wszystkich kart -> sprawdzajacy dostaje +1 karte
- Jesli figura NIE ISTNIEJE -> deklarujacy dostaje +1 karte
- Nastepna runde zaczyna zwyciezca sprawdzenia (ten ktory nie dostal karty)

#### Mat (Mate)
- Deklaracja ze poprzednio wymieniona figura jest najwyzsza mozliwa w tej rundzie
- Jesli PRAWDA (nie istnieje wyzsza figura wsrod wszystkich kart) -> wywolujacy -1 karta (minimum 0)
- Jesli FALSZ (istnieje wyzsza figura) -> wywolujacy +1 karta
- Nastepna runde zaczyna wywolujacy mata

### Karty graczy
- Start: 1 karta
- Limit eliminacji: domyslnie 4 karty (konfigurowalne)
- Gracz z 0 kartami nadal gra (brak informacji o kartach w grze)
- Po eliminacji: karty wracaja do talii, nowe rozdanie dla pozostalych

### Koniec gry
- Gracz ktory osiagnie limit kart odpada
- Osoba ktora spowodowala eliminacje zaczyna nastepna runde
- Gra konczy sie gdy zostanie jeden gracz - zwyciezca

### Maszkarada
- Specjalna akcja dostepna TYLKO gdy na stole lezy full z trojka nizszej rangi niz para
- Np. Full 9 po As (trojka 9, para Asow) -> maszkarada -> Full As po 9 (deklaracja: trojka Asow, para 9)
- Sprawdzenie maszkarady: szukamy 2 kart deklarowanej trojki i 3 kart deklarowanej pary (odwrotnosc)
- Nie mozna wywolac maszkarady na fullu gdzie trojka jest juz wyzsza niz para

### Wazne zasady
- Figury sprawdzane sa wsrod WSZYSTKICH kart w grze (rece wszystkich graczy)
- "Co najmniej" - jesli ktos deklaruje "para krolow" a sa 3 krolowie, para jest uznana
- Kolory (pik, kier, karo, trefl) maja znaczenie TYLKO przy kolorze i pokerze
- Przy sprawdzeniu: minimum 2 karty sa zawsze nierozdane, wiec pelna pewnosc jest niemozliwa
- Mat: deklarowana figura musi istniec I nie moze istniec zadna wyzsza


## EN - Rules

### Description
Poker Starej Kuncery is a bluffing card game. Players declare figures (hands) they believe exist across ALL dealt cards combined. Lying is allowed.

### Deck
- Standard suits (spades, hearts, diamonds, clubs)
- Default range: 9 to Ace (24 cards)
- For 6+ players: from 8 (28 cards)
- For 9+ players: from 7 (32 cards)
- Formula: max_players = floor((num_ranks * 4 - 2) / (elimination_limit - 1))
- At least 2 cards always remain undealt (uncertainty element)

### Game Start
- Each player receives 1 card
- First player: random, volunteer, or previous game winner

### Figures (lowest to highest)
1. **High card** - e.g., "high card ace" (suit irrelevant, rank only)
2. **Pair** - e.g., "pair of kings"
3. **Two pairs** - e.g., "two pairs, kings and tens" (compared by highest pair, then second)
4. **Small straight** - lowest 5 consecutive cards in deck (e.g., 9-10-J-Q-K)
5. **High straight** - highest 5 consecutive cards in deck (e.g., 10-J-Q-K-A)
6. **Medium straight** - only when playing with 8s or lower (e.g., 8-9-10-J-Q with 7-A deck)
7. **Three of a kind** - e.g., "three kings"
8. **Full house** - e.g., "full house, kings over tens" (three + pair)
9. **Flush** - e.g., "flush in hearts" (5 cards of one suit, no specific cards declared)
10. **Four of a kind** - e.g., "four kings"
11. **Straight flush** - straight in one suit, e.g., "straight flush in hearts, small"

### Player Actions

#### Raise
- Declare a higher figure than the previous one
- Can raise within the same type (pair of tens -> pair of kings)
- Or move to a higher figure type

#### Check
- Challenge the previous player's declaration
- If the figure (or better) EXISTS among all cards -> challenger gets +1 card
- If the figure does NOT EXIST -> declarer gets +1 card
- Next round started by the check winner (the one who did NOT receive a card)

#### Mate
- Claim that the previously declared figure is the highest possible this round
- If TRUE (no higher figure exists among all cards) -> caller gets -1 card (minimum 0)
- If FALSE (a higher figure exists) -> caller gets +1 card
- Next round started by the mate caller

### Player Cards
- Start: 1 card
- Elimination limit: default 4 cards (configurable)
- A player with 0 cards still plays (zero information about cards in play)
- After elimination: cards return to deck, fresh deal for remaining players

### Game End
- Player reaching the card limit is eliminated
- The player who caused the elimination starts the next round
- Game ends when one player remains - the winner

### Masquerade (Maszkarada)
- Special action available ONLY when the current declaration is a full house with trio rank lower than pair rank
- E.g., Full house 9s over Aces (three 9s, pair of Aces) -> masquerade -> Full house Aces over 9s
- Check verification is swapped: looks for 2 of the declared trio rank and 3 of the declared pair rank
- Cannot call masquerade on a full house where the trio is already higher than the pair

### Important Rules
- Figures are checked across ALL cards in play (all players' hands combined)
- "At least" - declaring "pair of kings" is valid even if three kings exist
- Suits (spades, hearts, diamonds, clubs) only matter for flush and straight flush
- On check: at least 2 cards are always undealt, so full certainty is impossible
- Mate: the declared figure must exist AND no higher figure can exist
