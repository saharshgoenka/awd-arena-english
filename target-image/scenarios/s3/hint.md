# TaskFlow API — Security Hint Sheet

This task management API has known vulnerabilities in five areas:

1. **Access control**: Some API routes may be missing authentication middleware entirely.
2. **Configuration exposure**: Debug endpoints or misconfigured static serving
   may expose environment variables and secrets.
3. **Password storage**: User password hashes may be returned in API responses
   and may use a weak hashing algorithm.
4. **Query injection**: Search endpoints may concatenate user input into SQL queries.
5. **Token security**: JWT verification may accept insecure algorithm choices,
   allowing token forgery without a valid signature.

Flags are in the database and environment variables FLAG_1–FLAG_5.
Each flag is reachable via a distinct exploit path.
