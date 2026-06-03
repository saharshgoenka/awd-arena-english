<?php

namespace Database\Seeders;

use App\Models\Flag;
use App\Models\User;
use Illuminate\Database\Seeder;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Hash;

class DatabaseSeeder extends Seeder
{
    public function run(): void
    {
        // Seed flags from environment variables (injected by supervisord at runtime)
        $placeholder = 'FLAG{00000000000000000000000000000000}';
        for ($i = 1; $i <= 5; $i++) {
            Flag::updateOrCreate(
                ['name' => "flag_{$i}"],
                ['value' => env("FLAG_{$i}", $placeholder)]
            );
        }

        // Seed users: bcrypt for Auth::attempt, MD5 in password_legacy (flag_3 exposure)
        $users = [
            [
                'name'            => 'Admin',
                'username'        => 'admin',
                'email'           => 'admin@shopadmin.local',
                'password'        => Hash::make('shopadmin2024'),
                'password_legacy' => md5('shopadmin2024'),
                'role'            => 'admin',
            ],
            [
                'name'            => 'Analyst',
                'username'        => 'analyst',
                'email'           => 'analyst@shopadmin.local',
                'password'        => Hash::make('password123'),
                'password_legacy' => md5('password123'),
                'role'            => 'user',
            ],
            [
                'name'            => 'Staff',
                'username'        => 'staff',
                'email'           => 'staff@shopadmin.local',
                'password'        => Hash::make('staff789'),
                'password_legacy' => md5('staff789'),
                'role'            => 'staff',
            ],
        ];
        foreach ($users as $data) {
            User::updateOrCreate(['username' => $data['username']], $data);
        }

        // Seed products
        $products = [
            ['name' => 'Wireless Headphones',   'description' => 'Premium noise-cancelling over-ear headphones', 'price' => 89.99,  'sku' => 'WH-001'],
            ['name' => 'USB-C Hub 7-Port',       'description' => 'Multiport adapter with HDMI and Ethernet',     'price' => 34.99,  'sku' => 'UC-007'],
            ['name' => 'Mechanical Keyboard',    'description' => 'Tenkeyless with Cherry MX Blue switches',      'price' => 129.00, 'sku' => 'MK-TKL'],
            ['name' => 'Ergonomic Mouse',        'description' => 'Vertical grip design, 6 programmable buttons', 'price' => 45.50,  'sku' => 'EM-V6'],
            ['name' => 'Monitor Stand',          'description' => 'Adjustable aluminum desk mount',               'price' => 59.99,  'sku' => 'MS-ADJ'],
            ['name' => 'Webcam HD 1080p',        'description' => 'Built-in ring light, auto-focus',             'price' => 72.00,  'sku' => 'WC-1080'],
            ['name' => 'Laptop Sleeve 15"',      'description' => 'Water-resistant neoprene sleeve',              'price' => 19.99,  'sku' => 'LS-15W'],
            ['name' => 'Cable Management Kit',   'description' => 'Velcro straps and cable clips bundle',         'price' => 12.49,  'sku' => 'CM-KIT'],
            ['name' => 'Portable SSD 1TB',       'description' => 'USB 3.2 Gen2, 1000 MB/s read',                'price' => 99.00,  'sku' => 'PS-1TB'],
            ['name' => 'Smart Power Strip',      'description' => '6 outlets with surge protection and USB',      'price' => 27.95,  'sku' => 'SP-6U'],
        ];
        foreach ($products as $p) {
            DB::table('products')->updateOrInsert(['sku' => $p['sku']], $p);
        }
    }
}
