<?php
/**
 * stats_dashboard.php — live ERCOT market & grid dashboard feed for the
 * Power.Talks "Stats Illustrator" homepage.
 *
 * Reads ALL data on each request straight from the local MySQL `stats_illustrator`
 * schema, through its ERCOT report tables, and returns chart-ready JSON. No
 * snapshot, no generate step — the page always reflects the current tables.
 *
 * Four full-width charts:
 *   a) DAM (hourly) vs SCED (15-min) settlement-point prices at HB_BUSAVG
 *   b) AS MCPCs — one series set per type (DAM hourly vs SCED interval)
 *   c) actual load stacked by forecast zone + day-ahead load forecast
 *   d) top-20 congestion rents, DAM and SCED computed independently
 *
 * Served at:  http://localhost/Power.Talks/html/api/stats_dashboard.php[?date=YYYY-MM-DD]
 * Credentials reused from Database Codes/ercot_api/db_config.json. Read-only.
 */

header('Content-Type: application/json');
header('Cache-Control: no-store');

mysqli_report(MYSQLI_REPORT_ERROR | MYSQLI_REPORT_STRICT);

/** Rows for a query with one bound `date` string param. */
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

/** Fractional hour-ending from deliveryhour (1..24) + deliveryinterval (1..4). */
function frac_he($dh, $di) { return round(((int)$dh - 1) + ((int)$di) / 4, 2); }

function r2($v) { return $v === null ? null : round((float)$v, 2); }  // prices
function r1($v) { return $v === null ? null : round((float)$v, 1); }  // MW / rents

try {
    $cfgPath = __DIR__ . '/../../Database Codes/ercot_api/db_config.json';
    $cfg = json_decode(file_get_contents($cfgPath), true);
    if (!$cfg) { throw new RuntimeException("could not read db_config.json"); }

    $db = new mysqli($cfg['host'], $cfg['user'], $cfg['password'],
                     $cfg['database'], (int)$cfg['port']);
    $db->set_charset('utf8mb4');

    // ── target day: latest deliverydate common to the DAM anchor tables ───────
    $date = null;
    if (isset($_GET['date']) && preg_match('/^\d{4}-\d{2}-\d{2}$/', $_GET['date'])) {
        $date = $_GET['date'];
    } else {
        $res = $db->query(
            "SELECT LEAST(
                (SELECT MAX(deliverydate) FROM np4_190_cd_dam_settlement_point_prices),
                (SELECT MAX(deliverydate) FROM np4_188_cd_dam_clearing_prices_for_capacity),
                (SELECT MAX(deliverydate) FROM np4_191_cd_dam_shadow_prices),
                (SELECT MAX(deliverydate) FROM gen_55_cd_hourly_real_time_load_vs_actual_report)
             ) AS d"
        );
        $date = $res->fetch_assoc()['d'] ?? null;
    }
    if (!$date) { throw new RuntimeException("no data available to pick a target day"); }

    $out = ['generated_at' => date('c'), 'date' => $date];

    // ── (a) settlement-point prices at HB_BUSAVG ──────────────────────────────
    $damP = array_fill(0, 24, null);
    foreach (rows($db,
        "SELECT hourending AS he, AVG(settlementpointprice) AS val
           FROM np4_190_cd_dam_settlement_point_prices
          WHERE settlementpoint = 'HB_BUSAVG' AND deliverydate = ?
          GROUP BY hourending", $date) as $r) {
        $damP[he_index($r['he']) - 1] = r2($r['val']);
    }
    $scedX = []; $scedP = [];
    foreach (rows($db,
        "SELECT deliveryhour AS dh, deliveryinterval AS di, settlementpointprice AS val
           FROM np6_905_cd_settlement_point_prices_at_resource_node
          WHERE settlementpointname = 'HB_BUSAVG' AND content_date = ?
          ORDER BY (deliveryhour + 0), (deliveryinterval + 0)", $date) as $r) {
        $scedX[] = frac_he($r['dh'], $r['di']);
        $scedP[] = r2($r['val']);
    }
    $out['prices_hub'] = [
        'point' => 'HB_BUSAVG',
        'dam'   => ['hours' => range(1, 24), 'price' => $damP],
        'sced'  => ['x' => $scedX, 'price' => $scedP],
    ];

    // ── (b) AS MCPCs by type (DAM hourly vs SCED interval) ────────────────────
    $types = ['REGUP', 'REGDN', 'RRS', 'ECRS', 'NSPIN'];
    $series = [];
    foreach ($types as $t) $series[$t] = ['dam' => array_fill(0, 24, null), 'rt_x' => [], 'rt' => []];
    foreach (rows($db,
        "SELECT ancillarytype AS t, hourending AS he, AVG(mcpc) AS val
           FROM np4_188_cd_dam_clearing_prices_for_capacity
          WHERE deliverydate = ?
          GROUP BY ancillarytype, hourending", $date) as $r) {
        $k = strtoupper(trim($r['t']));
        if (isset($series[$k])) $series[$k]['dam'][he_index($r['he']) - 1] = r2($r['val']);
    }
    foreach (rows($db,
        "SELECT astype AS t, deliveryhour AS dh, deliveryinterval AS di, mcpc AS val
           FROM np6_331_cd_real_time_clearing_prices_for_capacity_b
          WHERE content_date = ?
          ORDER BY astype, (deliveryhour + 0), (deliveryinterval + 0)", $date) as $r) {
        $k = strtoupper(trim($r['t']));
        if (isset($series[$k])) { $series[$k]['rt_x'][] = frac_he($r['dh'], $r['di']); $series[$k]['rt'][] = r2($r['val']); }
    }
    $out['as_mcpc'] = ['types' => $types, 'hours' => range(1, 24), 'series' => $series];

    // ── (c) actual load by forecast zone (stacked) + day-ahead forecast ───────
    $zones = ['North', 'South', 'West', 'Houston'];
    $zcol  = ['North' => 'north', 'South' => 'south', 'West' => 'west', 'Houston' => 'houston'];
    $stacks = [];
    foreach ($zones as $z) $stacks[$z] = array_fill(0, 24, null);
    foreach (rows($db,
        "SELECT hourending AS he, north, south, west, houston
           FROM np6_346_cd_actual_system_load_by_forecast_zone
          WHERE operday = ?", $date) as $r) {
        $i = he_index($r['he']) - 1;
        foreach ($zones as $z) $stacks[$z][$i] = r1($r[$zcol[$z]]);
    }
    $forecast = array_fill(0, 24, null);
    foreach (rows($db,
        "SELECT hourending AS he, dayaheadforecast AS val
           FROM gen_55_cd_hourly_real_time_load_vs_actual_report
          WHERE deliverydate = ?", $date) as $r) {
        $forecast[he_index($r['he']) - 1] = r1($r['val']);
    }
    $out['load_zone'] = [
        'hours' => range(1, 24), 'zones' => $zones,
        'stacks' => $stacks, 'forecast' => $forecast,
    ];

    // ── (d) congestion rents — DAM and SCED, top 20 each, independent ─────────
    $topN = function ($rowset) {
        return array_map(function ($r) {
            return ['from' => $r['f'], 'to' => $r['t'], 'rent' => r1($r['rent'])];
        }, $rowset);
    };
    $damC = rows($db,
        "SELECT fromstation AS f, tostation AS t, SUM(shadowprice * constraintvalue) AS rent
           FROM np4_191_cd_dam_shadow_prices
          WHERE deliverydate = ? AND fromstation IS NOT NULL AND fromstation <> ''
          GROUP BY fromstation, tostation
          ORDER BY rent DESC LIMIT 20", $date);
    $scedC = rows($db,
        "SELECT fromstation AS f, tostation AS t, SUM(shadowprice * `value`) * (5/60) AS rent
           FROM np6_86_cd_sced_shadow_prices_and_binding_transmiss
          WHERE content_date = ? AND fromstation IS NOT NULL AND fromstation <> ''
          GROUP BY fromstation, tostation
          ORDER BY rent DESC LIMIT 20", $date);
    $out['congestion'] = ['dam' => $topN($damC), 'sced' => $topN($scedC)];

    echo json_encode($out);
    $db->close();

} catch (\Throwable $e) {
    http_response_code(500);
    echo json_encode(['error' => $e->getMessage()]);
}
