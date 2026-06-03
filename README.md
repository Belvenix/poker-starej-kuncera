# Poker Starej Kuncery

Blefowa gra karciana / Bluffing card game for friends.

## Quick Start

```bash
pip install websockets
python3 run.py
```

Open `http://<your-ip>:8000` on your phone.

One person creates a room, others join with the room code.

### Termux (Android)

```bash
pkg install python
pip install websockets
python3 run.py 0.0.0.0 8000
```

To find your phone's local IP (for others to connect):

```bash
python3 -c "import socket; s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); s.connect(('8.8.8.8',80)); print(s.getsockname()[0]); s.close()"
```

### macOS / Linux

```bash
# macOS
ipconfig getifaddr en0

# Linux
hostname -I | awk '{print $1}'
```

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

- Python + websockets (single pure-Python dependency)
- Vanilla HTML/CSS/JS frontend
- No database, no build tools, no C extensions
- Mobile-first UI
- Runs on any device with Python 3.11+
