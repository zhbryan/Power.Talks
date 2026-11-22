<?php
/**
 * gallery.php — live feed for the Power.Talks "Gallery" section.
 *
 * Reads the local MySQL `gallery` schema on every request (no snapshot step):
 *   keyword_id       — canonical ERCOT market vocabulary, generated nightly from
 *                      Database Codes/reference_info/ercot_market_keywords.md
 *   gallery_keywords — keyword <-> chart links
 *   gallery_charts   — one row per chart PNG extracted to Documents Database/GALLERY
 *
 * Actions:
 *   ?action=keywords              → the whole vocabulary + per-keyword chart count.
 *                                   Small (~93 rows), so the page fetches it once and
 *                                   filters hint words client-side for instant suggestions.
 *   ?action=charts&keyword_id=ID  → charts carrying that keyword (chart_id + title + source)
 *   ?action=chart&chart_id=ID     → one chart's full record, its PNG url, and its keywords
 *
 * Served at:  http://localhost/Power.Talks/html/api/gallery.php?action=keywords
 * Credentials reused from Database Codes/ercot_api/db_config.json. Read-only.
 */

header('Content-Type: application/json');
header('Cache-Control: no-store');

mysqli_report(MYSQLI_REPORT_ERROR | MYSQLI_REPORT_STRICT);

const GALLERY_SCHEMA = 'gallery';

/** Rows for a query with optional bound params (string-typed). */
function q(mysqli $db, string $sql, array $params = []): array {
    $st = $db->prepare($sql);
    if ($params) { $st->bind_param(str_repeat('s', count($params)), ...$params); }
    $st->execute();
    $res = $st->get_result();
    $out = [];
    while ($r = $res->fetch_assoc()) { $out[] = $r; }
    $st->close();
    return $out;
}

/**
 * gallery_charts.doc_group holds a committee acronym. Spell it out for the
 * "meeting name" line: the downloader's own registry first (it keeps learning
 * new groups), then this org-chart fallback, then the acronym itself.
 */
function group_names(): array {
    static $map = null;
    if ($map !== null) { return $map; }
    $map = [
        'BOARD' => 'ERCOT Board of Directors',
        'FA'    => 'Finance & Audit Committee',
        'HRG'   => 'Human Resources & Governance Committee',
        'TS'    => 'Technology & Security Committee',
        'TAC'   => 'Technical Advisory Committee',
        'PRS'   => 'Protocol Revisions Subcommittee',
        'ROS'   => 'Reliability and Operations Subcommittee',
        'RMS'   => 'Retail Market Subcommittee',
        'WMS'   => 'Wholesale Market Subcommittee',
        'COPS'  => 'Commercial Operations Subcommittee',
        'CMWG'  => 'Congestion Management Working Group',
        'DSWG'  => 'Demand Side Working Group',
        'SAWG'  => 'Supply Analysis Working Group',
        'WMWG'  => 'Wholesale Market Working Group',
        'BSWG'  => 'Black Start Working Group',
        'DWG'   => 'Dynamics Working Group',
        'IBRWG' => 'Inverter-Based Resources Working Group',
        'MWG'   => 'Meter Working Group',
        'NDSWG' => 'Network Data Support Working Group',
        'OWG'   => 'Operations Working Group',
        'OTWG'  => 'Operations Training Working Group',
        'PDCWG' => 'Performance, Disturbance, Compliance Working Group',
        'PLWG'  => 'Planning Working Group',
        'SPWG'  => 'System Protection Working Group',
        'SSWG'  => 'Steady State Working Group',
        'VPWG'  => 'Voltage Profile Working Group',
        'CIPWG' => 'Critical Infrastructure Protection Working Group',
        'LLWG'  => 'Large Load Working Group',
        'CFSG'  => 'Credit Finance Sub Group',
        'TDTMS' => 'Texas Data Transport & MarkeTrans Services Working Group',
        'TXSETLP' => 'Texas SET / Load Profiling Working Group',
        'TXSET' => 'Texas SET Working Group (inactive)',
        'RMTTF' => 'Retail Market Training Task Force',
        'RTCBTF' => 'Real-Time Co-Optimization & Batteries Task Force',
        'IBRTF' => 'Inverter-Based Resources Task Force (inactive)',
        'BESTF' => 'Battery Energy Storage Task Force (inactive)',
    ];
    $reg = __DIR__ . '/../../Documents Database/ERCOT.STKHDR.MEETS/_committees.json';
    if (is_file($reg)) {
        $j = json_decode(file_get_contents($reg), true);
        foreach (($j['committees'] ?? []) as $abbr => $info) {
            if (!empty($info['name'])) { $map[strtoupper($abbr)] = $info['name']; }
        }
    }
    return $map;
}

function group_name($abbr): string {
    $a = strtoupper((string)$abbr);
    $m = group_names();
    return $m[$a] ?? ($a !== '' ? $a : '');
}

/** Web path of a chart PNG under the Apache document root. */
function png_url(string $chartId): string {
    return '/Power.Talks/Documents%20Database/GALLERY/' . rawurlencode($chartId) . '.png';
}

/** Absolute path of the same file, for an existence check. */
function png_path(string $chartId): string {
    return __DIR__ . '/../../Documents Database/GALLERY/' . $chartId . '.png';
}

/**
 * Where the chart's source document sits, relative to the stakeholder tree.
 *
 * The extractor walks  ERCOT.STKHDR.MEETS/<GROUP>/<YYYY-MM-DD>/<file>  and
 * stores those three components as doc_group / doc_time / doc_name
 * (parse_source_path in gallery_charts_extractions_generations.py), so the
 * download path is derived rather than stored — one less column to keep in
 * step when a document is re-filed. Every PDF in the tree is exactly that
 * deep, so there is no deeper case to handle.
 */
function doc_rel(array $c): string {
    $g = (string)($c['doc_group'] ?? '');
    $d = substr((string)($c['doc_time'] ?? ''), 0, 10);   // DATE or DATETIME
    $n = (string)($c['doc_name'] ?? '');
    if ($g === '' || $d === '' || $n === '') { return ''; }
    if (strpos($g . $d . $n, '..') !== false) { return ''; }
    return $g . '/' . $d . '/' . $n;
}

/**
 * Web path of the source document. Each segment is encoded on its own: real
 * file names in this tree carry spaces, '#', '&' and parentheses, and
 * encoding the joined path would swallow the slashes too.
 */
function doc_url(array $c): string {
    $rel = doc_rel($c);
    if ($rel === '') { return ''; }
    $enc = implode('/', array_map('rawurlencode', explode('/', $rel)));
    return '/Power.Talks/Documents%20Database/ERCOT.STKHDR.MEETS/' . $enc;
}

/** Absolute path of the same document, for an existence check. */
function doc_path(array $c): string {
    $rel = doc_rel($c);
    return $rel === ''
        ? ''
        : __DIR__ . '/../../Documents Database/ERCOT.STKHDR.MEETS/' . $rel;
}

try {
    $cfgPath = __DIR__ . '/../../Database Codes/ercot_api/db_config.json';
    $cfg = json_decode(file_get_contents($cfgPath), true);
    if (!$cfg) { throw new RuntimeException('could not read db_config.json'); }

    // The gallery schema must be one the config declares — the same guard the
    // Python side (sync_keyword_ids.py) applies.
    $known = isset($cfg['databases']) ? $cfg['databases'] : array($cfg['database']);
    if (!in_array(GALLERY_SCHEMA, $known, true)) {
        throw new RuntimeException('db_config.json does not list the "' . GALLERY_SCHEMA . '" schema');
    }

    $db = new mysqli($cfg['host'], $cfg['user'], $cfg['password'],
                     GALLERY_SCHEMA, (int)$cfg['port']);
    $db->set_charset('utf8mb4');

    $action = isset($_GET['action']) ? $_GET['action'] : 'keywords';
    $out = ['generated_at' => date('c'), 'action' => $action];

    if ($action === 'keywords') {
        // Whole vocabulary, each with the number of charts that carry it.
        // LEFT JOIN so terms with no charts yet are still searchable.
        // `status` is set by sync_keyword_ids.py from the curated vocabulary:
        // retired terms are kept in the table so their ids stay reserved, but
        // they are no longer offered for search. Candidate terms are real
        // vocabulary that has yet to match a chart; they carry a count of 0
        // and the page dims them.
        $rows = q($db,
            "SELECT k.keyword_id, k.term, k.acronym, k.category, k.description,
                    k.trending, k.facet, k.broader, k.glossary_ref, k.status,
                    COUNT(DISTINCT g.chart_id) AS chart_count
               FROM keyword_id k
               LEFT JOIN gallery_keywords g ON g.keyword_id = k.keyword_id
              WHERE k.status <> 'retired'
              GROUP BY k.keyword_id, k.term, k.acronym, k.category, k.description,
                       k.trending, k.facet, k.broader, k.glossary_ref, k.status
              ORDER BY chart_count DESC, k.term ASC");
        $out['keywords'] = array_map(function ($r) {
            return [
                'keyword_id'  => $r['keyword_id'],
                'term'        => $r['term'],
                'acronym'     => $r['acronym'],
                'category'    => $r['category'],
                'description' => $r['description'],
                'trending'    => (int)$r['trending'] === 1,
                'facet'       => $r['facet'],
                'broader'     => $r['broader'],
                'glossary_ref' => $r['glossary_ref'],
                'status'      => $r['status'],
                'chart_count' => (int)$r['chart_count'],
            ];
        }, $rows);
        $tot = $db->query("SELECT COUNT(*) AS c FROM gallery_charts")->fetch_assoc();
        $out['total_charts'] = (int)$tot['c'];

    } elseif ($action === 'charts') {
        $kid = isset($_GET['keyword_id']) ? $_GET['keyword_id'] : '';
        if (!preg_match('/^[0-9a-f]{12}$/', $kid)) {
            throw new RuntimeException('keyword_id must be 12 hex characters');
        }
        $kw = q($db, "SELECT keyword_id, term, acronym, category, description
                        FROM keyword_id WHERE keyword_id = ?", [$kid]);
        if (!$kw) { throw new RuntimeException('no such keyword_id'); }
        $out['keyword'] = $kw[0];

        // Newest meeting first; charts from one document keep in-document order.
        $rows = q($db,
            "SELECT c.chart_id, c.chart_title, c.doc_name, c.doc_type, c.doc_group,
                    c.doc_time, c.page_num, c.sequence_id
               FROM gallery_keywords g
               JOIN gallery_charts c ON c.chart_id = g.chart_id
              WHERE g.keyword_id = ?
              ORDER BY c.doc_time DESC, c.doc_name ASC, c.sequence_id ASC", [$kid]);
        $out['charts'] = array_map(function ($r) {
            return [
                'chart_id'    => $r['chart_id'],
                'chart_title' => $r['chart_title'],
                'doc_name'    => $r['doc_name'],
                'doc_type'    => $r['doc_type'],
                'doc_group'   => $r['doc_group'],
                'group_name'  => group_name($r['doc_group']),
                'doc_time'    => $r['doc_time'],
                'page_num'    => $r['page_num'],
                'image_url'   => png_url($r['chart_id']),
            ];
        }, $rows);

    } elseif ($action === 'chart') {
        $cid = isset($_GET['chart_id']) ? $_GET['chart_id'] : '';
        if (!preg_match('/^GC_\d{8}_\d{6}_\d+$/', $cid)) {
            throw new RuntimeException('chart_id must look like GC_YYYYMMDD_HHMMSS_N');
        }
        $rows = q($db,
            "SELECT chart_id, chart_title, doc_name, doc_type, doc_group, doc_time,
                    page_num, sequence_id, keywords, record_timestamp
               FROM gallery_charts WHERE chart_id = ?", [$cid]);
        if (!$rows) { throw new RuntimeException('no such chart_id'); }
        $c = $rows[0];

        // Keyword ids for this chart, so the page can pivot from a chart back
        // into another keyword. The chart's own `keywords` column is the JSON
        // array written at extraction time; the link table is authoritative.
        // `source` and `matched_in` record why the keyword is here: a literal
        // match in the chart's title/sheet/axis/document, or the model reading
        // the PDF page. It makes a wrong keyword traceable instead of magic.
        $links = q($db,
            "SELECT g.keyword_id, g.keyword, g.source, g.matched_in,
                    k.category, k.acronym
               FROM gallery_keywords g
               LEFT JOIN keyword_id k ON k.keyword_id = g.keyword_id
              WHERE g.chart_id = ? ORDER BY g.keyword ASC", [$cid]);

        // A document can be re-filed or pruned after extraction, so the panel
        // is told whether the file is actually there instead of offering a
        // download link that 404s.
        $docPath = doc_path($c);

        $out['chart'] = [
            'chart_id'         => $c['chart_id'],
            'chart_title'      => $c['chart_title'],
            'doc_name'         => $c['doc_name'],
            'doc_url'          => doc_url($c),
            'doc_exists'       => $docPath !== '' && is_file($docPath),
            'doc_type'         => $c['doc_type'],
            'doc_group'        => $c['doc_group'],
            'group_name'       => group_name($c['doc_group']),
            'doc_time'         => $c['doc_time'],
            'page_num'         => $c['page_num'],
            'sequence_id'      => (int)$c['sequence_id'],
            'record_timestamp' => $c['record_timestamp'],
            'image_url'        => png_url($c['chart_id']),
            'image_exists'     => is_file(png_path($c['chart_id'])),
            'keywords'         => $links,
        ];

    } else {
        throw new RuntimeException('unknown action: ' . $action);
    }

    echo json_encode($out);
    $db->close();

} catch (\Throwable $e) {
    http_response_code(500);
    echo json_encode(['error' => $e->getMessage()]);
}
