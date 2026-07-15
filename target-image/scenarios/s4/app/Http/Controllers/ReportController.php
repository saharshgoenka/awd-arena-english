<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;

class ReportController extends Controller
{
    // The escalation report stores a placeholder; the real flag is substituted from
    // the environment at serve time so it is never persisted in SQLite (keeps it out
    // of reach of the flag_4 UNION SQLi, which can only dump table contents).
    private function serialize($row): array
    {
        $body = str_replace('__FLAG_1__', getenv('FLAG_1') ?: 'FLAG{missing}', $row->body);
        return [
            'id'             => $row->id,
            'owner'          => $row->owner,
            'title'          => $row->title,
            'body'           => $body,
            'escalation_ref' => $row->escalation_ref,
        ];
    }

    // GET /reports/mine — the caller's own report (references a related report id)
    public function mine(Request $request)
    {
        $row = DB::table('reports')
            ->where('owner', $request->user()->username)
            ->orderBy('id')
            ->first();
        if (!$row) {
            return response()->json(['error' => 'No report for this account'], 404);
        }
        return response()->json(['report' => $this->serialize($row)]);
    }

    // GET /reports/{id} — flag_1 (A01 IDOR/BOLA). Auth is enforced by route
    // middleware, but the per-object ownership check is MISSING, so any authenticated
    // caller can read any report by id — including the admin escalation record that
    // carries the flag. Unknown ids fail closed (404), so blind enumeration of the
    // large, non-sequential id space does not yield the flag; the winning id must be
    // derived from the escalation_ref in the caller's own report.
    public function show(Request $request, $id)
    {
        $row = DB::table('reports')->where('id', $id)->first();
        if (!$row) {
            return response()->json(['error' => 'Report not found'], 404);
        }
        // MISSING per-object authorization: should verify
        // $row->owner === $request->user()->username (or an explicit share).
        return response()->json(['report' => $this->serialize($row)]);
    }
}
