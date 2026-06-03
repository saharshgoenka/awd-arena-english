# ShopAdmin — Security Hint Sheet

This e-commerce admin panel has known vulnerabilities in five areas:

1. **Access control**: Some admin routes may lack authentication and authorization middleware.
2. **Configuration exposure**: Debug controllers or misplaced configuration files
   may expose environment variables including secrets.
3. **Password storage**: A legacy password column may store weak hashes that are
   exposed through profile endpoints.
4. **Query injection**: Product search may concatenate user input directly into SQL.
5. **Login security**: The login endpoint may lack rate limiting and may leak
   information that enables username enumeration.

Flags are in the database and environment variables FLAG_1–FLAG_5.
Each flag is reachable via a distinct exploit path.
