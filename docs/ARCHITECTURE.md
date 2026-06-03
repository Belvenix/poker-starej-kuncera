# Poker Starej Kuncery - Architecture

## Phases

### Phase 1: POC (Playable on one machine / local network)
- Python backend (FastAPI + WebSockets)
- Minimal browser UI (HTML/CSS/JS, no framework)
- Game logic fully server-side
- Players connect via phone browsers on same WiFi
- Polish language UI

### Phase 2: QoL & Hardening
- English translation toggle
- Card animations, sounds, haptic feedback
- Incognito mode (screen privacy for peeking protection)
- Game configuration UI (elimination limit, deck range, player count)
- Reconnection handling

### Phase 3: Distribution
- Offline play (service worker / PWA)
- Online play (hosted server, room codes)
- Cost protection (rate limiting, max rooms, auto-cleanup, crash > bill)
- Peer-to-peer option for serverless play (WebRTC)
- Custom card assets (client-side theme packs)

## POC Architecture

```
Browser (Phone)          Server (Python)
+----------------+       +------------------+
| HTML/CSS/JS    | <---> | FastAPI          |
| WebSocket      |  WS   | WebSocket Hub    |
| Card Display   |       | Game Engine      |
| Action Buttons |       | Room Manager     |
+----------------+       +------------------+
```

### Server Components

#### `server.py` - Entry point
- FastAPI app, serves static files, WebSocket endpoint

#### `game/engine.py` - Core game logic
- Deck management (shuffle, deal, return cards)
- Figure validation (check if a declared figure exists in all dealt cards)
- Figure comparison (ordering, raise validation)
- Round state machine (declare -> raise/check/mate -> resolve -> new round)

#### `game/models.py` - Data models
- Card, Deck, Player, Figure, GameState, Room
- All game configuration (elimination limit, deck range, etc.)

#### `game/figures.py` - Figure detection & comparison
- Enumerate all figure types
- Detect if a figure exists in a set of cards
- Compare two figures (for raise validation)
- Determine highest possible figure (for mate validation)

#### `game/room.py` - Room/session management
- Create/join rooms with codes
- Player connection tracking
- Game lifecycle (lobby -> playing -> finished)

### Client Components

#### `static/index.html` - Single page
- Join/create room screen
- Game screen (hand, actions, history)

#### `static/game.js` - Game client
- WebSocket connection
- Render game state
- Send player actions
- Toggle history panel

#### `static/style.css` - Styling
- Mobile-first responsive design
- Card visuals (CSS-only for POC)
- Action buttons designed for easy thumb tapping

### WebSocket Protocol

```json
// Server -> Client
{"type": "state", "hand": [...], "current_player": "...", "last_figure": {...}, "players": [...]}
{"type": "round_result", "action": "check|mate", "winner": "...", "loser": "...", "cards_revealed": [...]}
{"type": "game_over", "winner": "..."}

// Client -> Server
{"type": "raise", "figure": {"type": "pair", "rank": "K"}}
{"type": "check"}
{"type": "mate"}
```

## Security Considerations (POC)

- Game state is SERVER-SIDE only; clients only see their own cards
- No card data sent to other players until check/mate reveals
- Room codes should be non-guessable (6 char alphanumeric)
- Input validation on all client messages
- NOTE: POC on local network assumes trusted environment; no auth

## Security Considerations (Release)

- Rate limiting per IP and per room
- Max rooms per server with auto-cleanup of idle rooms
- Max message size on WebSocket
- Server crash > unexpected bill (fail-closed)
- No persistent storage of game data (in-memory only)
- Optional: simple room passwords
- HTTPS required for production

## Anticipated Problems

### POC
- **WiFi requirement**: All players must be on same network; phone hotspot works
- **Phone sleep**: WebSocket disconnects when screen locks; need reconnect logic early
- **Fat fingers**: Action buttons must be large and spaced; accidental clicks are frustrating
- **Figure selection UX**: Declaring "full house, kings over tens" requires multiple taps; needs smart UI (type -> rank selectors, contextual)
- **Straights config**: Number of possible straights depends on deck range; must be dynamic

### Release
- **Offline + multiplayer conflict**: True offline requires all players in same physical network; PWA helps with "no internet" but still needs local connectivity
- **WebRTC complexity**: P2P removes server cost but adds NAT traversal issues, especially on mobile networks
- **Card asset size**: Custom themes increase app size; lazy loading needed
- **Cheating**: In P2P mode, a modified client could peek at state; server-authoritative mode is more secure
- **Physical cards feel**: Tangible cards are satisfying; compensate with good animations, card flip sounds, vibration on deal/check/mate

## Dependencies (POC, minimal)

- Python 3.11+
- FastAPI (web framework + WebSocket support)
- uvicorn (ASGI server)
- No database (in-memory state)
- No JS framework (vanilla JS)
- No build tools

## File Structure

```
poker-starej-kuncera-poc/
  docs/
    GAME_RULES.md
    ARCHITECTURE.md
  server/
    __init__.py
    server.py          # FastAPI app, entry point
    game/
      __init__.py
      models.py        # Data models
      figures.py       # Figure detection & comparison
      engine.py        # Game loop, state machine
      room.py          # Room management
  static/
    index.html
    game.js
    style.css
  requirements.txt
  README.md
```
