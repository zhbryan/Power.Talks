// Power.Talks — app.js
// Shared JS: manifest loader, dashboard filters, report loader, Claude chat.

// ---------------------------------------------------------------------------
// Dashboard — Manifest & Filters
// ---------------------------------------------------------------------------

let allReports = [];

async function loadManifest() {
  const tbody = document.getElementById("reports-body");
  try {
    const resp = await fetch("reports-manifest.json");
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    allReports = await resp.json();
    renderTable(allReports);
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6" class="empty-msg">
      No reports found yet. Run <code>study.py</code> to generate reports.
    </td></tr>`;
  }
}

function renderTable(reports) {
  const tbody = document.getElementById("reports-body");
  if (!reports.length) {
    tbody.innerHTML = '<tr><td colspan="6" class="empty-msg">No reports match the current filters.</td></tr>';
    return;
  }

  tbody.innerHTML = reports.map((r) => {
    const reportUrl = `report.html?report=${encodeURIComponent(r.report_file)}`;
    return `
      <tr>
        <td>${escHtml(r.group)}</td>
        <td>${escHtml(r.category)}</td>
        <td><a href="${reportUrl}">${escHtml(r.report_file)}</a></td>
        <td>${escHtml(r.source_file)}</td>
        <td>${escHtml(r.date)}</td>
        <td><span class="snippet">${escHtml(r.summary_snippet)}</span></td>
      </tr>`;
  }).join("");
}

function applyFilters() {
  const group   = document.getElementById("filter-group").value;
  const fromVal = document.getElementById("filter-date-from").value;
  const toVal   = document.getElementById("filter-date-to").value;
  const search  = document.getElementById("filter-search").value.toLowerCase();

  const filtered = allReports.filter((r) => {
    if (group && r.group !== group) return false;
    if (fromVal && r.date < fromVal) return false;
    if (toVal   && r.date > toVal)   return false;
    if (search) {
      const haystack = (r.report_file + r.source_file + r.category + r.summary_snippet).toLowerCase();
      if (!haystack.includes(search)) return false;
    }
    return true;
  });

  renderTable(filtered);
}

// ---------------------------------------------------------------------------
// Report Viewer — Load content
// ---------------------------------------------------------------------------

async function loadReportContent(reportFile) {
  const container = document.getElementById("report-content");
  try {
    // Reports are Word files; we load the pre-generated HTML sidecar if present,
    // otherwise show a fallback message with a download link.
    const htmlFile = reportFile.replace(/\.docx$/i, ".html");
    const resp = await fetch(`../Reports Database/${htmlFile}`);
    if (resp.ok) {
      container.innerHTML = await resp.text();
      return;
    }
  } catch (_) { /* fall through */ }

  // Fallback: render whatever metadata we have
  container.innerHTML = `
    <h1>${escHtml(reportFile)}</h1>
    <p style="color:#888;margin-top:1rem;">
      HTML preview not available.
      <a href="../Reports Database/${encodeURIComponent(reportFile)}" download>Download Word report</a>
    </p>
    <p style="margin-top:1rem;">
      You can still use the Claude chat panel on the right to ask questions —
      paste relevant text from the Word document into the chat for context.
    </p>`;
}

// ---------------------------------------------------------------------------
// Claude Chat
// ---------------------------------------------------------------------------

function appendChatMessage(role, text) {
  const history = document.getElementById("chat-history");
  const div = document.createElement("div");
  div.className = `chat-msg ${role}`;
  div.textContent = text;
  history.appendChild(div);
  history.scrollTop = history.scrollHeight;
  return div;
}

async function claudeChat(reportContent, userMessage) {
  const sendBtn = document.getElementById("chat-send");
  sendBtn.disabled = true;

  const thinkingDiv = appendChatMessage("thinking", "Claude is thinking...");

  const systemPrompt = `You are a helpful assistant for the Power.Talks project.
The user is reading an ERCOT regulatory report. Answer questions based on the report content below.
Be concise, accurate, and highlight any market impact or action items relevant to the question.

--- REPORT CONTENT ---
${reportContent.slice(0, 12000)}
--- END OF REPORT ---`;

  try {
    const apiKey = window.ANTHROPIC_API_KEY;
    if (!apiKey || apiKey === "YOUR_ANTHROPIC_API_KEY_HERE") {
      thinkingDiv.remove();
      appendChatMessage("assistant", "⚠️ Please set your Anthropic API key in html/config.js to use the chat feature.");
      return;
    }

    const response = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-api-key": apiKey,
        "anthropic-version": "2023-06-01",
        "anthropic-dangerous-direct-browser-access": "true",
      },
      body: JSON.stringify({
        model: "claude-sonnet-4-6",
        max_tokens: 1024,
        system: systemPrompt,
        messages: [{ role: "user", content: userMessage }],
        stream: true,
      }),
    });

    if (!response.ok) {
      const err = await response.text();
      throw new Error(`API error ${response.status}: ${err}`);
    }

    thinkingDiv.remove();
    const replyDiv = appendChatMessage("assistant", "");

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const lines = buffer.split("\n");
      buffer = lines.pop();

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const data = line.slice(6).trim();
        if (data === "[DONE]") break;
        try {
          const parsed = JSON.parse(data);
          if (parsed.type === "content_block_delta" && parsed.delta?.text) {
            replyDiv.textContent += parsed.delta.text;
            document.getElementById("chat-history").scrollTop =
              document.getElementById("chat-history").scrollHeight;
          }
        } catch (_) { /* ignore parse errors on partial chunks */ }
      }
    }
  } catch (err) {
    thinkingDiv.remove();
    appendChatMessage("assistant", `Error: ${err.message}`);
  } finally {
    sendBtn.disabled = false;
  }
}

// ---------------------------------------------------------------------------
// Utilities
// ---------------------------------------------------------------------------

function escHtml(str) {
  return String(str ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
