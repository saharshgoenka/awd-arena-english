# TaskFlow API — Security Hint Sheet

This task management API has known vulnerabilities in five areas:

1. **Access control**: Object endpoints may authenticate the caller but forget to
   check whether the caller owns the object being requested (IDOR/BOLA). Object ids
   referenced from your own records may point at other users' data.
2. **Configuration exposure**: An internal diagnostics endpoint may not be linked
   from discovery yet still dump the full environment. The genuine secret can be
   buried among realistic decoy variables, some deliberately flag-shaped.
3. **Cryptographic failure**: An encrypted export endpoint may XOR every item with
   the same fixed keystream (no per-message nonce/IV). A known (plaintext,
   ciphertext) pair recovers the keystream, which then decrypts the secret vault.
4. **Query injection**: Search endpoints may concatenate user input into SQL queries.
5. **Token security**: JWT verification may trust the token's own `alg` header. A
   token presented with `alg: none` may be accepted without any signature check,
   letting an attacker mint an admin token from a low-privilege one.

Flags are served from environment variables FLAG_1–FLAG_5; only the injection
target stores its own flag copy in the database.
Each flag is reachable via a distinct exploit path.
