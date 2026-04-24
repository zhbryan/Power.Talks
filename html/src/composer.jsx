function Composer({ value, onChange, onSend, onSuggest }) {
  const [recording, setRecording] = React.useState(false);
  const taRef = React.useRef(null);
  const autoResize = () => {
    const ta = taRef.current; if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 220) + "px";
  };
  React.useEffect(autoResize, [value]);

  const hasText = (value || "").trim().length > 0;

  const onKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (hasText) onSend();
    }
  };

  return (
    <div className="pt-composer-wrap">
      <style>{`
        .pt-composer-wrap {
          position: sticky; bottom: 0;
          padding: 10px 28px 18px;
          background: linear-gradient(180deg, transparent 0%, var(--bg) 40%);
        }
        .pt-composer {
          max-width: 760px; margin: 0 auto;
          background: var(--panel);
          border: 1px solid var(--rule-2);
          border-radius: 18px;
          box-shadow: var(--shadow-2);
          padding: 8px 8px 8px 14px;
          transition: border-color .15s;
        }
        .pt-composer:focus-within { border-color: var(--accent); }
        .pt-composer textarea {
          width: 100%;
          border: 0; outline: none; resize: none;
          background: transparent;
          font: inherit; font-size: 14.5px; color: var(--ink);
          padding: 10px 4px;
          min-height: 44px; max-height: 220px;
          line-height: 1.55;
        }
        .pt-composer textarea::placeholder { color: var(--muted); }
        .pt-comp-row {
          display: flex; align-items: center; gap: 6px;
          padding: 2px 4px 2px 0;
        }
        .pt-comp-chip {
          display: inline-flex; align-items: center; gap: 6px;
          padding: 6px 10px; border-radius: 999px;
          font-size: 12.5px; color: var(--ink-2);
          border: 1px solid transparent;
        }
        .pt-comp-chip:hover { background: var(--bg-2); color: var(--ink); }
        .pt-comp-chip.is-on {
          background: var(--ink); color: var(--bg); border-color: var(--ink);
        }
        .pt-comp-attach {
          width: 32px; height: 32px; border-radius: 8px; display: grid; place-items: center;
          color: var(--muted);
        }
        .pt-comp-attach:hover { background: var(--bg-2); color: var(--ink); }
        .pt-comp-spacer { flex: 1; }

        .pt-mic, .pt-send {
          width: 36px; height: 36px; border-radius: 999px;
          display: grid; place-items: center;
          transition: transform .1s, background .15s;
        }
        .pt-mic { color: var(--ink-2); }
        .pt-mic:hover { background: var(--bg-2); color: var(--ink); }
        .pt-mic.is-rec {
          background: var(--accent-soft); color: var(--accent-2);
          animation: pulse 1.2s ease-in-out infinite;
        }
        @keyframes pulse { 0%,100% { box-shadow: 0 0 0 0 var(--accent-soft); } 50% { box-shadow: 0 0 0 6px transparent; } }
        .pt-send {
          background: var(--ink); color: var(--bg);
        }
        .pt-send:disabled { opacity: .35; cursor: not-allowed; }
        .pt-send:not(:disabled):hover { transform: scale(1.05); }

        .pt-comp-foot {
          max-width: 760px; margin: 8px auto 0;
          display: flex; align-items: center; justify-content: space-between;
          color: var(--muted); font-size: 11.5px; font-family: var(--mono);
          padding: 0 4px;
        }
        .pt-comp-foot a { color: var(--ink-2); text-decoration: none; }
        .pt-comp-foot a:hover { color: var(--accent); }
      `}</style>
      <div className="pt-composer">
        <textarea
          ref={taRef}
          value={value}
          onChange={e => onChange(e.target.value)}
          onKeyDown={onKey}
          placeholder="Paste a draft, describe the moment, or just say what you're trying to land…"
          rows={1}
        />
        <div className="pt-comp-row">
          <button className="pt-comp-attach" title="Attach"><I.Attach size={16}/></button>
          <button
            className={`pt-mic ${recording ? "is-rec" : ""}`}
            onClick={() => setRecording(r => !r)}
            title="Record rehearsal"
          >
            <I.Mic size={16}/>
          </button>
          <div className="pt-comp-spacer"/>
          <button
            className="pt-send"
            disabled={!hasText}
            onClick={onSend}
            title="Send"
          >
            <I.Send size={16}/>
          </button>
        </div>
      </div>
      <div className="pt-comp-foot">
        <span>⏎ to send · ⇧⏎ newline · / for commands</span>
        <span>
          <a href="#" onClick={(e)=>{e.preventDefault(); onSuggest && onSuggest();}}>suggest a run →</a>
        </span>
      </div>
    </div>
  );
}

window.Composer = Composer;
