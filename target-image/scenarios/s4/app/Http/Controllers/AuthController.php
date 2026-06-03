<?php

namespace App\Http\Controllers;

use App\Models\User;
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

    // flag_3 path: returns MD5 hash stored in password_legacy
    public function legacyToken(Request $request)
    {
        return response()->json(['legacy_token' => $request->user()->password_legacy]);
    }
}
