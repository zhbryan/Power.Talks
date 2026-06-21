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
  const [rightOpen, setRightOpen] = React.useState(tweaks.rightPanel === "open");
  React.useEffect(() => { setSidebarExpanded(tweaks.sidebar === "expanded"); }, [tweaks.sidebar]);
  React.useEffect(() => { setRightOpen(tweaks.rightPanel === "open"); }, [tweaks.rightPanel]);

  const [activeId, setActiveId] = React.useState("s1");
  const [activeMarket, setActiveMarket] = React.useState("ERCOT");
  const [activeSection, setActiveSection] = React.useState("market-home");
  const [activePaperCode, setActivePaperCode] = React.useState("NPRR");
  // Meeting Tracks navigation: tree → group homepage → item (document) homepage.
  const [activeMeetingGroup, setActiveMeetingGroup] = React.useState(null);   // committee folder
  const [activeMeetingGroupName, setActiveMeetingGroupName] = React.useState("");
  const [activeMeetingDate, setActiveMeetingDate] = React.useState(null);     // focused meeting
  const [activeMeetingDoc, setActiveMeetingDoc] = React.useState(null);       // { committee, date, file }
  const [activeNprr, setActiveNprr] = React.useState(null);
  const [activeCopmgrr, setActiveCopmgrr] = React.useState(null);
  const [activePgrr, setActivePgrr] = React.useState(null);
  const [activeScr, setActiveScr] = React.useState(null);
  const [activeNogrr, setActiveNogrr] = React.useState(null);
  const [activeRmgrr, setActiveRmgrr] = React.useState(null);
  // A submitted document selected from an issue's "Documents Submitted" list —
  // its summary renders in the content window. { ...docEntry, issueId, cat }.
  const [activeRuleDoc, setActiveRuleDoc] = React.useState(null);
  const [draft, setDraft] = React.useState("");

  React.useEffect(() => { setActiveNprr(null); }, [activeSection, activePaperCode]);
  React.useEffect(() => { setActiveCopmgrr(null); }, [activeSection, activePaperCode]);
  React.useEffect(() => { setActivePgrr(null); }, [activeSection, activePaperCode]);
  React.useEffect(() => { setActiveScr(null); }, [activeSection, activePaperCode]);
  React.useEffect(() => { setActiveNogrr(null); }, [activeSection, activePaperCode]);
  React.useEffect(() => { setActiveRmgrr(null); }, [activeSection, activePaperCode]);
  // Clear the open document summary whenever the section, category, or selected
  // issue changes (so it doesn't linger over a different issue).
  React.useEffect(() => { setActiveRuleDoc(null); }, [activeSection, activePaperCode,
    activeNprr, activeCopmgrr, activePgrr, activeScr, activeNogrr, activeRmgrr]);
  const onRuleDocClick = (doc, issueId, cat) => setActiveRuleDoc({ ...doc, issueId, cat });

  // Leaving (or re-entering) Meeting Tracks resets to the tree landing view.
  React.useEffect(() => {
    setActiveMeetingGroup(null); setActiveMeetingGroupName("");
    setActiveMeetingDate(null); setActiveMeetingDoc(null);
  }, [activeSection]);

  const onMeetingGroupClick = (committee, name) => {
    setActiveMeetingGroup(committee); setActiveMeetingGroupName(name || committee);
    setActiveMeetingDoc(null); setActiveMeetingDate(null);
    setRightOpen(true);
  };
  const onMeetingDocClick = (committee, date, file) => {
    setActiveMeetingDoc({ committee, date, file }); setActiveMeetingDate(date);
    setRightOpen(true);
  };

  const SECTION_LABELS = {
    "paper-trails":      "Paper Trails",
    "meeting-tracks":    "Meeting Tracks",
    "hot-topics":        "Hot Topics",
    "daily-headlines":   "Daily Headlines",
    "stats-illustrated": "Stats Illustrator",
    "gallery":           "Gallery",
  };
  const sectionLabel = activeSection === "market-home" ? activeMarket : (SECTION_LABELS[activeSection] || "");

  const onMarketChange = (market) => {
    setActiveMarket(market);
    setActiveSection("market-home");
  };
  let detailLabel = "";
  if (activeSection === "paper-trails") {
    const item = (window.PAPER_TRAIL_CODES || []).find(c => c.code === activePaperCode);
    detailLabel = item ? `${item.code} · ${item.name}` : activePaperCode;
  } else if (activeSection === "meeting-tracks") {
    detailLabel = activeMeetingDoc ? activeMeetingDoc.file
      : activeMeetingGroupName || "";
  }

  const onPaperCodeClick = (code) => {
    setActivePaperCode(code);
    setRightOpen(true);
  };

  const onNprrClick = (n) => {
    setActiveNprr(n);
    if (n !== null) setRightOpen(true);
  };
  const onCopmgrrClick = (n) => {
    setActiveCopmgrr(n);
    if (n !== null) setRightOpen(true);
  };
  const onPgrrClick = (n) => {
    setActivePgrr(n);
    if (n !== null) setRightOpen(true);
  };
  const onScrClick = (n) => {
    setActiveScr(n);
    if (n !== null) setRightOpen(true);
  };
  const onNogrClick = (n) => {
    setActiveNogrr(n);
    if (n !== null) setRightOpen(true);
  };
  const onRmgrClick = (n) => {
    setActiveRmgrr(n);
    if (n !== null) setRightOpen(true);
  };

  const onRunPrompt = (r) => {
    setDraft(`${r.title} — ${r.desc}`);
  };

  const [injectedPanels, setInjectedPanels] = React.useState([]);
  const scrollRef = React.useRef(null);
  const lastPanelRef = React.useRef(null);

  // Artifact pages rendered in the content window (injected iframe panels).
  const ARTIFACT_SRCS = {
    "ercot-a1": "/Power.Talks/html/ERCOT%20Major%20Milestones.html",
  };
  // Artifacts rendered as native React panels in the content window
  // (component name looked up on window at render time).
  const ARTIFACT_COMPONENTS = {
    "ercot-a2": "ErcotOrgChart",
  };

  const onArtifactClick = (a) => {
    const comp = ARTIFACT_COMPONENTS[a.id];
    if (comp) {
      setInjectedPanels(prev => prev.some(p => p.comp === comp)
        ? prev
        : [...prev, { key: Date.now(), comp, title: a.title }]);
      return;
    }
    const src = ARTIFACT_SRCS[a.id];
    if (src) {
      // Inject each artifact panel at most once per session — repeat clicks
      // produce no additional output.
      setInjectedPanels(prev => prev.some(p => p.src === src)
        ? prev
        : [...prev, { key: Date.now(), src, title: a.title }]);
    } else {
      onRunPrompt(a);
    }
  };

  React.useEffect(() => {
    if (injectedPanels.length > 0 && lastPanelRef.current) {
      lastPanelRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [injectedPanels.length]);

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
        onSectionChange={(id) => {
          if (id === "paper-trails") setActivePaperCode("NPRR");
          setActiveSection(id);
        }}
        activeId={activeId}
        onSelect={setActiveId}
        activeMarket={activeMarket}
        onMarketChange={onMarketChange}
      />

      <Topbar
        sectionLabel={sectionLabel}
        detailLabel={detailLabel}
        rightOpen={rightOpen}
        onToggleRight={() => setRightOpen(o => !o)}
        onHome={() => setActiveSection("market-home")}
      />

      <div className="pt-main-col">
        <div className="pt-main-scroll" ref={scrollRef}>
          <MessageStream
            messages={MESSAGES}
            illustration={
              activeSection === "market-home"
                ? <ERCOTHome onSectionChange={setActiveSection}/>
                : activeSection === "paper-trails"
                ? <PaperTrailsIllustration active={activePaperCode} onActiveChange={onPaperCodeClick} onNprrClick={onNprrClick} onCopmgrrClick={onCopmgrrClick} onPgrrClick={onPgrrClick} onScrClick={onScrClick} onNogrClick={onNogrClick} onRmgrClick={onRmgrClick} ruleDoc={activeRuleDoc} onRuleDocClose={() => setActiveRuleDoc(null)}/>
                : activeSection === "meeting-tracks"
                ? (activeMeetingDoc
                    ? <MeetingTracksItemHome {...activeMeetingDoc} groupName={activeMeetingGroupName} onBack={() => setActiveMeetingDoc(null)}/>
                    : activeMeetingGroup
                    ? <MeetingTracksGroupHome committee={activeMeetingGroup} groupName={activeMeetingGroupName} onBack={() => { setActiveMeetingGroup(null); setActiveMeetingDate(null); }} onDocClick={onMeetingDocClick} onMeetingFocus={setActiveMeetingDate}/>
                    : <MeetingTracksOrgChart onGroupClick={onMeetingGroupClick}/>)
                : <TalkIllustration title={CURRENT_TALK_TITLE} meta={CURRENT_TALK_META}/>
            }
          />
          {activeSection === "market-home" && injectedPanels.map((p, i) => (
            <div key={p.key} ref={i === injectedPanels.length - 1 ? lastPanelRef : null} style={{ borderTop: "1px solid var(--rule)" }}>
              {p.comp
                ? (window[p.comp] ? React.createElement(window[p.comp]) : null)
                : <iframe
                src={p.src}
                title={p.title}
                style={{ width: "100%", border: "none", display: "block" }}
                onLoad={(e) => {
                  // Fit the iframe to its full content height, and keep
                  // refitting — web fonts and late reflows change the height
                  // after load, which used to clip the bottom of tall pages.
                  const frame = e.target;
                  const fit = () => {
                    try { frame.style.height = frame.contentDocument.documentElement.scrollHeight + "px"; } catch(_) {}
                  };
                  fit();
                  try {
                    const doc = frame.contentDocument;
                    if (doc.fonts && doc.fonts.ready) doc.fonts.ready.then(fit);
                    if (frame.contentWindow.ResizeObserver) {
                      new frame.contentWindow.ResizeObserver(fit).observe(doc.documentElement);
                    }
                  } catch(_) {}
                  setTimeout(fit, 600);
                  setTimeout(fit, 2000);
                }}
              />}
            </div>
          ))}
        </div>
        <Composer
          value={draft}
          onChange={setDraft}
          onSend={onSend}
        />
      </div>

      <RightPanel
        open={rightOpen}
        onClose={() => setRightOpen(false)}
        onRunPrompt={onRunPrompt}
        onArtifactClick={onArtifactClick}
        onRuleDocClick={onRuleDocClick}
        context={{ section: activeSection, code: activePaperCode, meetingGroup: activeMeetingGroup, meetingGroupName: activeMeetingGroupName, meetingDate: activeMeetingDate, meetingDoc: activeMeetingDoc, nprr: activeNprr, copmgrr: activeCopmgrr, pgrr: activePgrr, scr: activeScr, nogrr: activeNogrr, rmgrr: activeRmgrr }}
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
