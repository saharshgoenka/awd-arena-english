<?php

use App\Http\Controllers\AdminController;
use App\Http\Controllers\AuthController;
use App\Http\Controllers\DebugController;
use App\Http\Controllers\DiscoveryController;
use App\Http\Controllers\ProductController;
use Illuminate\Support\Facades\Route;

Route::get('/', [DiscoveryController::class, 'home']);
Route::get('/status', [DiscoveryController::class, 'status']);
Route::get('/help', [DiscoveryController::class, 'help']);
Route::get('/about', [DiscoveryController::class, 'about']);
Route::get('/api', [DiscoveryController::class, 'api']);

Route::get('/health', fn() => response()->json(['status' => 'ok']));

Route::get('/login',  [AuthController::class, 'showLogin'])->name('login');
Route::post('/login', [AuthController::class, 'login']);
Route::post('/logout', [AuthController::class, 'logout'])->middleware('auth');

Route::get('/dashboard', [AuthController::class, 'dashboard'])->middleware('auth');

Route::get('/admin/panel', [AdminController::class, 'panel'])->middleware('auth');

Route::get('/debug/phpinfo', [DebugController::class, 'phpinfo']);

Route::get('/profile/legacy-token', [AuthController::class, 'legacyToken'])->middleware('auth');

Route::middleware('auth')->group(function () {
    Route::get('/products',              [ProductController::class, 'index']);
    Route::get('/products/search',       [ProductController::class, 'search']);
    Route::get('/products/secret-vault', [ProductController::class, 'secretVault']);
});

Route::get('/admin/orders/report', [AdminController::class, 'ordersReport'])->middleware('auth');
