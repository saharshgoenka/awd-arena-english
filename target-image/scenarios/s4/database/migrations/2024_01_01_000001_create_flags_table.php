<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('flags', function (Blueprint $table) {
            $table->id();
            $table->string('name')->unique();
            $table->string('value', 100);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('flags');
    }
};
