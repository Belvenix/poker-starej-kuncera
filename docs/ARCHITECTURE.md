# Poker Starej Kuncery - Architecture

## Phases

### Phase 1: POC (Playable on one machine / local network)
- Python backend (websockets library + stdlib)
- Minimal browser UI (HTML/CSS/JS, no framework)
- Game logic fully server-side
- Players connect via phone browsers on same WiFi
- Polish language UI

### Phase 2: QoL & Hardening
- English translation toggle
- ~~Card animations, sounds, haptic feedback~~ (done in POC)
- Incognito mode (screen privacy for peeking protection)
- Game configuration UI (elimination limit, deck range, player count)
- Reconnection handling (basic auto-reconnect done in POC)
- Disable impossible figures (e.g., 4 aces with only 3 cards in play)
- Session persistence via localStorage (survive page refresh)

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
| HTML/CSS/JS    | <---> | websockets lib   |
| WebSocket      |  WS   | HTTP + WS server |
| Card Display   |       | Game Engine      |
| Action Buttons |       | Room Manager     |
+----------------+       +------------------+
```

### Server Components

#### `run.py` - Entry point
- Starts the async server on configurable host/port

#### `server/server.py` - Server
- websockets library serves both HTTP and WebSocket on a single port
- HTTP: static files + REST API (GET only, websockets limitation)
  - `GET /api/rooms` - list active room codes (debug)
  - `GET /api/rooms/new` - create a new room
  - `GET /api/rooms/{code}` - room info
- WebSocket: `/ws/{room_code}/{player_name}` for game actions

#### `server/game/engine.py` - Core game logic
- Deck management (shuffle, deal, return cards)
- Figure validation (check if a declared figure exists in all dealt cards)
- Figure comparison (ordering, raise validation)
- Round state machine (declare -> raise/check/mate -> resolve -> new round)

#### `server/game/models.py` - Data models
- Card, Deck, Player, Figure, GameState, Room
- All game configuration (elimination limit, deck range, etc.)

#### `server/game/figures.py` - Figure detection & comparison
- Enumerate all figure types
- Detect if a figure exists in a set of cards
- Compare two figures (for raise validation)
- Determine highest possible figure (for mate validation)

#### `server/game/room.py` - Room/session management
- Create/join rooms with codes
- Player connection tracking
- Game lifecycle (lobby -> playing -> finished)

### Client Components

#### `static/index.html` - Single page
- Join/create room screen
- Game screen (hand, actions, history)

#### `static/game.js` - Game client
- WebSocket connection with auto-reconnect (visibility change handler for phone sleep)
- Render game state
- Figure picker (type -> rank/suit selectors, only valid raises shown)
- Masquerade button for full house swap (single-click, auto-computed)
- Confirmation dialogs for check/mate
- Toggle history panel
- Lobby: room code list polling (debug), room creation via API
- Sound effects via Web Audio API (no external files):
  - Your turn chime, raise click, check/mate tones, win fanfare, lose tone
  - Masquerade: explosion (noise burst + bass boom + rising whistle + sparkles)
  - Player joined ping, card deal tick
- Haptic feedback (vibration) on key actions

#### `static/style.css` - Styling
- Mobile-first responsive design (scales to laptop)
- Card visuals with suit symbols (CSS-only)
- Casino-green theme, gold accents
- Action buttons: raise (blue), check (orange), mate (red), masquerade (purple)
- Animations: card deal stagger, declaration pop, current player glow pulse, card flip reveal, win bounce, title fade-in
- Room code displayed in game screen top bar

### WebSocket Protocol

```json
// Server -> Client
{"type": "state", "phase": "DECLARING", "players": [...], "round": {...}, "config": {...}}
{"type": "round_result", "event": "check|mate|raise", ...}
{"type": "game_over", "winner": "player_id"}
{"type": "player_joined", "name": "...", "players": [...]}
{"type": "player_left", "name": "...", "players": [...]}
{"type": "error", "message": "..."}

// Client -> Server
{"type": "raise", "figure": {"type": "pair", "params": [13]}}
{"type": "raise", "figure": {"type": "full_house", "params": [14, 9], "masquerade": true}}
{"type": "check"}
{"type": "mate"}
{"type": "start"}
```

## Security Considerations (POC)

- Game state is SERVER-SIDE only; clients only see their own cards
- No card data sent to other players until check/mate reveals
- Room codes are non-guessable (6 char alphanumeric)
- Input validation on all client messages
- Path traversal protection on static file serving
- NOTE: POC on local network assumes trusted environment; no auth

## Security Considerations (Release)

- Rate limiting per IP and per room
- Max rooms per server (100) with auto-cleanup every 30s
- Empty rooms (no connected players) expire after 2 minutes
- Max message size on WebSocket (4KB)
- Server crash > unexpected bill (fail-closed)
- No persistent storage of game data (in-memory only)
- Optional: simple room passwords
- HTTPS required for production

## Anticipated Problems

### POC
- **WiFi requirement**: All players must be on same network; phone hotspot works
- **Phone sleep**: WebSocket disconnects when screen locks; auto-reconnect on visibility change implemented
- **Fat fingers**: Confirmation dialogs on check/mate prevent accidents
- **Figure selection UX**: Two-step picker (type -> rank/suit) with only valid options shown
- **Straights config**: Number of possible straights depends on deck range; dynamically computed

### Release
- **Offline + multiplayer conflict**: True offline requires all players in same physical network; PWA helps with "no internet" but still needs local connectivity
- **WebRTC complexity**: P2P removes server cost but adds NAT traversal issues, especially on mobile networks
- **Card asset size**: Custom themes increase app size; lazy loading needed
- **Cheating**: In P2P mode, a modified client could peek at state; server-authoritative mode is more secure
- **Physical cards feel**: Tangible cards are satisfying; compensated with animations (deal, flip, pop, glow), sound effects (Web Audio API), and haptic vibration on key actions

## Dependencies

- Python 3.11+
- `websockets` (pure Python, no C extensions)
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
    server.py          # HTTP + WebSocket server
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
  run.py               # Entry point
  README.md
```
