function Sidebar({ expanded, onToggle, activeSection, onSectionChange, activeId, onSelect, activeMarket, onMarketChange }) {
  const { RECENT_SESSIONS } = window.DATA;
  const ISO_MARKETS = ["ERCOT","NYISO","MISO","NEISO","PJM","CAISO","SPP"];
  const [marketOpen, setMarketOpen] = React.useState(false);

  React.useEffect(() => {
    if (!marketOpen) return;
    const close = () => setMarketOpen(false);
    document.addEventListener("click", close);
    return () => document.removeEventListener("click", close);
  }, [marketOpen]);
  const SECTIONS = [
    { id: "market-home",      label: "Home",             icon: "Home"  },
    { id: "paper-trails",     label: "Paper Trails",     icon: "Book" },
    { id: "meeting-tracks",   label: "Meeting Tracks",   icon: "Waveform" },
    { id: "hot-topics",       label: "Hot Topics",       icon: "Flame" },
    { id: "daily-headlines",  label: "Daily Headlines",  icon: "Lightning" },
    { id: "stats-illustrated",label: "Stats Illustrated",icon: "Chart" },
    { id: "gallery",          label: "Gallery",          icon: "Folder" },
  ];
  return (
    <aside className={`pt-side ${expanded ? "is-expanded" : "is-collapsed"}`}>
      <style>{`
        .pt-side {
          grid-area: side;
          background: var(--bg-2);
          border-right: 1px solid var(--rule);
          display: flex; flex-direction: column;
          min-width: 0;
          transition: width .22s ease;
        }
        .pt-side.is-expanded { width: 260px; }
        .pt-side.is-collapsed { width: 56px; }
        .pt-side-top {
          padding: 12px 14px 8px;
          display: flex; align-items: center; gap: 10px;
          height: 52px;
        }
        .pt-brand {
          display: flex; align-items: center; gap: 10px;
          font-family: var(--serif); font-size: 19px; letter-spacing: -.01em;
          color: var(--ink); text-decoration: none;
        }
        .pt-brand b { font-weight: 500; }
        .pt-brand i { color: var(--accent); font-style: normal; }
        .pt-side.is-collapsed .pt-brand span,
        .pt-side.is-collapsed .pt-side-label,
        .pt-side.is-collapsed .pt-side-item span,
        .pt-side.is-collapsed .pt-side-row span,
        .pt-side.is-collapsed .pt-side-foot-name { display: none; }
        .pt-side-collapse {
          margin-left: auto; padding: 6px; border-radius: 8px;
          color: var(--muted);
        }
        .pt-side-collapse:hover { background: var(--rule); color: var(--ink); }
        .pt-side.is-collapsed .pt-side-collapse { margin-left: 0; }

        .pt-iso-wrap {
          position: relative; margin: 2px 10px 10px;
        }
        .pt-iso-btn {
          width: 100%; padding: 10px 12px;
          border: 1px solid var(--rule-2); border-radius: 10px;
          display: flex; align-items: center; gap: 9px;
          background: var(--panel); color: var(--ink);
          font-weight: 600; font-size: 13px; font-family: var(--mono);
          box-shadow: var(--shadow-1);
          transition: border-color .15s;
          cursor: pointer;
        }
        .pt-iso-btn:hover { border-color: var(--accent); color: var(--accent); }
        .pt-iso-btn.is-open { border-color: var(--accent); }
        .pt-iso-btn .chev { margin-left: auto; color: var(--muted); transition: transform .18s; }
        .pt-iso-btn.is-open .chev { transform: rotate(180deg); }
        .pt-side.is-collapsed .pt-iso-btn {
          padding: 10px; justify-content: center;
        }
        .pt-side.is-collapsed .pt-iso-btn .iso-label,
        .pt-side.is-collapsed .pt-iso-btn .chev { display: none; }
        .pt-iso-dropdown {
          position: absolute; top: calc(100% + 5px); left: 0; right: 0; z-index: 100;
          background: var(--panel); border: 1px solid var(--rule-2);
          border-radius: 10px; box-shadow: var(--shadow-2);
          overflow: hidden;
        }
        .pt-iso-opt {
          width: 100%; padding: 9px 14px;
          display: flex; align-items: center; gap: 10px;
          font-family: var(--mono); font-size: 12.5px; font-weight: 600;
          color: var(--ink-2); background: transparent; cursor: pointer;
          transition: background .1s, color .1s;
          text-align: left;
        }
        .pt-iso-opt:hover { background: var(--rule); color: var(--ink); }
        .pt-iso-opt.is-on { color: var(--accent); }
        .pt-iso-opt .dot {
          width: 6px; height: 6px; border-radius: 50%;
          background: var(--accent); flex: 0 0 auto;
        }
        .pt-iso-opt .dot-gap { width: 6px; flex: 0 0 auto; }

        .pt-side-search {
          margin: 0 10px 10px;
          display: flex; align-items: center; gap: 8px;
          padding: 8px 10px; border-radius: 10px;
          background: transparent; border: 1px solid transparent;
          color: var(--muted); font-size: 13px;
          cursor: text;
        }
        .pt-side-search:hover { background: var(--rule); color: var(--ink-2); }
        .pt-side.is-collapsed .pt-side-search { justify-content: center; }

        .pt-side-scroll { flex: 1; overflow-y: auto; padding: 4px 6px 12px; }

        .pt-side-label {
          padding: 14px 12px 6px; font-size: 11px;
          color: var(--muted); letter-spacing: .08em; text-transform: uppercase;
          font-weight: 500;
        }
        .pt-side-item {
          display: flex; align-items: center; gap: 10px;
          padding: 8px 10px; margin: 0 4px 1px; border-radius: 8px;
          color: var(--ink-2); font-size: 13.5px;
          cursor: pointer; position: relative;
          white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
          transition: background .12s;
        }
        .pt-side.is-collapsed .pt-side-item { justify-content: center; padding: 10px; }
        .pt-side-item:hover { background: var(--rule); }
        .pt-side-item.is-active {
          background: var(--panel);
          color: var(--ink);
          box-shadow: var(--shadow-1);
        }
        .pt-side-item.is-active::before {
          content: ""; position: absolute; left: 0; top: 8px; bottom: 8px; width: 2px;
          background: var(--accent); border-radius: 2px;
        }
        .pt-side-time {
          margin-left: auto; color: var(--muted); font-size: 11px;
          font-family: var(--mono);
        }
        .pt-side.is-collapsed .pt-side-time { display: none; }

        .pt-side-row {
          display: flex; align-items: center; gap: 10px;
          padding: 7px 10px; margin: 0 4px 1px; border-radius: 8px;
          color: var(--ink-2); font-size: 13.5px; cursor: pointer;
        }
        .pt-side-row:hover { background: var(--rule); color: var(--ink); }
        .pt-side-dot { width: 8px; height: 8px; border-radius: 2px; flex: 0 0 auto; }

        .pt-side-foot {
          border-top: 1px solid var(--rule);
          padding: 10px;
          display: flex; align-items: center; gap: 10px;
        }
        .pt-avatar {
          width: 30px; height: 30px; border-radius: 999px; flex: 0 0 auto;
          background: conic-gradient(from 140deg, #c8623e, #b0522f, #a3741b, #4e7a4a, #c8623e);
          box-shadow: inset 0 0 0 2px var(--panel), 0 0 0 1px var(--rule-2);
        }
        .pt-side-foot-name { flex: 1; min-width: 0; }
        .pt-side-foot-name b { display:block; font-weight: 500; font-size: 13px; color: var(--ink); }
        .pt-side-foot-name span { color: var(--muted); font-size: 11.5px; }
        .pt-side.is-collapsed .pt-side-foot { justify-content: center; padding: 10px 8px; }

        .pt-pro-chip {
          font-size: 10px; font-family: var(--mono); padding: 2px 6px;
          border-radius: 4px; background: var(--accent-soft); color: var(--accent-2);
        }
      `}</style>

      <div className="pt-side-top">
        <a className="pt-brand" href="#" onClick={(e)=>{ e.preventDefault(); onSectionChange("market-home"); }}>
          <I.Logo size={26}/>
          <span><b>Power</b><i>.</i>Talks</span>
        </a>
        <button className="pt-side-collapse" onClick={onToggle} aria-label="Collapse sidebar">
          {expanded ? <I.ChevL size={16}/> : <I.ChevR size={16}/>}
        </button>
      </div>

      {/* ISO market dropdown */}
      <div className="pt-iso-wrap" onClick={e => e.stopPropagation()}>
        <button
          className={`pt-iso-btn ${marketOpen ? "is-open" : ""}`}
          onClick={() => setMarketOpen(o => !o)}
          title={activeMarket}
        >
          <I.Globe size={15}/>
          <span className="iso-label">{activeMarket}</span>
          <I.ChevD size={13} className="chev"/>
        </button>
        {marketOpen && (
          <div className="pt-iso-dropdown">
            {ISO_MARKETS.map(m => (
              <button
                key={m}
                className={`pt-iso-opt ${activeMarket === m ? "is-on" : ""}`}
                onClick={() => { onMarketChange(m); setMarketOpen(false); }}
              >
                {activeMarket === m ? <span className="dot"/> : <span className="dot-gap"/>}
                {m}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="pt-side-search">
        <I.Search size={15}/>
        <span>Search talks…</span>
      </div>

      <div className="pt-side-scroll">
        <div className="pt-side-label">Sections</div>
        {SECTIONS.map(s => {
          const Ico = I[s.icon];
          return (
            <div
              key={s.id}
              className={`pt-side-item ${s.id === activeSection ? "is-active" : ""}`}
              onClick={() => onSectionChange(s.id)}
              title={s.label}
            >
              <Ico size={15}/>
              <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis" }}>{s.label}</span>
            </div>
          );
        })}

        <div className="pt-side-label">Recents</div>
        {RECENT_SESSIONS.length === 0 ? (
          <div style={{
            padding: "6px 12px", margin: "0 4px",
            color: "var(--muted)", fontSize: 12, fontStyle: "italic"
          }}>No recent items</div>
        ) : RECENT_SESSIONS.slice(0, 5).map(s => (
          <div
            key={s.id}
            className={`pt-side-row`}
            onClick={() => onSelect(s.id)}
            title={s.title}
          >
            <I.Clock size={14}/>
            <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{s.title}</span>
            <span className="pt-side-time">{s.time}</span>
          </div>
        ))}
      </div>

      <div className="pt-side-foot">
        <div className="pt-avatar" aria-hidden/>
        <div className="pt-side-foot-name">
          <b>Maya Okafor</b>
          <span>Pro plan</span>
        </div>
        <span className="pt-pro-chip">PRO</span>
      </div>
    </aside>
  );
}

window.Sidebar = Sidebar;
