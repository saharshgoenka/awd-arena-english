# FinLedger API — Security Hint Sheet

This financial ledger API has known vulnerabilities in five areas:

1. **Access control**: Some admin API routes may be missing authorization annotations,
   allowing unauthenticated access to privileged endpoints.
2. **Configuration exposure**: Spring Actuator endpoints may be enabled without
   authentication, exposing environment variables and application secrets.
3. **Password storage**: User accounts may be protected with MD5 password hashes,
   which are trivially reversible for common passwords.
4. **Query injection**: Search endpoints may concatenate user input directly into
   SQL queries rather than using parameterized statements.
5. **Authentication failures**: Admin accounts may lack brute-force protection,
   making weak passwords recoverable via credential stuffing.

Flags are stored in the database and injected as environment variables FLAG_1–FLAG_5.
Each flag is reachable via a distinct exploit path.
