# FinLedger API — Security Hint Sheet

This financial ledger API has known vulnerabilities in five areas:

1. **Access control**: Some admin API routes may only require a staff login and
   miss the role checks needed to keep low-privilege users out.
2. **Configuration exposure**: Support diagnostics endpoints may expose
   environment variables and application secrets.
3. **Password storage**: User accounts may be protected with MD5 password hashes,
   which are exposed through profile responses for other staff accounts.
4. **Query injection**: Search endpoints may concatenate user input directly into
   SQL queries rather than using parameterized statements.
5. **Authentication failures**: The staff sign-in flow may leak whether a
   username exists and may lack brute-force protection.

Flags are stored in the database and injected as environment variables FLAG_1–FLAG_5.
Each flag is reachable via a distinct exploit path.
