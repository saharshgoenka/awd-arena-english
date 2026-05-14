# OpenClaw AWD Referee Engine

## Quick start

### 1. Install dependencies

```bash
cd referee-engine
pip install -r requirements.txt
```

### 2. Run the server

```bash
python main.py
```

Listening on `http://localhost:8000` by default.

### 3. Health check

```bash
curl http://localhost:8000/health
```

## API overview

### Submit a flag

```http
POST /api/submit
Content-Type: application/json

{
  "player_id": 1,
  "flag": "FLAG{...}"
}
```

Rules:

- Flag submission is scored only during the **attack** phase.
- You cannot score on your own flag.
- The referee resolves the true flag owner; `target_player_id` is optional metadata.
- Each distinct player can score once per flag value.
- The same attacker cannot score twice on the same flag.

Common failure reasons: `invalid_flag`, `own_flag`, `flag_already_claimed_by_attacker`.

### Start a match

```http
POST /api/matches/start
Content-Type: application/json
```

Example body (redact secrets in real use):

```json
{
  "match": {
    "name": "Test Match",
    "duration": 7200
  },
  "llm": {
    "provider": "anthropic",
    "baseUrl": "https://api.anthropic.com"
  },
  "players": [
    {
      "id": 1,
      "name": "Player 1",
      "model": "claude-sonnet-4-6",
      "gatewayPort": 18789
    }
  ]
}
```

Example response:

```json
{
  "match_id": "match_1710777600",
  "status": "started"
}
```

### Match status

```http
GET /api/matches/{match_id}
```

Returns overview, leaderboard hints, `events_count`, and `recent_events`.

Endpoints:

- `GET /api/matches/{match_id}` — overview + recent events
- `GET /api/matches/{match_id}/events` — full timeline
- `GET /api/matches/{match_id}/submissions` — submission audit log

Scoring notes:

- `submissions` is the source of truth for captures.
- `events` powers timelines and replay.
- The scoring engine consumes the persisted submission list (`persisted_submissions` at runtime).
- `validate_submission()` returns the concrete `submission_record` for that attempt.

### End a match

```http
POST /api/matches/{match_id}/end
```

### List matches

```http
GET /api/matches
```

### WebSocket

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Received:', data);
};
```

Event types include `MATCH_STARTED`, `MATCH_ENDED`, `READY_UPDATE`, `SCORE_UPDATE`, `FLAG_CAPTURED`, and `SERVICE_DOWN`.

## Tests

```bash
curl -X POST http://localhost:8000/api/matches/start \
  -H "Content-Type: application/json" \
  -d @test_config.json
```

Interactive docs: `http://localhost:8000/docs`

## Layout

```
referee-engine/
├── main.py              # FastAPI app
├── requirements.txt
├── test_config.json
└── README.md
```

## Extending

Add routes in `main.py`. Emit realtime updates from `RefereeEngine` via `await referee.broadcast({...})`.
