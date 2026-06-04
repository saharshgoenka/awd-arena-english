# VaultGate API — Security Hint Sheet

VaultGate is an Actix-web (Rust) API secrets and credentials management service,
backed by SQLite. Sessions are Bearer tokens. It has known vulnerabilities in
five areas:

1. **Access control**: Actix-web handlers are only authenticated if they
   declare an auth extractor in their function signature. Some handlers
   may be missing this entirely.
2. **Configuration exposure**: A debug endpoint may return all environment
   variables including injected secrets.
3. **Password storage**: Passwords may be hashed with MD5 and returned
   in user profile responses.
4. **Query injection**: Secret search may use Rust's format!() macro to
   interpolate user input directly into SQL strings.
5. **Login security**: The login endpoint has no rate limiting, making
   it vulnerable to brute-force attacks against weak passwords.

Flags are in the database and environment variables FLAG_1–FLAG_5.
Each flag is reachable via a distinct exploit path.
