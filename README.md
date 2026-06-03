# Poker Starej Kuncery

Blefowa gra karciana / Bluffing card game for friends.

## Quick Start

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn server.server:app --host 0.0.0.0 --port 8000
```

Open `http://<your-ip>:8000` on your phone.

One person creates a room, others join with the room code.

## How to Play

See [docs/GAME_RULES.md](docs/GAME_RULES.md) for full rules in Polish and English.

**TL;DR**: Everyone gets cards. You declare poker figures (pair, straight, flush, etc.) that you claim exist across ALL players' combined cards. You can bluff. Others can check your claim or raise higher. Get caught lying = +1 card. Reach 4 cards = you're out. Last player standing wins.

## Playing on Local Network

1. Start the server on any machine (laptop, phone with Termux, etc.)
2. Make sure all phones are on the same WiFi / hotspot
3. Open the server's IP address in phone browsers
4. Create a room, share the code, play

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for technical details.

- Python (FastAPI + WebSockets)
- Vanilla HTML/CSS/JS frontend
- No database, no build tools
- Mobile-first UI
