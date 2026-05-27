# PeopleOps — Security Hint Sheet

This HR portal has known vulnerabilities in five areas:

1. **Access control**: Authentication alone does not guarantee authorization.
   Some staff-only views may be missing role/permission checks.
2. **Debug exposure**: The application may have debug endpoints or settings
   enabled that expose environment variables and internal configuration.
3. **Password storage**: Some accounts use legacy password hashing.
   Check how password hashes are stored and displayed.
4. **Search queries**: The employee search feature may pass user input
   directly into database queries.
5. **Login security**: The authentication endpoint may lack brute-force
   protections and may leak information about valid usernames.

Flags are stored in the database and in environment variables FLAG_1–FLAG_5.
Each flag is reachable via a distinct exploit path.
