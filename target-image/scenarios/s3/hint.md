# TaskFlow API — Security Hint Sheet

This task management API has known vulnerabilities in five areas:

1. **Access control**: Some API routes may authenticate users but still miss a
   stronger role check.
2. **Configuration exposure**: Diagnostics endpoints may leak one
   secret-bearing value even after broad static exposure paths are removed.
3. **Password storage**: User password hashes may still be returned in API
   responses and may use a weak hashing algorithm.
4. **Query injection**: Search endpoints may concatenate user input into SQL queries.
5. **Token security**: JWT-backed login flows may still be undermined by weak
   online authentication controls such as username enumeration and guessable
   credentials.

Flags are in the database and environment variables FLAG_1–FLAG_5.
Each flag is reachable via a distinct exploit path.
