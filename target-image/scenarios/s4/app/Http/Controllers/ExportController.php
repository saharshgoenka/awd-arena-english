<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;

class ExportController extends Controller
{
    // flag_3 (A02 Cryptographic Failure — reused-keystream / many-time pad): every
    // encrypted export is XORed with the SAME fixed keystream (no per-message
    // nonce/IV). Recover the keystream from any known (plaintext, ciphertext) pair and
    // decrypt the vault. Both the target and an attacker need only stdlib XOR — no
    // crypto library, no cracking.
    //   item=<report id owned by caller> -> encrypts that report body (also readable at
    //     /reports/mine), giving a known-plaintext pair >= 40 bytes.
    //   item=vault -> encrypts FLAG_3 (read from env at serve time, never persisted, so
    //     the flag_4 UNION SQLi cannot dump it). Same keystream for all -> recoverable.
    private function keystream(): string
    {
        // sha256("shopadmin-export-key-2024") repeated to 256 bytes, fixed.
        return str_repeat(hash('sha256', 'shopadmin-export-key-2024', true), 8);
    }

    private function xorExport(string $pt): string
    {
        $ks = $this->keystream();
        $out = '';
        for ($i = 0, $n = strlen($pt); $i < $n; $i++) {
            $out .= sprintf('%02x', ord($pt[$i]) ^ ord($ks[$i]));
        }
        return $out;
    }

    // GET /exports/encrypted?item=<id|vault>
    public function encrypted(Request $request)
    {
        $item = $request->query('item', '');
        if ($item === 'vault') {
            $pt = getenv('FLAG_3') ?: 'FLAG{missing}';
        } else {
            $row = DB::table('reports')
                ->where('id', $item)
                ->where('owner', $request->user()->username)
                ->first();
            if (!$row) {
                return response()->json(['error' => 'unknown item'], 404);
            }
            $pt = $row->body;
        }
        $out = ['item' => $item, 'cipher_hex' => $this->xorExport($pt)];
        if ($item !== 'vault') {
            // self-contained crib for the reused-keystream recovery
            $out['plaintext'] = $pt;
        }
        return response()->json($out);
    }
}
