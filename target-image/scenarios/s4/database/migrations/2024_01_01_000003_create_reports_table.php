<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        // flag_1 (A01 Broken Access Control -> IDOR/BOLA): per-user report objects
        // addressed by a non-guessable id. A low-priv user's own report references a
        // higher-priv (admin escalation) report id; the detail endpoint omits the
        // per-object owner check.
        Schema::create('reports', function (Blueprint $table) {
            $table->integer('id')->primary();
            $table->string('owner');
            $table->string('title');
            $table->text('body');
            $table->integer('escalation_ref')->nullable();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('reports');
    }
};
