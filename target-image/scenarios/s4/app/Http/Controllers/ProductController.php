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
}
