# ContentHub CMS — Security Hint Sheet

This content management system has known vulnerabilities in five areas:

1. **Access control**: Admin controllers may be missing required authorization
   callbacks, allowing any authenticated user to access admin functions.
2. **Debug exposure**: A debug endpoint and a misconfigured production setting
   may expose environment variables and runtime configuration.
3. **Password storage**: Passwords may be stored using a weak hashing function
   despite the column name suggesting otherwise.
4. **Query injection**: Post search may use string interpolation in ActiveRecord
   queries instead of parameterized placeholders.
5. **Login security**: The login endpoint may lack rate limiting and may return
   different error messages for unknown users vs. wrong passwords.

Flags are in the database and environment variables FLAG_1–FLAG_5.
