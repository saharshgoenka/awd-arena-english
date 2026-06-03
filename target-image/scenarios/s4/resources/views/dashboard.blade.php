<!DOCTYPE html>
<html>
<head><title>ShopAdmin Dashboard</title></head>
<body>
<h1>ShopAdmin Dashboard</h1>
<p>Welcome, {{ Auth::user()->name }} ({{ Auth::user()->role }})</p>
<nav>
    <a href="/products">Products</a> |
    <a href="/products/search?q=">Search</a> |
    <a href="/profile/legacy-token">Legacy Token</a>
</nav>
<form method="POST" action="/logout" style="display:inline">
    @csrf
    <button type="submit">Logout</button>
</form>
</body>
</html>
