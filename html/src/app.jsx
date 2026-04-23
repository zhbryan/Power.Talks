function App() {
  const initialTweaks = window.POWER_TALKS_TWEAKS || {};
  const [tweaks, setTweaks] = React.useState({
    theme: "light", accent: "terracotta",
    sidebar: "expanded", rightPanel: "open", typePair: "tight-serif",
    ...initialTweaks,
  });
  const [tweaksVisible, setTweaksVisible] = React.useState(false);

  const setTweak = (k, v) => {
    setTweaks(prev => {
      const next = { ...prev, [k]: v };
      try {
        window.parent.postMessage({ type: "__edit_mode_set_keys", edits: { [k]: v } }, "*");
      } catch (e) {}
      return next;
    });
  };

  React.useEffect(() => { window.applyTweaksToRoot(tweaks); }, [tweaks]);

  // Edit-mode wiring: register listener FIRST, then announce availability
  React.useEffect(() => {
    const onMsg = (e) => {
      const d = e.data;
      if (!d || typeof d !== "object") return;
      if (d.type === "__activate_edit_mode")   setTweaksVisible(true);
      if (d.type === "__deactivate_edit_mode") setTweaksVisible(false);
    };
    window.addEventListener("message", onMsg);
    try { window.parent.postMessage({ type: "__edit_mode_available" }, "*"); } catch (e) {}
    return () => window.removeEventListener("message", onMsg);
  }, []);

  // App state
  const [sidebarExpanded, setSidebarExpanded] = React.useState(tweaks.sidebar === "expanded");
  const [rightOpen, setRightOpen] = React.useState(false);
  React.useEffect(() => { setSidebarExpanded(tweaks.sidebar === "expanded"); }, [tweaks.sidebar]);
  React.useEffect(() => { setRightOpen(tweaks.rightPanel === "open"); }, [tweaks.rightPanel]);

  const [activeId, setActiveId] = React.useState("s1");
  const [activeSection, setActiveSection] = React.useState("paper-trails");
  const [activePaperCode, setActivePaperCode] = React.useState("NPRR");
  const [activeMeetingNode, setActiveMeetingNode] = React.useState("TAC");
  const [activeNprr, setActiveNprr] = React.useState(null);
  const [draft, setDraft] = React.useState("");

  React.useEffect(() => { setActiveNprr(null); }, [activeSection, activePaperCode]);

  const SECTION_LABELS = {
    "paper-trails":      "Paper Trails",
    "meeting-tracks":    "Meeting Tracks",
    "hot-topics":        "Hot Topics",
    "daily-headlines":   "Daily Headlines",
    "stats-illustrated": "Stats Illustrated",
    "gallery":           "Gallery",
  };
  const sectionLabel = SECTION_LABELS[activeSection] || "";
  let detailLabel = "";
  if (activeSection === "paper-trails") {
    const item = (window.PAPER_TRAIL_CODES || []).find(c => c.code === activePaperCode);
    detailLabel = item ? `${item.code} · ${item.name}` : activePaperCode;
  } else if (activeSection === "meeting-tracks") {
    detailLabel = activeMeetingNode;
  }

  const onPaperCodeClick = (code) => {
    setActivePaperCode(code);
    setRightOpen(true);
  };

  const onNprrClick = (n) => {
    setActiveNprr(n);
    if (n !== null) setRightOpen(true);
  };
  const onMeetingNodeClick = (id) => {
    setActiveMeetingNode(id);
    setRightOpen(true);
  };

  const onRunPrompt = (r) => {
    setDraft(`${r.title} — ${r.desc}`);
  };

  const onSend = () => {
    if (!draft.trim()) return;
    // demo: clear; in a real app, append to messages
    setDraft("");
  };

  const { CURRENT_TALK_TITLE, CURRENT_TALK_META, MESSAGES } = window.DATA;

  return (
    <div className={`pt-app ${rightOpen ? "right-open" : ""} ${sidebarExpanded ? "side-exp" : "side-col"}`}>
      <style>{`
        .pt-app {
          height: 100vh;
          display: grid;
          grid-template-columns: auto 1fr auto;
          grid-template-rows: 52px 1fr;
          grid-template-areas:
            "side top   top"
            "side main  right";
          background: var(--bg);
          color: var(--ink);
        }
        .pt-main-col {
          grid-area: main;
          min-width: 0;
          display: flex; flex-direction: column;
          overflow: hidden;
          position: relative;
        }
        .pt-main-scroll {
          flex: 1;
          overflow-y: auto;
          scroll-behavior: smooth;
        }
        /* Mobile fallback — right panel overlays */
        @media (max-width: 1100px) {
          .pt-app {
            grid-template-columns: auto 1fr;
            grid-template-areas:
              "side top"
              "side main";
          }
          .pt-right {
            position: fixed; right: 0; top: 52px; bottom: 0;
            z-index: 20; box-shadow: var(--shadow-2);
          }
        }
      `}</style>

      <Sidebar
        expanded={sidebarExpanded}
        onToggle={() => setSidebarExpanded(e => !e)}
        activeSection={activeSection}
        onSectionChange={setActiveSection}
        activeId={activeId}
        onSelect={setActiveId}
        onNew={() => setDraft("")}
      />

      <Topbar
        sectionLabel={sectionLabel}
        detailLabel={detailLabel}
        rightOpen={rightOpen}
        onToggleRight={() => setRightOpen(o => !o)}
      />

      <div className="pt-main-col">
        <div className="pt-main-scroll">
          <MessageStream
            messages={MESSAGES}
            illustration={
              activeSection === "paper-trails"
                ? <PaperTrailsIllustration active={activePaperCode} onActiveChange={onPaperCodeClick} onNprrClick={onNprrClick}/>
                : activeSection === "meeting-tracks"
                ? <MeetingTracksOrgChart selected={activeMeetingNode} onSelect={onMeetingNodeClick}/>
                : <TalkIllustration title={CURRENT_TALK_TITLE} meta={CURRENT_TALK_META}/>
            }
          />
        </div>
        <Composer
          value={draft}
          onChange={setDraft}
          onSend={onSend}
          onSuggest={() => setRightOpen(true)}
        />
      </div>

      <RightPanel
        open={rightOpen}
        onClose={() => setRightOpen(false)}
        onRunPrompt={onRunPrompt}
        context={{ section: activeSection, code: activePaperCode, node: activeMeetingNode, nprr: activeNprr }}
      />

      <TweaksPanel
        tweaks={tweaks}
        setTweak={setTweak}
        visible={tweaksVisible}
      />
    </div>
  );
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<App/>);
