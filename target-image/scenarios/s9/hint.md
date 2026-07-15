# VaultGate API — Security Hint Sheet

VaultGate is an Actix-web (Rust) API secrets and credentials management service,
backed by SQLite. Sessions are Bearer tokens. It has known vulnerabilities in
five areas:

1. **Access control**: Actix-web handlers are only authenticated if they
   declare an auth extractor in their function signature. Some handlers
   may be missing this entirely.
2. **Configuration exposure**: A debug endpoint may return environment
   variables, including the injected debug flag.
3. **Password storage**: Passwords may be hashed with MD5 and returned
   in user profile responses for a different authenticated engineer account,
   forcing leak-plus-crack-plus-pivot.
4. **Query injection**: Secret search may use Rust's format!() macro to
   interpolate user input directly into SQL strings.
5. **Token security**: JWT verification may trust the token's own `alg` header
   and honour `alg:"none"`, letting a low-privileged user forge an `admin` token
   offline by dropping the signature.

Only the SQL-injection flag is stored in the database; the other flags are read
from environment variables so the SQLi path cannot dump the whole flag set. Each
flag is reachable via a distinct exploit path.
