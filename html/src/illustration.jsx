// Animated waveform illustration — built from plain rects with CSS animations
function Waveform({ bars = 48, playing = true }) {
  // deterministic pseudo-random heights so re-renders don't reshuffle
  const heights = React.useMemo(() => {
    const out = [];
    let s = 1;
    for (let i = 0; i < bars; i++) {
      s = (s * 9301 + 49297) % 233280;
      const r = s / 233280;
      // rhythmic envelope
      const env = 0.35 + 0.55 * Math.abs(Math.sin(i * 0.28) * Math.cos(i * 0.11));
      out.push(0.15 + r * 0.4 + env * 0.5);
    }
    return out;
  }, [bars]);

  return (
    <div className="pt-wave" aria-hidden>
      <style>{`
        .pt-wave {
          display: flex; align-items: center; justify-content: center;
          gap: 3px; height: 92px; padding: 0 8px;
        }
        .pt-wave span {
          display: block; width: 4px; border-radius: 2px;
          background: linear-gradient(180deg, var(--accent), var(--accent-2));
          transform-origin: center;
          animation: pt-bar 1.8s ease-in-out infinite;
          opacity: .9;
        }
        .pt-wave.paused span { animation-play-state: paused; }
        @keyframes pt-bar {
          0%, 100% { transform: scaleY(.35); }
          50%      { transform: scaleY(1); }
        }
      `}</style>
      {heights.map((h, i) => (
        <span key={i}
          className={playing ? "" : "paused"}
          style={{
            height: `${Math.round(h * 88)}px`,
            animationDelay: `${(i * 47) % 1800}ms`,
            opacity: 0.5 + (h * 0.5),
          }}
        />
      ))}
    </div>
  );
}

// A content "illustration" panel — used inside a message as visual context
function TalkIllustration({ title, meta }) {
  const [playing, setPlaying] = React.useState(true);
  return (
    <div className="pt-illus">
      <style>{`
        .pt-illus {
          border: 1px solid var(--rule);
          background:
            radial-gradient(120% 80% at 0% 0%, var(--accent-soft) 0%, transparent 55%),
            linear-gradient(180deg, var(--panel), var(--bg-2));
          border-radius: var(--radius);
          padding: 20px;
          display: grid;
          grid-template-columns: 1fr auto;
          gap: 20px;
          align-items: center;
          box-shadow: var(--shadow-1);
          overflow: hidden;
          position: relative;
        }
        .pt-illus::before {
          content: "";
          position: absolute; inset: 0;
          background-image:
            repeating-linear-gradient(45deg, rgba(27,26,23,.03) 0 1px, transparent 1px 9px);
          pointer-events: none;
        }
        .pt-illus-meta { position: relative; }
        .pt-illus-eye {
          font-family: var(--mono); font-size: 10.5px; letter-spacing: .12em;
          color: var(--muted); text-transform: uppercase;
        }
        .pt-illus-title {
          font-family: var(--serif); font-size: 28px; line-height: 1.1;
          margin: 6px 0 8px; color: var(--ink); font-weight: 400;
        }
        .pt-illus-sub { color: var(--ink-2); font-size: 13px; }
        .pt-illus-wave {
          position: relative; min-width: 300px;
          border-left: 1px dashed var(--rule-2); padding-left: 18px;
        }
        .pt-illus-ctrl {
          display: flex; align-items: center; gap: 10px;
          margin-top: 10px; color: var(--muted);
          font-family: var(--mono); font-size: 11px;
        }
        .pt-illus-ctrl button {
          width: 28px; height: 28px; border-radius: 999px;
          background: var(--ink); color: var(--bg);
          display: grid; place-items: center;
          transition: transform .15s ease;
        }
        .pt-illus-ctrl button:hover { transform: scale(1.06); }
        .pt-pill {
          display: inline-flex; align-items: center; gap: 6px;
          padding: 2px 8px; border-radius: 999px;
          background: var(--accent-soft); color: var(--accent-2);
          font-size: 11px; font-weight: 500;
        }
        @media (max-width: 900px) {
          .pt-illus { grid-template-columns: 1fr; }
          .pt-illus-wave { border-left: 0; padding-left: 0; border-top: 1px dashed var(--rule-2); padding-top: 16px; }
        }
      `}</style>
      <div className="pt-illus-meta">
        <div className="pt-illus-eye">Now rehearsing</div>
        <h2 className="pt-illus-title">{title}</h2>
        <div className="pt-illus-sub">{meta}</div>
        <div style={{ marginTop: 14, display: "flex", gap: 8, flexWrap: "wrap" }}>
          <span className="pt-pill"><I.Target size={12} sw={2}/> exec audience</span>
          <span className="pt-pill" style={{ background: "transparent", border: "1px solid var(--rule-2)", color: "var(--ink-2)" }}>
            tone: candid, warm
          </span>
        </div>
      </div>
      <div className="pt-illus-wave">
        <Waveform playing={playing} />
        <div className="pt-illus-ctrl">
          <button onClick={() => setPlaying(p => !p)} aria-label={playing ? "Pause" : "Play"}>
            {playing
              ? <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="5" width="4" height="14" rx="1"/><rect x="14" y="5" width="4" height="14" rx="1"/></svg>
              : <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor"><path d="M7 5v14l12-7z"/></svg>}
          </button>
          <span>00:42 / 02:48</span>
          <span style={{ marginLeft: "auto", color: "var(--accent-2)" }}>▲ 147 wpm</span>
        </div>
      </div>
    </div>
  );
}

window.TalkIllustration = TalkIllustration;
window.Waveform = Waveform;

// Paper Trails — a grid of interactive rule/code buttons that open a detail pane
const PAPER_TRAIL_CODES = [
  { code: "NPRR",   name: "Nodal Protocol Revision Request",       count: 1287 },
  { code: "SCR",    name: "System Change Request",                  count: 412 },
  { code: "COPMGRR",name: "Commercial Ops Planning & Mkt Biz Req.", count: 58  },
  { code: "NOGRR",  name: "Nodal Operating Guide Revision Request", count: 274 },
  { code: "PGRR",   name: "Planning Guide Revision Request",        count: 118 },
  { code: "RMGRR",  name: "Retail Market Guide Revision Request",   count: 203 },
];

// "Documents Submitted" section for the center detail view — lists the issue's
// source_documents (from Summary.json), sorted by the sequence number after
// "[rule#][CAT]-". Title opens the document summary (content window); the
// download button fetches the original.
//
// source_documents is a flat list of filenames (strings) that the summarizer
// records by scanning the issue folder. We normalize each into a doc object,
// deriving download_url from the file's location in the issue folder. Objects
// (older schema, with title/download_url/summary fields) are passed through.
function DocumentsSubmittedSection({ cat, issueId, docs, onDocClick }) {
  const base = `/Power.Talks/Documents%20Database/ERCOT.MKT.RULES/${cat}/${issueId}`;
  const normalized = (Array.isArray(docs) ? docs : [])
    .map(x => (typeof x === "string" ? { file: x } : (x || {})))
    .filter(x => x.file && !/\.zip$/i.test(x.file))
    .map(x => ({ ...x, download_url: x.download_url || `${base}/${encodeURIComponent(x.file)}` }));
  const seqOf = (f) => { const m = (f || "").match(/^\d+[a-z]+[-_ ]+(\d+)/i); return m ? parseInt(m[1], 10) : 9999; };
  const list = normalized.slice().sort((a, b) => seqOf(a.file) - seqOf(b.file) || ((a.file || "") > (b.file || "") ? 1 : -1));
  return (
    <>
      <div className="nd-sec-hd">Documents Submitted</div>
      {list.length === 0
        ? <div className="nd-body">n/a</div>
        : <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {list.map((d, i) => (
              <div key={i} style={{ display: "flex", alignItems: "baseline", gap: 12 }}>
                <a href="#" onClick={(e) => { e.preventDefault(); onDocClick && onDocClick(d, issueId, cat); }}
                   title={d.file}
                   style={{ flex: 1, fontSize: "13px", color: "var(--accent-2)", textDecoration: "none", cursor: "pointer", lineHeight: 1.45 }}>
                  {d.title || (d.file || "").replace(/\.[^.]+$/, "").replace(/[_-]+/g, " ")}
                </a>
                {d.download_url &&
                  <a href={d.download_url} download onClick={(e) => e.stopPropagation()}
                     title="Download original document"
                     style={{ flexShrink: 0, fontSize: "12px", color: "var(--muted)", textDecoration: "none" }}>⬇ download</a>}
              </div>
            ))}
          </div>}
    </>
  );
}

// Shared body for every market-rule detail view. All six categories render the
// same 11 sections in the same order; they differ only in the key-change title,
// the "changed sections" field name, and the category/issue id. Empty sections
// show "n/a" (never a bare header). List of Changed Sections is a two-column
// table (section number | name) built from the flat [num, name, num, name, ...]
// array, sized to match body text.
function RuleDetailSections({ summary, cat, issueId, keyTitle, sectionsField, onDocClick }) {
  const NA = "n/a";
  const sections = summary[sectionsField] || [];
  const impacts = summary.impacts_summary || (summary.impacts || []).map(x => x.text).join(" ");
  const ia = summary.impact_analysis || [];
  const tl = summary.timeline || [];
  const cs = summary.current_status || [];
  return (
    <>
      <style>{`
        .nd-sections { width:100%; border-collapse:collapse; font-size:12.5px; margin-bottom:10px; }
        .nd-sections td { padding:2px 10px 2px 0; color:var(--ink-2); vertical-align:top; line-height:1.6; }
        .nd-sections td:first-child { color:var(--ink); white-space:nowrap; width:1%; padding-right:16px; }
      `}</style>

      <h2 className="nd-title">{summary.title}</h2>

      <div className="nd-sec-hd">Executive Summary</div>
      <div className="nd-body">{summary.executive_summary || NA}</div>

      <div className="nd-sec-hd">Revision Type</div>
      <div className="nd-body">{summary.background || NA}</div>

      <div className="nd-sec-hd">{keyTitle}</div>
      <div className="nd-body">{summary.key_change || NA}</div>

      <div className="nd-sec-hd">Potential Impacts</div>
      <div className="nd-body">{impacts || NA}</div>

      <div className="nd-sec-hd">Impact Analysis</div>
      {ia.length > 0
        ? ia.map((x, i) => (
            <table key={i} className="nd-table">
              <thead><tr><th>Category</th><th>Detail</th></tr></thead>
              <tbody>{x.rows.map((row, j) => (<tr key={j}><td>{row[0]}</td><td>{row[1]}</td></tr>))}</tbody>
            </table>
          ))
        : <div className="nd-body">{NA}</div>}

      <div className="nd-sec-hd">ERCOT/IMM Opinions</div>
      {(summary.ercot_opinion || summary.imm_opinion)
        ? <div className="nd-body">
            {summary.ercot_opinion && <div style={{ marginBottom: 6 }}><b>ERCOT Opinion:</b> {summary.ercot_opinion}</div>}
            {summary.imm_opinion && <div><b>Independent Market Monitor Opinion:</b> {summary.imm_opinion}</div>}
          </div>
        : <div className="nd-body">{NA}</div>}

      <div className="nd-sec-hd">Stakeholder Discussion Timeline</div>
      {tl.length > 0
        ? <table className="nd-tl-table">
            <thead><tr><th>Date</th><th>Body</th><th>Action / Vote</th><th>Notes</th></tr></thead>
            <tbody>{tl.map((t, i) => (
              <tr key={i}>
                <td className="nd-tl-date-cell">{t.date}</td>
                <td className="nd-tl-body-cell">{t.body}</td>
                <td className="nd-tl-action-cell">{t.action}</td>
                <td>{t.notes}</td>
              </tr>
            ))}</tbody>
          </table>
        : <div className="nd-body">{NA}</div>}

      <div className="nd-sec-hd">Stakeholder Key Debates</div>
      <div className="nd-body">{summary.stakeholder_key_debates || NA}</div>

      <div className="nd-sec-hd">Current Status</div>
      {cs.length > 0
        ? cs.map((p, i) => <div key={i} className="nd-body">{p}</div>)
        : <div className="nd-body">{NA}</div>}

      <DocumentsSubmittedSection cat={cat} issueId={issueId} docs={summary.source_documents} onDocClick={onDocClick} />

      <div className="nd-sec-hd">List of Changed Sections</div>
      {sections.length > 0
        ? <table className="nd-sections"><tbody>
            {Array.from({ length: Math.ceil(sections.length / 2) }, (_, i) => (
              <tr key={i}><td>{sections[2 * i]}</td><td>{sections[2 * i + 1] || ""}</td></tr>
            ))}
          </tbody></table>
        : <div className="nd-body">{NA}</div>}
    </>
  );
}

function NprrDetailView({ nprr, onBack, onDocClick }) {
  const [summary, setSummary] = React.useState(null);
  const [loading, setLoading] = React.useState(true);
  const [error,   setError]   = React.useState(null);

  React.useEffect(() => {
    setLoading(true); setError(null); setSummary(null);
    fetch(`/Power.Talks/Documents%20Database/ERCOT.MKT.RULES/NPRR/NPRR${nprr}/Quick%20runs/NPRR${nprr}%20Summary.json`, { cache: "no-store" })
      .then(r => r.ok ? r.json() : Promise.reject(`HTTP ${r.status}`))
      .then(d => { setSummary(d); setLoading(false); })
      .catch(e => { setError(String(e)); setLoading(false); });
  }, [nprr]);

  const STATUS_COLOR = { Approved: "var(--ok)", Withdrawn: "var(--muted)", Pending: "var(--warn)" };
  const sc = summary ? (STATUS_COLOR[summary.status] || "var(--muted)") : "var(--muted)";

  return (
    <div style={{ position: "relative" }}>
      <style>{`
        .nd-head { display:flex; align-items:center; gap:10px; margin-bottom:16px; flex-wrap:wrap; }
        .nd-back {
          display:flex; align-items:center; gap:5px;
          font-family:var(--mono); font-size:11px; color:var(--muted);
          padding:5px 10px; border-radius:6px; border:1px solid var(--rule-2);
          background:var(--bg); transition:border-color .15s, color .15s; cursor:pointer;
        }
        .nd-back:hover { border-color:var(--accent); color:var(--accent); }
        .nd-num { font-family:var(--mono); font-size:13px; font-weight:700; color:var(--accent-2); letter-spacing:.04em; }
        .nd-badge { padding:2px 10px; border-radius:99px; font-size:10.5px; font-weight:600; font-family:var(--mono); letter-spacing:.06em; }
        .nd-title { font-family:var(--serif); font-size:22px; font-weight:400; color:var(--ink); line-height:1.2; margin:0 0 6px; }
        .nd-eyebrow { font-family:var(--mono); font-size:9.5px; letter-spacing:.1em; text-transform:uppercase; color:var(--muted); margin-bottom:14px; }
        .nd-sec-hd {
          font-family:var(--mono); font-size:9.5px; letter-spacing:.12em; text-transform:uppercase; color:var(--muted);
          padding-top:2px; margin:16px 0 8px;
        }
        .nd-body { font-size:13px; color:var(--ink-2); line-height:1.7; margin-bottom:10px; }
        .nd-bullets { margin:4px 0 10px; padding-left:20px; font-size:13px; color:var(--ink-2); line-height:1.7; }
        .nd-bullets li { margin-bottom:3px; }
        .nd-impact-list { display:flex; flex-direction:column; gap:6px; margin-bottom:8px; }
        .nd-impact-row { display:flex; gap:10px; font-size:12.5px; line-height:1.5; }
        .nd-impact-cat { font-weight:600; color:var(--ink); white-space:nowrap; min-width:160px; flex-shrink:0; }
        .nd-impact-txt { color:var(--ink-2); }
        .nd-ia-lbl { font-size:12px; font-weight:600; color:var(--ink-2); margin:10px 0 5px; }
        .nd-table { width:100%; border-collapse:collapse; font-size:11.5px; margin-bottom:12px; }
        .nd-table th { text-align:left; font-family:var(--mono); font-size:9.5px; letter-spacing:.08em; text-transform:uppercase; color:var(--muted); padding:5px 8px; border-bottom:1px solid var(--rule-2); }
        .nd-table td { padding:5px 8px; border-bottom:1px solid var(--rule); color:var(--ink-2); vertical-align:top; }
        .nd-table tr:last-child td { border-bottom:0; }
        .nd-table td:first-child { font-weight:600; color:var(--ink); white-space:nowrap; width:30%; }
        .nd-tl-table { width:100%; border-collapse:collapse; font-size:11px; }
        .nd-tl-table th { text-align:left; font-family:var(--mono); font-size:9px; letter-spacing:.08em; text-transform:uppercase; color:var(--muted); padding:5px 6px; border-bottom:1px solid var(--rule-2); }
        .nd-tl-table td { padding:5px 6px; border-bottom:1px solid var(--rule); color:var(--ink-2); vertical-align:top; }
        .nd-tl-table tr:last-child td { border-bottom:0; background:color-mix(in oklab,var(--ok),transparent 88%); }
        .nd-tl-table tr:last-child td { font-weight:500; color:var(--ink); }
        .nd-tl-date-cell { font-family:var(--mono); font-size:10px; white-space:nowrap; color:var(--muted); }
        .nd-tl-body-cell { font-family:var(--mono); font-size:10px; color:var(--accent-2); white-space:nowrap; }
        .nd-tl-action-cell { font-weight:600; color:var(--ink); }
        .nd-proto-tag { font-family:var(--mono); font-size:11px; color:var(--accent-2); padding:4px 10px; border-radius:6px; background:var(--accent-soft); border:1px solid var(--rule-2); display:inline-block; margin:0 4px 4px 0; }
        .nd-loading { padding:40px 0; text-align:center; color:var(--muted); font-family:var(--mono); font-size:12px; }
        .nd-error { padding:16px 0; color:var(--muted); font-family:var(--mono); font-size:11.5px; }
      `}</style>

      <div className="nd-head">
        <button className="nd-back" onClick={onBack}>← Back</button>
        {summary && <>
          <span className="nd-num">NPRR{summary.nprr_number}</span>
          <span className="nd-badge" style={{ background: sc + "22", color: sc }}>{summary.status}</span>
        </>}
      </div>

      {loading && <div className="nd-loading">Loading summary…</div>}
      {error && (() => {
        const isNetwork = error.toLowerCase().includes("failed to fetch") || error.toLowerCase().includes("networkerror");
        return (
          <div className="nd-error">
            {isNetwork
              ? <>Cannot reach server — open via <b>http://localhost</b>, not file://.<br/>Path: <code style={{fontSize:10}}>/Power.Talks/Documents Database/ERCOT.MKT.RULES/NPRR/NPRR{nprr}/Quick runs/</code></>
              : error.includes("404")
                ? <>Summary not yet generated for NPRR{nprr}. Run the <b>NPRR Summarization and Timeline of Status</b> skill to create it.</>
                : <>Could not load summary. ({error})</>
            }
          </div>
        );
      })()}

      {summary && <RuleDetailSections summary={summary} cat="NPRR" issueId={`NPRR${nprr}`} keyTitle="Key Protocol Change" sectionsField="protocol_sections" onDocClick={onDocClick} />}
    </div>
  );
}

function NprrListPanel({ code = "NPRR", label, items, maxHeight, statusColor, onNprrClick }) {
  const [query, setQuery] = React.useState("");
  const baseFolder = FOLDER_PATHS[code];
  const filtered = items
    .filter(item => {
      const q = query.trim().toLowerCase();
      if (!q) return true;
      return String(item.n).includes(q) || (item.title || "").toLowerCase().includes(q);
    })
    .sort((a, b) => b.n - a.n);
  return (
    <div className="pt-nprr-panel">
      <style>{`
        .pt-nprr-panel {
          margin-top: 14px;
          border-top: 1px dashed var(--rule-2);
          padding-top: 12px;
        }
        .pt-nprr-label-row {
          display: flex; align-items: center; gap: 8px; margin-bottom: 8px;
        }
        .pt-nprr-label {
          font-family: var(--mono); font-size: 10px; font-weight: 600;
          letter-spacing: .1em; text-transform: uppercase;
          padding: 2px 8px; border-radius: 5px;
        }
        .pt-nprr-search-wrap {
          display: flex; align-items: center; gap: 8px; margin-bottom: 6px;
        }
        .pt-nprr-search {
          flex: 1; padding: 6px 10px;
          border: 1px solid var(--rule-2); border-radius: 7px;
          background: var(--bg); color: var(--ink);
          font-family: var(--mono); font-size: 11.5px;
          outline: none; transition: border-color .15s;
        }
        .pt-nprr-search:focus { border-color: var(--accent); }
        .pt-nprr-search::placeholder { color: var(--muted); }
        .pt-nprr-count {
          font-family: var(--mono); font-size: 10.5px; color: var(--muted);
          white-space: nowrap;
        }
        .pt-nprr-list {
          overflow-y: auto; display: flex; flex-direction: column; gap: 1px;
          scrollbar-width: thin;
        }
        .pt-nprr-item {
          display: flex; align-items: center; gap: 10px;
          padding: 5px 8px; border-radius: 6px;
          border: 1px solid transparent;
          text-decoration: none; color: inherit;
          transition: background .12s, border-color .12s;
        }
        .pt-nprr-item:hover {
          background: var(--accent-soft); border-color: var(--rule-2);
        }
        .pt-nprr-num {
          font-family: var(--mono); font-size: 11px; font-weight: 600;
          color: var(--accent-2); min-width: 50px; flex-shrink: 0;
        }
        .pt-nprr-title {
          font-size: 12px; color: var(--ink-2); line-height: 1.3;
          flex: 1; min-width: 0;
          white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }
        .pt-nprr-item:hover .pt-nprr-title { color: var(--ink); }
        .pt-nprr-empty {
          padding: 14px; text-align: center; font-size: 12px; color: var(--muted);
        }
      `}</style>

      <div className="pt-nprr-label-row">
        <span className="pt-nprr-label" style={{ background: statusColor + "22", color: statusColor }}>
          {label}
        </span>
      </div>

      <div className="pt-nprr-search-wrap">
        <input
          className="pt-nprr-search"
          type="text"
          placeholder={`Search ${label.toLowerCase()} by number or keyword…`}
          value={query}
          onChange={e => setQuery(e.target.value)}
          spellCheck={false}
        />
        <span className="pt-nprr-count">{filtered.length} / {items.length}</span>
      </div>

      <div className="pt-nprr-list" style={{ maxHeight }}>
        {filtered.length === 0
          ? <div className="pt-nprr-empty">No matching {code}s</div>
          : filtered.map(item => (
            <div
              key={item.n}
              className="pt-nprr-item"
              onClick={() => onNprrClick ? onNprrClick(item.n) : window.open(`${baseFolder}/${code}${String(item.n).padStart((code === "NPRR" || code === "PGRR") ? 0 : 3, "0")}`, "_blank")}
              title={`${code}${item.n} — ${item.title}`}
              style={{ cursor: "pointer" }}
            >
              <span className="pt-nprr-num">{code}{(code !== "NPRR" && code !== "PGRR") ? String(item.n).padStart(3, "0") : item.n}</span>
              <span className="pt-nprr-title">{item.title || "—"}</span>
            </div>
          ))
        }
      </div>
    </div>
  );
}

function NprrPanels({ onNprrClick }) {
  const d = window.DATA || {};
  return (
    <React.Fragment>
      <NprrListPanel label="Pending"   items={d.NPRR_PENDING   || []} maxHeight="200px" statusColor="var(--warn)"   onNprrClick={onNprrClick} />
      <NprrListPanel label="Approved"  items={d.NPRR_APPROVED  || []} maxHeight="130px" statusColor="var(--ok)"     onNprrClick={onNprrClick} />
      <NprrListPanel label="Withdrawn" items={d.NPRR_WITHDRAWN || []} maxHeight="130px" statusColor="var(--muted)"  onNprrClick={onNprrClick} />
    </React.Fragment>
  );
}

function CopmgrrDetailView({ copmgrr, onBack, onDocClick }) {
  const [summary, setSummary] = React.useState(null);
  const [loading, setLoading] = React.useState(true);
  const [error,   setError]   = React.useState(null);

  React.useEffect(() => {
    setLoading(true); setError(null); setSummary(null);
    const n = String(copmgrr).padStart(3, "0");
    fetch(`/Power.Talks/Documents%20Database/ERCOT.MKT.RULES/COPMGRR/COPMGRR${n}/Quick%20runs/COPMGRR${n}%20Summary.json`, { cache: "no-store" })
      .then(r => r.ok ? r.json() : Promise.reject(`HTTP ${r.status}`))
      .then(d => { setSummary(d); setLoading(false); })
      .catch(e => { setError(String(e)); setLoading(false); });
  }, [copmgrr]);

  const STATUS_COLOR = { Approved: "var(--ok)", Withdrawn: "var(--muted)", Pending: "var(--warn)" };
  const sc = summary ? (STATUS_COLOR[summary.status] || "var(--muted)") : "var(--muted)";
  const numStr = String(copmgrr).padStart(3, "0");

  return (
    <div style={{ position: "relative" }}>
      <style>{`
        .nd-head { display:flex; align-items:center; gap:10px; margin-bottom:16px; flex-wrap:wrap; }
        .nd-back { display:flex; align-items:center; gap:5px; font-family:var(--mono); font-size:11px; color:var(--muted); padding:5px 10px; border-radius:6px; border:1px solid var(--rule-2); background:var(--bg); transition:border-color .15s, color .15s; cursor:pointer; }
        .nd-back:hover { border-color:var(--accent); color:var(--accent); }
        .nd-num { font-family:var(--mono); font-size:13px; font-weight:700; color:var(--accent-2); letter-spacing:.04em; }
        .nd-badge { padding:2px 10px; border-radius:99px; font-size:10.5px; font-weight:600; font-family:var(--mono); letter-spacing:.06em; }
        .nd-title { font-family:var(--serif); font-size:22px; font-weight:400; color:var(--ink); line-height:1.2; margin:0 0 6px; }
        .nd-eyebrow { font-family:var(--mono); font-size:9.5px; letter-spacing:.1em; text-transform:uppercase; color:var(--muted); margin-bottom:14px; }
        .nd-sec-hd { font-family:var(--mono); font-size:9.5px; letter-spacing:.12em; text-transform:uppercase; color:var(--muted); padding-top:2px; margin:16px 0 8px; }
        .nd-body { font-size:13px; color:var(--ink-2); line-height:1.7; margin-bottom:10px; }
        .nd-bullets { margin:4px 0 10px; padding-left:20px; font-size:13px; color:var(--ink-2); line-height:1.7; }
        .nd-bullets li { margin-bottom:3px; }
        .nd-impact-list { display:flex; flex-direction:column; gap:6px; margin-bottom:8px; }
        .nd-impact-row { display:flex; gap:10px; font-size:12.5px; line-height:1.5; }
        .nd-impact-cat { font-weight:600; color:var(--ink); white-space:nowrap; min-width:160px; flex-shrink:0; }
        .nd-impact-txt { color:var(--ink-2); }
        .nd-ia-lbl { font-size:12px; font-weight:600; color:var(--ink-2); margin:10px 0 5px; }
        .nd-table { width:100%; border-collapse:collapse; font-size:11.5px; margin-bottom:12px; }
        .nd-table th { text-align:left; font-family:var(--mono); font-size:9.5px; letter-spacing:.08em; text-transform:uppercase; color:var(--muted); padding:5px 8px; border-bottom:1px solid var(--rule-2); }
        .nd-table td { padding:5px 8px; border-bottom:1px solid var(--rule); color:var(--ink-2); vertical-align:top; }
        .nd-table tr:last-child td { border-bottom:0; }
        .nd-table td:first-child { font-weight:600; color:var(--ink); white-space:nowrap; width:30%; }
        .nd-tl-table { width:100%; border-collapse:collapse; font-size:11px; }
        .nd-tl-table th { text-align:left; font-family:var(--mono); font-size:9px; letter-spacing:.08em; text-transform:uppercase; color:var(--muted); padding:5px 6px; border-bottom:1px solid var(--rule-2); }
        .nd-tl-table td { padding:5px 6px; border-bottom:1px solid var(--rule); color:var(--ink-2); vertical-align:top; }
        .nd-tl-table tr:last-child td { border-bottom:0; background:color-mix(in oklab,var(--ok),transparent 88%); }
        .nd-tl-table tr:last-child td { font-weight:500; color:var(--ink); }
        .nd-tl-date-cell { font-family:var(--mono); font-size:10px; white-space:nowrap; color:var(--muted); }
        .nd-tl-body-cell { font-family:var(--mono); font-size:10px; color:var(--accent-2); white-space:nowrap; }
        .nd-tl-action-cell { font-weight:600; color:var(--ink); }
        .nd-proto-tag { font-family:var(--mono); font-size:11px; color:var(--accent-2); padding:4px 10px; border-radius:6px; background:var(--accent-soft); border:1px solid var(--rule-2); display:inline-block; margin:0 4px 4px 0; }
        .nd-loading { padding:40px 0; text-align:center; color:var(--muted); font-family:var(--mono); font-size:12px; }
        .nd-error { padding:16px 0; color:var(--muted); font-family:var(--mono); font-size:11.5px; }
      `}</style>
      <div className="nd-head">
        <button className="nd-back" onClick={onBack}>← Back</button>
        {summary && <>
          <span className="nd-num">COPMGRR{numStr}</span>
          <span className="nd-badge" style={{ background: sc + "22", color: sc }}>{summary.status}</span>
        </>}
      </div>

      {loading && <div className="nd-loading">Loading summary…</div>}
      {error && (() => {
        const isNetwork = error.toLowerCase().includes("failed to fetch") || error.toLowerCase().includes("networkerror");
        return (
          <div className="nd-error">
            {isNetwork
              ? <>Cannot reach server — open via <b>http://localhost</b>, not file://.<br/>Path: <code style={{fontSize:10}}>/Power.Talks/Documents Database/ERCOT.MKT.RULES/COPMGRR/COPMGRR{numStr}/Quick runs/</code></>
              : error.includes("404")
                ? <>Summary not yet generated for COPMGRR{numStr}. Run the <b>COPMGRR Summarization and Timeline of Status</b> skill to create it.</>
                : <>Could not load summary. ({error})</>
            }
          </div>
        );
      })()}

      {summary && <RuleDetailSections summary={summary} cat="COPMGRR" issueId={`COPMGRR${String(copmgrr).padStart(3, "0")}`} keyTitle="Key Change" sectionsField="agreement_sections" onDocClick={onDocClick} />}
    </div>
  );
}

function CopmgrrPanels({ onCopmgrrClick }) {
  const d = window.DATA || {};
  return (
    <React.Fragment>
      <NprrListPanel code="COPMGRR" label="Pending"   items={d.COPMGRR_PENDING   || []} maxHeight="200px" statusColor="var(--warn)"  onNprrClick={onCopmgrrClick} />
      <NprrListPanel code="COPMGRR" label="Approved"  items={d.COPMGRR_APPROVED  || []} maxHeight="200px" statusColor="var(--ok)"    onNprrClick={onCopmgrrClick} />
      <NprrListPanel code="COPMGRR" label="Withdrawn" items={d.COPMGRR_WITHDRAWN || []} maxHeight="130px" statusColor="var(--muted)" onNprrClick={onCopmgrrClick} />
    </React.Fragment>
  );
}

function PgrrDetailView({ pgrr, onBack, onDocClick }) {
  const [summary, setSummary] = React.useState(null);
  const [loading, setLoading] = React.useState(true);
  const [error,   setError]   = React.useState(null);

  React.useEffect(() => {
    setLoading(true); setError(null); setSummary(null);
    fetch(`/Power.Talks/Documents%20Database/ERCOT.MKT.RULES/PGRR/PGRR${pgrr}/Quick%20runs/PGRR${pgrr}%20Summary.json`, { cache: "no-store" })
      .then(r => r.ok ? r.json() : Promise.reject(`HTTP ${r.status}`))
      .then(d => { setSummary(d); setLoading(false); })
      .catch(e => { setError(String(e)); setLoading(false); });
  }, [pgrr]);

  const STATUS_COLOR = { Approved: "var(--ok)", Withdrawn: "var(--muted)", Pending: "var(--warn)" };
  const sc = summary ? (STATUS_COLOR[summary.status] || "var(--muted)") : "var(--muted)";

  return (
    <div style={{ position: "relative" }}>
      <style>{`
        .nd-head { display:flex; align-items:center; gap:10px; margin-bottom:16px; flex-wrap:wrap; }
        .nd-back { display:flex; align-items:center; gap:5px; font-family:var(--mono); font-size:11px; color:var(--muted); padding:5px 10px; border-radius:6px; border:1px solid var(--rule-2); background:var(--bg); transition:border-color .15s, color .15s; cursor:pointer; }
        .nd-back:hover { border-color:var(--accent); color:var(--accent); }
        .nd-num { font-family:var(--mono); font-size:13px; font-weight:700; color:var(--accent-2); letter-spacing:.04em; }
        .nd-badge { padding:2px 10px; border-radius:99px; font-size:10.5px; font-weight:600; font-family:var(--mono); letter-spacing:.06em; }
        .nd-title { font-family:var(--serif); font-size:22px; font-weight:400; color:var(--ink); line-height:1.2; margin:0 0 6px; }
        .nd-eyebrow { font-family:var(--mono); font-size:9.5px; letter-spacing:.1em; text-transform:uppercase; color:var(--muted); margin-bottom:14px; }
        .nd-sec-hd { font-family:var(--mono); font-size:9.5px; letter-spacing:.12em; text-transform:uppercase; color:var(--muted); padding-top:2px; margin:16px 0 8px; }
        .nd-body { font-size:13px; color:var(--ink-2); line-height:1.7; margin-bottom:10px; }
        .nd-bullets { margin:4px 0 10px; padding-left:20px; font-size:13px; color:var(--ink-2); line-height:1.7; }
        .nd-bullets li { margin-bottom:3px; }
        .nd-impact-list { display:flex; flex-direction:column; gap:6px; margin-bottom:8px; }
        .nd-impact-row { display:flex; gap:10px; font-size:12.5px; line-height:1.5; }
        .nd-impact-cat { font-weight:600; color:var(--ink); white-space:nowrap; min-width:160px; flex-shrink:0; }
        .nd-impact-txt { color:var(--ink-2); }
        .nd-ia-lbl { font-size:12px; font-weight:600; color:var(--ink-2); margin:10px 0 5px; }
        .nd-table { width:100%; border-collapse:collapse; font-size:11.5px; margin-bottom:12px; }
        .nd-table th { text-align:left; font-family:var(--mono); font-size:9.5px; letter-spacing:.08em; text-transform:uppercase; color:var(--muted); padding:5px 8px; border-bottom:1px solid var(--rule-2); }
        .nd-table td { padding:5px 8px; border-bottom:1px solid var(--rule); color:var(--ink-2); vertical-align:top; }
        .nd-table tr:last-child td { border-bottom:0; }
        .nd-table td:first-child { font-weight:600; color:var(--ink); white-space:nowrap; width:30%; }
        .nd-tl-table { width:100%; border-collapse:collapse; font-size:11px; }
        .nd-tl-table th { text-align:left; font-family:var(--mono); font-size:9px; letter-spacing:.08em; text-transform:uppercase; color:var(--muted); padding:5px 6px; border-bottom:1px solid var(--rule-2); }
        .nd-tl-table td { padding:5px 6px; border-bottom:1px solid var(--rule); color:var(--ink-2); vertical-align:top; }
        .nd-tl-table tr:last-child td { border-bottom:0; background:color-mix(in oklab,var(--ok),transparent 88%); }
        .nd-tl-table tr:last-child td { font-weight:500; color:var(--ink); }
        .nd-tl-date-cell { font-family:var(--mono); font-size:10px; white-space:nowrap; color:var(--muted); }
        .nd-tl-body-cell { font-family:var(--mono); font-size:10px; color:var(--accent-2); white-space:nowrap; }
        .nd-tl-action-cell { font-weight:600; color:var(--ink); }
        .nd-proto-tag { font-family:var(--mono); font-size:11px; color:var(--accent-2); padding:4px 10px; border-radius:6px; background:var(--accent-soft); border:1px solid var(--rule-2); display:inline-block; margin:0 4px 4px 0; }
        .nd-loading { padding:40px 0; text-align:center; color:var(--muted); font-family:var(--mono); font-size:12px; }
        .nd-error { padding:16px 0; color:var(--muted); font-family:var(--mono); font-size:11.5px; }
      `}</style>
      <div className="nd-head">
        <button className="nd-back" onClick={onBack}>← Back</button>
        {summary && <>
          <span className="nd-num">PGRR{summary.pgrr_number}</span>
          <span className="nd-badge" style={{ background: sc + "22", color: sc }}>{summary.status}</span>
        </>}
      </div>

      {loading && <div className="nd-loading">Loading summary…</div>}
      {error && (() => {
        const isNetwork = error.toLowerCase().includes("failed to fetch") || error.toLowerCase().includes("networkerror");
        return (
          <div className="nd-error">
            {isNetwork
              ? <>Cannot reach server — open via <b>http://localhost</b>, not file://.<br/>Path: <code style={{fontSize:10}}>/Power.Talks/Documents Database/ERCOT.MKT.RULES/PGRR/PGRR{pgrr}/Quick runs/</code></>
              : error.includes("404")
                ? <>Summary not yet generated for PGRR{pgrr}. Run the <b>PGRR Summarization and Timeline of Status</b> skill to create it.</>
                : <>Could not load summary. ({error})</>
            }
          </div>
        );
      })()}

      {summary && <RuleDetailSections summary={summary} cat="PGRR" issueId={`PGRR${pgrr}`} keyTitle="Revision Description" sectionsField="planning_sections" onDocClick={onDocClick} />}
    </div>
  );
}

function PgrrPanels({ onPgrrClick }) {
  const d = window.DATA || {};
  return (
    <React.Fragment>
      <NprrListPanel code="PGRR" label="Pending"   items={d.PGRR_PENDING   || []} maxHeight="200px" statusColor="var(--warn)"  onNprrClick={onPgrrClick} />
      <NprrListPanel code="PGRR" label="Approved"  items={d.PGRR_APPROVED  || []} maxHeight="200px" statusColor="var(--ok)"    onNprrClick={onPgrrClick} />
      <NprrListPanel code="PGRR" label="Withdrawn" items={d.PGRR_WITHDRAWN || []} maxHeight="130px" statusColor="var(--muted)" onNprrClick={onPgrrClick} />
    </React.Fragment>
  );
}

function ScrDetailView({ scr, onBack, onDocClick }) {
  const [summary, setSummary] = React.useState(null);
  const [loading, setLoading] = React.useState(true);
  const [error,   setError]   = React.useState(null);

  React.useEffect(() => {
    setLoading(true); setError(null); setSummary(null);
    fetch(`/Power.Talks/Documents%20Database/ERCOT.MKT.RULES/SCR/SCR${scr}/Quick%20runs/SCR${scr}%20Summary.json`, { cache: "no-store" })
      .then(r => r.ok ? r.json() : Promise.reject(`HTTP ${r.status}`))
      .then(d => { setSummary(d); setLoading(false); })
      .catch(e => { setError(String(e)); setLoading(false); });
  }, [scr]);

  const STATUS_COLOR = { Approved: "var(--ok)", Withdrawn: "var(--muted)", Rejected: "var(--warn)", Pending: "var(--warn)" };
  const sc = summary ? (STATUS_COLOR[summary.status] || "var(--muted)") : "var(--muted)";

  return (
    <div style={{ position: "relative" }}>
      <style>{`
        .nd-head { display:flex; align-items:center; gap:10px; margin-bottom:16px; flex-wrap:wrap; }
        .nd-back { display:flex; align-items:center; gap:5px; font-family:var(--mono); font-size:11px; color:var(--muted); padding:5px 10px; border-radius:6px; border:1px solid var(--rule-2); background:var(--bg); transition:border-color .15s, color .15s; cursor:pointer; }
        .nd-back:hover { border-color:var(--accent); color:var(--accent); }
        .nd-num { font-family:var(--mono); font-size:13px; font-weight:700; color:var(--accent-2); letter-spacing:.04em; }
        .nd-badge { padding:2px 10px; border-radius:99px; font-size:10.5px; font-weight:600; font-family:var(--mono); letter-spacing:.06em; }
        .nd-title { font-family:var(--serif); font-size:22px; font-weight:400; color:var(--ink); line-height:1.2; margin:0 0 6px; }
        .nd-eyebrow { font-family:var(--mono); font-size:9.5px; letter-spacing:.1em; text-transform:uppercase; color:var(--muted); margin-bottom:14px; }
        .nd-sec-hd { font-family:var(--mono); font-size:9.5px; letter-spacing:.12em; text-transform:uppercase; color:var(--muted); padding-top:2px; margin:16px 0 8px; }
        .nd-body { font-size:13px; color:var(--ink-2); line-height:1.7; margin-bottom:10px; }
        .nd-bullets { margin:4px 0 10px; padding-left:20px; font-size:13px; color:var(--ink-2); line-height:1.7; }
        .nd-bullets li { margin-bottom:3px; }
        .nd-impact-list { display:flex; flex-direction:column; gap:6px; margin-bottom:8px; }
        .nd-impact-row { display:flex; gap:10px; font-size:12.5px; line-height:1.5; }
        .nd-impact-cat { font-weight:600; color:var(--ink); white-space:nowrap; min-width:160px; flex-shrink:0; }
        .nd-impact-txt { color:var(--ink-2); }
        .nd-ia-lbl { font-size:12px; font-weight:600; color:var(--ink-2); margin:10px 0 5px; }
        .nd-table { width:100%; border-collapse:collapse; font-size:11.5px; margin-bottom:12px; }
        .nd-table th { text-align:left; font-family:var(--mono); font-size:9.5px; letter-spacing:.08em; text-transform:uppercase; color:var(--muted); padding:5px 8px; border-bottom:1px solid var(--rule-2); }
        .nd-table td { padding:5px 8px; border-bottom:1px solid var(--rule); color:var(--ink-2); vertical-align:top; }
        .nd-table tr:last-child td { border-bottom:0; }
        .nd-table td:first-child { font-weight:600; color:var(--ink); white-space:nowrap; width:30%; }
        .nd-tl-table { width:100%; border-collapse:collapse; font-size:11px; }
        .nd-tl-table th { text-align:left; font-family:var(--mono); font-size:9px; letter-spacing:.08em; text-transform:uppercase; color:var(--muted); padding:5px 6px; border-bottom:1px solid var(--rule-2); }
        .nd-tl-table td { padding:5px 6px; border-bottom:1px solid var(--rule); color:var(--ink-2); vertical-align:top; }
        .nd-tl-table tr:last-child td { border-bottom:0; background:color-mix(in oklab,var(--ok),transparent 88%); }
        .nd-tl-table tr:last-child td { font-weight:500; color:var(--ink); }
        .nd-tl-date-cell { font-family:var(--mono); font-size:10px; white-space:nowrap; color:var(--muted); }
        .nd-tl-body-cell { font-family:var(--mono); font-size:10px; color:var(--accent-2); white-space:nowrap; }
        .nd-tl-action-cell { font-weight:600; color:var(--ink); }
        .nd-proto-tag { font-family:var(--mono); font-size:11px; color:var(--accent-2); padding:4px 10px; border-radius:6px; background:var(--accent-soft); border:1px solid var(--rule-2); display:inline-block; margin:0 4px 4px 0; }
        .nd-loading { padding:40px 0; text-align:center; color:var(--muted); font-family:var(--mono); font-size:12px; }
        .nd-error { padding:16px 0; color:var(--muted); font-family:var(--mono); font-size:11.5px; }
      `}</style>
      <div className="nd-head">
        <button className="nd-back" onClick={onBack}>← Back</button>
        {summary && <>
          <span className="nd-num">SCR{summary.scr_number}</span>
          <span className="nd-badge" style={{ background: sc + "22", color: sc }}>{summary.status}</span>
        </>}
      </div>

      {loading && <div className="nd-loading">Loading summary…</div>}
      {error && (() => {
        const isNetwork = error.toLowerCase().includes("failed to fetch") || error.toLowerCase().includes("networkerror");
        return (
          <div className="nd-error">
            {isNetwork
              ? <>Cannot reach server — open via <b>http://localhost</b>, not file://.<br/>Path: <code style={{fontSize:10}}>/Power.Talks/Documents Database/ERCOT.MKT.RULES/SCR/SCR{scr}/Quick runs/</code></>
              : error.includes("404")
                ? <>Summary not yet generated for SCR{scr}. Run the <b>SCR Summarization and Timeline of Status</b> skill to create it.</>
                : <>Could not load summary. ({error})</>
            }
          </div>
        );
      })()}

      {summary && <RuleDetailSections summary={summary} cat="SCR" issueId={`SCR${scr}`} keyTitle="Key System Change" sectionsField="systems_affected" onDocClick={onDocClick} />}
    </div>
  );
}

function ScrPanels({ onScrClick }) {
  const d = window.DATA || {};
  return (
    <React.Fragment>
      <NprrListPanel code="SCR" label="Approved"  items={d.SCR_APPROVED  || []} maxHeight="200px" statusColor="var(--ok)"    onNprrClick={onScrClick} />
      <NprrListPanel code="SCR" label="Withdrawn" items={d.SCR_WITHDRAWN || []} maxHeight="130px" statusColor="var(--muted)" onNprrClick={onScrClick} />
      <NprrListPanel code="SCR" label="Rejected"  items={d.SCR_REJECTED  || []} maxHeight="80px"  statusColor="var(--warn)"  onNprrClick={onScrClick} />
    </React.Fragment>
  );
}

function NogrDetailView({ nogrr, onBack, onDocClick }) {
  const [summary, setSummary] = React.useState(null);
  const [loading, setLoading] = React.useState(true);
  const [error,   setError]   = React.useState(null);

  React.useEffect(() => {
    setLoading(true); setError(null); setSummary(null);
    fetch(`/Power.Talks/Documents%20Database/ERCOT.MKT.RULES/NOGRR/NOGRR${nogrr}/Quick%20runs/NOGRR${nogrr}%20Summary.json`, { cache: "no-store" })
      .then(r => r.ok ? r.json() : Promise.reject(`HTTP ${r.status}`))
      .then(d => { setSummary(d); setLoading(false); })
      .catch(e => { setError(String(e)); setLoading(false); });
  }, [nogrr]);

  const STATUS_COLOR = { Approved: "var(--ok)", Withdrawn: "var(--muted)", Rejected: "var(--warn)", Pending: "var(--warn)" };
  const sc = summary ? (STATUS_COLOR[summary.status] || "var(--muted)") : "var(--muted)";

  return (
    <div style={{ position: "relative" }}>
      <style>{`
        .nd-head { display:flex; align-items:center; gap:10px; margin-bottom:16px; flex-wrap:wrap; }
        .nd-back { display:flex; align-items:center; gap:5px; font-family:var(--mono); font-size:11px; color:var(--muted); padding:5px 10px; border-radius:6px; border:1px solid var(--rule-2); background:var(--bg); transition:border-color .15s, color .15s; cursor:pointer; }
        .nd-back:hover { border-color:var(--accent); color:var(--accent); }
        .nd-num { font-family:var(--mono); font-size:13px; font-weight:700; color:var(--accent-2); letter-spacing:.04em; }
        .nd-badge { padding:2px 10px; border-radius:99px; font-size:10.5px; font-weight:600; font-family:var(--mono); letter-spacing:.06em; }
        .nd-title { font-family:var(--serif); font-size:22px; font-weight:400; color:var(--ink); line-height:1.2; margin:0 0 6px; }
        .nd-eyebrow { font-family:var(--mono); font-size:9.5px; letter-spacing:.1em; text-transform:uppercase; color:var(--muted); margin-bottom:14px; }
        .nd-sec-hd { font-family:var(--mono); font-size:9.5px; letter-spacing:.12em; text-transform:uppercase; color:var(--muted); padding-top:2px; margin:16px 0 8px; }
        .nd-body { font-size:13px; color:var(--ink-2); line-height:1.7; margin-bottom:10px; }
        .nd-bullets { margin:4px 0 10px; padding-left:20px; font-size:13px; color:var(--ink-2); line-height:1.7; }
        .nd-bullets li { margin-bottom:3px; }
        .nd-impact-list { display:flex; flex-direction:column; gap:6px; margin-bottom:8px; }
        .nd-impact-row { display:flex; gap:10px; font-size:12.5px; line-height:1.5; }
        .nd-impact-cat { font-weight:600; color:var(--ink); white-space:nowrap; min-width:160px; flex-shrink:0; }
        .nd-impact-txt { color:var(--ink-2); }
        .nd-ia-lbl { font-size:12px; font-weight:600; color:var(--ink-2); margin:10px 0 5px; }
        .nd-table { width:100%; border-collapse:collapse; font-size:11.5px; margin-bottom:12px; }
        .nd-table th { text-align:left; font-family:var(--mono); font-size:9.5px; letter-spacing:.08em; text-transform:uppercase; color:var(--muted); padding:5px 8px; border-bottom:1px solid var(--rule-2); }
        .nd-table td { padding:5px 8px; border-bottom:1px solid var(--rule); color:var(--ink-2); vertical-align:top; }
        .nd-table tr:last-child td { border-bottom:0; }
        .nd-table td:first-child { font-weight:600; color:var(--ink); white-space:nowrap; width:30%; }
        .nd-tl-table { width:100%; border-collapse:collapse; font-size:11px; }
        .nd-tl-table th { text-align:left; font-family:var(--mono); font-size:9px; letter-spacing:.08em; text-transform:uppercase; color:var(--muted); padding:5px 6px; border-bottom:1px solid var(--rule-2); }
        .nd-tl-table td { padding:5px 6px; border-bottom:1px solid var(--rule); color:var(--ink-2); vertical-align:top; }
        .nd-tl-table tr:last-child td { border-bottom:0; background:color-mix(in oklab,var(--ok),transparent 88%); }
        .nd-tl-table tr:last-child td { font-weight:500; color:var(--ink); }
        .nd-tl-date-cell { font-family:var(--mono); font-size:10px; white-space:nowrap; color:var(--muted); }
        .nd-tl-body-cell { font-family:var(--mono); font-size:10px; color:var(--accent-2); white-space:nowrap; }
        .nd-tl-action-cell { font-weight:600; color:var(--ink); }
        .nd-proto-tag { font-family:var(--mono); font-size:11px; color:var(--accent-2); padding:4px 10px; border-radius:6px; background:var(--accent-soft); border:1px solid var(--rule-2); display:inline-block; margin:0 4px 4px 0; }
        .nd-loading { padding:40px 0; text-align:center; color:var(--muted); font-family:var(--mono); font-size:12px; }
        .nd-error { padding:16px 0; color:var(--muted); font-family:var(--mono); font-size:11.5px; }
      `}</style>
      <div className="nd-head">
        <button className="nd-back" onClick={onBack}>← Back</button>
        {summary && <>
          <span className="nd-num">NOGRR{summary.nogrr_number}</span>
          <span className="nd-badge" style={{ background: sc + "22", color: sc }}>{summary.status}</span>
        </>}
      </div>
      {loading && <div className="nd-loading">Loading summary…</div>}
      {error && (() => {
        const isNetwork = error.toLowerCase().includes("failed to fetch") || error.toLowerCase().includes("networkerror");
        return (
          <div className="nd-error">
            {isNetwork
              ? <>Cannot reach server — open via <b>http://localhost</b>, not file://.<br/>Path: <code style={{fontSize:10}}>/Power.Talks/Documents Database/ERCOT.MKT.RULES/NOGRR/NOGRR{nogrr}/Quick runs/</code></>
              : error.includes("404")
                ? <>Summary not yet generated for NOGRR{nogrr}.</>
                : <>Could not load summary. ({error})</>
            }
          </div>
        );
      })()}
      {summary && <RuleDetailSections summary={summary} cat="NOGRR" issueId={`NOGRR${nogrr}`} keyTitle="Key Operating Guide Change" sectionsField="guide_sections" onDocClick={onDocClick} />}
    </div>
  );
}

function NogrPanels({ onNogrClick }) {
  const d = window.DATA || {};
  return (
    <React.Fragment>
      <NprrListPanel code="NOGRR" label="Pending"   items={d.NOGRR_PENDING   || []} maxHeight="160px" statusColor="var(--warn)"  onNprrClick={onNogrClick} />
      <NprrListPanel code="NOGRR" label="Approved"  items={d.NOGRR_APPROVED  || []} maxHeight="200px" statusColor="var(--ok)"    onNprrClick={onNogrClick} />
      <NprrListPanel code="NOGRR" label="Withdrawn" items={d.NOGRR_WITHDRAWN || []} maxHeight="130px" statusColor="var(--muted)" onNprrClick={onNogrClick} />
      <NprrListPanel code="NOGRR" label="Rejected"  items={d.NOGRR_REJECTED  || []} maxHeight="80px"  statusColor="var(--warn)"  onNprrClick={onNogrClick} />
    </React.Fragment>
  );
}

function RmgrDetailView({ rmgrr, onBack, onDocClick }) {
  const [summary, setSummary] = React.useState(null);
  const [loading, setLoading] = React.useState(true);
  const [error,   setError]   = React.useState(null);

  React.useEffect(() => {
    setLoading(true); setError(null); setSummary(null);
    fetch(`/Power.Talks/Documents%20Database/ERCOT.MKT.RULES/RMGRR/RMGRR${rmgrr}/Quick%20runs/RMGRR${rmgrr}%20Summary.json`, { cache: "no-store" })
      .then(r => r.ok ? r.json() : Promise.reject(`HTTP ${r.status}`))
      .then(d => { setSummary(d); setLoading(false); })
      .catch(e => { setError(String(e)); setLoading(false); });
  }, [rmgrr]);

  const STATUS_COLOR = { Approved: "var(--ok)", Withdrawn: "var(--muted)", Pending: "var(--warn)" };
  const sc = summary ? (STATUS_COLOR[summary.status] || "var(--muted)") : "var(--muted)";

  return (
    <div style={{ position: "relative" }}>
      <style>{`
        .nd-head { display:flex; align-items:center; gap:10px; margin-bottom:16px; flex-wrap:wrap; }
        .nd-back { display:flex; align-items:center; gap:5px; font-family:var(--mono); font-size:11px; color:var(--muted); padding:5px 10px; border-radius:6px; border:1px solid var(--rule-2); background:var(--bg); transition:border-color .15s, color .15s; cursor:pointer; }
        .nd-back:hover { border-color:var(--accent); color:var(--accent); }
        .nd-num { font-family:var(--mono); font-size:13px; font-weight:700; color:var(--accent-2); letter-spacing:.04em; }
        .nd-badge { padding:2px 10px; border-radius:99px; font-size:10.5px; font-weight:600; font-family:var(--mono); letter-spacing:.06em; }
        .nd-title { font-family:var(--serif); font-size:22px; font-weight:400; color:var(--ink); line-height:1.2; margin:0 0 6px; }
        .nd-eyebrow { font-family:var(--mono); font-size:9.5px; letter-spacing:.1em; text-transform:uppercase; color:var(--muted); margin-bottom:14px; }
        .nd-sec-hd { font-family:var(--mono); font-size:9.5px; letter-spacing:.12em; text-transform:uppercase; color:var(--muted); padding-top:2px; margin:16px 0 8px; }
        .nd-body { font-size:13px; color:var(--ink-2); line-height:1.7; margin-bottom:10px; }
        .nd-bullets { margin:4px 0 10px; padding-left:20px; font-size:13px; color:var(--ink-2); line-height:1.7; }
        .nd-bullets li { margin-bottom:3px; }
        .nd-impact-list { display:flex; flex-direction:column; gap:6px; margin-bottom:8px; }
        .nd-impact-row { display:flex; gap:10px; font-size:12.5px; line-height:1.5; }
        .nd-impact-cat { font-weight:600; color:var(--ink); white-space:nowrap; min-width:160px; flex-shrink:0; }
        .nd-impact-txt { color:var(--ink-2); }
        .nd-ia-lbl { font-size:12px; font-weight:600; color:var(--ink-2); margin:10px 0 5px; }
        .nd-table { width:100%; border-collapse:collapse; font-size:11.5px; margin-bottom:12px; }
        .nd-table th { text-align:left; font-family:var(--mono); font-size:9.5px; letter-spacing:.08em; text-transform:uppercase; color:var(--muted); padding:5px 8px; border-bottom:1px solid var(--rule-2); }
        .nd-table td { padding:5px 8px; border-bottom:1px solid var(--rule); color:var(--ink-2); vertical-align:top; }
        .nd-table tr:last-child td { border-bottom:0; }
        .nd-table td:first-child { font-weight:600; color:var(--ink); white-space:nowrap; width:30%; }
        .nd-tl-table { width:100%; border-collapse:collapse; font-size:11px; }
        .nd-tl-table th { text-align:left; font-family:var(--mono); font-size:9px; letter-spacing:.08em; text-transform:uppercase; color:var(--muted); padding:5px 6px; border-bottom:1px solid var(--rule-2); }
        .nd-tl-table td { padding:5px 6px; border-bottom:1px solid var(--rule); color:var(--ink-2); vertical-align:top; }
        .nd-tl-table tr:last-child td { border-bottom:0; background:color-mix(in oklab,var(--ok),transparent 88%); }
        .nd-tl-table tr:last-child td { font-weight:500; color:var(--ink); }
        .nd-tl-date-cell { font-family:var(--mono); font-size:10px; white-space:nowrap; color:var(--muted); }
        .nd-tl-body-cell { font-family:var(--mono); font-size:10px; color:var(--accent-2); white-space:nowrap; }
        .nd-tl-action-cell { font-weight:600; color:var(--ink); }
        .nd-proto-tag { font-family:var(--mono); font-size:11px; color:var(--accent-2); padding:4px 10px; border-radius:6px; background:var(--accent-soft); border:1px solid var(--rule-2); display:inline-block; margin:0 4px 4px 0; }
        .nd-loading { padding:40px 0; text-align:center; color:var(--muted); font-family:var(--mono); font-size:12px; }
        .nd-error { padding:16px 0; color:var(--muted); font-family:var(--mono); font-size:11.5px; }
      `}</style>
      <div className="nd-head">
        <button className="nd-back" onClick={onBack}>← Back</button>
        {summary && <>
          <span className="nd-num">RMGRR{summary.rmgrr_number}</span>
          <span className="nd-badge" style={{ background: sc + "22", color: sc }}>{summary.status}</span>
        </>}
      </div>
      {loading && <div className="nd-loading">Loading summary…</div>}
      {error && (() => {
        const isNetwork = error.toLowerCase().includes("failed to fetch") || error.toLowerCase().includes("networkerror");
        return (
          <div className="nd-error">
            {isNetwork
              ? <>Cannot reach server — open via <b>http://localhost</b>, not file://.<br/>Path: <code style={{fontSize:10}}>/Power.Talks/Documents Database/ERCOT.MKT.RULES/RMGRR/RMGRR{rmgrr}/Quick runs/</code></>
              : error.includes("404")
                ? <>Summary not yet generated for RMGRR{rmgrr}.</>
                : <>Could not load summary. ({error})</>
            }
          </div>
        );
      })()}
      {summary && <RuleDetailSections summary={summary} cat="RMGRR" issueId={`RMGRR${rmgrr}`} keyTitle="Key Market Guide Change" sectionsField="guide_sections" onDocClick={onDocClick} />}
    </div>
  );
}

function RmgrPanels({ onRmgrClick }) {
  const d = window.DATA || {};
  return (
    <React.Fragment>
      <NprrListPanel code="RMGRR" label="Pending"   items={d.RMGRR_PENDING   || []} maxHeight="120px" statusColor="var(--warn)"  onNprrClick={onRmgrClick} />
      <NprrListPanel code="RMGRR" label="Approved"  items={d.RMGRR_APPROVED  || []} maxHeight="200px" statusColor="var(--ok)"    onNprrClick={onRmgrClick} />
      <NprrListPanel code="RMGRR" label="Withdrawn" items={d.RMGRR_WITHDRAWN || []} maxHeight="130px" statusColor="var(--muted)" onNprrClick={onRmgrClick} />
    </React.Fragment>
  );
}

function DocumentSummaryView({ doc, onBack }) {
  if (!doc) return null;
  // Always render the label; show an em dash when the field wasn't extracted.
  const Row = ({ label, value }) => (
    <div style={{ marginBottom: 10 }}>
      <div style={{ fontFamily: "var(--mono)", fontSize: "9.5px", letterSpacing: ".1em", textTransform: "uppercase", color: "var(--muted)", marginBottom: 2 }}>{label}</div>
      <div style={{ fontSize: "13px", color: "var(--ink-2)", lineHeight: 1.5 }}>{value || "—"}</div>
    </div>
  );
  return (
    <div style={{ marginTop: 16, borderTop: "1px dashed var(--rule-2)", paddingTop: 14 }}>
      <div style={{ display: "flex", alignItems: "baseline", gap: 10, marginBottom: 10, flexWrap: "wrap" }}>
        <a href="#" onClick={(e) => { e.preventDefault(); onBack && onBack(); }}
           style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--accent-2)", textDecoration: "none" }}>← back to {doc.issueId}</a>
        {doc.download_url &&
          <a href={doc.download_url} download
             style={{ marginLeft: "auto", fontSize: 12, color: "var(--accent-2)", textDecoration: "none", border: "1px solid var(--rule-2)", borderRadius: 8, padding: "4px 10px" }}>
            ⬇ Download original
          </a>}
      </div>
      <div style={{ fontFamily: "var(--mono)", fontSize: 10.5, letterSpacing: ".12em", textTransform: "uppercase", color: "var(--muted)" }}>
        {doc.issueId} · Document Summary
      </div>
      <div style={{ fontFamily: "var(--serif)", fontSize: 22, lineHeight: 1.15, margin: "2px 0 10px", color: "var(--ink)" }}>
        {doc.title || (doc.file || "").replace(/\.[^.]+$/, "").replace(/[_-]+/g, " ")}
      </div>
      <Row label="Revision Reason" value={doc.revision_reason} />
      <Row label="Description" value={doc.description || doc.summary} />
      <Row label="Justification of Revision" value={doc.justification} />
      <Row label="Detailed Background of Changes" value={doc.detailed_background} />
    </div>
  );
}

function PaperTrailsIllustration({ active, onActiveChange, onNprrClick, onCopmgrrClick, onPgrrClick, onScrClick, onNogrClick, onRmgrClick, ruleDoc, onRuleDocClick, onRuleDocClose }) {
  const activeItem = PAPER_TRAIL_CODES.find(c => c.code === active) || PAPER_TRAIL_CODES[0];
  const [selectedNprr, setSelectedNprr] = React.useState(null);
  const [selectedCopmgrr, setSelectedCopmgrr] = React.useState(null);
  const [selectedPgrr, setSelectedPgrr] = React.useState(null);
  const [selectedScr, setSelectedScr] = React.useState(null);
  const [selectedNogrr, setSelectedNogrr] = React.useState(null);
  const [selectedRmgrr, setSelectedRmgrr] = React.useState(null);

  React.useEffect(() => { setSelectedNprr(null); setSelectedCopmgrr(null); setSelectedPgrr(null); setSelectedScr(null); setSelectedNogrr(null); setSelectedRmgrr(null); }, [active]);

  const handleNprrClick = (n) => {
    setSelectedNprr(n);
    if (onNprrClick) onNprrClick(n);
  };
  const handleBack = () => {
    setSelectedNprr(null);
    if (onNprrClick) onNprrClick(null);
  };
  const handleCopmgrrClick = (n) => {
    setSelectedCopmgrr(n);
    if (onCopmgrrClick) onCopmgrrClick(n);
  };
  const handleCopmgrrBack = () => {
    setSelectedCopmgrr(null);
    if (onCopmgrrClick) onCopmgrrClick(null);
  };
  const handlePgrrClick = (n) => {
    setSelectedPgrr(n);
    if (onPgrrClick) onPgrrClick(n);
  };
  const handlePgrrBack = () => {
    setSelectedPgrr(null);
    if (onPgrrClick) onPgrrClick(null);
  };
  const handleScrClick = (n) => {
    setSelectedScr(n);
    if (onScrClick) onScrClick(n);
  };
  const handleScrBack = () => {
    setSelectedScr(null);
    if (onScrClick) onScrClick(null);
  };
  const handleNogrClick = (n) => {
    setSelectedNogrr(n);
    if (onNogrClick) onNogrClick(n);
  };
  const handleNogrBack = () => {
    setSelectedNogrr(null);
    if (onNogrClick) onNogrClick(null);
  };
  const handleRmgrClick = (n) => {
    setSelectedRmgrr(n);
    if (onRmgrClick) onRmgrClick(n);
  };
  const handleRmgrBack = () => {
    setSelectedRmgrr(null);
    if (onRmgrClick) onRmgrClick(null);
  };
  return (
    <div className="pt-paper">
      <style>{`
        .pt-paper {
          border: 1px solid var(--rule);
          background:
            radial-gradient(120% 80% at 100% 0%, var(--accent-soft) 0%, transparent 55%),
            linear-gradient(180deg, var(--panel), var(--bg-2));
          border-radius: var(--radius);
          padding: 22px;
          box-shadow: var(--shadow-1);
          position: relative; overflow: hidden;
        }
        .pt-paper-head {
          display: flex; align-items: baseline; gap: 10px; position: relative;
          margin-bottom: 16px;
        }
        .pt-paper-eye {
          font-family: var(--mono); font-size: 10.5px; letter-spacing: .14em;
          color: var(--muted); text-transform: uppercase;
        }
        .pt-paper-title {
          font-family: var(--serif); font-size: 26px; line-height: 1.1;
          margin: 2px 0 0; font-weight: 400; color: var(--ink);
        }
        .pt-paper-sub {
          color: var(--ink-2); font-size: 13px; margin-top: 4px;
        }
        .pt-paper-grid {
          position: relative;
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 8px;
          margin-top: 14px;
        }
        @media (max-width: 480px) {
          .pt-paper-grid { grid-template-columns: repeat(2, minmax(0,1fr)); }
        }
        .pt-paper-btn {
          position: relative;
          padding: 14px 10px 12px;
          border: 1px solid var(--rule-2);
          background: var(--panel);
          border-radius: 10px;
          color: var(--ink);
          font-family: var(--mono);
          font-size: 13px; font-weight: 600; letter-spacing: .02em;
          display: flex; flex-direction: column; align-items: center; gap: 4px;
          cursor: pointer;
          transition: transform .12s, border-color .15s, background .15s, color .15s;
        }
        .pt-paper-btn:hover {
          border-color: var(--accent);
          transform: translateY(-1px);
          box-shadow: var(--shadow-1);
        }
        .pt-paper-btn .n {
          font-size: 10px; font-weight: 500; color: var(--muted);
          letter-spacing: .04em;
        }
        .pt-paper-btn.is-on {
          background: var(--ink); color: var(--bg);
          border-color: var(--ink);
        }
        .pt-paper-btn.is-on .n { color: color-mix(in oklab, var(--bg), transparent 40%); }
        .pt-paper-detail {
          margin-top: 16px; padding-top: 14px;
          border-top: 1px dashed var(--rule-2);
          display: flex; align-items: center; gap: 14px;
          position: relative;
        }
        .pt-paper-detail .tag {
          font-family: var(--mono); font-size: 12px; font-weight: 600;
          padding: 4px 10px; border-radius: 6px;
          background: var(--accent-soft); color: var(--accent-2);
        }
        .pt-paper-detail .name { color: var(--ink); font-size: 14px; font-weight: 500; }
        .pt-paper-detail .count {
          margin-left: auto; font-family: var(--mono); font-size: 11px;
          color: var(--muted);
        }
      `}</style>

      <div className="pt-paper-head">
        <div>
          <div className="pt-paper-eye">Paper Trails</div>
          <h2 className="pt-paper-title">Pick a revision track</h2>
        </div>
      </div>

      <div className="pt-paper-grid">
        {PAPER_TRAIL_CODES.map(c => (
          <button key={c.code}
            className={`pt-paper-btn ${active === c.code ? "is-on" : ""}`}
            onClick={() => onActiveChange(c.code)}
            title={c.name}
          >
            <span>{c.code}</span>
            <span className="n">{c.count.toLocaleString()} docs</span>
          </button>
        ))}
      </div>

      <div className="pt-paper-detail">
        <span className="tag">{activeItem.code}</span>
        <span className="name">{activeItem.name}</span>
        <span className="count">{activeItem.count.toLocaleString()} documents on file</span>
      </div>

      {ruleDoc && <DocumentSummaryView doc={ruleDoc} onBack={onRuleDocClose} />}

      {!ruleDoc && active === "NPRR" && (
        selectedNprr
          ? <div style={{ marginTop: 16, borderTop: "1px dashed var(--rule-2)", paddingTop: 14 }}>
              <NprrDetailView nprr={selectedNprr} onBack={handleBack} onDocClick={onRuleDocClick} />
            </div>
          : <NprrPanels onNprrClick={handleNprrClick} />
      )}

      {!ruleDoc && active === "COPMGRR" && (
        selectedCopmgrr
          ? <div style={{ marginTop: 16, borderTop: "1px dashed var(--rule-2)", paddingTop: 14 }}>
              <CopmgrrDetailView copmgrr={selectedCopmgrr} onBack={handleCopmgrrBack} onDocClick={onRuleDocClick} />
            </div>
          : <CopmgrrPanels onCopmgrrClick={handleCopmgrrClick} />
      )}

      {!ruleDoc && active === "PGRR" && (
        selectedPgrr
          ? <div style={{ marginTop: 16, borderTop: "1px dashed var(--rule-2)", paddingTop: 14 }}>
              <PgrrDetailView pgrr={selectedPgrr} onBack={handlePgrrBack} onDocClick={onRuleDocClick} />
            </div>
          : <PgrrPanels onPgrrClick={handlePgrrClick} />
      )}

      {!ruleDoc && active === "SCR" && (
        selectedScr
          ? <div style={{ marginTop: 16, borderTop: "1px dashed var(--rule-2)", paddingTop: 14 }}>
              <ScrDetailView scr={selectedScr} onBack={handleScrBack} onDocClick={onRuleDocClick} />
            </div>
          : <ScrPanels onScrClick={handleScrClick} />
      )}

      {!ruleDoc && active === "NOGRR" && (
        selectedNogrr
          ? <div style={{ marginTop: 16, borderTop: "1px dashed var(--rule-2)", paddingTop: 14 }}>
              <NogrDetailView nogrr={selectedNogrr} onBack={handleNogrBack} onDocClick={onRuleDocClick} />
            </div>
          : <NogrPanels onNogrClick={handleNogrClick} />
      )}

      {!ruleDoc && active === "RMGRR" && (
        selectedRmgrr
          ? <div style={{ marginTop: 16, borderTop: "1px dashed var(--rule-2)", paddingTop: 14 }}>
              <RmgrDetailView rmgrr={selectedRmgrr} onBack={handleRmgrBack} onDocClick={onRuleDocClick} />
            </div>
          : <RmgrPanels onRmgrClick={handleRmgrClick} />
      )}
    </div>
  );
}

// Local OneDrive folder paths for codes that have downloaded document sets
const FOLDER_PATHS = {
  "NPRR":    "file:///E:/wamp64/www/Power.Talks/Documents%20Database/ERCOT.MKT.RULES/NPRR",
  "SCR":     "file:///E:/wamp64/www/Power.Talks/Documents%20Database/ERCOT.MKT.RULES/SCR",
  "NOGRR":   "file:///E:/wamp64/www/Power.Talks/Documents%20Database/ERCOT.MKT.RULES/NOGRR",
  "COPMGRR": "file:///E:/wamp64/www/Power.Talks/Documents%20Database/ERCOT.MKT.RULES/COPMGRR",
  "PGRR":    "file:///E:/wamp64/www/Power.Talks/Documents%20Database/ERCOT.MKT.RULES/PGRR",
};

window.PaperTrailsIllustration = PaperTrailsIllustration;
window.PAPER_TRAIL_CODES = PAPER_TRAIL_CODES;
window.FOLDER_PATHS = FOLDER_PATHS;

// ERCOT market home page — shown when ERCOT is selected from the ISO market list
function ERCOTHome({ onSectionChange }) {
  const LINKS = [
    { id: "paper-trails",     icon: "Book",      label: "Paper Trails",     desc: "NPRRs, NOGRRs, COPMGRRs and more"  },
    { id: "meeting-tracks",   icon: "Waveform",  label: "Meeting Tracks",   desc: "TAC, COPS, RMS committee activity"  },
    { id: "hot-topics",       icon: "Flame",     label: "Hot Topics",       desc: "Market design issues and debates"   },
    { id: "daily-headlines",  icon: "Lightning", label: "Daily Headlines",  desc: "Latest ERCOT news and alerts"       },
    { id: "stats-illustrated",icon: "Chart",     label: "Stats Illustrator",desc: "Charts, data, and market analytics" },
    { id: "gallery",          icon: "Folder",    label: "Gallery",          desc: "Documents, filings, and archives"   },
  ];
  return (
    <div className="pt-ercot-home">
      <style>{`
        .pt-ercot-home { padding: 24px 28px 32px; max-width: 760px; margin: 0 auto; }
        .pt-ercot-hdr {
          display: flex; align-items: center; gap: 14px; margin-bottom: 22px;
        }
        .pt-ercot-logo {
          width: 48px; height: 48px; border-radius: 12px;
          background: var(--accent); display: grid; place-items: center;
          flex: 0 0 auto; color: #fff;
        }
        .pt-ercot-h1 {
          font-family: var(--serif); font-size: 32px; font-weight: 700;
          color: var(--ink); margin: 0; line-height: 1.15;
        }
        .pt-ercot-sub { color: var(--ink-2); font-size: 13px; margin-top: 2px; }
        .pt-ercot-intro { margin-bottom: 20px; }
        .pt-ercot-intro-eye {
          font-family: var(--mono); font-size: 10px; letter-spacing: .1em;
          text-transform: uppercase; color: var(--muted); font-weight: 500;
          margin-bottom: 7px;
        }
        .pt-ercot-intro-body {
          font-size: 13px; color: var(--ink-2); line-height: 1.75;
        }
        .pt-ercot-intro-divider {
          border: none; border-top: 1px dashed var(--rule-2); margin: 18px 0;
        }
        .pt-ercot-qlbl {
          font-size: 11px; font-family: var(--mono); letter-spacing: .08em;
          text-transform: uppercase; color: var(--muted); font-weight: 500; margin-bottom: 10px;
        }
        .pt-ercot-links {
          display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px;
        }
        @media (max-width: 560px) { .pt-ercot-links { grid-template-columns: 1fr; } }
        .pt-ercot-lnk {
          display: flex; align-items: flex-start; gap: 12px;
          padding: 14px 16px; border: 1px solid var(--rule-2);
          border-radius: 10px; background: var(--panel);
          color: var(--ink); text-align: left; cursor: pointer;
          transition: border-color .15s, transform .1s, box-shadow .1s;
        }
        .pt-ercot-lnk:hover {
          border-color: var(--accent); transform: translateY(-1px); box-shadow: var(--shadow-1);
        }
        .pt-ercot-lnk-ico {
          width: 32px; height: 32px; border-radius: 8px;
          background: var(--accent-soft); display: grid; place-items: center;
          color: var(--accent-2); flex: 0 0 auto;
        }
        .pt-ercot-lnk b { display: block; font-weight: 500; font-size: 13.5px; margin-bottom: 2px; }
        .pt-ercot-lnk span { font-size: 12px; color: var(--muted); line-height: 1.4; }
      `}</style>

      <div className="pt-ercot-hdr">
        <div className="pt-ercot-logo"><I.Bolt size={22}/></div>
        <div>
          <h1 className="pt-ercot-h1">ERCOT</h1>
          <div className="pt-ercot-sub">Electric Reliability Council of Texas</div>
        </div>
      </div>

      <div className="pt-ercot-intro">
        <div className="pt-ercot-intro-eye">About ERCOT</div>
        <div className="pt-ercot-intro-body">
          ERCOT (Electric Reliability Council of Texas) is the independent system operator (ISO) for roughly 90% of Texas's electric load, managing over 89,000 MW of generation capacity and serving approximately 26 million customers. As a non-profit, member-governed organization, ERCOT operates one of the largest competitive wholesale electricity markets in North America. The market is energy-only — there is no separate capacity market — relying instead on real-time scarcity pricing and ancillary service markets to maintain grid reliability and incentivize investment in generation resources. ERCOT is unique among U.S. ISOs in operating an intrastate grid largely isolated from neighboring interconnections, giving Texas significant autonomy over its own market design. Most recently, ERCOT launched Real-Time Co-optimization with Batteries (RTC-B), a landmark market enhancement that simultaneously optimizes energy and ancillary service awards for battery storage resources in the real-time market — enabling batteries to provide multiple grid services at once and significantly improving the efficiency of storage dispatch across the grid.
        </div>
      </div>

      <hr className="pt-ercot-intro-divider"/>

      <div className="pt-ercot-intro">
        <div className="pt-ercot-intro-eye">Market Rules &amp; Stakeholder Process</div>
        <div className="pt-ercot-intro-body">
          ERCOT's market rules are codified in the Nodal Protocols and several associated guides — the Planning Guide, Operating Guide, Retail Market Guide, Verifiable Cost Manual, and others. Changes to these rules are proposed through standardized revision requests submitted by any market participant, ERCOT staff, or the Public Utility Commission of Texas (PUCT): NPRRs (Nodal Protocol), NOGRRs (Operating Guide), PGRRs (Planning Guide), COPMGRRs (Commercial Operations), and more. Each request advances through a structured stakeholder review — working groups and subcommittees (WMS, COPS, RMS, PRS) analyze and discuss the proposal, which then proceeds to the Technical Advisory Committee (TAC) for recommendation. TAC sends approved revisions to the ERCOT Board of Directors for final vote. The PUCT holds ultimate regulatory authority and may direct or override Board decisions on significant market design matters.
        </div>
      </div>

      <hr className="pt-ercot-intro-divider"/>

      <div className="pt-ercot-qlbl">Quick Access</div>
      <div className="pt-ercot-links">
        {LINKS.map(l => {
          const Ico = I[l.icon];
          return (
            <button key={l.id} className="pt-ercot-lnk" onClick={() => onSectionChange && onSectionChange(l.id)}>
              <div className="pt-ercot-lnk-ico"><Ico size={16}/></div>
              <div><b>{l.label}</b><span>{l.desc}</span></div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

window.ERCOTHome = ERCOTHome;

// ── Hot Topics home ─────────────────────────────────────────────────────────
// Center view for the "hot-topics" section. It reads the daily reports produced
// under  Documents Database/HOT.TOPICS/<date>/hot_topics_<date>.md  (see the
// "Hot Topics Generator" skill). A date dropdown picks which day's report to
// show — the most recent date is selected by default. Content is fetched live
// from WAMP and rendered from Markdown in the browser, so a newly generated
// daily report appears without rebuilding the bundle; only index.json (the list
// of available dates, written by gen_hot_topics.py) needs refreshing.
const HT_BASE = "/Power.Talks/Documents%20Database/HOT.TOPICS";

function htEscape(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
// Inline Markdown → HTML: code spans, links, bold, italic. Content is escaped
// first so raw HTML in the source can never inject.
function htInline(s) {
  let t = htEscape(s);
  t = t.replace(/`([^`]+)`/g, (m, c) => `<code>${c}</code>`);
  t = t.replace(/\[([^\]]+)\]\(([^)\s]+)\)/g,
        (m, txt, url) => `<a href="${url}" target="_blank" rel="noopener noreferrer">${txt}</a>`);
  t = t.replace(/\*\*([^*]+)\*\*/g, (m, c) => `<strong>${c}</strong>`);
  t = t.replace(/\*([^*]+)\*/g, (m, c) => `<em>${c}</em>`);
  return t;
}
// One (optionally nested) bullet list. Returns [html, nextIndex].
function htParseList(lines, start) {
  let i = start;
  const items = [];
  while (i < lines.length && /^-\s+/.test(lines[i])) {
    let content = lines[i].replace(/^-\s+/, "");
    i++;
    const children = [];
    while (i < lines.length && /^\s{2,}-\s+/.test(lines[i])) {
      children.push(lines[i].replace(/^\s*-\s+/, ""));
      i++;
    }
    let li = `<li>${htInline(content)}`;
    if (children.length) li += `<ul>${children.map(c => `<li>${htInline(c)}</li>`).join("")}</ul>`;
    items.push(li + "</li>");
  }
  return [`<ul>${items.join("")}</ul>`, i];
}
// Block Markdown → HTML. Supports headings, GFM tables (with alignment),
// bullet lists (one nesting level), blockquotes, hr, and paragraphs — the
// constructs the daily reports use. The first H1 is dropped because the date is
// already shown in the header/dropdown.
function htMarkdownToHtml(md) {
  const lines = String(md).replace(/\r\n/g, "\n").split("\n");
  const out = [];
  let para = [];
  let i = 0, strippedH1 = false;
  const flush = () => { if (para.length) { out.push(`<p>${htInline(para.join(" "))}</p>`); para = []; } };
  while (i < lines.length) {
    const line = lines[i];
    const t = line.trim();
    if (!strippedH1 && /^#\s+/.test(t)) { strippedH1 = true; i++; continue; }
    if (t === "") { flush(); i++; continue; }
    // GFM table: a pipe row immediately followed by a separator row
    if (/^\|.*\|$/.test(t) && i + 1 < lines.length && /^\|[\s:|-]+\|$/.test(lines[i + 1].trim())) {
      flush();
      const cells = (row) => row.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map(c => c.trim());
      const header = cells(t);
      const align = cells(lines[i + 1]).map(c => {
        const l = c.startsWith(":"), r = c.endsWith(":");
        return (l && r) ? "center" : r ? "right" : l ? "left" : "";
      });
      i += 2;
      const body = [];
      while (i < lines.length && /^\|.*\|$/.test(lines[i].trim())) { body.push(cells(lines[i])); i++; }
      const sty = (k) => align[k] ? ` style="text-align:${align[k]}"` : "";
      let tbl = "<table class=\"ht-table\"><thead><tr>";
      header.forEach((h, k) => tbl += `<th${sty(k)}>${htInline(h)}</th>`);
      tbl += "</tr></thead><tbody>";
      body.forEach(r => { tbl += "<tr>"; r.forEach((c, k) => tbl += `<td${sty(k)}>${htInline(c)}</td>`); tbl += "</tr>"; });
      out.push(tbl + "</tbody></table>");
      continue;
    }
    const h = t.match(/^(#{1,6})\s+(.*)$/);
    if (h) { flush(); out.push(`<h${h[1].length}>${htInline(h[2])}</h${h[1].length}>`); i++; continue; }
    if (/^---+$/.test(t)) { flush(); out.push("<hr/>"); i++; continue; }
    if (/^>\s?/.test(t)) {
      flush();
      const buf = [];
      while (i < lines.length && /^>\s?/.test(lines[i].trim())) { buf.push(lines[i].trim().replace(/^>\s?/, "")); i++; }
      out.push(`<blockquote>${htInline(buf.join(" "))}</blockquote>`);
      continue;
    }
    if (/^-\s+/.test(line)) { flush(); const [html, ni] = htParseList(lines, i); out.push(html); i = ni; continue; }
    para.push(t); i++;
  }
  flush();
  return out.join("\n");
}

// Drop whole `##`-level sections whose heading matches any of `titles` (emoji
// and punctuation ignored), including their `###` subsections. Used to hide the
// "Source Summaries" and "Sources checked" sections from the website while the
// database .md files keep them in full.
function htStripSections(md, titles) {
  const norm = (s) => String(s).replace(/[^a-z0-9 ]/gi, " ").replace(/\s+/g, " ").trim().toLowerCase();
  const drop = titles.map(norm);
  const lines = String(md).replace(/\r\n/g, "\n").split("\n");
  const out = [];
  let skip = false;
  for (const line of lines) {
    const h = line.match(/^(#{1,6})\s+(.*)$/);
    if (h && h[1].length <= 2) skip = drop.some(d => norm(h[2]).includes(d));
    if (!skip) out.push(line);
  }
  return out.join("\n");
}
const HT_HIDDEN_SECTIONS = ["Source Summaries", "Sources checked"];

// Calendar date picker for the Hot Topics section. `dates` is the index.json
// list (newest-first) of days that have a report; only those days are
// selectable. Renders a button showing the current date that opens a month grid
// popover; month navigation is clamped to the range of available reports.
function HotTopicsDatePicker({ dates, value, onChange }) {
  const [open, setOpen] = React.useState(false);
  const ref = React.useRef(null);
  const avail = React.useMemo(() => new Set(dates.map(d => d.date)), [dates]);
  const parse = (s) => { const [y, m, d] = s.split("-").map(Number); return new Date(y, m - 1, d); };
  const iso = (y, m, d) => `${y}-${String(m + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
  const fmtLong = (s) => parse(s).toLocaleDateString("en-US", { weekday: "short", year: "numeric", month: "short", day: "numeric" });

  const anchor = value ? parse(value) : (dates[0] ? parse(dates[0].date) : new Date());
  const [view, setView] = React.useState({ y: anchor.getFullYear(), m: anchor.getMonth() });

  // Reset the visible month to the selected date each time the popover opens.
  React.useEffect(() => { if (open) setView({ y: anchor.getFullYear(), m: anchor.getMonth() }); }, [open, value]);

  // Close on outside click / Escape.
  React.useEffect(() => {
    if (!open) return;
    const onDoc = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    const onKey = (e) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("mousedown", onDoc); document.removeEventListener("keydown", onKey); };
  }, [open]);

  const maxD = dates.length ? parse(dates[0].date) : anchor;                 // newest
  const minD = dates.length ? parse(dates[dates.length - 1].date) : anchor;  // oldest
  const viewYm = view.y * 12 + view.m;
  const atMax = viewYm >= maxD.getFullYear() * 12 + maxD.getMonth();
  const atMin = viewYm <= minD.getFullYear() * 12 + minD.getMonth();
  const shift = (delta) => setView(v => { const d = new Date(v.y, v.m + delta, 1); return { y: d.getFullYear(), m: d.getMonth() }; });

  const monthLabel = new Date(view.y, view.m, 1).toLocaleDateString("en-US", { month: "long", year: "numeric" });
  const firstDow = new Date(view.y, view.m, 1).getDay();
  const daysInMonth = new Date(view.y, view.m + 1, 0).getDate();
  const cells = [];
  for (let i = 0; i < firstDow; i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(d);

  return (
    <div className="ht-cal" ref={ref}>
      <button className="ht-cal-btn" onClick={() => setOpen(o => !o)} aria-haspopup="dialog" aria-expanded={open}>
        <I.Calendar size={14}/>
        <span>{value ? fmtLong(value) : "Select date"}</span>
        <span className="ht-cal-caret"><I.ChevD size={12}/></span>
      </button>
      {open && (
        <div className="ht-cal-pop" role="dialog" aria-label="Choose report date">
          <div className="ht-cal-nav">
            <button className="ht-cal-arrow" onClick={() => shift(-1)} disabled={atMin} aria-label="Previous month"><I.ChevL size={15}/></button>
            <div className="ht-cal-month">{monthLabel}</div>
            <button className="ht-cal-arrow" onClick={() => shift(1)} disabled={atMax} aria-label="Next month"><I.ChevR size={15}/></button>
          </div>
          <div className="ht-cal-week">
            {["S", "M", "T", "W", "T", "F", "S"].map((w, i) => <div key={i} className="ht-cal-wd">{w}</div>)}
          </div>
          <div className="ht-cal-days">
            {cells.map((d, i) => {
              if (d === null) return <div key={i} className="ht-cal-blank"/>;
              const ds = iso(view.y, view.m, d);
              const has = avail.has(ds);
              const isSel = ds === value;
              return (
                <button key={i} type="button" disabled={!has}
                  className={"ht-cal-day" + (has ? " has" : "") + (isSel ? " sel" : "")}
                  title={has ? fmtLong(ds) : "No report"}
                  onClick={() => { onChange(ds); setOpen(false); }}>
                  {d}
                </button>
              );
            })}
          </div>
          {dates.length > 0 && (
            <button className="ht-cal-latest" onClick={() => { onChange(dates[0].date); setOpen(false); }}>
              Jump to latest report
            </button>
          )}
        </div>
      )}
    </div>
  );
}

function HotTopicsHome() {
  const [index, setIndex]       = React.useState(null);       // { dates: [{date,file,title}] }
  const [sel, setSel]           = React.useState(null);       // selected date string
  const [bodyHtml, setBodyHtml] = React.useState("");
  const [state, setState]       = React.useState("loading");  // loading | ready | error | empty
  const [docState, setDocState] = React.useState("idle");     // idle | loading | ready | error

  // Load the list of available dates once.
  React.useEffect(() => {
    setState("loading");
    fetch(`${HT_BASE}/index.json`, { cache: "no-store" })
      .then(r => r.ok ? r.json() : Promise.reject(`HTTP ${r.status}`))
      .then(d => {
        const dates = (d.dates || []).slice();
        if (!dates.length) { setState("empty"); return; }
        setIndex({ ...d, dates });
        setSel(dates[0].date);   // most recent (index.json is newest-first)
        setState("ready");
      })
      .catch(() => setState("error"));
  }, []);

  // Load the selected date's report whenever the selection changes.
  React.useEffect(() => {
    if (!sel || !index) return;
    const entry = (index.dates || []).find(x => x.date === sel);
    if (!entry) return;
    setDocState("loading"); setBodyHtml("");
    fetch(`${HT_BASE}/${encodeURIComponent(sel)}/${encodeURIComponent(entry.file)}`, { cache: "no-store" })
      .then(r => r.ok ? r.text() : Promise.reject(`HTTP ${r.status}`))
      .then(md => { setBodyHtml(htMarkdownToHtml(htStripSections(md, HT_HIDDEN_SECTIONS))); setDocState("ready"); })
      .catch(() => setDocState("error"));
  }, [sel, index]);

  return (
    <div className="ht-home">
      <style>{`
        .ht-home { padding: 24px 28px 40px; max-width: 860px; margin: 0 auto; }
        .ht-hdr { display: flex; align-items: center; gap: 14px; margin-bottom: 20px; flex-wrap: wrap; }
        .ht-logo {
          width: 44px; height: 44px; border-radius: 11px; background: var(--accent);
          display: grid; place-items: center; color: #fff; flex: 0 0 auto;
        }
        .ht-h1 { font-family: var(--serif); font-size: 30px; font-weight: 700; color: var(--ink); margin: 0; line-height: 1.15; }
        .ht-sub { color: var(--ink-2); font-size: 13px; margin-top: 2px; }
        .ht-cal { margin-left: auto; position: relative; }
        .ht-cal-btn {
          display: flex; align-items: center; gap: 8px;
          font-family: var(--sans); font-size: 13px; color: var(--ink);
          background: var(--panel); border: 1px solid var(--rule-2); border-radius: 8px;
          padding: 7px 10px 7px 12px; cursor: pointer;
        }
        .ht-cal-btn:hover { border-color: var(--accent); }
        .ht-cal-btn > span:first-of-type { min-width: 0; }
        .ht-cal-caret { color: var(--muted); display: inline-flex; }
        .ht-cal-pop {
          position: absolute; top: calc(100% + 6px); right: 0; z-index: 30; width: 268px;
          background: var(--panel); border: 1px solid var(--rule-2); border-radius: 12px;
          box-shadow: var(--shadow-1); padding: 12px;
        }
        .ht-cal-nav { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
        .ht-cal-month { font-family: var(--sans); font-size: 13.5px; font-weight: 600; color: var(--ink); }
        .ht-cal-arrow {
          width: 28px; height: 28px; border-radius: 7px; display: grid; place-items: center;
          background: transparent; border: 1px solid var(--rule-2); color: var(--ink-2); cursor: pointer;
        }
        .ht-cal-arrow:hover:not(:disabled) { border-color: var(--accent); color: var(--accent-2); }
        .ht-cal-arrow:disabled { opacity: .35; cursor: default; }
        .ht-cal-week, .ht-cal-days { display: grid; grid-template-columns: repeat(7, 1fr); gap: 2px; }
        .ht-cal-wd {
          text-align: center; font-family: var(--mono); font-size: 10px; color: var(--muted);
          padding: 4px 0; text-transform: uppercase;
        }
        .ht-cal-blank { aspect-ratio: 1; }
        .ht-cal-day {
          aspect-ratio: 1; display: grid; place-items: center; border: none; border-radius: 7px;
          font-family: var(--sans); font-size: 12.5px; color: var(--muted);
          background: transparent; cursor: default;
        }
        .ht-cal-day.has { color: var(--ink); background: var(--accent-soft); cursor: pointer; font-weight: 500; }
        .ht-cal-day.has:hover { background: var(--accent); color: #fff; }
        .ht-cal-day.sel { background: var(--accent); color: #fff; font-weight: 600; }
        .ht-cal-day:disabled { opacity: .5; }
        .ht-cal-latest {
          margin-top: 10px; width: 100%; padding: 7px; border-radius: 8px;
          border: 1px solid var(--rule-2); background: transparent; cursor: pointer;
          font-family: var(--mono); font-size: 10.5px; letter-spacing: .05em; text-transform: uppercase; color: var(--ink-2);
        }
        .ht-cal-latest:hover { border-color: var(--accent); color: var(--accent-2); }
        .ht-status { color: var(--muted); font-size: 13px; padding: 40px 0; text-align: center; }
        .ht-md { font-size: 13.5px; color: var(--ink-2); line-height: 1.7; }
        .ht-md h1 { font-family: var(--serif); font-size: 26px; color: var(--ink); margin: 22px 0 10px; }
        .ht-md h2 { font-size: 18px; color: var(--ink); margin: 26px 0 10px; font-weight: 600; }
        .ht-md h3 {
          font-size: 12px; font-family: var(--mono); letter-spacing: .06em; text-transform: uppercase;
          color: var(--muted); margin: 20px 0 8px; font-weight: 500;
        }
        .ht-md p { margin: 10px 0; }
        .ht-md ul { margin: 8px 0; padding-left: 20px; }
        .ht-md li { margin: 4px 0; }
        .ht-md a { color: var(--accent-2); text-decoration: none; }
        .ht-md a:hover { text-decoration: underline; }
        .ht-md strong { color: var(--ink); font-weight: 600; }
        .ht-md code { font-family: var(--mono); font-size: 12px; background: var(--accent-soft); padding: 1px 5px; border-radius: 4px; }
        .ht-md hr { border: none; border-top: 1px dashed var(--rule-2); margin: 20px 0; }
        .ht-md blockquote {
          margin: 12px 0; padding: 8px 14px; border-left: 3px solid var(--accent);
          background: var(--accent-soft); border-radius: 0 6px 6px 0; color: var(--ink-2);
        }
        .ht-md .ht-table {
          border-collapse: collapse; width: 100%; margin: 14px 0; font-size: 12.5px; display: block; overflow-x: auto;
        }
        .ht-md .ht-table th, .ht-md .ht-table td {
          border: 1px solid var(--rule-2); padding: 7px 10px; vertical-align: top; text-align: left;
        }
        .ht-md .ht-table th { background: var(--panel); color: var(--ink); font-weight: 600; }
      `}</style>

      <div className="ht-hdr">
        <div className="ht-logo"><I.Flame size={20}/></div>
        <div>
          <h1 className="ht-h1">Hot Topics</h1>
          <div className="ht-sub">Daily ERCOT market intelligence — ranked by cross-source frequency</div>
        </div>
        {state === "ready" && index && (
          <HotTopicsDatePicker dates={index.dates} value={sel} onChange={setSel}/>
        )}
      </div>

      {state === "loading" && <div className="ht-status">Loading Hot Topics…</div>}
      {state === "empty"   && <div className="ht-status">No Hot Topics reports yet. Run the Hot Topics Generator skill to create today's report.</div>}
      {state === "error"   && <div className="ht-status">Couldn't load the Hot Topics index. Is WAMP serving <code>Documents Database/HOT.TOPICS/index.json</code>?</div>}

      {state === "ready" && (
        docState === "loading" ? <div className="ht-status">Loading report…</div>
        : docState === "error" ? <div className="ht-status">Couldn't load this date's report.</div>
        : <div className="ht-md" dangerouslySetInnerHTML={{ __html: bodyHtml }}/>
      )}
    </div>
  );
}
window.HotTopicsHome = HotTopicsHome;
