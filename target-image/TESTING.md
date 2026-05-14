# Target image — testing notes

## Status

**Implementation**: done  
**Full image tests**: pending stable Docker Hub access (pull timeouts were observed)

## What ships

### Production `ctf/Dockerfile`

- Based on `bkimminich/juice-shop:latest`
- Adds Python 3, SQLite, OpenSSH, curl
- SSH hardening and `juice` service user
- `init_arena_db.sql`, entrypoints, health checks

### Test `Dockerfile.test`

- Based on `node:20-alpine`
- Minimal HTTP server plus SSH + SQLite for quick wiring checks

### `test.sh`

Covers HTTP 200, DB read/write, flag injection, and SSH login.

### Database bootstrap

- `init_arena_db.sql` creates `arena_secret`, indexes, trigger, placeholder flag

### Entrypoints

- `docker-entrypoint.sh` — production path
- `docker-entrypoint-test.sh` — test image path

## Acceptance criteria

### 1. Port 3000 returns HTTP 200

- `EXPOSE 3000` in Dockerfile
- Health probe uses `curl -f http://localhost:3000/`

```bash
curl -I http://localhost:3000
# Expect: HTTP/1.1 200 OK
```

### 2. SSH password from env

- `docker-entrypoint.sh` reads `SSH_PASSWORD`
- Uses `chpasswd`

```bash
docker run -d -p 2222:22 -e SSH_PASSWORD=test123 openclaw/ctf-target:v1
ssh -p 2222 defender@localhost
# Password: test123
```

### 3. SQLite writable via `docker exec`

- DB file mode `644`, owned by `juice:juice`

```bash
docker exec <id> sqlite3 /app/arena/arena.db "SELECT * FROM arena_secret;"
docker exec <id> sqlite3 /app/arena/arena.db \
  "UPDATE arena_secret SET flag='FLAG{test}' WHERE id=1;"
docker exec <id> sqlite3 /app/arena/arena.db "SELECT flag FROM arena_secret WHERE id=1;"
# Expect: FLAG{test}
```

## How to run tests after network is healthy

### Option A — production image

```bash
cd target-image
cd ctf && docker build -t openclaw/ctf-target:v1 . && cd ..
docker run -d --name awd_target_test -p 3000:3000 -p 2222:22 -e SSH_PASSWORD=test123 openclaw/ctf-target:v1
sleep 10
curl -I http://localhost:3000
docker exec awd_target_test sqlite3 /app/arena/arena.db "SELECT * FROM arena_secret;"
# … flag update + SSH checks …
docker stop awd_target_test && docker rm awd_target_test
```

### Option B — `test.sh`

```bash
cd target-image
chmod +x test.sh
./test.sh
```

### Option C — test Dockerfile

```bash
cd target-image
docker build -f Dockerfile.test -t openclaw/ctf-target:test .
./test.sh
```

## Known issues

### Docker Hub timeouts

Use a mirror, offline tarballs, or retry when the registry is reachable.

### Editor import warnings

Install `referee-engine` deps inside a venv so Python tooling resolves imports:

```bash
cd referee-engine
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## File list

```
target-image/
├── Dockerfile
├── Dockerfile.test
├── init_arena_db.sql
├── docker-entrypoint.sh
├── docker-entrypoint-test.sh
├── test.sh
└── README.md
```

## Next steps

1. When the network is stable, run `./test.sh` end-to-end.
2. If something fails, inspect container logs and adjust config.
3. After green tests, push the image to your private registry.

## Conclusion

Implementation and scripts are ready for validation; execute `./test.sh` once base images pull cleanly to finish sign-off.
