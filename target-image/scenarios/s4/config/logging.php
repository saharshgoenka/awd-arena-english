<?php

return [
    'default' => env('LOG_CHANNEL', 'stderr'),

    'channels' => [
        'stderr' => [
            'driver'    => 'monolog',
            'handler'   => Monolog\Handler\StreamHandler::class,
            'formatter' => env('LOG_STDERR_FORMATTER'),
            'with'      => ['stream' => 'php://stderr'],
            'level'     => env('LOG_LEVEL', 'debug'),
        ],
        'stack' => [
            'driver'   => 'stack',
            'channels' => ['stderr'],
        ],
    ],
];
