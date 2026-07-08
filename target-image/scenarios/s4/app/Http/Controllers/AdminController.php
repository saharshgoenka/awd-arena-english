<?php

namespace App\Http\Controllers;

use App\Models\Flag;
use Illuminate\Support\Facades\Auth;

class AdminController extends Controller
{
    // flag_1: no auth check — route has no middleware
    public function panel()
    {
        // env, not the injectable flags table (only flag_4 lives in the DB)
        $flag = (object) ['value' => getenv('FLAG_1') ?: 'FLAG{missing}'];
        return view('admin.panel', ['flag' => $flag->value]);
    }

    // flag_5 target: admin-only orders report
    public function ordersReport()
    {
        if (Auth::user()->role !== 'admin') {
            abort(403, 'Forbidden');
        }
        // env, not the injectable flags table (only flag_4 lives in the DB)
        $flag = (object) ['value' => getenv('FLAG_5') ?: 'FLAG{missing}'];
        return response()->json([
            'report'        => 'Monthly Orders Summary',
            'total_orders'  => 142,
            'revenue'       => 28450.00,
            'internal_ref'  => $flag->value,
        ]);
    }
}
