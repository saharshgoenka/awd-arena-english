# FinLedger API — Security Hint Sheet

This financial ledger API has known vulnerabilities in five areas:

1. **Access control**: Report detail objects are reached by id. A user's own
   report may reference a privileged approval report owned by another account.
2. **Configuration exposure**: An unadvertised diagnostics path may expose
   environment-like configuration with the real secret under a non-obvious key.
3. **Cryptographic failure**: Encrypted ledger exports may reuse one keystream
   for every item; a known plaintext entry can reveal the vault contents.
4. **Query injection**: Search endpoints may concatenate user input directly into
   SQL queries rather than using parameterized statements.
5. **Authentication failures**: The staff access token verifier may trust
   `alg: none` tokens with forged role claims.

Only FLAG_4 is stored in the injectable database table; the other flags are served
from environment variables at runtime through distinct exploit paths.
