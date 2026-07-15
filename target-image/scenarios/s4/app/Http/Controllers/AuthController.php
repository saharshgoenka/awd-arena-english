<?php

namespace App\Http\Controllers;

use App\Models\User;
use App\Support\ApiToken;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;

class AuthController extends Controller
{
    public function showLogin()
    {
        return view('login');
    }

    public function login(Request $request)
    {
        $username = $request->input('username', '');
        $password = $request->input('password', '');

        // flag_5 vulnerability: separate lookup reveals whether username exists
        $user = User::where('username', $username)->first();
        if (!$user) {
            return back()->withErrors(['login' => 'User not found']);
        }

        if (!Auth::attempt(['username' => $username, 'password' => $password], false)) {
            return back()->withErrors(['login' => 'Invalid password']);
        }

        $request->session()->regenerate();
        return redirect('/dashboard');
    }

    public function logout(Request $request)
    {
        Auth::logout();
        $request->session()->invalidate();
        $request->session()->regenerateToken();
        return redirect('/login');
    }

    public function dashboard()
    {
        return view('dashboard');
    }

    // flag_5 path: the SPA fetches its API bearer token after login. The app issues
    // a self-describing token carrying the caller's role, which the API routes trust.
    public function apiToken(Request $request)
    {
        $user = $request->user();
        $token = ApiToken::issue([
            'sub'      => $user->id,
            'username' => $user->username,
            'role'     => $user->role,
            'iat'      => time(),
        ]);
        return response()->json(['token' => $token]);
    }
}
