# NexusBI — Security Hint Sheet

This application has known vulnerabilities in the following areas:

1. **Access control**: Some admin routes may only require a basic user session
   when they should enforce stronger role checks.
2. **Debug exposure**: Support or diagnostics endpoints may leak one
   secret-bearing value even without a full environment dump.
3. **Password storage**: Legacy password hashing may still appear in internal
   audit or profile workflows.
4. **Data queries**: User input may flow directly into database queries.
5. **Login security**: The authentication endpoint may lack brute-force protections.

Flags are stored as environment variables FLAG_1 through FLAG_5 and seeded
into the database at startup. Each flag is reachable via a distinct exploit path.
