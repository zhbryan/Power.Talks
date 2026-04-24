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
  { code: "NPRR",   name: "Nodal Protocol Revision Request",        count: 1287 },
  { code: "SCR",    name: "System Change Request",                   count: 412 },
  { code: "COPMGRR",name: "Commercial Ops Planning & Mkt Biz Req.",  count: 58  },
  { code: "NOGRR",  name: "Nodal Operating Guide Revision Request",  count: 274 },
  { code: "OBDRR",  name: "Other Binding Document Revision Request", count: 96  },
  { code: "PGRR",   name: "Planning Guide Revision Request",         count: 118 },
  { code: "RMGRR",  name: "Retail Market Guide Revision Request",    count: 203 },
  { code: "RRGRR",  name: "Resource Registration Glossary RR",       count: 47  },
  { code: "SMOGRR", name: "Settlement Metering Op. Guide RR",        count: 81  },
  { code: "VCMRR",  name: "Verifiable Cost Manual Revision Request", count: 39  },
];

function NprrDetailView({ nprr, onBack }) {
  const [summary, setSummary] = React.useState(null);
  const [loading, setLoading] = React.useState(true);
  const [error,   setError]   = React.useState(null);

  React.useEffect(() => {
    setLoading(true); setError(null); setSummary(null);
    fetch(`/Power.Talks/Documents%20Database/ERCOT.MKT.RULES/NPRR/NPRR${nprr}/Quick%20runs/NPRR${nprr}%20Summary.json`)
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
          border-top:1px dashed var(--rule-2); padding-top:12px; margin:18px 0 8px;
        }
        .nd-body { font-size:13px; color:var(--ink-2); line-height:1.7; margin-bottom:10px; }
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

      {summary && <>
        <h2 className="nd-title">{summary.title}</h2>
        <div className="nd-eyebrow">
          Posted {summary.date_posted}
          {summary.effective_date ? `  ·  Effective: ${summary.effective_date}` : ""}
          {summary.sponsor ? `  ·  Sponsor: ${summary.sponsor}` : ""}
        </div>

        {summary.protocol_sections?.length > 0 && <>
          <div>{summary.protocol_sections.map((s, i) =>
            <span key={i} className="nd-proto-tag">{s}</span>
          )}</div>
        </>}

        {/* 1. Executive Summary */}
        <div className="nd-sec-hd">Executive Summary</div>
        <div className="nd-body">{summary.executive_summary}</div>

        {/* 2. Background */}
        {summary.background && <>
          <div className="nd-sec-hd">Background</div>
          <div className="nd-body">{summary.background}</div>
        </>}

        {/* 3. Key Protocol Change */}
        {summary.key_change && <>
          <div className="nd-sec-hd">Key Protocol Change</div>
          <div className="nd-body">{summary.key_change}</div>
        </>}

        {/* 4. Potential Impacts */}
        {summary.impacts?.length > 0 && <>
          <div className="nd-sec-hd">Potential Impacts</div>
          <div className="nd-impact-list">
            {summary.impacts.map((imp, i) => (
              <div key={i} className="nd-impact-row">
                <span className="nd-impact-cat">{imp.category}</span>
                <span className="nd-impact-txt">{imp.text}</span>
              </div>
            ))}
          </div>
        </>}

        {/* 5. Impact Analysis tables */}
        {summary.impact_analysis?.length > 0 && <>
          <div className="nd-sec-hd">Impact Analysis</div>
          {summary.impact_analysis.map((ia, i) => (
            <div key={i}>
              <div className="nd-ia-lbl">{ia.label}</div>
              <table className="nd-table">
                <thead><tr><th>Category</th><th>Detail</th></tr></thead>
                <tbody>
                  {ia.rows.map((row, j) => (
                    <tr key={j}><td>{row[0]}</td><td>{row[1]}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
        </>}

        {/* 6. Stakeholder Timeline */}
        {summary.timeline?.length > 0 && <>
          <div className="nd-sec-hd">Stakeholder Discussion Timeline</div>
          <table className="nd-tl-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Body</th>
                <th>Action / Vote</th>
                <th>Notes</th>
              </tr>
            </thead>
            <tbody>
              {summary.timeline.map((t, i) => (
                <tr key={i}>
                  <td className="nd-tl-date-cell">{t.date}</td>
                  <td className="nd-tl-body-cell">{t.body}</td>
                  <td className="nd-tl-action-cell">{t.action}</td>
                  <td>{t.notes}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>}

        {/* 7. Current Status */}
        {summary.current_status?.length > 0 && <>
          <div className="nd-sec-hd">Current Status</div>
          {summary.current_status.map((p, i) =>
            <div key={i} className="nd-body">{p}</div>
          )}
        </>}
      </>}
    </div>
  );
}

function NprrListPanel({ label, items, maxHeight, statusColor, onNprrClick }) {
  const [query, setQuery] = React.useState("");
  const baseFolder = FOLDER_PATHS["NPRR"];
  const filtered = items.filter(item => {
    const q = query.trim().toLowerCase();
    if (!q) return true;
    return String(item.n).includes(q) || item.title.toLowerCase().includes(q);
  });
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
          ? <div className="pt-nprr-empty">No matching NPRRs</div>
          : filtered.map(item => (
            <div
              key={item.n}
              className="pt-nprr-item"
              onClick={() => onNprrClick ? onNprrClick(item.n) : window.open(`${baseFolder}/NPRR${item.n}`, "_blank")}
              title={`NPRR${item.n} — ${item.title}`}
              style={{ cursor: "pointer" }}
            >
              <span className="pt-nprr-num">NPRR{item.n}</span>
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

function PaperTrailsIllustration({ active, onActiveChange, onNprrClick }) {
  const activeItem = PAPER_TRAIL_CODES.find(c => c.code === active) || PAPER_TRAIL_CODES[0];
  const [selectedNprr, setSelectedNprr] = React.useState(null);

  React.useEffect(() => { setSelectedNprr(null); }, [active]);

  const handleNprrClick = (n) => {
    setSelectedNprr(n);
    if (onNprrClick) onNprrClick(n);
  };
  const handleBack = () => {
    setSelectedNprr(null);
    if (onNprrClick) onNprrClick(null);
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
        .pt-paper::before {
          content: ""; position: absolute; inset: 0;
          background-image:
            repeating-linear-gradient(0deg, rgba(27,26,23,.04) 0 1px, transparent 1px 28px);
          pointer-events: none;
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
          grid-template-columns: repeat(5, minmax(0, 1fr));
          gap: 8px;
          margin-top: 14px;
        }
        @media (max-width: 720px) {
          .pt-paper-grid { grid-template-columns: repeat(3, minmax(0,1fr)); }
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
          <div className="pt-paper-sub">Select a rule-stack code to scope the conversation.</div>
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

      {active === "NPRR" && (
        selectedNprr
          ? <div style={{ marginTop: 16, borderTop: "1px dashed var(--rule-2)", paddingTop: 14 }}>
              <NprrDetailView nprr={selectedNprr} onBack={handleBack} />
            </div>
          : <NprrPanels onNprrClick={handleNprrClick} />
      )}
    </div>
  );
}

// Local OneDrive folder paths for codes that have downloaded document sets
const FOLDER_PATHS = {
  "NPRR":  "file:///E:/wamp64/www/Power.Talks/Documents%20Database/ERCOT.MKT.RULES/NPRR",
  "SCR":   "file:///E:/wamp64/www/Power.Talks/Documents%20Database/ERCOT.MKT.RULES/SCR",
  "NOGRR": "file:///E:/wamp64/www/Power.Talks/Documents%20Database/ERCOT.MKT.RULES/NOGRR",
};

window.PaperTrailsIllustration = PaperTrailsIllustration;
window.PAPER_TRAIL_CODES = PAPER_TRAIL_CODES;
window.FOLDER_PATHS = FOLDER_PATHS;

// ERCOT market home page — shown when ERCOT is selected from the ISO market list
function ERCOTHome({ onSectionChange }) {
  const STATS = [
    { label: "Grid Status",       value: "Normal",   unit: "",        ok: true  },
    { label: "Current Load",      value: "52,847",   unit: "MW"               },
    { label: "Wind Generation",   value: "14,203",   unit: "MW"               },
    { label: "Solar Generation",  value: "6,891",    unit: "MW"               },
    { label: "Installed Capacity",value: "89,312",   unit: "MW"               },
    { label: "Active NPRRs",      value: "1,287",    unit: "tracked"          },
  ];
  const LINKS = [
    { id: "paper-trails",    icon: "Book",      label: "Paper Trails",    desc: "NPRRs, NOGRRs, COPMGRRs and more" },
    { id: "meeting-tracks",  icon: "Waveform",  label: "Meeting Tracks",  desc: "TAC, COPS, RMS committee activity" },
    { id: "hot-topics",      icon: "Flame",     label: "Hot Topics",      desc: "Market design issues and debates"  },
    { id: "daily-headlines", icon: "Lightning", label: "Daily Headlines", desc: "Latest ERCOT news and alerts"      },
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
          font-family: var(--serif); font-size: 28px; font-weight: 400;
          color: var(--ink); margin: 0; line-height: 1.15;
        }
        .pt-ercot-sub { color: var(--ink-2); font-size: 13px; margin-top: 2px; }
        .pt-ercot-badge {
          margin-left: auto;
          padding: 5px 12px; border-radius: 99px;
          font-family: var(--mono); font-size: 11px; font-weight: 600; letter-spacing: .06em;
          background: color-mix(in oklab, #2d9e5a, transparent 85%);
          color: #1e7a44;
          border: 1px solid color-mix(in oklab, #2d9e5a, transparent 65%);
        }
        .pt-ercot-stats {
          display: grid; grid-template-columns: repeat(3, 1fr);
          gap: 10px; margin-bottom: 22px;
        }
        @media (max-width: 560px) { .pt-ercot-stats { grid-template-columns: repeat(2, 1fr); } }
        .pt-ercot-stat {
          padding: 14px 16px; border: 1px solid var(--rule);
          border-radius: 10px; background: var(--panel);
        }
        .pt-ercot-stat-val {
          font-family: var(--mono); font-size: 20px; font-weight: 700;
          color: var(--ink); letter-spacing: -.01em;
          display: flex; align-items: baseline; gap: 4px;
        }
        .pt-ercot-stat-val .u { font-size: 11px; font-weight: 500; color: var(--muted); }
        .pt-ercot-stat.ok .pt-ercot-stat-val { color: #1e7a44; }
        .pt-ercot-stat-lbl { font-size: 11.5px; color: var(--muted); margin-top: 3px; font-family: var(--mono); }
        .pt-ercot-rule { border: none; border-top: 1px solid var(--rule); margin: 0 0 18px; }
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
        <div className="pt-ercot-badge">GRID NORMAL</div>
      </div>

      <div className="pt-ercot-stats">
        {STATS.map((s, i) => (
          <div key={i} className={`pt-ercot-stat ${s.ok ? "ok" : ""}`}>
            <div className="pt-ercot-stat-val">
              {s.value}
              {s.unit && <span className="u">{s.unit}</span>}
            </div>
            <div className="pt-ercot-stat-lbl">{s.label}</div>
          </div>
        ))}
      </div>

      <hr className="pt-ercot-rule"/>

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
