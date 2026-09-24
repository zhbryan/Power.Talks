<?php
/**
 * stats_dashboard.php — live ERCOT market & grid dashboard feed for the
 * Power.Talks "Stats Illustrator" homepage.
 *
 * Reads ALL data on each request straight from the local MySQL `stats_illustrator`
 * schema, through its ERCOT report tables, and returns chart-ready JSON. No
 * snapshot, no generate step — the page always reflects the current tables.
 *
 * Served at:  http://localhost/Power.Talks/html/api/stats_dashboard.php[?date=YYYY-MM-DD]
 *
 * Credentials are reused from Database Codes/ercot_api/db_config.json (the same
 * config the Python tools use), so they live in one place.
 *
 * Read-only: SELECTs only, date param bound via prepared statements.
 */

header('Content-Type: application/json');
header('Cache-Control: no-store');

mysqli_report(MYSQLI_REPORT_ERROR | MYSQLI_REPORT_STRICT); // exceptions on error

/** Fetch rows for a query with a single bound `date` string param. */
function rows(mysqli $db, string $sql, string $date): array {
    $st = $db->prepare($sql);
    $st->bind_param('s', $date);
    $st->execute();
    $res = $st->get_result();
    $out = [];
    while ($r = $res->fetch_assoc()) { $out[] = $r; }
    $st->close();
    return $out;
}

/** Normalize an hour-ending value ('1', '01', '01:00', '24:00') to 1..24. */
function he_index($v): int {
    $h = (int)$v;                 // (int)'01:00' === 1, (int)'24:00' === 24
    if ($h < 1)  $h = 1;
    if ($h > 24) $h = 24;
    return $h;
}

function r2($v) { return $v === null ? null : round((float)$v, 2); }  // prices / $
function r1($v) { return $v === null ? null : round((float)$v, 1); }  // MW / rents

try {
    // ── connect (credentials from the shared Python config) ───────────────────
    $cfgPath = __DIR__ . '/../../Database Codes/ercot_api/db_config.json';
    $cfg = json_decode(file_get_contents($cfgPath), true);
    if (!$cfg) { throw new RuntimeException("could not read db_config.json"); }

    $db = new mysqli($cfg['host'], $cfg['user'], $cfg['password'],
                     $cfg['database'], (int)$cfg['port']);
    $db->set_charset('utf8mb4');

    // ── resolve the target day ────────────────────────────────────────────────
    // Optional ?date=YYYY-MM-DD override (validated); else the latest day common
    // to the DAM-settled, SCED real-time, and actual-demand tables.
    $date = null;
    if (isset($_GET['date']) && preg_match('/^\d{4}-\d{2}-\d{2}$/', $_GET['date'])) {
        $date = $_GET['date'];
    } else {
        $res = $db->query(
            "SELECT LEAST(
                (SELECT MAX(deliverydate) FROM np4_523_cd_dam_system_lambda),
                (SELECT MAX(content_date)  FROM np6_322_cd_sced_system_lambda),
                (SELECT MAX(deliverydate)  FROM np6_235_cd_system_wide_demand)
             ) AS d"
        );
        $date = $res->fetch_assoc()['d'] ?? null;
    }
    if (!$date) { throw new RuntimeException("no data available to pick a target day"); }

    $out = [
        'generated_at' => date('c'),
        'date'         => $date,
        'notes'        => [
            'available_capacity' =>
                'available capacity = actual system demand + online headroom '
              . '(NP6-328 capregup_rrs_ecrs_nspintotal, avg per hour) — approximate.',
            'congestion' =>
                'rent = shadowPrice x constraintValue, summed over the day; '
              . 'SCED 5-min rents scaled by 5/60 to an hourly-equivalent.',
        ],
    ];

    // ── (a) DAM vs SCED energy prices ($/MWh, by hour ending) ─────────────────
    $dam = array_fill(0, 24, null);
    $sced = array_fill(0, 24, null);
    foreach (rows($db,
        "SELECT hourending AS he, AVG(systemlambda) AS val
           FROM np4_523_cd_dam_system_lambda
          WHERE deliverydate = ?
          GROUP BY hourending", $date) as $r) {
        $dam[he_index($r['he']) - 1] = r2($r['val']);
    }
    // scedtimestamp is a varchar in 'MM/DD/YYYY HH:MM:SS' — parse before HOUR().
    foreach (rows($db,
        "SELECT (HOUR(STR_TO_DATE(scedtimestamp, '%m/%d/%Y %H:%i:%s')) + 1) AS he,
                AVG(cappedsystemlambda) AS val
           FROM np6_322_cd_sced_system_lambda
          WHERE content_date = ?
          GROUP BY he", $date) as $r) {
        if ($r['he'] === null) continue;
        $sced[he_index($r['he']) - 1] = r2($r['val']);
    }
    $out['energy_prices'] = ['hours' => range(1, 24), 'dam' => $dam, 'sced' => $sced];

    // ── (b) DAM vs SCED ancillary-service MCPCs by type ($/MW) ────────────────
    $types = ['REGUP', 'REGDN', 'RRS', 'ECRS', 'NSPIN'];
    $damM = array_fill_keys($types, null);
    $rtM  = array_fill_keys($types, null);
    foreach (rows($db,
        "SELECT ancillarytype AS t, AVG(mcpc) AS val
           FROM np4_188_cd_dam_clearing_prices_for_capacity
          WHERE deliverydate = ?
          GROUP BY ancillarytype", $date) as $r) {
        $k = strtoupper(trim($r['t']));
        if (array_key_exists($k, $damM)) $damM[$k] = r2($r['val']);
    }
    // np6_331's normalized date column is content_date (deliverydate is the raw
    // 'MM/DD/YYYY' report field).
    foreach (rows($db,
        "SELECT astype AS t, AVG(mcpc) AS val
           FROM np6_331_cd_real_time_clearing_prices_for_capacity_b
          WHERE content_date = ?
          GROUP BY astype", $date) as $r) {
        $k = strtoupper(trim($r['t']));
        if (array_key_exists($k, $rtM)) $rtM[$k] = r2($r['val']);
    }
    $out['as_mcpc'] = [
        'types' => $types,
        'dam'   => array_values($damM),
        'rt'    => array_values($rtM),
    ];

    // ── (c) load forecast vs actual vs available capacity (MW, by hour) ───────
    $forecast = array_fill(0, 24, null);
    $actual   = array_fill(0, 24, null);
    $headroom = array_fill(0, 24, null);
    // Forecast: system total from the in-use model for the day.
    foreach (rows($db,
        "SELECT hourending AS he, AVG(systemtotal) AS val
           FROM np3_565_cd_seven_day_load_forecast_by_model_and_wea
          WHERE deliverydate = ? AND inuseflag = 'Y'
          GROUP BY hourending", $date) as $r) {
        $forecast[he_index($r['he']) - 1] = r1($r['val']);
    }
    // Actual system-wide demand — sub-hourly (timeending 'HH:MM' varchar), so
    // average to hour ending.
    foreach (rows($db,
        "SELECT (HOUR(STR_TO_DATE(timeending, '%H:%i')) + 1) AS he, AVG(demand) AS val
           FROM np6_235_cd_system_wide_demand
          WHERE deliverydate = ?
          GROUP BY he", $date) as $r) {
        if ($r['he'] === null) continue;
        $actual[he_index($r['he']) - 1] = r1($r['val']);
    }
    // Online headroom (available-but-not-deployed) averaged per hour.
    // scedtimestamp is 'MM/DD/YYYY HH:MM:SS' varchar — parse before HOUR().
    foreach (rows($db,
        "SELECT (HOUR(STR_TO_DATE(scedtimestamp, '%m/%d/%Y %H:%i:%s')) + 1) AS he,
                AVG(capregup_rrs_ecrs_nspintotal) AS val
           FROM np6_328_cd_total_capability_of_resources_available
          WHERE content_date = ?
          GROUP BY he", $date) as $r) {
        if ($r['he'] === null) continue;
        $headroom[he_index($r['he']) - 1] = (float)$r['val'];
    }
    // available capacity = actual demand + headroom (only where both known).
    $available = array_fill(0, 24, null);
    for ($i = 0; $i < 24; $i++) {
        if ($actual[$i] !== null && $headroom[$i] !== null) {
            $available[$i] = r1($actual[$i] + $headroom[$i]);
        }
    }
    $out['load_capacity'] = [
        'hours'     => range(1, 24),
        'forecast'  => $forecast,
        'actual'    => $actual,
        'available' => $available,
    ];

    // ── (d) top-20 DAM vs SCED congestion rents by fromStation -> toStation ───
    $rent = [];  // key "from||to" => ['from','to','dam','sced']
    $key = function ($f, $t) { return $f . '||' . $t; };
    foreach (rows($db,
        "SELECT fromstation AS f, tostation AS t,
                SUM(shadowprice * constraintvalue) AS rent
           FROM np4_191_cd_dam_shadow_prices
          WHERE deliverydate = ? AND fromstation IS NOT NULL AND fromstation <> ''
          GROUP BY fromstation, tostation", $date) as $r) {
        $k = $key($r['f'], $r['t']);
        $rent[$k] = ['from' => $r['f'], 'to' => $r['t'],
                     'dam' => (float)$r['rent'], 'sced' => 0.0];
    }
    foreach (rows($db,
        "SELECT fromstation AS f, tostation AS t,
                SUM(shadowprice * `value`) * (5/60) AS rent
           FROM np6_86_cd_sced_shadow_prices_and_binding_transmiss
          WHERE content_date = ? AND fromstation IS NOT NULL AND fromstation <> ''
          GROUP BY fromstation, tostation", $date) as $r) {
        $k = $key($r['f'], $r['t']);
        if (!isset($rent[$k])) {
            $rent[$k] = ['from' => $r['f'], 'to' => $r['t'], 'dam' => 0.0, 'sced' => 0.0];
        }
        $rent[$k]['sced'] = (float)$r['rent'];
    }
    $rows = array_values($rent);
    usort($rows, function ($a, $b) {   // rank by the larger of the two rents
        return max($b['dam'], $b['sced']) <=> max($a['dam'], $a['sced']);
    });
    $out['congestion'] = array_map(function ($x) {
        return ['from' => $x['from'], 'to' => $x['to'],
                'dam' => r1($x['dam']), 'sced' => r1($x['sced'])];
    }, array_slice($rows, 0, 20));

    echo json_encode($out);
    $db->close();

} catch (\Throwable $e) {
    http_response_code(500);
    echo json_encode(['error' => $e->getMessage()]);
}
