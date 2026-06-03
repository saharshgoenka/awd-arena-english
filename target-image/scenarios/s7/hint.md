# FleetView — Security Hint Sheet

FleetView is a Go (net/http) fleet-management API backed by SQLite. It has known
vulnerabilities in five areas:

1. **Access control**: The admin settings endpoint may only check that a user is
   logged in, not that they hold the `admin` role, letting any authenticated user
   read admin-only configuration.
2. **Debug exposure**: A `/debug/env` endpoint may dump the entire process
   environment (including secrets) with no authentication.
3. **Password storage**: Passwords may be stored using a fast, unsalted hash
   (SHA-256) despite the column being named `password_hash`, and the stored hash
   may be exposed through a profile endpoint.
4. **Query injection**: Vehicle search may concatenate user input directly into a
   SQL string instead of using a bound placeholder.
5. **Login security**: The login endpoint may lack rate limiting and may return
   different error messages for unknown users vs. wrong passwords, enabling
   username enumeration and brute force.

Flags are in the database and environment variables FLAG_1–FLAG_5.
