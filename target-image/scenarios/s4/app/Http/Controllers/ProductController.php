<?php

namespace App\Http\Controllers;

use App\Models\Flag;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;

class ProductController extends Controller
{
    public function index()
    {
        $products = DB::table('products')->get();
        return response()->json(['products' => $products]);
    }

    // flag_4: raw SQL with string interpolation
    public function search(Request $request)
    {
        $q = $request->input('q', '');
        $results = DB::select("SELECT id, name, description FROM products WHERE name LIKE '%{$q}%'");
        return response()->json(['results' => $results]);
    }

    // flag_3 target: analyst-only endpoint
    public function secretVault(Request $request)
    {
        if ($request->user()->username !== 'analyst') {
            return response()->json(['error' => 'Access restricted'], 403);
        }
        $flag = Flag::where('name', 'flag_3')->first();
        return response()->json(['secret' => $flag->value]);
    }
}
