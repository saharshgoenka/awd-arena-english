<?php

namespace App\Http\Controllers;

use App\Support\ApiToken;
use Illuminate\Http\Request;

class AdminController extends Controller
{
    // flag_5 target: admin-only orders report. Access is granted purely on the
    // `role` claim of the API bearer token (see App\Support\ApiToken). A real
    // low-priv token carries role=staff and gets 403 here — an alg:none forgery
    // that sets role=admin is required.
    public function ordersReport(Request $request)
    {
        $auth = (string) $request->header('Authorization', '');
        if (!str_starts_with($auth, 'Bearer ')) {
            return response()->json(['error' => 'Bearer token required'], 401);
        }
        $claims = ApiToken::verify(substr($auth, 7));
        if (!$claims) {
            return response()->json(['error' => 'Invalid token'], 401);
        }
        if (($claims['role'] ?? '') !== 'admin') {
            return response()->json(['error' => 'Forbidden'], 403);
        }
        // env, not the injectable flags table (only flag_4 lives in the DB)
        $flag = getenv('FLAG_5') ?: 'FLAG{missing}';
        return response()->json([
            'report'        => 'Monthly Orders Summary',
            'total_orders'  => 142,
            'revenue'       => 28450.00,
            'internal_ref'  => $flag,
        ]);
    }
}
