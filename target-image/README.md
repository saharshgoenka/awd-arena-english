# OpenClaw AWD target image

## Quick start

```bash
cd target-image/ctf
docker build -t openclaw/ctf-target:v1 .
docker run -d -p 3000:3000 -p 2222:22 -e SSH_PASSWORD=test123 openclaw/ctf-target:v1
```

## Images

| Image | Dockerfile | Purpose |
|-------|------------|---------|
| `openclaw/ctf-target:v1` | `ctf/Dockerfile` | Production-style CTF target (supervisor, `app.py`, `flag_sync.sh`) |
| `openclaw/ctf-target:test` | `Dockerfile.test` | Lightweight HTTP + SSH for fast checks |

## Manual checks

### 1. HTTP

```bash
curl -I http://localhost:3000
```

Expect `HTTP/1.1 200 OK`.

### 2. SSH

```bash
ssh -p 2222 defender@localhost
```

Password `test123` unless overridden with `SSH_PASSWORD`.

### 3. SQLite

```bash
docker exec <container_id> sqlite3 /app/arena/arena.db "SELECT * FROM arena_secret;"
```

You should see the seeded flag row.

### 4. Flag injection

```bash
docker exec <container_id> sqlite3 /app/arena/arena.db \
  "UPDATE arena_secret SET flag='FLAG{test_flag_12345}' WHERE id=1;"

docker exec <container_id> sqlite3 /app/arena/arena.db \
  "SELECT flag FROM arena_secret WHERE id=1;"
```

Expect `FLAG{test_flag_12345}`.

## Environment

| Variable | Meaning | Default |
|----------|---------|---------|
| `SSH_PASSWORD` | Password for the maintenance SSH user | `changeme` |

## Layout

```
target-image/
├── ctf/
│   ├── Dockerfile
│   ├── app.py
│   ├── entrypoint.sh
│   ├── flag_sync.sh
│   └── supervisord.conf
├── Dockerfile.test
├── init_arena_db.sql
├── docker-entrypoint.sh
├── docker-entrypoint-test.sh
├── test.sh
└── README.md
```

## `arena_secret` table

| Column | Type | Notes |
|--------|------|--------|
| id | INTEGER | Primary key |
| flag | TEXT | Unique flag body |
| created_at | TIMESTAMP | Created |
| updated_at | TIMESTAMP | Updated on change |

## Ports

| Port | Service |
|------|---------|
| 3000 | Web app |
| 22 | SSH |

## Security notes

- SSH is intended for the `defender` (or configured) maintenance user, not ad-hoc root shells.
- Change default passwords via environment variables in real deployments.
- Database file permissions are set so the referee can update flags in-container.

## Troubleshooting

### SSH fails

```bash
docker exec <container_id> service ssh status
docker logs <container_id>
```

### Database missing

```bash
docker exec <container_id> ls -la /app/arena/
docker exec <container_id> cat /app/arena/init_arena_db.sql
```

### Web not responding

```bash
docker exec <container_id> curl http://localhost:3000
docker logs <container_id>
```
