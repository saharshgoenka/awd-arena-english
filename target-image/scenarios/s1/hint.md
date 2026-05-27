# NexusBI — Security Hint Sheet

This application has known vulnerabilities in the following areas:

1. **Access control**: Some admin routes may be missing authentication checks.
2. **Debug exposure**: Development endpoints may have been left enabled.
3. **Password storage**: Legacy password hashing may be in use.
4. **Data queries**: User input may flow directly into database queries.
5. **Login security**: The authentication endpoint may lack brute-force protections.

Flags are stored as environment variables FLAG_1 through FLAG_5 and seeded
into the database at startup. Each flag is reachable via a distinct exploit path.
