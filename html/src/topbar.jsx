function Topbar({ sectionLabel, detailLabel, onToggleRight, rightOpen, onHome }) {
  const [menuOpen, setMenuOpen] = React.useState(false);
  const items = ["Home", "Pricing", "Account", "Contact"];
  const [active, setActive] = React.useState("Home");
  return (
    <header className="pt-top">
      <style>{`
        .pt-top {
          grid-area: top;
          height: 52px;
          border-bottom: 1px solid var(--rule);
          background: var(--bg);
          display: flex; align-items: center;
          padding: 0 18px; gap: 14px;
          position: relative; z-index: 5;
        }
        .pt-top-title {
          display: flex; align-items: center; gap: 8px;
          font-size: 13.5px; color: var(--ink); font-weight: 500;
          min-width: 0;
        }
        .pt-top-title .crumb { color: var(--muted); font-weight: 400; }
        .pt-top-title .sep  { color: var(--rule-2); }
        .pt-top-title .name {
          overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 360px;
        }
        .pt-top-chip {
          font-size: 11px; font-family: var(--mono); color: var(--muted);
          padding: 3px 7px; border: 1px solid var(--rule-2); border-radius: 999px;
        }

        .pt-nav { margin-left: auto; display: flex; align-items: center; gap: 2px; }
        .pt-nav-item {
          padding: 6px 12px; border-radius: 8px; font-size: 13px;
          color: var(--ink-2); position: relative;
        }
        .pt-nav-item:hover { color: var(--ink); background: var(--bg-2); }
        .pt-nav-item.is-active { color: var(--ink); }
        .pt-nav-item.is-active::after {
          content: ""; position: absolute; left: 12px; right: 12px; bottom: -14px;
          height: 2px; background: var(--accent); border-radius: 2px;
        }

        .pt-top-actions { display: flex; align-items: center; gap: 4px; margin-left: 8px; }
        .pt-iconbtn {
          width: 32px; height: 32px; border-radius: 8px;
          display: grid; place-items: center;
          color: var(--ink-2);
        }
        .pt-iconbtn:hover { background: var(--bg-2); color: var(--ink); }
        .pt-iconbtn.is-on { background: var(--ink); color: var(--bg); }
        .pt-iconbtn.is-on:hover { background: var(--ink); }

        .pt-share {
          padding: 6px 12px; border-radius: 8px; font-size: 13px; font-weight: 500;
          border: 1px solid var(--rule-2); color: var(--ink);
          display: inline-flex; align-items: center; gap: 6px;
        }
        .pt-share:hover { border-color: var(--ink); }

        @media (max-width: 1020px) {
          .pt-nav { display: none; }
        }
      `}</style>

      <div className="pt-top-title">
        <span className="crumb">{sectionLabel}</span>
        {detailLabel && <>
          <span className="sep">/</span>
          <span className="name">{detailLabel}</span>
        </>}
      </div>

      <nav className="pt-nav">
        {items.map(it => (
          <a key={it} href="#"
            className={`pt-nav-item ${active === it ? "is-active" : ""}`}
            onClick={(e) => { e.preventDefault(); setActive(it); if (it === "Home" && onHome) onHome(); }}
          >{it}</a>
        ))}
      </nav>

      <div className="pt-top-actions">
        <button className="pt-iconbtn" title="Search" aria-label="Search"><I.Search size={16}/></button>
        <button className="pt-share" title="Share">
          <I.Share size={14}/> Share
        </button>
        <button
          className={`pt-iconbtn ${rightOpen ? "is-on" : ""}`}
          onClick={onToggleRight}
          title={rightOpen ? "Close runs panel" : "Open runs panel"}
          aria-label="Toggle runs panel"
        >
          <I.Sparkle size={16}/>
        </button>
      </div>
    </header>
  );
}

window.Topbar = Topbar;
