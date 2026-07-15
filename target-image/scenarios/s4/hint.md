# ShopAdmin — Security Hint Sheet

This e-commerce admin panel has known vulnerabilities in five areas:

1. **Access control**: Some admin routes may require a staff login but still lack
   the role checks needed to keep low-privilege users out.
2. **Configuration exposure**: A diagnostics endpoint may expose environment
   variables including secrets.
3. **Cryptographic failure**: A legacy re-authentication path may compare MD5
   token hashes loosely, letting PHP "0e" magic hashes bypass the real token.
4. **Query injection**: Product search may concatenate user input directly into SQL.
5. **Login security**: The login endpoint may lack rate limiting and may leak
   information that enables username enumeration.

Flags are in the database and environment variables FLAG_1–FLAG_5.
Each flag is reachable via a distinct exploit path.
