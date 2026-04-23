// ERCOT stakeholder meeting process — a simplified, navigable org chart
// Root: Board of Directors → TAC → 4 standing subcommittees → their WGs/TFs
const ERCOT_ORG = {
  id: "BOD",
  name: "ERCOT Board of Directors",
  tag: "Board",
  children: [
    {
      id: "TAC",
      name: "Technical Advisory Committee",
      tag: "TAC",
      children: [
        {
          id: "ROS",
          name: "Reliability & Operations Subcommittee",
          tag: "ROS",
          children: [
            { id: "OWG", name: "Operations Working Group",            tag: "OWG" },
            { id: "PDCWG", name: "Performance, Disturbance & Compliance WG", tag: "PDCWG" },
            { id: "DWG", name: "Dynamics Working Group",              tag: "DWG" },
            { id: "NDSWG", name: "Network Data Support WG",           tag: "NDSWG" },
            { id: "SAWG", name: "System Protection WG",               tag: "SAWG" },
          ],
        },
        {
          id: "WMS",
          name: "Wholesale Market Subcommittee",
          tag: "WMS",
          children: [
            { id: "CMWG",  name: "Congestion Management WG",          tag: "CMWG"  },
            { id: "QMWG",  name: "Qualification Methodology WG",      tag: "QMWG"  },
            { id: "MCWG",  name: "Market Credit WG",                  tag: "MCWG"  },
            { id: "DSWG",  name: "Demand Side WG",                    tag: "DSWG"  },
            { id: "SAWG2", name: "Supply Analysis WG",                tag: "SAWG"  },
          ],
        },
        {
          id: "RMS",
          name: "Retail Market Subcommittee",
          tag: "RMS",
          children: [
            { id: "COPS",  name: "Commercial Operations Subcommittee",tag: "COPS"  },
            { id: "RMPTF", name: "Retail Market Processes TF",        tag: "RMPTF" },
            { id: "TDTWG", name: "Texas Data Transport WG",           tag: "TDTWG" },
            { id: "RCWG",  name: "Retail Customer WG",                tag: "RCWG"  },
          ],
        },
        {
          id: "PLWG",
          name: "Protocol Revision Subcommittee",
          tag: "PRS",
          children: [
            { id: "LFSTF", name: "Load Forecasting Stakeholder TF",   tag: "LFSTF" },
            { id: "SMTF",  name: "Settlement Metering TF",            tag: "SMTF"  },
            { id: "PIPTF", name: "Planning Interim Process TF",       tag: "PIPTF" },
          ],
        },
      ],
    },
  ],
};

const MEETINGS_BY_NODE = {
  BOD:   [{ when: "Apr 22, 2026", kind: "Open session" }, { when: "May 20, 2026", kind: "Open session" }],
  TAC:   [{ when: "Apr 30, 2026", kind: "Regular" }, { when: "May 28, 2026", kind: "Regular" }],
  ROS:   [{ when: "Apr 08, 2026", kind: "Monthly" }, { when: "May 13, 2026", kind: "Monthly" }],
  WMS:   [{ when: "Apr 09, 2026", kind: "Monthly" }, { when: "May 14, 2026", kind: "Monthly" }],
  RMS:   [{ when: "Apr 15, 2026", kind: "Monthly" }, { when: "May 20, 2026", kind: "Monthly" }],
  PLWG:  [{ when: "Apr 10, 2026", kind: "Bi-weekly" }, { when: "Apr 24, 2026", kind: "Bi-weekly" }],
};

function MeetingTracksOrgChart({ selected, onSelect }) {
  const [expanded, setExpanded] = React.useState({ TAC: true });
  const toggle = (id) => setExpanded(e => ({ ...e, [id]: !e[id] }));

  const selectedNode = React.useMemo(() => {
    const findNode = (n, id) => {
      if (n.id === id) return n;
      for (const c of n.children || []) { const f = findNode(c, id); if (f) return f; }
      return null;
    };
    return findNode(ERCOT_ORG, selected) || ERCOT_ORG.children[0]; // default TAC
  }, [selected]);

  const meetings = MEETINGS_BY_NODE[selectedNode.id] || [
    { when: "Apr 16, 2026", kind: "Standing" },
    { when: "May 21, 2026", kind: "Standing" },
  ];

  const renderNode = (node, depth = 0) => {
    const isOpen = expanded[node.id];
    const hasKids = (node.children || []).length > 0;
    const isSel = node.id === selectedNode.id;
    return (
      <div key={node.id} className="mt-row-wrap">
        <div
          className={`mt-node depth-${depth} ${isSel ? "is-sel" : ""}`}
          onClick={() => onSelect(node.id)}
        >
          {hasKids ? (
            <button className="mt-chev" onClick={(e) => { e.stopPropagation(); toggle(node.id); }}
              aria-label={isOpen ? "Collapse" : "Expand"}>
              <svg width="10" height="10" viewBox="0 0 24 24" style={{ transform: isOpen ? "rotate(90deg)" : "none", transition: "transform .15s" }}>
                <path d="m9 6 6 6-6 6" stroke="currentColor" strokeWidth="2.2" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </button>
          ) : <span className="mt-chev-spacer"/>}
          <span className="mt-tag">{node.tag}</span>
          <span className="mt-name">{node.name}</span>
          {hasKids && <span className="mt-count">{node.children.length}</span>}
        </div>
        {isOpen && hasKids && (
          <div className="mt-children">
            {node.children.map(c => renderNode(c, depth + 1))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="pt-orgchart">
      <style>{`
        .pt-orgchart {
          border: 1px solid var(--rule);
          background:
            radial-gradient(120% 80% at 0% 0%, var(--accent-soft) 0%, transparent 55%),
            linear-gradient(180deg, var(--panel), var(--bg-2));
          border-radius: var(--radius);
          padding: 22px;
          box-shadow: var(--shadow-1);
          display: grid;
          grid-template-columns: 1.3fr 1fr;
          gap: 22px;
          position: relative; overflow: hidden;
        }
        @media (max-width: 820px) {
          .pt-orgchart { grid-template-columns: 1fr; }
        }
        .pt-orgchart::before {
          content: ""; position: absolute; inset: 0;
          background-image: repeating-linear-gradient(90deg, rgba(27,26,23,.03) 0 1px, transparent 1px 28px);
          pointer-events: none;
        }
        .mt-head-eye {
          font-family: var(--mono); font-size: 10.5px; letter-spacing: .14em;
          color: var(--muted); text-transform: uppercase;
        }
        .mt-head-title {
          font-family: var(--serif); font-size: 26px; line-height: 1.1;
          margin: 2px 0 6px; font-weight: 400; color: var(--ink);
        }
        .mt-head-sub { color: var(--ink-2); font-size: 13px; margin-bottom: 14px; }

        .mt-tree { position: relative; font-size: 13px; }
        .mt-row-wrap { position: relative; }
        .mt-children {
          position: relative;
          padding-left: 14px;
          margin-left: 12px;
          border-left: 1px dashed var(--rule-2);
        }
        .mt-node {
          display: flex; align-items: center; gap: 8px;
          padding: 7px 10px; margin: 2px 0;
          border-radius: 8px;
          color: var(--ink-2);
          cursor: pointer;
          transition: background .12s, color .12s;
        }
        .mt-node:hover { background: var(--bg-2); color: var(--ink); }
        .mt-node.is-sel {
          background: var(--ink); color: var(--bg);
        }
        .mt-node.is-sel .mt-tag {
          background: color-mix(in oklab, var(--bg), transparent 80%);
          color: var(--bg);
        }
        .mt-node.depth-0 .mt-tag { background: var(--accent); color: #fff; }
        .mt-node.depth-1 .mt-tag { background: var(--accent-soft); color: var(--accent-2); }
        .mt-chev {
          width: 18px; height: 18px; border-radius: 4px;
          display: grid; place-items: center; color: inherit;
          background: transparent;
        }
        .mt-chev:hover { background: color-mix(in oklab, currentColor, transparent 85%); }
        .mt-chev-spacer { width: 18px; height: 18px; display: inline-block; }
        .mt-tag {
          font-family: var(--mono); font-size: 10.5px; font-weight: 600;
          padding: 2px 6px; border-radius: 4px;
          background: var(--bg-2); color: var(--ink-2);
          letter-spacing: .02em;
          flex: 0 0 auto;
        }
        .mt-name { flex: 1; font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .mt-count {
          font-family: var(--mono); font-size: 10.5px;
          color: var(--muted);
          padding: 0 6px; border-radius: 999px;
          border: 1px solid var(--rule-2);
        }
        .mt-node.is-sel .mt-count { color: var(--bg); border-color: color-mix(in oklab, var(--bg), transparent 70%); }

        .mt-detail {
          position: relative;
          border-left: 1px dashed var(--rule-2);
          padding-left: 22px;
        }
        @media (max-width: 820px) {
          .mt-detail { border-left: 0; padding-left: 0; border-top: 1px dashed var(--rule-2); padding-top: 16px; }
        }
        .mt-detail-tag {
          display: inline-block;
          font-family: var(--mono); font-size: 11px; font-weight: 600;
          padding: 3px 8px; border-radius: 6px;
          background: var(--accent-soft); color: var(--accent-2);
        }
        .mt-detail-name {
          font-family: var(--serif); font-size: 22px; font-weight: 400;
          color: var(--ink); margin: 8px 0 6px; line-height: 1.2;
        }
        .mt-detail-sub { font-size: 12.5px; color: var(--muted); margin-bottom: 14px; }
        .mt-detail-section {
          font-family: var(--mono); font-size: 10.5px; letter-spacing: .12em;
          color: var(--muted); text-transform: uppercase;
          margin: 12px 0 6px;
        }
        .mt-meet {
          display: flex; align-items: center; gap: 10px;
          padding: 10px 12px; margin-bottom: 6px;
          border: 1px solid var(--rule);
          border-radius: 10px;
          background: var(--bg);
          font-size: 13px;
        }
        .mt-meet b { color: var(--ink); font-weight: 500; }
        .mt-meet .kind {
          font-family: var(--mono); font-size: 10.5px;
          padding: 2px 7px; border-radius: 4px;
          background: var(--bg-2); color: var(--ink-2);
          margin-left: auto;
        }
        .mt-actions { display: flex; gap: 8px; margin-top: 12px; flex-wrap: wrap; }
        .mt-actions button {
          padding: 7px 12px; border-radius: 8px;
          font-size: 12.5px; font-weight: 500;
          border: 1px solid var(--rule-2); color: var(--ink);
          display: inline-flex; align-items: center; gap: 6px;
        }
        .mt-actions button.primary { background: var(--ink); color: var(--bg); border-color: var(--ink); }
        .mt-actions button.primary:hover { background: var(--accent); border-color: var(--accent); }
        .mt-actions button:hover { border-color: var(--ink); }
      `}</style>

      <div>
        <div className="mt-head-eye">Meeting Tracks</div>
        <h2 className="mt-head-title">ERCOT stakeholder process</h2>
        <div className="mt-head-sub">Click any node to inspect its upcoming meetings.</div>
        <div className="mt-tree">
          {renderNode(ERCOT_ORG)}
        </div>
      </div>

      <div className="mt-detail">
        <span className="mt-detail-tag">{selectedNode.tag}</span>
        <div className="mt-detail-name">{selectedNode.name}</div>
        <div className="mt-detail-sub">
          {(selectedNode.children || []).length} subgroup{(selectedNode.children || []).length === 1 ? "" : "s"}
          {selectedNode.children && selectedNode.children.length > 0 ? " · reports to " : ""}
          {selectedNode.id === "BOD" ? "" : selectedNode.id === "TAC" ? "Board" : "TAC"}
        </div>

        <div className="mt-detail-section">Upcoming meetings</div>
        {meetings.map((m, i) => (
          <div key={i} className="mt-meet">
            <I.Clock size={13}/>
            <b>{m.when}</b>
            <span className="kind">{m.kind}</span>
          </div>
        ))}

        <div className="mt-actions">
          <button className="primary"><I.Book size={13}/> Open agenda</button>
          <button><I.Share size={13}/> Subscribe</button>
          <button><I.Chart size={13}/> Voting history</button>
        </div>
      </div>
    </div>
  );
}

window.MeetingTracksOrgChart = MeetingTracksOrgChart;
