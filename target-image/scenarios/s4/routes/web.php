<?php

use App\Http\Controllers\AdminController;
use App\Http\Controllers\AuthController;
use App\Http\Controllers\DebugController;
use App\Http\Controllers\DiscoveryController;
use App\Http\Controllers\ExportController;
use App\Http\Controllers\ProductController;
use App\Http\Controllers\ReportController;
use Illuminate\Support\Facades\Route;

Route::get('/', [DiscoveryController::class, 'home']);
Route::get('/status', [DiscoveryController::class, 'status']);
Route::get('/help', [DiscoveryController::class, 'help']);
Route::get('/about', [DiscoveryController::class, 'about']);
Route::get('/api', [DiscoveryController::class, 'api']);

Route::get('/health', fn() => response()->json(['status' => 'ok']));

// Standard discovery breadcrumb pointing at the diagnostics/admin surfaces.
Route::get('/robots.txt', fn() => response(
    "User-agent: *\nDisallow: /debug/env\nDisallow: /admin\n",
    200,
    ['Content-Type' => 'text/plain']
));

Route::get('/login',  [AuthController::class, 'showLogin'])->name('login');
Route::post('/login', [AuthController::class, 'login']);
Route::post('/logout', [AuthController::class, 'logout'])->middleware('auth');

Route::get('/dashboard', [AuthController::class, 'dashboard'])->middleware('auth');

// flag_5: API bearer token issued to the authenticated session.
Route::get('/api/token', [AuthController::class, 'apiToken'])->middleware('auth');

// flag_2: un-advertised diagnostics env dump (discovery via fuzzing alone).
Route::get('/debug/env', [DebugController::class, 'phpinfo']);

// flag_3 (A02 reused-keystream): encrypted export vault. Every item is XORed with the
// SAME fixed keystream, so recovering it from a known (plaintext, ciphertext) pair
// decrypts item=vault (FLAG_3).
Route::get('/exports/encrypted', [ExportController::class, 'encrypted'])->middleware('auth');

Route::middleware('auth')->group(function () {
    Route::get('/products',              [ProductController::class, 'index']);
    Route::get('/products/search',       [ProductController::class, 'search']);

    // flag_1 (A01 IDOR/BOLA): auth-required report objects; the detail route omits
    // the per-object owner check (see ReportController::show).
    Route::get('/reports/mine',  [ReportController::class, 'mine']);
    Route::get('/reports/{id}',  [ReportController::class, 'show']);
});

// flag_5: admin-only orders report, gated purely on the API bearer token's role
// claim — no session/role middleware, so an alg:none token forgery is the gate.
Route::get('/admin/orders/report', [AdminController::class, 'ordersReport']);
