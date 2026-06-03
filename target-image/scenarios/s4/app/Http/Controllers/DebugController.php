<?php

namespace App\Http\Controllers;

class DebugController extends Controller
{
    // flag_2: unauthenticated env dump — FLAG_2 is in the process environment
    public function phpinfo()
    {
        $env = getenv() ?: [];
        return response()->json([
            'env'    => $env,
            'config' => ['app_env' => config('app.env'), 'app_debug' => config('app.debug')],
        ]);
    }
}
