function UserMsg({ text }) {
  return (
    <div className="pt-msg pt-msg--user">
      <style>{`
        .pt-msg { max-width: 760px; margin: 0 auto 26px; }
        .pt-msg--user {
          display: flex; justify-content: flex-end;
        }
        .pt-msg--user .bubble {
          background: var(--panel);
          border: 1px solid var(--rule);
          border-radius: 14px 14px 4px 14px;
          padding: 12px 16px;
          max-width: 82%;
          white-space: pre-wrap;
          font-size: 14.5px;
          line-height: 1.6;
          color: var(--ink);
          box-shadow: var(--shadow-1);
        }
      `}</style>
      <div className="bubble">{text}</div>
    </div>
  );
}

function AssistantAnalysis({ m }) {
  return (
    <div className="pt-msg pt-msg--ai">
      <style>{`
        .pt-msg--ai { display: grid; grid-template-columns: 28px 1fr; gap: 14px; }
        .pt-ai-avatar {
          width: 28px; height: 28px; border-radius: 999px;
          background: var(--ink); color: var(--bg);
          display: grid; place-items: center; flex: 0 0 auto;
          margin-top: 2px;
        }
        .pt-ai-body { min-width: 0; color: var(--ink); font-size: 14.5px; line-height: 1.65; }
        .pt-ai-body p { margin: 0 0 12px; }
        .pt-ai-points {
          display: flex; flex-direction: column; gap: 10px;
          margin: 6px 0 18px;
        }
        .pt-ai-pt {
          display: grid; grid-template-columns: auto 1fr; gap: 12px;
          align-items: baseline;
          padding: 12px 14px;
          border: 1px solid var(--rule);
          border-radius: 10px;
          background: var(--panel);
        }
        .pt-ai-pt .num {
          font-family: var(--mono); font-size: 11px;
          color: var(--accent-2); letter-spacing: .05em;
        }
        .pt-ai-pt b { font-weight: 600; color: var(--ink); }
        .pt-ai-pt .detail { color: var(--ink-2); margin-top: 2px; display: block; font-size: 13.5px; }
        .pt-ai-rewrite {
          margin-top: 14px;
          border-left: 3px solid var(--accent);
          padding: 4px 16px;
          font-family: var(--serif);
          font-size: 19px; font-style: italic;
          color: var(--ink); line-height: 1.45;
        }
        .pt-ai-actions {
          display: flex; gap: 4px; margin-top: 14px;
          color: var(--muted);
        }
        .pt-ai-actions button {
          width: 28px; height: 28px; border-radius: 6px; display: grid; place-items: center;
        }
        .pt-ai-actions button:hover { background: var(--bg-2); color: var(--ink); }
      `}</style>
      <div className="pt-ai-avatar"><I.Logo size={18}/></div>
      <div className="pt-ai-body">
        <p>{m.text}</p>
        <div className="pt-ai-points">
          {m.points.map((p, i) => (
            <div key={i} className="pt-ai-pt">
              <span className="num">0{i+1}</span>
              <div>
                <b>{p.label}</b>
                <span className="detail">{p.detail}</span>
              </div>
            </div>
          ))}
        </div>
        {m.followup && <p>{m.followup}</p>}
        {m.rewrite && <div className="pt-ai-rewrite">“{m.rewrite.replace(/^"|"$/g, "")}”</div>}
        <div className="pt-ai-actions">
          <button title="Copy"><I.Copy size={14}/></button>
          <button title="Regenerate"><I.Refresh size={14}/></button>
          <button title="Good response"><I.Thumbsup size={14}/></button>
          <button title="Pin"><I.Pin size={14}/></button>
        </div>
      </div>
    </div>
  );
}

function MessageStream({ messages, illustration }) {
  return (
    <div className="pt-stream">
      <style>{`
        .pt-stream { padding: 28px 28px 0; }
        .pt-illus-wrap { max-width: 760px; margin: 0 auto 28px; }
      `}</style>
      <div className="pt-illus-wrap">{illustration}</div>
      {messages.map((m, i) =>
        m.role === "user"
          ? <UserMsg key={i} text={m.text}/>
          : <AssistantAnalysis key={i} m={m}/>
      )}
    </div>
  );
}

window.MessageStream = MessageStream;
window.UserMsg = UserMsg;
window.AssistantAnalysis = AssistantAnalysis;
