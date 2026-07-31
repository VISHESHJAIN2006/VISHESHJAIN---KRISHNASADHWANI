// CodePractice frontend -- vanilla JS, no build step.
(() => {
  const state = {
    token: localStorage.getItem("cp_token") || null,
    user: JSON.parse(localStorage.getItem("cp_user") || "null"),
    view: "loading",
    params: {},
    languages: [],
  };

  const app = document.getElementById("app");

  // ---------------------------------------------------------------- API
  async function api(path, { method = "GET", body } = {}) {
    const headers = { "Content-Type": "application/json" };
    if (state.token) headers["Authorization"] = `Bearer ${state.token}`;
    const res = await fetch(`/api${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
    return data;
  }

  function toast(msg) {
    const el = document.createElement("div");
    el.className = "toast";
    el.textContent = msg;
    document.body.appendChild(el);
    setTimeout(() => el.remove(), 3200);
  }

  function setAuth(token, user) {
    state.token = token;
    state.user = user;
    localStorage.setItem("cp_token", token || "");
    localStorage.setItem("cp_user", JSON.stringify(user || null));
  }

  function logout() {
    setAuth(null, null);
    navigate("auth");
  }

  function navigate(view, params = {}) {
    state.view = view;
    state.params = params;
    document.body.dataset.view = view;
    render();
    window.scrollTo(0, 0);
  }

  // drag-to-resize a horizontal split (two panes side by side)
  function makeHResizable(handle, leftPane, container, { min = 25, max = 75 } = {}) {
    if (!handle || !leftPane || !container) return;
    let dragging = false;
    const onMove = (e) => {
      if (!dragging) return;
      const x = e.touches ? e.touches[0].clientX : e.clientX;
      const rect = container.getBoundingClientRect();
      let pct = ((x - rect.left) / rect.width) * 100;
      pct = Math.min(max, Math.max(min, pct));
      leftPane.style.width = pct + "%";
    };
    const onUp = () => {
      dragging = false;
      document.body.classList.remove("resizing-h");
    };
    handle.addEventListener("mousedown", () => { dragging = true; document.body.classList.add("resizing-h"); });
    handle.addEventListener("touchstart", () => { dragging = true; document.body.classList.add("resizing-h"); });
    window.addEventListener("mousemove", onMove);
    window.addEventListener("touchmove", onMove);
    window.addEventListener("mouseup", onUp);
    window.addEventListener("touchend", onUp);
  }

  // drag-to-resize a vertical split (editor above / results below)
  function makeVResizable(handle, topPane, container, { min = 30, max = 80 } = {}) {
    if (!handle || !topPane || !container) return;
    let dragging = false;
    const onMove = (e) => {
      if (!dragging) return;
      const y = e.touches ? e.touches[0].clientY : e.clientY;
      const rect = container.getBoundingClientRect();
      let pct = ((y - rect.top) / rect.height) * 100;
      pct = Math.min(max, Math.max(min, pct));
      topPane.style.height = pct + "%";
    };
    const onUp = () => {
      dragging = false;
      document.body.classList.remove("resizing-v");
    };
    handle.addEventListener("mousedown", () => { dragging = true; document.body.classList.add("resizing-v"); });
    handle.addEventListener("touchstart", () => { dragging = true; document.body.classList.add("resizing-v"); });
    window.addEventListener("mousemove", onMove);
    window.addEventListener("touchmove", onMove);
    window.addEventListener("mouseup", onUp);
    window.addEventListener("touchend", onUp);
  }

  function esc(s) {
    return String(s ?? "").replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
  }

  function mdLite(md) {
    // Minimal markdown-ish rendering: **bold**, `code`, headings, lists, paragraphs.
    let html = esc(md || "");
    html = html.replace(/```([\s\S]*?)```/g, (_, code) => `<pre><code>${code}</code></pre>`);
    html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
    html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    html = html.replace(/^### (.*)$/gm, "<h3>$1</h3>");
    html = html.replace(/^## (.*)$/gm, "<h3>$1</h3>");
    html = html.replace(/^- (.*)$/gm, "<li>$1</li>");
    html = html.replace(/(<li>.*<\/li>\n?)+/g, (m) => `<ul>${m}</ul>`);
    html = html.split(/\n{2,}/).map((block) => {
      if (/^<(h3|ul|pre)/.test(block.trim())) return block;
      return `<p>${block.trim().replace(/\n/g, "<br/>")}</p>`;
    }).join("\n");
    return html;
  }

  // ------------------------------------------------------------ Shell
  function shell(contentHtml) {
    const u = state.user;
    return `
      <div class="topbar">
        <div class="wordmark">VIT Code
          <svg viewBox="0 0 120 8" preserveAspectRatio="none"><path d="M2 5 Q 20 1, 40 5 T 80 4 T 118 5" stroke="var(--accent)" stroke-width="2.5" fill="none" stroke-linecap="round"/></svg>
        </div>
        <nav>
          ${u?.role === "STUDENT" ? `
            <button class="navlink ${state.view === "problems" ? "active" : ""}" data-nav="problems">Problems</button>
            <button class="navlink ${state.view === "sheets" ? "active" : ""}" data-nav="sheets">Daily Sheets</button>
            <button class="navlink ${state.view === "progress" ? "active" : ""}" data-nav="progress">My Progress</button>
          ` : ""}
          ${u?.role === "TRAINER" ? `
            <button class="navlink ${state.view === "trainer-problems" ? "active" : ""}" data-nav="trainer-problems">Problems</button>
            <button class="navlink ${state.view === "trainer-sheets" ? "active" : ""}" data-nav="trainer-sheets">Sheets</button>
            <button class="navlink ${state.view === "trainer-analytics" ? "active" : ""}" data-nav="trainer-analytics">Analytics</button>
          ` : ""}
          <span class="who">${esc(u?.name || "")} &middot; ${esc(u?.role || "")}</span>
          <button class="btn-link" id="logout-btn" style="margin-left:8px;">log out</button>
        </nav>
      </div>
      <main>${contentHtml}</main>
    `;
  }

  function wireShell() {
    document.querySelectorAll("[data-nav]").forEach((btn) => {
      btn.addEventListener("click", () => navigate(btn.dataset.nav));
    });
    document.getElementById("logout-btn")?.addEventListener("click", logout);
  }

  // ------------------------------------------------------------ Auth view
  function renderAuth() {
    const mode = state.params.mode || "login";
    app.innerHTML = `
      <div class="narrow panel">
        <div class="eyebrow">College Placement Prep</div>
        <h1 style="margin-bottom:4px;">${mode === "login" ? "Welcome back" : "Create an account"}</h1>
        <p class="muted" style="margin-top:0;">Daily practice, curated by your trainers. Free for every student.</p>
        <form id="auth-form">
          ${mode === "signup" ? `
            <div class="field"><label>Full name</label><input name="name" required /></div>
            <div class="field"><label>I am a</label>
              <select name="role">
                <option value="STUDENT">Student</option>
                <option value="TRAINER">Placement Trainer</option>
              </select>
            </div>
            <div class="field"><label>Cohort / batch (optional)</label><input name="cohort_name" placeholder="e.g. CSE Batch 2027" /></div>
          ` : ""}
          <div class="field"><label>Email</label><input name="email" type="email" required /></div>
          <div class="field"><label>Password</label><input name="password" type="password" required minlength="6" /></div>
          <p class="error-text" id="auth-error"></p>
          <div class="btn-row">
            <button class="btn btn-primary" type="submit">${mode === "login" ? "Log in" : "Sign up"}</button>
            <button class="btn btn-ghost" type="button" id="auth-switch">
              ${mode === "login" ? "Need an account? Sign up" : "Have an account? Log in"}
            </button>
          </div>
        </form>
        <p class="muted" style="font-family: var(--mono); font-size: 12px; margin-top: 18px;">
          Demo logins &mdash; trainer@college.edu / trainer123 &middot; student@college.edu / student123
        </p>
      </div>
    `;
    document.getElementById("auth-switch").addEventListener("click", () => {
      navigate("auth", { mode: mode === "login" ? "signup" : "login" });
    });
    document.getElementById("auth-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = Object.fromEntries(new FormData(e.target));
      const errorEl = document.getElementById("auth-error");
      errorEl.textContent = "";
      try {
        const data = await api(mode === "login" ? "/auth/login" : "/auth/signup", { method: "POST", body: fd });
        setAuth(data.token, data.user);
        await afterLogin();
      } catch (err) {
        errorEl.textContent = err.message;
      }
    });
  }

  async function afterLogin() {
    const langData = await api("/languages");
    state.languages = langData.languages;
    navigate(state.user.role === "TRAINER" ? "trainer-problems" : "problems");
  }

  // ------------------------------------------------------------ Student: Problem list (grouped by topic)
  async function renderProblems() {
    app.innerHTML = shell(`<p class="muted">Loading problems&hellip;</p>`);
    wireShell();
    const { problems } = await api("/problems");

    // filter state lives for the lifetime of this view
    const filterState = { q: "", difficulty: "ALL", status: "ALL" };

    function problemRow(p) {
      return `
        <div class="problem-row" data-title="${esc(p.title.toLowerCase())}">
          <span class="problem-row-status status-${p.my_status}" title="${p.my_status.replace("_", " ")}"></span>
          <a href="#" data-open="${esc(p.slug)}" class="problem-row-title">${esc(p.title)}</a>
          <span class="badge badge-${p.difficulty}">${p.difficulty}</span>
        </div>
      `;
    }

    function buildGroups() {
      // group by every topic a problem carries, LeetCode "explore"-style;
      // problems with no topic land in a catch-all group.
      const groups = new Map();
      problems.forEach((p) => {
        const topics = p.topics && p.topics.length ? p.topics : ["Uncategorized"];
        topics.forEach((t) => {
          if (!groups.has(t)) groups.set(t, []);
          groups.get(t).push(p);
        });
      });
      return [...groups.entries()].sort((a, b) => b[1].length - a[1].length || a[0].localeCompare(b[0]));
    }

    function applyFilters(list) {
      return list.filter((p) => {
        if (filterState.q && !p.title.toLowerCase().includes(filterState.q)) return false;
        if (filterState.difficulty !== "ALL" && p.difficulty !== filterState.difficulty) return false;
        if (filterState.status !== "ALL" && p.my_status !== filterState.status) return false;
        return true;
      });
    }

    function renderList() {
      const groups = buildGroups();

      const groupsHtml = groups.map(([topic, list], i) => {
        const visible = applyFilters(list);
        if (!visible.length) return "";
        const solved = list.filter((p) => p.my_status === "SOLVED").length;
        const pct = list.length ? Math.round((solved / list.length) * 100) : 0;
        return `
          <details class="category-group" ${i < 3 ? "open" : ""}>
            <summary class="category-header">
              <span class="category-caret">&#9656;</span>
              <span class="category-name">${esc(topic)}</span>
              <span class="category-count muted">${solved}/${list.length} solved</span>
              <span class="category-progress"><span class="category-progress-fill" style="width:${pct}%"></span></span>
            </summary>
            <div class="category-body">
              ${visible.map(problemRow).join("")}
            </div>
          </details>
        `;
      }).join("");

      const listEl = document.getElementById("category-list");
      if (listEl) {
        listEl.innerHTML = groupsHtml || `<div class="empty-state">No problems match these filters.</div>`;
        document.querySelectorAll("[data-open]").forEach((a) => {
          a.addEventListener("click", (e) => { e.preventDefault(); navigate("problem", { slug: a.dataset.open }); });
        });
      }
    }

    // sidebar stats
    const solvedTotal = problems.filter((p) => p.my_status === "SOLVED").length;
    const attemptedTotal = problems.filter((p) => p.my_status === "ATTEMPTED").length;
    const diffCounts = { EASY: 0, MEDIUM: 0, HARD: 0 };
    const diffSolved = { EASY: 0, MEDIUM: 0, HARD: 0 };
    problems.forEach((p) => {
      if (diffCounts[p.difficulty] !== undefined) {
        diffCounts[p.difficulty]++;
        if (p.my_status === "SOLVED") diffSolved[p.difficulty]++;
      }
    });
    const overallPct = problems.length ? Math.round((solvedTotal / problems.length) * 100) : 0;
    const groupsForNav = buildGroups();

    app.innerHTML = shell(`
      <div class="eyebrow">Problem Catalog</div>
      <h1>Solve at your own pace</h1>
      <p class="muted" style="margin-top:-6px;">${problems.length} problems &middot; sorted into categories, just like a real judge sheet.</p>

      <div class="problems-layout">
        <aside class="problems-sidebar">
          <div class="panel stats-card">
            <div class="stats-ring" style="--pct:${overallPct}">
              <div class="stats-ring-inner">
                <strong>${solvedTotal}</strong>
                <span>/ ${problems.length}</span>
              </div>
            </div>
            <div class="stats-breakdown">
              <div class="stats-row"><span class="dot dot-EASY"></span>Easy <b>${diffSolved.EASY}/${diffCounts.EASY}</b></div>
              <div class="stats-row"><span class="dot dot-MEDIUM"></span>Medium <b>${diffSolved.MEDIUM}/${diffCounts.MEDIUM}</b></div>
              <div class="stats-row"><span class="dot dot-HARD"></span>Hard <b>${diffSolved.HARD}/${diffCounts.HARD}</b></div>
              <div class="stats-row muted"><span class="dot" style="background:var(--accent);"></span>Attempted <b>${attemptedTotal}</b></div>
            </div>
          </div>
          <div class="panel category-nav">
            <h3 style="margin-bottom:10px;">Categories</h3>
            ${groupsForNav.map(([topic, list]) => {
              const solved = list.filter((p) => p.my_status === "SOLVED").length;
              return `<button type="button" class="category-nav-item" data-jump="${esc(topic)}">
                <span>${esc(topic)}</span>
                <span class="muted">${solved}/${list.length}</span>
              </button>`;
            }).join("")}
          </div>
        </aside>

        <div class="problems-main">
          <div class="filter-bar">
            <input type="search" id="pf-search" placeholder="Search problems&hellip;" />
            <div class="filter-pills" id="pf-difficulty">
              ${["ALL", "EASY", "MEDIUM", "HARD"].map((d) => `<button type="button" class="pill ${d === "ALL" ? "active" : ""}" data-diff="${d}">${d === "ALL" ? "All" : d}</button>`).join("")}
            </div>
            <div class="filter-pills" id="pf-status">
              ${[["ALL", "All"], ["SOLVED", "Solved"], ["ATTEMPTED", "Attempted"], ["NOT_ATTEMPTED", "Untouched"]].map(([v, l]) => `<button type="button" class="pill ${v === "ALL" ? "active" : ""}" data-status="${v}">${l}</button>`).join("")}
            </div>
          </div>

          <div id="category-list"></div>
        </div>
      </div>
    `);
    wireShell();

    if (!problems.length) {
      document.getElementById("category-list").innerHTML = `<div class="empty-state">No problems published yet. Check back once your trainer publishes some.</div>`;
      return;
    }

    renderList();

    document.getElementById("pf-search").addEventListener("input", (e) => {
      filterState.q = e.target.value.trim().toLowerCase();
      renderList();
    });
    document.getElementById("pf-difficulty").addEventListener("click", (e) => {
      const btn = e.target.closest("[data-diff]");
      if (!btn) return;
      filterState.difficulty = btn.dataset.diff;
      document.querySelectorAll("#pf-difficulty .pill").forEach((p) => p.classList.toggle("active", p === btn));
      renderList();
    });
    document.getElementById("pf-status").addEventListener("click", (e) => {
      const btn = e.target.closest("[data-status]");
      if (!btn) return;
      filterState.status = btn.dataset.status;
      document.querySelectorAll("#pf-status .pill").forEach((p) => p.classList.toggle("active", p === btn));
      renderList();
    });
    document.querySelectorAll("[data-jump]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const target = [...document.querySelectorAll(".category-name")].find((el) => el.textContent === btn.dataset.jump);
        const details = target?.closest("details");
        if (details) {
          details.open = true;
          details.scrollIntoView({ behavior: "smooth", block: "start" });
        }
      });
    });
  }

  // ------------------------------------------------------------ Student: Problem workspace
  async function renderProblem() {
    app.innerHTML = shell(`<p class="muted">Loading problem&hellip;</p>`);
    wireShell();
    const { problem } = await api(`/problems/${state.params.slug}`);
    const langs = state.languages.length ? state.languages : (await api("/languages")).languages;
    state.languages = langs;
    const defaultLang = langs[0]?.id || "python";

    app.innerHTML = shell(`
      <div class="ide-topbar">
        <button class="btn-link" id="back-btn">&larr; back to problems</button>
        <div style="display:flex; align-items:center; gap:10px;">
          <span class="badge badge-${problem.difficulty}">${problem.difficulty}</span>
          ${problem.source === "LEETCODE" ? `<span class="badge badge-NOT_ATTEMPTED">LeetCode #${esc(problem.external_ref_id)}</span>` : ""}
          <strong style="font-family: var(--display);">${esc(problem.title)}</strong>
        </div>
      </div>
      <div class="ide" id="ide">
        <div class="ide-pane ide-statement panel statement" id="pane-statement">
          ${mdLite(problem.statement_md)}
          ${problem.constraints_md ? `<h3>Constraints</h3>${mdLite(problem.constraints_md)}` : ""}
          <h3>Sample tests</h3>
          ${problem.sample_test_cases.map((tc, i) => `
            <div style="margin-bottom:10px; font-family: var(--mono); font-size: 13px;">
              <div class="muted">Sample ${i + 1} &mdash; input</div>
              <pre style="background: var(--bg); padding:8px; border-radius:6px; overflow-x:auto;">${esc(tc.input_payload)}</pre>
              <div class="muted">expected output</div>
              <pre style="background: var(--bg); padding:8px; border-radius:6px; overflow-x:auto;">${esc(tc.expected_output)}</pre>
            </div>
          `).join("")}
        </div>
        <div class="ide-resizer-h" id="resizer-h"></div>
        <div class="ide-pane ide-editor-col" id="pane-editor">
          <div class="panel ide-editor-panel">
            <div class="editor-toolbar">
              <select class="lang-select" id="lang-select">
                ${langs.map((l) => `<option value="${l.id}" ${l.id === defaultLang ? "selected" : ""}>${esc(l.label)}</option>`).join("")}
              </select>
              <div class="btn-row" style="margin-top:0;">
                <button class="btn" id="run-btn">&#9654; Run</button>
                <button class="btn btn-primary" id="submit-btn">Submit</button>
              </div>
            </div>
            <textarea class="code-editor" id="code-editor" spellcheck="false"></textarea>
          </div>
          <div class="ide-resizer-v" id="resizer-v"></div>
          <div class="panel ide-console" id="pane-console">
            <div class="ide-console-header">
              <h3 style="margin:0;">Console</h3>
              <div id="judge-status" class="muted" style="font-family: var(--mono); font-size:12px;"></div>
            </div>
            <div id="results" class="results">
              <p class="muted" style="font-family: var(--mono); font-size:13px;">Run your code to see results here.</p>
            </div>
          </div>
        </div>
      </div>
    `);
    wireShell();
    document.getElementById("back-btn").addEventListener("click", () => navigate("problems"));

    makeHResizable(document.getElementById("resizer-h"), document.getElementById("pane-statement"), document.getElementById("ide"));
    makeVResizable(document.getElementById("resizer-v"), document.getElementById("pane-editor").querySelector(".ide-editor-panel"), document.getElementById("pane-editor"));

    const editor = document.getElementById("code-editor");
    const langSelect = document.getElementById("lang-select");
    const starter = problem.starter_code || {};
    editor.value = starter[defaultLang] || "";
    langSelect.addEventListener("change", () => {
      editor.value = starter[langSelect.value] || "";
    });

    async function runJudge(mode) {
      const statusEl = document.getElementById("judge-status");
      const resultsEl = document.getElementById("results");
      statusEl.textContent = mode === "RUN" ? "Running sample tests\u2026" : "Submitting for full judging\u2026";
      resultsEl.innerHTML = "";
      document.getElementById("run-btn").disabled = true;
      document.getElementById("submit-btn").disabled = true;
      try {
        const { submission } = await api("/submissions", {
          method: "POST",
          body: { problem_id: problem.id, language: langSelect.value, source_code: editor.value, mode },
        });
        renderJudgeResult(submission, mode);
      } catch (err) {
        statusEl.textContent = "";
        resultsEl.innerHTML = `<p class="error-text">${esc(err.message)}</p>`;
      } finally {
        document.getElementById("run-btn").disabled = false;
        document.getElementById("submit-btn").disabled = false;
      }
    }

    function renderJudgeResult(submission, mode) {
      const statusEl = document.getElementById("judge-status");
      const resultsEl = document.getElementById("results");
      const passedAll = submission.status === "ACCEPTED";
      statusEl.textContent = `${submission.results.length} test case(s) &middot; ${submission.runtime_ms} ms total`.replace("&middot;", "\u00b7");
      const stampClass = passedAll ? "ok" : "bad";
      const stampLabel = passedAll ? (mode === "RUN" ? "Samples Passed" : "Accepted") : submission.status.replace(/_/g, " ");
      resultsEl.innerHTML = `
        <div class="stamp ${stampClass}">${esc(stampLabel)}</div>
        <div style="margin-top:12px;">
          ${submission.results.map((r, i) => `
            <div class="tc-row">
              <span>${r.is_sample ? "Sample" : "Hidden"} test ${i + 1}</span>
              <span class="${r.passed ? "tc-pass" : "tc-fail"}">${r.passed ? "\u2713 passed" : "\u2717 " + r.status.replace(/_/g, " ").toLowerCase()}</span>
            </div>
            ${!r.passed && r.stderr_excerpt ? `<pre style="background:var(--bg); padding:8px; border-radius:6px; font-size:12px; color:var(--bad); overflow-x:auto;">${esc(r.stderr_excerpt)}</pre>` : ""}
          `).join("")}
        </div>
      `;
    }

    document.getElementById("run-btn").addEventListener("click", () => runJudge("RUN"));
    document.getElementById("submit-btn").addEventListener("click", () => runJudge("SUBMIT"));
  }

  // ------------------------------------------------------------ Student: Sheets
  async function renderSheets() {
    app.innerHTML = shell(`<p class="muted">Loading&hellip;</p>`);
    wireShell();
    const { sheets } = await api("/sheets");
    const html = sheets.map((s) => `
      <div class="card">
        <h3 style="margin-bottom:8px;">${esc(s.title)}</h3>
        ${s.problems.map((p) => `
          <div class="card-row" style="padding:6px 0;">
            <a href="#" data-open="${esc(p.slug)}" style="color: var(--ink); text-decoration:none;">${esc(p.title)}</a>
            <span class="badge badge-${p.difficulty}">${p.difficulty}</span>
          </div>
        `).join("")}
      </div>
    `).join("") || `<div class="empty-state">No practice sheets assigned to your cohort yet.</div>`;

    app.innerHTML = shell(`<div class="eyebrow">Assigned by your trainers</div><h1>Daily Sheets</h1>${html}`);
    wireShell();
    document.querySelectorAll("[data-open]").forEach((a) => {
      a.addEventListener("click", (e) => { e.preventDefault(); navigate("problem", { slug: a.dataset.open }); });
    });
  }

  // ------------------------------------------------------------ Student: Progress
  async function renderProgress() {
    app.innerHTML = shell(`<p class="muted">Loading&hellip;</p>`);
    wireShell();
    const stats = await api("/analytics/me");
    const diffRows = Object.entries(stats.solved_by_difficulty).map(([k, v]) => `
      <div class="card-row" style="padding:6px 0;"><span class="badge badge-${k}">${k}</span><span class="muted">${v} solved</span></div>
    `).join("");
    const topicRows = Object.entries(stats.solved_by_topic).map(([k, v]) => `
      <div class="card-row" style="padding:6px 0;"><span>${esc(k)}</span><span class="muted">${v} solved</span></div>
    `).join("") || `<p class="muted">Solve a few problems to see topic breakdown.</p>`;

    app.innerHTML = shell(`
      <div class="eyebrow">Your journey so far</div>
      <h1>Progress</h1>
      <div class="workspace">
        <div class="panel">
          <h3>Overview</h3>
          <p style="font-family: var(--display); font-size: 40px; margin: 4px 0;">${stats.solved_count}<span class="muted" style="font-size:16px;"> solved</span></p>
          <p class="muted">${stats.attempted_count} problems attempted in total</p>
          <h3 style="margin-top:20px;">By difficulty</h3>
          ${diffRows}
        </div>
        <div class="panel">
          <h3>By topic</h3>
          ${topicRows}
        </div>
      </div>
    `);
    wireShell();
  }

  // ------------------------------------------------------------ Trainer: Problems
  async function renderTrainerProblems() {
    app.innerHTML = shell(`<p class="muted">Loading&hellip;</p>`);
    wireShell();
    const { problems } = await api("/problems");
    const rows = problems.map((p) => `
      <tr>
        <td>${esc(p.title)}</td>
        <td><span class="badge badge-${p.difficulty}">${p.difficulty}</span></td>
        <td>${esc(p.source)}</td>
        <td><span class="badge badge-NOT_ATTEMPTED">${esc(p.status)}</span></td>
        <td><button class="btn-link" data-edit="${p.id}">manage</button></td>
      </tr>
    `).join("");

    app.innerHTML = shell(`
      <div class="card-row" style="margin-bottom:18px;">
        <div><div class="eyebrow">Trainer Console</div><h1>Problem Catalog</h1></div>
        <button class="btn btn-primary" id="new-problem-btn">+ New problem</button>
      </div>
      <div class="panel">
        <table class="data-table">
          <thead><tr><th>Title</th><th>Difficulty</th><th>Source</th><th>Status</th><th></th></tr></thead>
          <tbody>${rows || `<tr><td colspan="5" class="muted">No problems yet.</td></tr>`}</tbody>
        </table>
      </div>
    `);
    wireShell();
    document.getElementById("new-problem-btn").addEventListener("click", () => navigate("trainer-problem-form", {}));
    document.querySelectorAll("[data-edit]").forEach((btn) => {
      btn.addEventListener("click", () => navigate("trainer-problem-detail", { id: btn.dataset.edit }));
    });
  }

  function ingestionNote() {
    return `
      <p class="muted" style="font-family: var(--mono); font-size:12px; margin-top:-4px;">
        LeetCode-sourced problems are ingested via <code>[LEETCODE_DATA_SOURCE_URL]</code> into DRAFT status
        for your review before publishing (see architecture doc &sect;6). Use the form below either to author an
        internal problem, or to hand-enter/adjust an ingested one for this MVP.
      </p>`;
  }

  async function renderTrainerProblemForm() {
    app.innerHTML = shell(`
      <button class="btn-link" id="back-btn" style="margin-bottom:14px;">&larr; back</button>
      <div class="eyebrow">New Problem</div>
      <h1>Add a problem</h1>
      ${ingestionNote()}
      <form id="problem-form" class="panel" style="margin-top:14px;">
        <div class="field-row">
          <div class="field"><label>Title</label><input name="title" required /></div>
          <div class="field"><label>Slug (URL-safe)</label><input name="slug" required placeholder="e.g. valid-anagram" /></div>
        </div>
        <div class="field-row">
          <div class="field"><label>Difficulty</label>
            <select name="difficulty"><option>EASY</option><option>MEDIUM</option><option>HARD</option></select>
          </div>
          <div class="field"><label>Source</label>
            <select name="source"><option value="INTERNAL">Internal</option><option value="LEETCODE">LeetCode</option></select>
          </div>
          <div class="field"><label>LeetCode # (if sourced)</label><input name="external_ref_id" /></div>
        </div>
        <div class="field"><label>Topics (comma-separated)</label><input name="topics" placeholder="array, hash-table" /></div>
        <div class="field"><label>Statement (Markdown)</label><textarea name="statement_md" rows="6" required></textarea></div>
        <div class="field"><label>Constraints (Markdown)</label><textarea name="constraints_md" rows="3"></textarea></div>
        <div class="field"><label>Status</label>
          <select name="status"><option value="DRAFT">Draft (hidden from students)</option><option value="PUBLISHED">Published</option></select>
        </div>
        <p class="error-text" id="form-error"></p>
        <div class="btn-row"><button class="btn btn-primary" type="submit">Create problem</button></div>
      </form>
    `);
    wireShell();
    document.getElementById("back-btn").addEventListener("click", () => navigate("trainer-problems"));
    document.getElementById("problem-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = Object.fromEntries(new FormData(e.target));
      fd.topics = fd.topics.split(",").map((s) => s.trim()).filter(Boolean);
      try {
        const { problem } = await api("/problems", { method: "POST", body: fd });
        toast("Problem created. Add test cases next.");
        navigate("trainer-problem-detail", { id: problem.id });
      } catch (err) {
        document.getElementById("form-error").textContent = err.message;
      }
    });
  }

  async function renderTrainerProblemDetail() {
    app.innerHTML = shell(`<p class="muted">Loading&hellip;</p>`);
    wireShell();
    const problemId = state.params.id;
    const [{ problems }, { test_cases }] = await Promise.all([
      api("/problems"),
      api(`/problems/${problemId}/testcases`),
    ]);
    const problem = problems.find((p) => String(p.id) === String(problemId));
    if (!problem) { navigate("trainer-problems"); return; }

    const tcRows = test_cases.map((tc) => `
      <tr>
        <td><pre style="margin:0; white-space:pre-wrap;">${esc(tc.input_payload) || "<em>(none)</em>"}</pre></td>
        <td><pre style="margin:0; white-space:pre-wrap;">${esc(tc.expected_output)}</pre></td>
        <td>${tc.is_sample ? "Sample" : "Hidden"}</td>
      </tr>
    `).join("");

    app.innerHTML = shell(`
      <button class="btn-link" id="back-btn" style="margin-bottom:14px;">&larr; back</button>
      <div class="card-row">
        <div>
          <div class="eyebrow">${esc(problem.source)}${problem.external_ref_id ? " #" + esc(problem.external_ref_id) : ""}</div>
          <h1>${esc(problem.title)}</h1>
        </div>
        <div>
          <span class="badge badge-${problem.difficulty}">${problem.difficulty}</span>
          <span class="badge badge-NOT_ATTEMPTED">${esc(problem.status)}</span>
        </div>
      </div>

      <div class="workspace">
        <div class="panel statement">${mdLite(problem.statement_md)}</div>
        <div>
          <div class="panel" style="margin-bottom:14px;">
            <h3>Publish status</h3>
            <div class="btn-row" style="margin-top:8px;">
              <button class="btn ${problem.status === "PUBLISHED" ? "" : "btn-primary"}" id="toggle-publish">
                ${problem.status === "PUBLISHED" ? "Unpublish (move to Draft)" : "Publish to students"}
              </button>
            </div>
          </div>
          <div class="panel">
            <h3>Add test case</h3>
            <form id="tc-form">
              <div class="field"><label>Input (stdin)</label><textarea name="input_payload" rows="2"></textarea></div>
              <div class="field"><label>Expected output</label><textarea name="expected_output" rows="1" required></textarea></div>
              <div class="field"><label><input type="checkbox" name="is_sample" style="width:auto;" /> Visible to students as a sample</label></div>
              <button class="btn btn-primary" type="submit">Add test case</button>
            </form>
          </div>
        </div>
      </div>

      <h3 style="margin-top:20px;">Test cases (${test_cases.length})</h3>
      <div class="panel">
        <table class="data-table">
          <thead><tr><th>Input</th><th>Expected output</th><th>Visibility</th></tr></thead>
          <tbody>${tcRows || `<tr><td colspan="3" class="muted">No test cases yet -- this problem can't be judged until you add some.</td></tr>`}</tbody>
        </table>
      </div>
    `);
    wireShell();
    document.getElementById("back-btn").addEventListener("click", () => navigate("trainer-problems"));
    document.getElementById("toggle-publish").addEventListener("click", async () => {
      const newStatus = problem.status === "PUBLISHED" ? "DRAFT" : "PUBLISHED";
      await api(`/problems/${problem.id}`, { method: "PUT", body: { status: newStatus } });
      toast(newStatus === "PUBLISHED" ? "Published to students." : "Moved back to draft.");
      navigate("trainer-problem-detail", { id: problemId });
    });
    document.getElementById("tc-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = Object.fromEntries(new FormData(e.target));
      fd.is_sample = !!e.target.querySelector('[name="is_sample"]').checked;
      try {
        await api(`/problems/${problem.id}/testcases`, { method: "POST", body: fd });
        navigate("trainer-problem-detail", { id: problemId });
      } catch (err) {
        toast(err.message);
      }
    });
  }

  // ------------------------------------------------------------ Trainer: Sheets
  async function renderTrainerSheets() {
    app.innerHTML = shell(`<p class="muted">Loading&hellip;</p>`);
    wireShell();
    const [{ sheets }, { problems }, { cohorts }] = await Promise.all([
      api("/sheets"), api("/problems"), api("/cohorts"),
    ]);
    const published = problems.filter((p) => p.status === "PUBLISHED");

    const sheetCards = sheets.map((s) => `
      <div class="card">
        <h3>${esc(s.title)}</h3>
        <p class="muted">${s.problems.length} problem(s)</p>
      </div>
    `).join("") || `<div class="empty-state">No sheets created yet.</div>`;

    app.innerHTML = shell(`
      <div class="eyebrow">Trainer Console</div>
      <h1>Daily Sheets</h1>
      <div class="workspace">
        <div>${sheetCards}</div>
        <div class="panel">
          <h3>Create a sheet</h3>
          <form id="sheet-form">
            <div class="field"><label>Title</label><input name="title" required placeholder="e.g. Week 2: Graphs" /></div>
            <div class="field"><label>Problems to include</label>
              <div style="max-height:160px; overflow-y:auto; border:1px solid var(--border); border-radius:6px; padding:8px;">
                ${published.map((p) => `
                  <label style="display:flex; align-items:center; gap:8px; padding:4px 0; font-family: var(--mono); font-size:13px;">
                    <input type="checkbox" name="problem_ids" value="${p.id}" style="width:auto;" /> ${esc(p.title)}
                  </label>
                `).join("") || `<span class="muted">Publish some problems first.</span>`}
              </div>
            </div>
            <div class="field"><label>Assign to cohort</label>
              <select name="cohort_ids">
                <option value="">-- none --</option>
                ${cohorts.map((c) => `<option value="${c.id}">${esc(c.name)}</option>`).join("")}
              </select>
            </div>
            <button class="btn btn-primary" type="submit">Create sheet</button>
          </form>
        </div>
      </div>
    `);
    wireShell();
    document.getElementById("sheet-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      const form = e.target;
      const problem_ids = [...form.querySelectorAll('[name="problem_ids"]:checked')].map((el) => Number(el.value));
      const cohort_ids = form.cohort_ids.value ? [Number(form.cohort_ids.value)] : [];
      if (!problem_ids.length) { toast("Select at least one problem."); return; }
      try {
        await api("/sheets", { method: "POST", body: { title: form.title.value, problem_ids, cohort_ids } });
        toast("Sheet created.");
        navigate("trainer-sheets");
      } catch (err) {
        toast(err.message);
      }
    });
  }

  // ------------------------------------------------------------ Trainer: Analytics
  async function renderTrainerAnalytics() {
    app.innerHTML = shell(`<p class="muted">Loading&hellip;</p>`);
    wireShell();
    const { cohorts } = await api("/cohorts");
    if (!cohorts.length) {
      app.innerHTML = shell(`<div class="empty-state">No cohorts yet.</div>`);
      wireShell();
      return;
    }
    const cohortId = state.params.cohortId || cohorts[0].id;
    const data = await api(`/analytics/cohort/${cohortId}`);

    app.innerHTML = shell(`
      <div class="eyebrow">Trainer Console</div>
      <h1>Cohort Analytics</h1>
      <select id="cohort-select" style="margin-bottom:16px;">
        ${cohorts.map((c) => `<option value="${c.id}" ${c.id === Number(cohortId) ? "selected" : ""}>${esc(c.name)}</option>`).join("")}
      </select>
      <div class="workspace">
        <div class="panel">
          <h3>Students &mdash; problems solved</h3>
          <table class="data-table">
            <thead><tr><th>Student</th><th>Solved</th></tr></thead>
            <tbody>${data.students.map((s) => `<tr><td>${esc(s.name)}</td><td>${s.solved_count}</td></tr>`).join("") || `<tr><td colspan="2" class="muted">No students in this cohort yet.</td></tr>`}</tbody>
          </table>
        </div>
        <div class="panel">
          <h3>Most-failed problems</h3>
          <table class="data-table">
            <thead><tr><th>Problem</th><th>Failed submissions</th></tr></thead>
            <tbody>${data.most_failed_problems.map((p) => `<tr><td>${esc(p.title)}</td><td>${p.fail_count}</td></tr>`).join("") || `<tr><td colspan="2" class="muted">No submissions yet.</td></tr>`}</tbody>
          </table>
        </div>
      </div>
    `);
    wireShell();
    document.getElementById("cohort-select").addEventListener("change", (e) => {
      navigate("trainer-analytics", { cohortId: e.target.value });
    });
  }

  // ------------------------------------------------------------ Router
  const views = {
    auth: renderAuth,
    problems: renderProblems,
    problem: renderProblem,
    sheets: renderSheets,
    progress: renderProgress,
    "trainer-problems": renderTrainerProblems,
    "trainer-problem-form": renderTrainerProblemForm,
    "trainer-problem-detail": renderTrainerProblemDetail,
    "trainer-sheets": renderTrainerSheets,
    "trainer-analytics": renderTrainerAnalytics,
  };

  async function render() {
    try {
      await views[state.view]();
    } catch (err) {
      if (String(err.message).includes("401") || String(err.message).toLowerCase().includes("token")) {
        logout();
        return;
      }
      app.innerHTML = shell(`<p class="error-text">Something went wrong: ${esc(err.message)}</p>`);
      wireShell();
    }
  }

  // ------------------------------------------------------------ Boot
  (async function boot() {
    if (state.token && state.user) {
      try {
        await api("/auth/me");
        const langData = await api("/languages");
        state.languages = langData.languages;
        navigate(state.user.role === "TRAINER" ? "trainer-problems" : "problems");
        return;
      } catch {
        setAuth(null, null);
      }
    }
    navigate("auth");
  })();
})();