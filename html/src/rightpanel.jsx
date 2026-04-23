function NprrProfileCard({ nprr }) {
  const [profile, setProfile] = React.useState(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState(null);

  React.useEffect(() => {
    setLoading(true); setError(null); setProfile(null);
    fetch(`/Power.Talks/Documents%20Database/ERCOT.MKT.RULES/NPRR/NPRR${nprr}/Quick%20runs/NPRR${nprr}%20Profile.json`)
      .then(r => r.ok ? r.json() : Promise.reject(`HTTP ${r.status}`))
      .then(d => { setProfile(d); setLoading(false); })
      .catch(e => { setError(String(e)); setLoading(false); });
  }, [nprr]);

  const STATUS_COLOR = { Approved: "var(--ok)", Withdrawn: "var(--muted)", Pending: "var(--warn)" };
  const sc = profile ? (STATUS_COLOR[profile.status] || "var(--muted)") : "var(--muted)";

  if (loading) return <div style={{ padding: "24px 0", textAlign: "center", color: "var(--muted)", fontFamily: "var(--mono)", fontSize: 11 }}>Loading profile…</div>;
  if (error) {
    const isNetwork = error.toLowerCase().includes("failed to fetch") || error.toLowerCase().includes("networkerror");
    return (
      <div style={{ padding: "12px 0", color: "var(--muted)", fontFamily: "var(--mono)", fontSize: 11, lineHeight: 1.6 }}>
        {isNetwork
          ? <>No profile loaded — open via <span style={{ color: "var(--accent-2)" }}>http://localhost</span>, not file://.</>
          : error.includes("404")
            ? <>Profile not yet generated for NPRR{nprr}.<br/>Run the <span style={{ color: "var(--accent-2)" }}>NPRR Profile</span> skill to create it.</>
            : <>Could not load profile. ({error})</>
        }
      </div>
    );
  }
  if (!profile) return null;

  const Field = ({ label, value }) => value ? (
    <div style={{ marginBottom: 10 }}>
      <div style={{ fontFamily: "var(--mono)", fontSize: "9.5px", letterSpacing: ".1em", textTransform: "uppercase", color: "var(--muted)", marginBottom: 3 }}>{label}</div>
      <div style={{ fontSize: "12.5px", color: "var(--ink-2)", lineHeight: 1.4 }}>{value}</div>
    </div>
  ) : null;

  return (
    <div>
      <style>{`
        .np-status-row { display:flex; align-items:center; gap:8px; margin-bottom:12px; }
        .np-badge { padding:2px 10px; border-radius:99px; font-family:var(--mono); font-size:10px; font-weight:600; letter-spacing:.06em; }
        .np-num { font-family:var(--mono); font-size:12px; font-weight:700; color:var(--accent-2); }
        .np-title { font-family:var(--serif); font-size:16px; font-weight:400; color:var(--ink); line-height:1.3; margin-bottom:14px; }
        .np-divider { border:0; border-top:1px dashed var(--rule-2); margin:12px 0; }
        .np-sec-lbl { font-family:var(--mono); font-size:9.5px; letter-spacing:.1em; text-transform:uppercase; color:var(--muted); margin-bottom:6px; }
        .np-proto-tag { font-family:var(--mono); font-size:10.5px; color:var(--accent-2); padding:3px 8px; border-radius:5px; background:var(--accent-soft); border:1px solid var(--rule-2); display:block; margin-bottom:4px; }
        .np-reason-chip { font-size:11px; color:var(--ink-2); padding:3px 8px; border-radius:99px; border:1px solid var(--rule-2); background:var(--bg); display:inline-block; margin:0 4px 4px 0; }
        .np-tl { display:flex; flex-direction:column; position:relative; }
        .np-tl::before { content:""; position:absolute; left:6px; top:6px; bottom:6px; width:1px; background:var(--rule-2); }
        .np-tl-row { display:flex; align-items:flex-start; gap:10px; padding:4px 0; }
        .np-tl-dot { width:13px; height:13px; border-radius:50%; flex-shrink:0; border:2px solid var(--accent); background:var(--bg); z-index:1; margin-top:1px; }
        .np-tl-dot.last { background:var(--accent); }
        .np-tl-date { font-family:var(--mono); font-size:9.5px; color:var(--muted); white-space:nowrap; min-width:68px; margin-top:2px; }
        .np-tl-ev { font-size:11.5px; color:var(--ink-2); }
        .np-tl-ev b { color:var(--ink); font-weight:600; }
      `}</style>

      <div className="np-status-row">
        <span className="np-num">NPRR{profile.nprr_number}</span>
        <span className="np-badge" style={{ background: sc + "22", color: sc }}>{profile.status}</span>
      </div>
      <div className="np-title">{profile.title}</div>

      <Field label="Date Posted"           value={profile.date_posted_decision} />
      <Field label="Requested Resolution"  value={profile.timeline_requested_resolution} />
      <Field label="Effective Date"        value={profile.effective_date} />
      <Field label="Market Segment"        value={profile.market_segment} />

      <hr className="np-divider" />
      <Field label="Sponsor"   value={profile.sponsor_name && `${profile.sponsor_name} · ${profile.sponsor_company}`} />
      <Field label="Email"     value={profile.sponsor_email} />
      <Field label="Phone"     value={profile.sponsor_phone} />

      {profile.protocol_sections_requiring_revision?.length > 0 && <>
        <hr className="np-divider" />
        <div className="np-sec-lbl">Protocol Sections</div>
        {profile.protocol_sections_requiring_revision.map((s, i) =>
          <span key={i} className="np-proto-tag">{s}</span>
        )}
      </>}

      {profile.reason_for_revision?.length > 0 && <>
        <hr className="np-divider" />
        <div className="np-sec-lbl">Reason for Revision</div>
        <div>{profile.reason_for_revision.map((r, i) =>
          <span key={i} className="np-reason-chip">{r}</span>
        )}</div>
      </>}

      {profile.timeline?.length > 0 && <>
        <hr className="np-divider" />
        <div className="np-sec-lbl">Timeline</div>
        <div className="np-tl">
          {profile.timeline.map((t, i) => (
            <div key={i} className="np-tl-row">
              <div className={`np-tl-dot ${i === profile.timeline.length - 1 ? "last" : ""}`} />
              <span className="np-tl-date">{t.date}</span>
              <span className="np-tl-ev"><b>{t.event}</b></span>
            </div>
          ))}
        </div>
      </>}
    </div>
  );
}

function RightPanel({ open, onClose, onRunPrompt, context }) {
  const { SUGGESTED_RUNS, ARTIFACTS } = window.DATA;
  const [tab, setTab] = React.useState("runs"); // runs | artifacts | profile

  const ctx = context || {};
  const hasNprr = Boolean(ctx.nprr);

  React.useEffect(() => {
    if (hasNprr) setTab("runs");
  }, [ctx.nprr]);

  return (
    <aside className={`pt-right ${open ? "is-open" : ""}`} aria-hidden={!open}>
      <style>{`
        .pt-right {
          grid-area: right;
          width: 360px;
          background: var(--panel);
          border-left: 1px solid var(--rule);
          display: flex; flex-direction: column;
          transition: width .28s cubic-bezier(.3,.7,.2,1), transform .28s;
          overflow: hidden;
        }
        .pt-right:not(.is-open) {
          width: 0;
          border-left-width: 0;
          pointer-events: none;
        }
        .pt-right-head {
          height: 52px; flex: 0 0 auto;
          padding: 0 14px 0 18px;
          border-bottom: 1px solid var(--rule);
          display: flex; align-items: center; gap: 10px;
        }
        .pt-right-title {
          font-family: var(--serif); font-size: 18px; color: var(--ink);
          letter-spacing: -.01em;
        }
        .pt-right-close {
          margin-left: auto;
          width: 32px; height: 32px; border-radius: 8px;
          display: grid; place-items: center;
          color: var(--muted);
        }
        .pt-right-close:hover { background: var(--bg-2); color: var(--ink); }

        .pt-right-tabs {
          display: flex; gap: 2px;
          padding: 10px 14px 0;
        }
        .pt-right-tab {
          padding: 6px 12px; border-radius: 8px;
          font-size: 12.5px; color: var(--muted);
        }
        .pt-right-tab.is-on {
          background: var(--bg-2); color: var(--ink);
        }

        .pt-right-scroll { flex: 1; overflow-y: auto; padding: 14px; }

        .pt-runs-note {
          font-size: 12px; color: var(--muted); margin: 0 0 12px;
          display: flex; align-items: center; gap: 8px;
        }
        .pt-runs-note::before {
          content: ""; width: 6px; height: 6px; background: var(--ok); border-radius: 999px;
          box-shadow: 0 0 0 3px color-mix(in oklab, var(--ok), transparent 80%);
        }

        .pt-run {
          border: 1px solid var(--rule);
          border-radius: 12px;
          padding: 14px;
          margin-bottom: 10px;
          background: var(--bg);
          cursor: pointer;
          transition: border-color .15s, transform .1s, box-shadow .15s;
        }
        .pt-run:hover {
          border-color: var(--accent);
          transform: translateY(-1px);
          box-shadow: var(--shadow-2);
        }
        .pt-run-tag {
          font-family: var(--mono); font-size: 10px; letter-spacing: .14em;
          color: var(--accent-2); font-weight: 600;
        }
        .pt-run-title {
          font-size: 14px; font-weight: 600; color: var(--ink);
          margin: 4px 0 4px;
        }
        .pt-run-desc {
          font-size: 12.5px; color: var(--ink-2); line-height: 1.5;
        }
        .pt-run-foot {
          display: flex; align-items: center; gap: 8px;
          margin-top: 10px;
          font-family: var(--mono); font-size: 10px; color: var(--muted);
          letter-spacing: .03em;
        }

        .pt-artifact {
          display: flex; align-items: flex-start; gap: 12px;
          padding: 12px; border-radius: 10px;
          border: 1px solid var(--rule);
          background: var(--bg);
          margin-bottom: 8px;
          cursor: pointer;
          transition: border-color .15s, transform .1s, box-shadow .15s;
        }
        .pt-artifact:hover {
          border-color: var(--accent);
          transform: translateY(-1px);
          box-shadow: var(--shadow-2);
        }
        .pt-artifact-ico {
          width: 32px; height: 32px; border-radius: 8px; flex-shrink: 0;
          background: var(--accent-soft); color: var(--accent-2);
          display: grid; place-items: center;
        }
        .pt-artifact-body { flex: 1; min-width: 0; }
        .pt-artifact-title { font-size: 13px; font-weight: 600; color: var(--ink); margin-bottom: 3px; }
        .pt-artifact-desc  { font-size: 11.5px; color: var(--ink-2); line-height: 1.45; }
        .pt-artifact-tag {
          margin-top: 6px;
          font-family: var(--mono); font-size: 10px; letter-spacing: .1em;
          color: var(--muted); text-transform: uppercase;
        }

        .pt-right-foot {
          border-top: 1px solid var(--rule);
          padding: 12px 14px;
          display: flex; align-items: center; gap: 10px;
          background: var(--bg-2);
        }
        .pt-right-foot .txt { font-size: 12px; color: var(--ink-2); flex: 1; }
        .pt-right-foot .txt b { color: var(--ink); font-weight: 600; }
      `}</style>

      <div className="pt-right-head">
        <I.Bolt size={16} stroke="var(--accent)"/>
        <div className="pt-right-title">Quick runs</div>
        <button className="pt-right-close" onClick={onClose} aria-label="Close panel">
          <I.Close size={15}/>
        </button>
      </div>

      <div className="pt-right-tabs">
        <button
          className={`pt-right-tab ${tab === "runs" ? "is-on" : ""}`}
          onClick={() => setTab("runs")}
        >For the talk</button>
        <button
          className={`pt-right-tab ${tab === "artifacts" ? "is-on" : ""}`}
          onClick={() => setTab("artifacts")}
        >Artifacts</button>
      </div>

      <div className="pt-right-scroll">
        {tab === "runs" && (
          hasNprr
            ? <NprrProfileCard nprr={ctx.nprr} />
            : <>
                <p className="pt-runs-note">Suggested study runs</p>
                {(SUGGESTED_RUNS || []).map(r => (
                  <div key={r.id} className="pt-run" onClick={() => onRunPrompt(r)}>
                    <div className="pt-run-tag">{r.tag}</div>
                    <div className="pt-run-title">{r.title}</div>
                    <div className="pt-run-desc">{r.desc}</div>
                    <div className="pt-run-foot"><I.Clock size={11}/>{r.est}</div>
                  </div>
                ))}
              </>
        )}

        {tab === "artifacts" && (
          <div>
            {(ARTIFACTS || []).map(a => {
              const Icon = I[a.icon] || I.Sparkle;
              return (
                <div key={a.id} className="pt-artifact" onClick={() => onRunPrompt(a)}>
                  <div className="pt-artifact-ico"><Icon size={16}/></div>
                  <div className="pt-artifact-body">
                    <div className="pt-artifact-title">{a.title}</div>
                    <div className="pt-artifact-desc">{a.desc}</div>
                    <div className="pt-artifact-tag">{a.tag}</div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      <div className="pt-right-foot">
        <I.Sparkle size={14} stroke="var(--accent)"/>
        <div className="txt">
          <b>Tip</b> — these refresh as your draft evolves.
        </div>
      </div>
    </aside>
  );
}

window.RightPanel = RightPanel;
