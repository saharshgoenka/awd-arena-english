# NexusBI — Security Hint Sheet

This application has known vulnerabilities in the following areas:

1. **Access control**: Report detail objects are reached by id. A user's own
   report may reference a different user's report, and ownership checks matter.
2. **Debug exposure**: An unadvertised diagnostics path may dump environment-like
   configuration with the real secret under a non-obvious key among decoys.
3. **Cryptographic failure**: Encrypted exports may reuse one keystream for every
   item; a known plaintext export can reveal the keystream needed for the vault.
4. **Data queries**: User input may flow directly into database queries.
5. **Token security**: The portal access token verifier may trust `alg: none`
   tokens with forged role claims.

Only FLAG_4 is stored in the injectable database table; the other flags are served
from environment variables at runtime through distinct exploit paths.
