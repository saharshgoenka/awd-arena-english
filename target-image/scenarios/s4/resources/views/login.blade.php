<!DOCTYPE html>
<html>
<head><title>ShopAdmin Login</title></head>
<body>
<h1>ShopAdmin</h1>
@if ($errors->any())
<ul style="color:red">
    @foreach ($errors->all() as $error)
        <li>{{ $error }}</li>
    @endforeach
</ul>
@endif
<form method="POST" action="/login">
    @csrf
    <p><input type="text" name="username" placeholder="Username" value="{{ old('username') }}"></p>
    <p><input type="password" name="password" placeholder="Password"></p>
    <p><button type="submit">Login</button></p>
</form>
</body>
</html>
