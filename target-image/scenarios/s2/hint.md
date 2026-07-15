# PeopleOps — Security Hint Sheet

This HR portal has known vulnerabilities in five areas:

1. **Access control (object-level)**: Records are fetched by id with a login
   check but no per-object owner check. Your own record may reference another
   record's id that you were never meant to open.
2. **Debug exposure**: A diagnostics endpoint is not listed in API discovery, and
   its verbose bundle hides one real secret among many realistic-looking config
   values (including decoy FLAG-shaped strings).
3. **Password storage**: Some accounts use legacy password hashing.
   Check how password hashes are stored and whether one account must pivot
   into another.
4. **Search queries**: The employee search feature may expose both HTML and
   JSON-backed surfaces, and user input may flow directly into raw SQL.
5. **Auth token forgery**: The portal issues a self-describing access token.
   Inspect how it claims to be signed — and whether the server actually verifies
   that claim.

Flags are served from environment variables FLAG_1–FLAG_5; only the injection
target stores its own flag copy in the database.
Each flag is reachable via a distinct exploit path.
