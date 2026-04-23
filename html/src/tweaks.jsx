function TweaksPanel({ tweaks, setTweak, visible }) {
  if (!visible) return null;
  const accents = [
    { id: "terracotta", color: "#C8623E", color2: "#B0522F", soft: "#F3E3D8" },
    { id: "indigo",     color: "#4A5BD6", color2: "#3C4BB8", soft: "#E0E3F7" },
    { id: "forest",     color: "#4E7A4A", color2: "#3F6A3B", soft: "#DDE9D8" },
    { id: "amber",      color: "#A3741B", color2: "#8D6014", soft: "#F4E6C5" },
    { id: "rose",       color: "#B84568", color2: "#9F3856", soft: "#F4D9E2" },
  ];
  return (
    <div className="pt-tweaks">
      <style>{`
        .pt-tweaks {
          position: fixed; bottom: 18px; right: 18px; z-index: 50;
          width: 300px;
          background: var(--panel);
          border: 1px solid var(--rule-2);
          border-radius: 14px;
          box-shadow: 0 20px 40px -16px rgba(0,0,0,.3), 0 4px 12px rgba(0,0,0,.08);
          padding: 14px;
          font-size: 12.5px;
        }
        .pt-tweaks h4 {
          margin: 0 0 10px;
          font-family: var(--serif); font-size: 17px; font-weight: 500;
          color: var(--ink);
        }
        .pt-tweaks .row { display: flex; align-items: center; justify-content: space-between; margin: 8px 0; gap: 10px; }
        .pt-tweaks .row > span { color: var(--ink-2); font-size: 12.5px; }
        .pt-seg {
          display: inline-flex; padding: 2px; gap: 2px;
          background: var(--bg-2); border-radius: 8px;
        }
        .pt-seg button {
          padding: 4px 10px; font-size: 11.5px; border-radius: 6px;
          color: var(--ink-2);
        }
        .pt-seg button.on { background: var(--panel); color: var(--ink); box-shadow: var(--shadow-1); }
        .pt-accents { display: flex; gap: 6px; }
        .pt-accents button {
          width: 22px; height: 22px; border-radius: 999px;
          border: 2px solid transparent;
          transition: transform .1s;
        }
        .pt-accents button:hover { transform: scale(1.1); }
        .pt-accents button.on { border-color: var(--ink); }
      `}</style>
      <h4>Tweaks</h4>

      <div className="row">
        <span>Theme</span>
        <div className="pt-seg">
          <button className={tweaks.theme === "light" ? "on" : ""} onClick={() => setTweak("theme", "light")}>Light</button>
          <button className={tweaks.theme === "dark"  ? "on" : ""} onClick={() => setTweak("theme", "dark")}>Dark</button>
        </div>
      </div>

      <div className="row">
        <span>Accent</span>
        <div className="pt-accents">
          {accents.map(a => (
            <button key={a.id}
              className={tweaks.accent === a.id ? "on" : ""}
              style={{ background: a.color }}
              onClick={() => setTweak("accent", a.id)}
              title={a.id}
            />
          ))}
        </div>
      </div>

      <div className="row">
        <span>Sidebar</span>
        <div className="pt-seg">
          <button className={tweaks.sidebar === "expanded"  ? "on" : ""} onClick={() => setTweak("sidebar", "expanded")}>Expanded</button>
          <button className={tweaks.sidebar === "collapsed" ? "on" : ""} onClick={() => setTweak("sidebar", "collapsed")}>Rail</button>
        </div>
      </div>

      <div className="row">
        <span>Runs panel</span>
        <div className="pt-seg">
          <button className={tweaks.rightPanel === "open"   ? "on" : ""} onClick={() => setTweak("rightPanel", "open")}>Open</button>
          <button className={tweaks.rightPanel === "closed" ? "on" : ""} onClick={() => setTweak("rightPanel", "closed")}>Closed</button>
        </div>
      </div>

      <div className="row">
        <span>Type pairing</span>
        <div className="pt-seg">
          <button className={tweaks.typePair === "tight-serif" ? "on" : ""} onClick={() => setTweak("typePair", "tight-serif")}>Serif+Tight</button>
          <button className={tweaks.typePair === "sans-only"   ? "on" : ""} onClick={() => setTweak("typePair", "sans-only")}>All sans</button>
        </div>
      </div>
    </div>
  );
}

const ACCENTS = {
  terracotta: { a: "#C8623E", b: "#B0522F", soft: "#F3E3D8", aDark: "#E17A52", softDark: "#2A1E17" },
  indigo:     { a: "#4A5BD6", b: "#3C4BB8", soft: "#E0E3F7", aDark: "#7A88E8", softDark: "#1A1D33" },
  forest:     { a: "#4E7A4A", b: "#3F6A3B", soft: "#DDE9D8", aDark: "#6E9A68", softDark: "#1B2A1A" },
  amber:      { a: "#A3741B", b: "#8D6014", soft: "#F4E6C5", aDark: "#C99535", softDark: "#2C2110" },
  rose:       { a: "#B84568", b: "#9F3856", soft: "#F4D9E2", aDark: "#D46A8A", softDark: "#2E1820" },
};

function applyTweaksToRoot(tweaks) {
  const root = document.documentElement;
  root.dataset.theme = tweaks.theme;
  const isDark = tweaks.theme === "dark";
  const a = ACCENTS[tweaks.accent] || ACCENTS.terracotta;
  root.style.setProperty("--accent",      isDark ? a.aDark : a.a);
  root.style.setProperty("--accent-2",    a.b);
  root.style.setProperty("--accent-soft", isDark ? a.softDark : a.soft);
  if (tweaks.typePair === "sans-only") {
    root.style.setProperty("--serif", "'Inter Tight', ui-sans-serif, system-ui, sans-serif");
  } else {
    root.style.setProperty("--serif", "'Instrument Serif', Georgia, serif");
  }
}

window.TweaksPanel = TweaksPanel;
window.applyTweaksToRoot = applyTweaksToRoot;
