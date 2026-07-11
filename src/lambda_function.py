"""
ThreeToday — AI daily focus planner for the AWS Weekend Productivity Challenge.

Architecture:
  - One Lambda + Function URL (serves UI on GET, API on POST)
  - Amazon Bedrock (Nova Lite) for AI extraction / prioritization
  - Deterministic code enforces the "exactly three today" rule
  - Least-privilege IAM (InvokeModel on Nova Lite only)
"""

from __future__ import annotations

import json
import os
import re
import traceback
from typing import Any

# boto3 is required only when calling Bedrock (Lambda always has it).
# Local mock mode can import this module without boto3 installed.
try:
    import boto3
except ImportError:  # pragma: no cover
    boto3 = None  # type: ignore

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

MODEL_ID = os.environ.get("MODEL_ID", "amazon.nova-lite-v1:0")
REGION = os.environ.get("AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "ap-southeast-2"))
MAX_BRAIN_DUMP_CHARS = 6000
MAX_HOURS = 12.0
MIN_HOURS = 0.5

_bedrock_client = None


def _bedrock():
    global _bedrock_client
    if _bedrock_client is None:
        if boto3 is None:
            raise RuntimeError("boto3 is not installed. pip install boto3")
        _bedrock_client = boto3.client("bedrock-runtime", region_name=REGION)
    return _bedrock_client


# ---------------------------------------------------------------------------
# HTML UI (single origin — no CORS issues)
# ---------------------------------------------------------------------------

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>ThreeToday — Lock in three things you can finish</title>
  <meta name="description" content="Paste your brain dump. ThreeToday turns chaos into exactly three finishable outcomes for today." />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet" />
  <style>
    :root {
      --bg: #0b0f14;
      --bg-elevated: #121820;
      --bg-card: #161e28;
      --border: #243041;
      --border-strong: #334155;
      --text: #e8eef6;
      --text-muted: #8b9bb0;
      --text-dim: #5c6b7e;
      --accent: #3dffa8;
      --accent-dim: rgba(61, 255, 168, 0.12);
      --accent-border: rgba(61, 255, 168, 0.35);
      --warn: #ffb020;
      --warn-dim: rgba(255, 176, 32, 0.12);
      --danger: #ff6b6b;
      --danger-dim: rgba(255, 107, 107, 0.12);
      --park: #7aa2ff;
      --park-dim: rgba(122, 162, 255, 0.12);
      --radius: 14px;
      --shadow: 0 20px 50px rgba(0,0,0,0.45);
      --font: "DM Sans", system-ui, sans-serif;
      --mono: "JetBrains Mono", ui-monospace, monospace;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: var(--font);
      background:
        radial-gradient(1200px 600px at 10% -10%, rgba(61,255,168,0.08), transparent 55%),
        radial-gradient(900px 500px at 100% 0%, rgba(122,162,255,0.08), transparent 50%),
        var(--bg);
      color: var(--text);
      min-height: 100vh;
      line-height: 1.5;
    }

    .wrap {
      max-width: 920px;
      margin: 0 auto;
      padding: 32px 20px 80px;
    }

    header {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 28px;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .logo {
      width: 42px;
      height: 42px;
      border-radius: 12px;
      background: linear-gradient(145deg, var(--accent), #1ecf88);
      display: grid;
      place-items: center;
      color: #062316;
      font-weight: 700;
      font-size: 18px;
      box-shadow: 0 0 0 1px rgba(61,255,168,0.4), 0 8px 24px rgba(61,255,168,0.2);
    }

    h1 {
      font-size: 1.45rem;
      font-weight: 700;
      letter-spacing: -0.02em;
    }

    .tagline {
      color: var(--text-muted);
      font-size: 0.92rem;
      margin-top: 2px;
    }

    .badge {
      font-family: var(--mono);
      font-size: 0.72rem;
      color: var(--accent);
      background: var(--accent-dim);
      border: 1px solid var(--accent-border);
      padding: 6px 10px;
      border-radius: 999px;
      white-space: nowrap;
    }

    .card {
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 22px;
      box-shadow: var(--shadow);
      margin-bottom: 18px;
    }

    label {
      display: block;
      font-size: 0.82rem;
      font-weight: 600;
      color: var(--text-muted);
      margin-bottom: 8px;
      letter-spacing: 0.02em;
      text-transform: uppercase;
    }

    textarea, input, select {
      width: 100%;
      background: var(--bg-elevated);
      border: 1px solid var(--border);
      border-radius: 10px;
      color: var(--text);
      font-family: var(--font);
      font-size: 1rem;
      padding: 14px 14px;
      outline: none;
      transition: border-color 0.15s, box-shadow 0.15s;
    }

    textarea:focus, input:focus, select:focus {
      border-color: var(--accent-border);
      box-shadow: 0 0 0 3px var(--accent-dim);
    }

    textarea {
      min-height: 180px;
      resize: vertical;
      line-height: 1.55;
    }

    .row {
      display: grid;
      grid-template-columns: 1fr 1fr 1fr;
      gap: 14px;
      margin-top: 16px;
    }

    @media (max-width: 700px) {
      .row { grid-template-columns: 1fr; }
      header { flex-direction: column; }
    }

    .hint {
      margin-top: 8px;
      font-size: 0.82rem;
      color: var(--text-dim);
    }

    .actions {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      margin-top: 18px;
      align-items: center;
    }

    button {
      font-family: var(--font);
      font-weight: 600;
      font-size: 0.95rem;
      border: none;
      border-radius: 10px;
      padding: 12px 18px;
      cursor: pointer;
      transition: transform 0.12s, opacity 0.12s, background 0.12s;
    }

    button:active { transform: scale(0.98); }
    button:disabled { opacity: 0.55; cursor: not-allowed; }

    .btn-primary {
      background: linear-gradient(145deg, #4dffb4, #1ecf88);
      color: #042216;
      box-shadow: 0 8px 20px rgba(61,255,168,0.22);
    }

    .btn-secondary {
      background: transparent;
      color: var(--text-muted);
      border: 1px solid var(--border-strong);
    }

    .status {
      font-family: var(--mono);
      font-size: 0.78rem;
      color: var(--text-dim);
    }

    .status.error { color: var(--danger); }
    .status.ok { color: var(--accent); }

    .section-title {
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 14px;
    }

    .section-title h2 {
      font-size: 1.05rem;
      font-weight: 700;
      letter-spacing: -0.01em;
    }

    .pill {
      font-family: var(--mono);
      font-size: 0.7rem;
      padding: 3px 8px;
      border-radius: 999px;
      border: 1px solid;
    }

    .pill-today { color: var(--accent); background: var(--accent-dim); border-color: var(--accent-border); }
    .pill-park { color: var(--park); background: var(--park-dim); border-color: rgba(122,162,255,0.35); }
    .pill-kill { color: var(--danger); background: var(--danger-dim); border-color: rgba(255,107,107,0.35); }
    .pill-schedule { color: var(--warn); background: var(--warn-dim); border-color: rgba(255,176,32,0.35); }

    .item {
      border: 1px solid var(--border);
      background: var(--bg-elevated);
      border-radius: 12px;
      padding: 14px 16px;
      margin-bottom: 10px;
    }

    .item-top {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: flex-start;
    }

    .item-title {
      font-weight: 600;
      font-size: 1rem;
    }

    .item-meta {
      font-family: var(--mono);
      font-size: 0.72rem;
      color: var(--text-dim);
      white-space: nowrap;
    }

    .item-body {
      margin-top: 8px;
      color: var(--text-muted);
      font-size: 0.92rem;
    }

    .item-next {
      margin-top: 10px;
      padding: 10px 12px;
      border-radius: 8px;
      background: var(--accent-dim);
      border: 1px solid var(--accent-border);
      color: var(--text);
      font-size: 0.9rem;
    }

    .item-next strong {
      color: var(--accent);
      font-weight: 600;
    }

    .summary {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 10px;
      margin-bottom: 16px;
    }

    @media (max-width: 600px) {
      .summary { grid-template-columns: 1fr; }
    }

    .stat {
      background: var(--bg-elevated);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 14px;
      text-align: center;
    }

    .stat .n {
      font-size: 1.6rem;
      font-weight: 700;
      font-family: var(--mono);
      color: var(--accent);
    }

    .stat .l {
      font-size: 0.78rem;
      color: var(--text-muted);
      margin-top: 2px;
    }

    .schedule-row {
      display: grid;
      grid-template-columns: 88px 1fr;
      gap: 12px;
      padding: 12px 0;
      border-bottom: 1px solid var(--border);
      align-items: start;
    }

    .schedule-row:last-child { border-bottom: none; }

    .time-block {
      font-family: var(--mono);
      font-size: 0.78rem;
      color: var(--warn);
      padding-top: 2px;
    }

    .empty {
      color: var(--text-dim);
      font-size: 0.92rem;
      padding: 8px 0;
    }

    footer {
      margin-top: 28px;
      text-align: center;
      color: var(--text-dim);
      font-size: 0.8rem;
    }

    footer a { color: var(--text-muted); }

    .loader {
      display: inline-block;
      width: 14px;
      height: 14px;
      border: 2px solid rgba(4,34,22,0.25);
      border-top-color: #042216;
      border-radius: 50%;
      animation: spin 0.7s linear infinite;
      vertical-align: -2px;
      margin-right: 8px;
    }

    @keyframes spin { to { transform: rotate(360deg); } }

    #results { display: none; }
    #results.show { display: block; }
  </style>
</head>
<body>
  <div class="wrap">
    <header>
      <div class="brand">
        <div class="logo">3</div>
        <div>
          <h1>ThreeToday</h1>
          <p class="tagline">Paste the chaos. Lock three things you can actually finish.</p>
        </div>
      </div>
      <div class="badge">AI · Amazon Bedrock</div>
    </header>

    <section class="card">
      <label for="brainDump">Brain dump</label>
      <textarea id="brainDump" placeholder="Dump everything on your mind — tasks, worries, half-started work, messages you need to send, meetings, side projects…

Example:
- finish client proposal draft
- reply to Sarah about pricing
- fix login bug
- gym
- research new CRM
- pay invoices
- clean desk
- maybe start that blog post"></textarea>
      <p class="hint">Rough lists, messy notes, and incomplete sentences are fine. ThreeToday sorts the signal from the noise.</p>

      <div class="row">
        <div>
          <label for="hours">Hours available today</label>
          <input id="hours" type="number" min="0.5" max="12" step="0.5" value="4" />
        </div>
        <div>
          <label for="energy">Energy level</label>
          <select id="energy">
            <option value="low">Low — protect deep work</option>
            <option value="medium" selected>Medium — balanced day</option>
            <option value="high">High — tackle hard things</option>
          </select>
        </div>
        <div>
          <label for="context">Day context (optional)</label>
          <input id="context" type="text" placeholder="e.g. client deadline Friday" maxlength="120" />
        </div>
      </div>

      <div class="actions">
        <button class="btn-primary" id="planBtn" onclick="runPlan()">Lock my three</button>
        <button class="btn-secondary" id="sampleBtn" onclick="loadSample()">Load sample</button>
        <button class="btn-secondary" id="copyBtn" onclick="copyMarkdown()" style="display:none">Copy as Markdown</button>
        <span class="status" id="status"></span>
      </div>
    </section>

    <div id="results">
      <section class="card">
        <div class="summary" id="summary"></div>
        <p id="rationale" class="item-body" style="margin-bottom: 8px"></p>
      </section>

      <section class="card">
        <div class="section-title">
          <h2>Today — your three</h2>
          <span class="pill pill-today">DO</span>
        </div>
        <div id="todayList"></div>
      </section>

      <section class="card">
        <div class="section-title">
          <h2>Focus schedule</h2>
          <span class="pill pill-schedule">SEQUENCE</span>
        </div>
        <div id="schedule"></div>
      </section>

      <section class="card">
        <div class="section-title">
          <h2>Parked for later</h2>
          <span class="pill pill-park">LATER</span>
        </div>
        <div id="parkedList"></div>
      </section>

      <section class="card">
        <div class="section-title">
          <h2>Killed (on purpose)</h2>
          <span class="pill pill-kill">CUT</span>
        </div>
        <div id="killedList"></div>
      </section>
    </div>

    <footer>
      Built for the AWS Weekend Productivity Challenge · Powered by Amazon Bedrock Nova Lite
    </footer>
  </div>

  <script>
    let lastPlan = null;

    const SAMPLE = `- rewrite homepage hero copy for AX Digital
- reply to 3 inbound leads from yesterday
- fix broken contact form redirect
- research Apollo enrichment options
- pay software invoices
- book dentist
- plan Instagram reel batch for next week
- maybe learn Rust this weekend
- clean downloads folder
- send proposal to dental clinic lead
- standup notes for team
- grocery run
- watch that AWS re:Invent keynote eventually`;

    function loadSample() {
      document.getElementById('brainDump').value = SAMPLE;
      document.getElementById('hours').value = 5;
      document.getElementById('energy').value = 'medium';
      document.getElementById('context').value = 'Need 2 client deliverables out today';
      setStatus('Sample loaded — hit Lock my three', 'ok');
    }

    function setStatus(msg, kind) {
      const el = document.getElementById('status');
      el.textContent = msg || '';
      el.className = 'status' + (kind ? ' ' + kind : '');
    }

    function esc(s) {
      return String(s ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;');
    }

    async function runPlan() {
      const brain_dump = document.getElementById('brainDump').value.trim();
      const hours = parseFloat(document.getElementById('hours').value);
      const energy = document.getElementById('energy').value;
      const context = document.getElementById('context').value.trim();

      if (!brain_dump) {
        setStatus('Paste a brain dump first', 'error');
        return;
      }
      if (!hours || hours < 0.5 || hours > 12) {
        setStatus('Hours must be between 0.5 and 12', 'error');
        return;
      }

      const btn = document.getElementById('planBtn');
      btn.disabled = true;
      btn.innerHTML = '<span class="loader"></span>Thinking…';
      setStatus('Calling Amazon Bedrock…');

      try {
        const res = await fetch(window.location.href, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ brain_dump, hours, energy, context })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Request failed');
        lastPlan = data;
        renderPlan(data);
        document.getElementById('copyBtn').style.display = 'inline-block';
        setStatus('Plan locked ✓', 'ok');
      } catch (err) {
        setStatus(err.message || String(err), 'error');
      } finally {
        btn.disabled = false;
        btn.textContent = 'Lock my three';
      }
    }

    function renderPlan(data) {
      document.getElementById('results').classList.add('show');
      document.getElementById('summary').innerHTML = `
        <div class="stat"><div class="n">${esc(data.today?.length || 0)}</div><div class="l">Today</div></div>
        <div class="stat"><div class="n">${esc(data.parked?.length || 0)}</div><div class="l">Parked</div></div>
        <div class="stat"><div class="n">${esc(data.killed?.length || 0)}</div><div class="l">Killed</div></div>
      `;
      document.getElementById('rationale').textContent = data.rationale || '';

      const todayEl = document.getElementById('todayList');
      if (!data.today?.length) {
        todayEl.innerHTML = '<p class="empty">No finishable items fit your hours. Add more concrete tasks or free up time.</p>';
      } else {
        todayEl.innerHTML = data.today.map((t, i) => `
          <div class="item">
            <div class="item-top">
              <div class="item-title">${i + 1}. ${esc(t.title)}</div>
              <div class="item-meta">~${esc(t.hours)}h · ${esc(t.effort || 'medium')}</div>
            </div>
            <div class="item-body">${esc(t.why)}</div>
            <div class="item-next"><strong>First move:</strong> ${esc(t.first_move)}</div>
          </div>
        `).join('');
      }

      const sched = document.getElementById('schedule');
      if (!data.schedule?.length) {
        sched.innerHTML = '<p class="empty">No schedule generated.</p>';
      } else {
        sched.innerHTML = data.schedule.map(s => `
          <div class="schedule-row">
            <div class="time-block">${esc(s.block)}</div>
            <div>
              <div class="item-title" style="font-size:0.95rem">${esc(s.focus)}</div>
              <div class="item-body">${esc(s.note || '')}</div>
            </div>
          </div>
        `).join('');
      }

      const park = document.getElementById('parkedList');
      park.innerHTML = data.parked?.length
        ? data.parked.map(t => `
          <div class="item">
            <div class="item-title">${esc(t.title)}</div>
            <div class="item-body">${esc(t.why)}</div>
          </div>`).join('')
        : '<p class="empty">Nothing parked — clean dump.</p>';

      const kill = document.getElementById('killedList');
      kill.innerHTML = data.killed?.length
        ? data.killed.map(t => `
          <div class="item">
            <div class="item-title">${esc(t.title)}</div>
            <div class="item-body">${esc(t.why)}</div>
          </div>`).join('')
        : '<p class="empty">Nothing killed — everything was worth keeping.</p>';

      document.getElementById('results').scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    function copyMarkdown() {
      if (!lastPlan) return;
      const lines = [];
      lines.push('# ThreeToday plan');
      lines.push('');
      if (lastPlan.rationale) lines.push(lastPlan.rationale, '');
      lines.push('## Today');
      (lastPlan.today || []).forEach((t, i) => {
        lines.push(`${i + 1}. **${t.title}** (~${t.hours}h)`);
        lines.push(`   - Why: ${t.why}`);
        lines.push(`   - First move: ${t.first_move}`);
      });
      lines.push('', '## Focus schedule');
      (lastPlan.schedule || []).forEach(s => {
        lines.push(`- ${s.block}: ${s.focus}${s.note ? ' — ' + s.note : ''}`);
      });
      lines.push('', '## Parked');
      (lastPlan.parked || []).forEach(t => lines.push(`- ${t.title} — ${t.why}`));
      lines.push('', '## Killed');
      (lastPlan.killed || []).forEach(t => lines.push(`- ${t.title} — ${t.why}`));
      navigator.clipboard.writeText(lines.join('\n')).then(() => {
        setStatus('Copied Markdown ✓', 'ok');
      }).catch(() => setStatus('Copy failed', 'error'));
    }

    // Enter+Cmd/Ctrl to submit
    document.getElementById('brainDump').addEventListener('keydown', (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') runPlan();
    });
  </script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Bedrock helpers
# ---------------------------------------------------------------------------

def _extract_json(text: str) -> dict[str, Any]:
    """Pull a JSON object from model output (handles fences / preamble)."""
    text = text.strip()
    # fenced block
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    # raw object
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("Model did not return JSON")
    return json.loads(text[start : end + 1])


def call_nova(brain_dump: str, hours: float, energy: str, context: str) -> dict[str, Any]:
    """Ask Nova Lite to extract + triage tasks. Code still enforces max-3 today."""
    system = (
        "You are ThreeToday, a ruthless but kind productivity coach. "
        "Your job is to turn a messy brain dump into a realistic plan for ONE day. "
        "People overcommit. You undercommit on purpose. "
        "Prefer concrete, finishable outcomes over vague ambitions. "
        "Respond with ONLY valid JSON — no markdown, no preamble."
    )

    user = f"""Brain dump:
\"\"\"
{brain_dump}
\"\"\"

Constraints:
- Available focused hours today: {hours}
- Energy level: {energy}
- Extra context: {context or "none"}

Return JSON with this exact shape:
{{
  "rationale": "1-2 sentences explaining the plan tradeoffs",
  "candidates": [
    {{
      "title": "short concrete outcome",
      "hours": 1.5,
      "effort": "low|medium|high",
      "priority_score": 1-100,
      "bucket_suggestion": "today|parked|killed",
      "why": "one sentence",
      "first_move": "a 2-10 minute starting action"
    }}
  ]
}}

Rules:
- Extract 4-12 distinct candidates from the dump (merge duplicates).
- hours must be realistic fractions (0.25 to 4).
- Mark low-value / vague / not-today items as parked or killed.
- Prefer high priority_score for urgent + high-impact + finishable today.
- For energy=low, prefer low/medium effort items for "today".
- For energy=high, allow one high-effort item if impact is high.
- first_move must be specific and tiny.
- Do NOT invent tasks that are not implied by the dump.
"""

    # Nova Messages API via converse (preferred) with invoke_model fallback shape
    client = _bedrock()
    try:
        response = client.converse(
            modelId=MODEL_ID,
            system=[{"text": system}],
            messages=[{"role": "user", "content": [{"text": user}]}],
            inferenceConfig={"maxTokens": 2200, "temperature": 0.2},
        )
        text = response["output"]["message"]["content"][0]["text"]
    except Exception:
        # Fallback: raw invoke_model for Nova
        body = {
            "messages": [
                {"role": "user", "content": [{"text": f"{system}\n\n{user}"}]}
            ],
            "inferenceConfig": {"max_new_tokens": 2200, "temperature": 0.2},
        }
        raw = client.invoke_model(
            modelId=MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(body),
        )
        payload = json.loads(raw["body"].read())
        # Nova invoke_model response shapes vary; try common paths
        text = (
            payload.get("output", {})
            .get("message", {})
            .get("content", [{}])[0]
            .get("text")
            or payload.get("outputText")
            or payload.get("generation")
            or json.dumps(payload)
        )

    return _extract_json(text)


def enforce_three(model_out: dict[str, Any], hours: float, energy: str) -> dict[str, Any]:
    """
    Deterministic layer: budget hours top-down and cap TODAY at 3 items.
    The model suggests; the code decides.
    """
    candidates = model_out.get("candidates") or []
    cleaned = []
    for c in candidates:
        try:
            h = float(c.get("hours") or 1.0)
        except (TypeError, ValueError):
            h = 1.0
        h = max(0.25, min(4.0, h))
        try:
            score = float(c.get("priority_score") or 0)
        except (TypeError, ValueError):
            score = 0.0
        title = str(c.get("title") or "").strip()
        if not title:
            continue
        effort = str(c.get("effort") or "medium").lower()
        if effort not in ("low", "medium", "high"):
            effort = "medium"
        # Soft energy bias on score
        if energy == "low" and effort == "high":
            score -= 15
        if energy == "high" and effort == "high":
            score += 8
        cleaned.append(
            {
                "title": title[:140],
                "hours": round(h, 2),
                "effort": effort,
                "priority_score": score,
                "bucket_suggestion": str(c.get("bucket_suggestion") or "parked").lower(),
                "why": str(c.get("why") or "")[:280],
                "first_move": str(c.get("first_move") or "Start with a 5-minute outline.")[:220],
            }
        )

    # Sort by score desc; stable secondary by suggested today
    cleaned.sort(
        key=lambda x: (
            x["priority_score"],
            1 if x["bucket_suggestion"] == "today" else 0,
        ),
        reverse=True,
    )

    today: list[dict[str, Any]] = []
    parked: list[dict[str, Any]] = []
    killed: list[dict[str, Any]] = []
    used = 0.0

    for item in cleaned:
        suggestion = item["bucket_suggestion"]
        # Hard kill if model says kill and score is weak
        if suggestion == "killed" and item["priority_score"] < 55:
            killed.append(
                {
                    "title": item["title"],
                    "why": item["why"] or "Low impact relative to the cost of attention.",
                }
            )
            continue

        fits = (used + item["hours"]) <= (hours + 0.05) and len(today) < 3
        if fits and suggestion != "killed":
            today.append(
                {
                    "title": item["title"],
                    "hours": item["hours"],
                    "effort": item["effort"],
                    "why": item["why"] or "High leverage for today's constraints.",
                    "first_move": item["first_move"],
                }
            )
            used += item["hours"]
        elif suggestion == "killed":
            killed.append(
                {
                    "title": item["title"],
                    "why": item["why"] or "Not worth the attention tax today.",
                }
            )
        else:
            parked.append(
                {
                    "title": item["title"],
                    "why": item["why"]
                    or (
                        "Doesn't fit today's hour budget after higher-priority work."
                        if len(today) >= 3 or used >= hours
                        else "Better as a later commitment."
                    ),
                }
            )

    # Build a simple focus schedule from today items
    schedule = []
    cursor = 0.0
    for t in today:
        block_h = t["hours"]
        # split long items into 50-min style chunks for readability
        remaining = block_h
        part = 1
        while remaining > 0.01:
            chunk = min(1.0, remaining) if block_h > 1.25 else remaining
            start = cursor
            end = cursor + chunk
            label = f"{_fmt_hours(start)}–{_fmt_hours(end)}"
            note = "Deep focus block" if t["effort"] == "high" else "Steady progress block"
            if block_h > 1.25:
                note = f"Part {part} · {note}"
            schedule.append(
                {
                    "block": label,
                    "focus": t["title"],
                    "note": f"{note}. Start: {t['first_move']}" if part == 1 else note,
                }
            )
            cursor = end
            remaining -= chunk
            part += 1
            # small buffer break marker between items only once at end of task
        if t != today[-1]:
            schedule.append(
                {
                    "block": f"{_fmt_hours(cursor)}–{_fmt_hours(cursor + 0.15)}",
                    "focus": "Break / reset",
                    "note": "Stand up, water, no inbox.",
                }
            )
            cursor += 0.15

    rationale = str(model_out.get("rationale") or "").strip()
    if not rationale:
        rationale = (
            f"Locked {len(today)} outcome(s) into ~{round(used, 1)}h of your {hours}h budget. "
            "Everything else is parked or cut so today stays finishable."
        )
    else:
        rationale = rationale[:400]

    return {
        "rationale": rationale,
        "hours_budget": hours,
        "hours_allocated": round(used, 2),
        "today": today,
        "parked": parked,
        "killed": killed,
        "schedule": schedule,
        "model": MODEL_ID,
    }


def _fmt_hours(h: float) -> str:
    """Format fractional hours from day-start as e.g. +0:00, +1:30 (relative clock)."""
    total_min = int(round(h * 60))
    hh, mm = divmod(total_min, 60)
    return f"+{hh}:{mm:02d}"


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------

def _response(status: int, body: str | dict, content_type: str = "application/json") -> dict:
    if isinstance(body, dict):
        body = json.dumps(body)
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": content_type,
            "Cache-Control": "no-store",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        },
        "body": body,
    }


def handler(event, context):
    try:
        # Function URL / API GW HTTP API shapes
        method = (
            event.get("requestContext", {}).get("http", {}).get("method")
            or event.get("httpMethod")
            or "GET"
        ).upper()

        if method == "OPTIONS":
            return _response(204, "")

        if method == "GET":
            return _response(200, HTML_PAGE, "text/html; charset=utf-8")

        if method != "POST":
            return _response(405, {"error": "Method not allowed"})

        raw_body = event.get("body") or "{}"
        if event.get("isBase64Encoded"):
            import base64

            raw_body = base64.b64decode(raw_body).decode("utf-8")

        try:
            data = json.loads(raw_body)
        except json.JSONDecodeError:
            return _response(400, {"error": "Invalid JSON body"})

        brain_dump = str(data.get("brain_dump") or "").strip()
        if not brain_dump:
            return _response(400, {"error": "brain_dump is required"})
        if len(brain_dump) > MAX_BRAIN_DUMP_CHARS:
            return _response(
                400,
                {"error": f"brain_dump too long (max {MAX_BRAIN_DUMP_CHARS} chars)"},
            )

        try:
            hours = float(data.get("hours") or 4)
        except (TypeError, ValueError):
            return _response(400, {"error": "hours must be a number"})
        hours = max(MIN_HOURS, min(MAX_HOURS, hours))

        energy = str(data.get("energy") or "medium").lower()
        if energy not in ("low", "medium", "high"):
            energy = "medium"

        context_str = str(data.get("context") or "").strip()[:120]

        model_out = call_nova(brain_dump, hours, energy, context_str)
        plan = enforce_three(model_out, hours, energy)
        return _response(200, plan)

    except Exception as exc:
        # Surface useful debug without leaking stack to casual users in prod-ish use
        print("ERROR:", traceback.format_exc())
        msg = str(exc)
        if "AccessDenied" in msg or "not authorized" in msg.lower():
            msg = (
                "Bedrock access denied. Enable model access for Amazon Nova Lite "
                "in the Amazon Bedrock console (same region as the Lambda)."
            )
        elif "ValidationException" in msg or "doesn't have access" in msg.lower():
            msg = (
                "Model not available. In Bedrock → Model access, enable Amazon Nova Lite "
                f"({MODEL_ID}) in region {REGION}."
            )
        return _response(500, {"error": msg})


# AWS Lambda entrypoint name
lambda_handler = handler
