<?php

namespace App\Http\Controllers;

class DebugController extends Controller
{
    // flag_2: unauthenticated env dump — FLAG_2 is in the process environment.
    // BOUNDED to FLAG_2 only: dumping every FLAG_* leaked all 5 flags at once.
    public function phpinfo()
    {
        $env = array_filter(
            getenv() ?: [],
            fn ($k) => !(str_starts_with($k, 'FLAG_') && $k !== 'FLAG_2'),
            ARRAY_FILTER_USE_KEY
        );
        return response()->json([
            'env'    => $env,
            'config' => ['app_env' => config('app.env'), 'app_debug' => config('app.debug')],
        ]);
    }
}
