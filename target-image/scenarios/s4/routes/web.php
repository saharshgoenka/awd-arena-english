<?php

use App\Http\Controllers\AdminController;
use App\Http\Controllers\AuthController;
use App\Http\Controllers\DebugController;
use App\Http\Controllers\ProductController;
use Illuminate\Support\Facades\Route;

// Health check — no auth required
Route::get('/health', fn() => response()->json(['status' => 'ok']));

// Auth
Route::get('/login',  [AuthController::class, 'showLogin'])->name('login');
Route::post('/login', [AuthController::class, 'login']);
Route::post('/logout', [AuthController::class, 'logout'])->middleware('auth');

// Dashboard
Route::get('/dashboard', [AuthController::class, 'dashboard'])->middleware('auth');

// flag_1: admin panel — intentionally missing auth + role middleware
Route::get('/admin/panel', [AdminController::class, 'panel']);

// flag_2: debug endpoint — no auth; FLAG_2 in JSON dump
Route::get('/debug/phpinfo', [DebugController::class, 'phpinfo']);

// flag_3 path: legacy MD5 token exposed
Route::get('/profile/legacy-token', [AuthController::class, 'legacyToken'])->middleware('auth');

// Products
Route::middleware('auth')->group(function () {
    Route::get('/products',              [ProductController::class, 'index']);
    Route::get('/products/search',       [ProductController::class, 'search']);       // flag_4 (SQLi)
    Route::get('/products/secret-vault', [ProductController::class, 'secretVault']); // flag_3 target
});

// flag_5 target: admin orders report (requires login, brute-forceable)
Route::get('/admin/orders/report', [AdminController::class, 'ordersReport'])->middleware('auth');
