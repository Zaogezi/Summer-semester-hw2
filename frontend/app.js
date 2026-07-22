const state = {
  user: null,
  problems: [],
  problemFilter: "all",
  problemSearch: "",
  page: 1,
};
const app = document.querySelector("#app"),
  nav = document.querySelector("#main-nav"),
  actions = document.querySelector("#user-actions");
const html = (strings, ...values) => strings.reduce((markup, part, index) => markup + part + (index < values.length ? values[index] : ""), "");
const esc = (v) => String(v ?? "").replace(/[&<>'"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[c]);
const fmt = (d) =>
  d
    ? new Intl.DateTimeFormat("zh-CN", {
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      }).format(new Date(d))
    : "—";
const roleName = { student: "学生", teacher: "教师", admin: "管理员" };
async function api(path, options = {}) {
  const res = await fetch("/api" + path, {
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const body = await res.json();
  if (!res.ok) throw new Error(body.message);
  return body.data;
}
function toast(message, type = "") {
  const el = document.createElement("div");
  el.className = "toast " + type;
  el.textContent = message;
  document.querySelector("#toast-region").append(el);
  setTimeout(() => el.remove(), 3200);
}
function setLoading(rows = 5) {
  app.innerHTML = html`<div class="page">
    <div class="card">${'<div class="skeleton"></div>'.repeat(rows)}</div>
  </div>`;
}
function difficulty(v) {
  return html`<span class="difficulty ${v}">${{ easy: "简单", medium: "中等", hard: "困难" }[v]}</span>`;
}
function verdict(v, status) {
  const value = v || status || "pending";
  return html`<span class="verdict ${esc(value)}">${value}</span>`;
}
async function init() {
  try {
    state.user = await api("/auth/me");
  } catch {
    state.user = null;
  }
  renderChrome();
  addEventListener("hashchange", route);
  route();
}
function renderChrome() {
  const routeName = location.hash.split("/")[1] || "problems";
  const items = state.user ? [["problems", "题库"], ["submissions", "提交记录"], ...( (state.user.role === "admin" || state.user.role === "teacher") ? [["manage", "题目维护"]] : []), ...(state.user.role === "admin" ? [["admin", "管理中心"]] : [] )] : [];
  nav.innerHTML = items.map(([key, label]) => html`<a class="nav-link ${routeName === key ? "active" : ""}" href="#/${key}">${label}</a>`).join("");
  actions.innerHTML = state.user
    ? html`<div class="user-chip">
          <span class="avatar">${esc(state.user.username[0].toUpperCase())}</span><small><b>${esc(state.user.username)}</b><br />${roleName[state.user.role]}</small>
        </div>
        <button class="button ghost" data-action="logout">退出</button>`
    : html`<button class="button ghost auth-label" data-action="login">登录</button><button class="button primary" data-action="register">开始使用</button>`;
}
async function route() {
  renderChrome();
  const parts = (location.hash || "#/problems").slice(2).split("/");
  if (!state.user) return renderWelcome();
  setLoading();
  try {
    if (parts[0] === "problems" && parts[1]) await renderProblem(parts[1]);
    else if (parts[0] === "problems") await renderProblems();
    else if (parts[0] === "submissions" && parts[1]) await renderSubmission(parts[1]);
    else if (parts[0] === "submissions") await renderSubmissions();
    else if (parts[0] === "admin" && state.user.role === "admin") await renderAdmin();
    else if (parts[0] === "manage" && ["teacher", "admin"].includes(state.user.role)) await renderManage();
    else location.hash = "#/problems";
  } catch (e) {
    app.innerHTML = html`<div class="page">
      <div class="card empty">
        <div class="icon">!</div>
        <h2>页面加载失败</h2>
        <p>${esc(e.message)}</p>
        <button class="button" onclick="route()">重新加载</button>
      </div>
    </div>`;
  }
}
function renderWelcome() {
  app.innerHTML = html`<div class="page">
    <section class="hero">
      <div class="hero-stats">
        <div class="hero-stat"><strong>基于FastAPI的轻量化在线OJ系统</strong></div>
      </div>
      <button class="button primary" data-action="register" style="margin-top:28px">创建账号→</button>
    </section>
  </div>`;
}
async function renderProblems() {
  const data = await api("/problems?page=1&page_size=100");
  state.problems = data.items;
  drawProblems();
}
function drawProblems() {
  const list = state.problems.filter((p) => (state.problemFilter === "all" || p.difficulty === state.problemFilter) && `${p.id} ${p.title} ${(p.tags || []).join(" ")}`.toLowerCase().includes(state.problemSearch.toLowerCase()));
  app.innerHTML = html`<div class="page">
    <div class="section-head">
      <div>
        <h2>全部题目</h2>
        <p>按难度筛选，或搜索编号、标题与标签</p>
      </div>
    </div>
    <div class="card toolbar">
      <div class="search">
        <input id="problem-search" value="${esc(state.problemSearch)}" placeholder="搜索题目" />
      </div>
      <div class="filter-group">
        ${[
          ["all", "全部"],
          ["easy", "简单"],
          ["medium", "中等"],
          ["hard", "困难"],
        ]
          .map(([v, l]) => html`<button class="filter ${state.problemFilter === v ? "active" : ""}" data-filter="${v}">${l}</button>`)
          .join("")}
      </div>
    </div>
    <div class="card problem-list">
      ${list.length
        ? list
            .map(
              (p) =>
                html`<a class="problem-row" href="#/problems/${encodeURIComponent(p.id)}"><span class="problem-id">${esc(p.id)}</span>
                  <div>
                    <div class="problem-title">${esc(p.title)}</div>
                    <div class="tags">${(p.tags || []).map((t) => html`<span class="tag">${esc(t)}</span>`).join("")}</div>
                  </div>
                  ${difficulty(p.difficulty)}<span class="meta">${p.time_limit}s · ${p.memory_limit}MB</span></a>`,
            )
            .join("")
        : html`<div class="empty">
            <div class="icon">⌕</div>
            <h3>没有找到匹配的题目</h3>
            <p>换个关键词或难度试试。</p>
          </div>`}
    </div>
  </div>`;
}
async function renderProblem(id) {
  const p = await api("/problems/" + encodeURIComponent(id));
  const saved = localStorage.getItem("draft:" + p.id) || `# ${p.title}\n\n# 在这里编写你的 Python 代码\n`;
  app.innerHTML = html`<div class="page">
    <a class="link" href="#/problems">← 返回题库</a>
    <div class="detail-layout" style="margin-top:16px">
      <article class="card problem-content">
        <header class="problem-header">
          <span class="problem-id">${esc(p.id)}</span>
          <h1>${esc(p.title)}</h1>
          <div class="problem-meta">${difficulty(p.difficulty)}<span class="meta">时间限制 ${p.time_limit}s</span><span class="meta">内存限制 ${p.memory_limit}MB</span>${(p.tags || []).map((t) => html`<span class="tag">${esc(t)}</span>`).join("")}</div>
        </header>
        <div class="prose">
          <h3>题目描述</h3>
          <p>${esc(p.description)}</p>
          <h3>输入格式</h3>
          <p>${esc(p.input_description)}</p>
          <h3>输出格式</h3>
          <p>${esc(p.output_description)}</p>
          ${p.constraints
            ? html`<h3>数据范围</h3>
                <p>${esc(p.constraints)}</p>`
            : ""}
          <h3>样例</h3>
          ${(p.samples || [])
            .map(
              (s, i) =>
                html`<div class="sample">
                  <div class="sample-head"><span>样例 ${i + 1} · 输入</span><button class="button small ghost" data-copy="${esc(s.input)}">复制</button></div>
                  <pre>${esc(s.input)}</pre>
                  <div class="sample-head"><span>输出</span></div>
                  <pre>${esc(s.output)}</pre>
                </div>`,
            )
            .join("")}
        </div>
      </article>
      <aside class="card editor-card">
        <div class="editor-head"><b>代码编辑器</b><span class="tag">Python 3</span></div>
        <textarea id="code-editor" class="editor" spellcheck="false" aria-label="Python 代码"></textarea>
        <div class="editor-foot"><span id="code-size" class="meta"></span><button class="button primary" data-action="submit" data-id="${esc(p.id)}">提交评测</button></div>
      </aside>
    </div>
  </div>`;
  document.querySelector("#code-editor").value = saved;
  updateCodeSize();
}
async function renderSubmissions() {
  const data = await api("/submissions?page=1&page_size=50");
  app.innerHTML = html`<div class="page">
    <div class="section-head">
      <div>
        <span class="eyebrow">Submissions</span>
        <h1>提交记录</h1>
      </div>
    </div>
    <div class="card table-wrap">
      <table class="data-table">
        <thead>
          <tr>
            <th>提交编号</th>
            <th>题目</th>
            <th>状态</th>
            <th>得分</th>
            <th>用时</th>
            <th>提交时间</th>
          </tr>
        </thead>
        <tbody>
          ${data.items.length
            ? data.items
                .map(
                  (s) =>
                    html`<tr>
                      <td>
                        <a class="link mono" href="#/submissions/${s.id}">${esc(s.id.slice(0, 8))}</a>
                      </td>
                      <td>
                        <a class="link" href="#/problems/${encodeURIComponent(s.problem_id)}">${esc(s.problem_id)}</a>
                      </td>
                      <td>${verdict(s.result, s.status)}</td>
                      <td><b>${s.score ?? 0}</b></td>
                      <td>${s.total_time != null ? s.total_time.toFixed(3) + "s" : "—"}</td>
                      <td class="meta">${fmt(s.created_at)}</td>
                    </tr>`,
                )
                .join("")
            : html`<tr>
                <td colspan="6">
                  <div class="empty">还没有提交记录，去题库完成第一道题吧。</div>
                </td>
              </tr>`}
        </tbody>
      </table>
    </div>
  </div>`;
}
async function renderSubmission(id) {
  const [detail, logData] = await Promise.all([api("/submissions/" + id), api("/submissions/" + id + "/logs")]);
  const cases = logData.cases || [];
  app.innerHTML = html`<div class="page">
    <a class="link" href="#/submissions">← 返回提交记录</a>
    <div class="section-head">
      <div>
        <span class="eyebrow">Submission Detail</span>
        <h1>提交 ${esc(id.slice(0, 8))}</h1>
      </div>
      <div class="section-actions">
        ${verdict(detail.result, detail.status)}
        ${["teacher", "admin"].includes(state.user.role) && ["finished", "failed"].includes(detail.status)
          ? html`<button class="button primary" data-action="rejudge" data-id="${esc(detail.id)}">重新评测</button>`
          : ""}
      </div>
    </div>
    <div class="stats-grid">
      <div class="card stat-card">
        <span>题目</span><strong><a class="link" href="#/problems/${detail.problem_id}">${esc(detail.problem_id)}</a></strong>
      </div>
      <div class="card stat-card"><span>得分</span><strong>${detail.score ?? 0}</strong></div>
      <div class="card stat-card"><span>总用时</span><strong>${detail.total_time != null ? detail.total_time.toFixed(3) + "s" : "—"}</strong></div>
      <div class="card stat-card"><span>语言</span><strong>${esc(detail.language)}</strong></div>
    </div>
    <div class="detail-layout">
      <section class="card problem-content">
        <h3>源代码</h3>
        <pre class="codebox">${esc(detail.source_code)}</pre>
      </section>
      <section class="card problem-content">
        <h3>测试点 (${cases.length})</h3>
        <div class="case-grid">
          ${cases.length
            ? cases
                .map(
                  (c) =>
                    html`<div class="case">
                      <div class="case-top">
                        <span><b>${esc(c.case_id)}</b>${verdict(c.result)}</span>
                        ${state.user.role === "student" && c.is_hidden ? "" : html`<button class="button small ghost" data-action="toggle-case">详情</button>`}
                      </div>
                      <div class="meta">得分 ${c.score} · ${c.time_used ?? 0}s${c.message ? " · " + c.message : ""}</div>
                      <div class="case-detail" hidden>
                        <div class="detail-label">输入</div>
                        <pre>${esc(c.input_data)}</pre>
                        <div class="detail-label">预期输出</div>
                        <pre>${esc(c.expected_output)}</pre>
                        <div class="detail-label">实际输出</div>
                        <pre>${esc(c.stdout)}</pre>
                        ${c.stderr ? html`<div class="detail-label">错误信息</div><pre>${esc(c.stderr)}</pre>` : ""}
                      </div>
                    </div>`,
                )
                .join("")
            : '<p class="meta">评测尚未生成测试点记录。</p>'}
        </div>
      </section>
    </div>
  </div>`;
  if (["pending", "running"].includes(detail.status))
    setTimeout(() => {
      if (location.hash.endsWith(id)) renderSubmission(id);
    }, 1800);
}
async function renderManage() {
  const data = await api("/problems?page=1&page_size=100");
  app.innerHTML = html`<div class="page">
    <div class="section-head">
      <div>
        <span class="eyebrow">Teacher Workspace</span>
        <h1>题目维护</h1>
      </div>
      <button class="button primary" data-action="problem-form">＋ 新建题目</button>
    </div>
    <div class="card table-wrap">
      <table class="data-table">
        <thead>
          <tr>
            <th>编号</th>
            <th>标题</th>
            <th>难度</th>
            <th>测试点</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          ${data.items
            .map(
              (p) =>
                html`<tr>
                  <td class="mono">${esc(p.id)}</td>
                  <td>${esc(p.title)}</td>
                  <td>${difficulty(p.difficulty)}</td>
                  <td>${(p.test_cases || []).length}</td>
                  <td>
                    <button class="button small" data-action="problem-form" data-id="${esc(p.id)}">编辑</button>
                    <button class="button small danger" data-action="delete-problem" data-id="${esc(p.id)}">删除</button>
                  </td>
                </tr>`,
            )
            .join("")}
        </tbody>
      </table>
    </div>
  </div>`;
}
async function renderAdmin() {
  const [users, backups] = await Promise.all([api("/users?page=1&page_size=100"), api("/admin/backups")]);
  app.innerHTML = html`<div class="page">
    <div class="section-head">
      <div>
        <span class="eyebrow">Administration</span>
        <h1>管理中心</h1>
      </div>
      <button class="button primary" data-action="backup">创建备份</button>
    </div>
    <div class="stats-grid">
      <div class="card stat-card"><span>学生</span><strong>${users.items.filter((u) => u.role === "student").length}</strong></div>
      <div class="card stat-card"><span>教师</span><strong>${users.items.filter((u) => u.role === "teacher").length}</strong></div>
      <div class="card stat-card"><span>管理员</span><strong>${users.items.filter((u) => u.role === "admin").length}</strong></div>
      <div class="card stat-card"><span>数据备份数</span><strong>${backups.length}</strong></div>
    </div>
    <div class="section-head"><h2>用户管理</h2></div>
    <div class="card table-wrap">
      <table class="data-table">
        <thead>
          <tr>
            <th>用户</th>
            <th>角色</th>
            <th>状态</th>
            <th>注册时间</th>
            <th>管理</th>
          </tr>
        </thead>
        <tbody>
          ${users.items
            .map(
              (u) =>
                html`<tr>
                  <td><b>${esc(u.username)}</b><br /><span class="meta mono">${esc(u.id.slice(0, 8))}</span></td>
                  <td>${roleName[u.role]}</td>
                  <td>${u.is_active ? '<span class="verdict AC">正常</span>' : '<span class="verdict WA">已禁用</span>'}</td>
                  <td class="meta">${fmt(u.created_at)}</td>
                  <td>
                    <button class="button small" data-action="" data-user="">
                      点击设置
                    </button>
                  </td>
                </tr>`,
            )
            .join("")}
        </tbody>
      </table>
    </div>
    <div class="section-head"><h2>最近备份</h2></div>
    <div class="card table-wrap">
      <table class="data-table">
        <thead>
          <tr>
            <th>备份编号</th>
            <th>创建时间</th>
            <th>恢复备份</th>
          </tr>
        </thead>
        <tbody>
          ${backups.length
            ? backups
                .map(
                  (b) =>
                    html`<tr>
                      <td class="mono">${esc(b.id)}</td>
                      <td>${fmt(b.created_at)}</td>
                      <td>
                        <button class="button small" data-action="restore-backup" data-backup="${esc(b.id)}">
                          点击恢复备份
                        </button>
                      </td>
                    </tr>`,
                )
                .join("")
            : '<tr><td colspan="3" class="empty">暂无备份</td></tr>'}
        </tbody>
        
      </table>
    </div>
  </div>`;
}
function openAuth(mode = "login") {
  const isLogin = mode === "login";
  openModal(
    html`<div class="modal-head">
        <div>
          <span class="eyebrow">Light OJ</span>
          <h2>${isLogin ? "欢迎回来" : "创建账号"}</h2>
        </div>
        <button class="close" data-close>×</button>
      </div>
      <form id="auth-form" data-mode="${mode}">
        <div class="field"><label>用户名</label><input name="username" minlength="3" maxlength="32" autocomplete="username" required placeholder="3–32 个字符" /></div>
        <div class="field"><label>密码</label><input type="password" name="password" minlength="8" autocomplete="${isLogin ? "current-password" : "new-password"}" required placeholder="至少 8 个字符" /></div>
        <button class="button primary" style="width:100%;margin-top:6px">${isLogin ? "登录" : "注册并登录"}</button>
      </form>
      <div class="auth-switch">${isLogin ? '还没有账号？<a class="link" href="#" data-auth-switch="register">立即注册</a>' : '已有账号？<a class="link" href="#" data-auth-switch="login">直接登录</a>'}</div>`,
  );
}
function openModal(content, wide = false) {
  document.querySelector("#modal-root").innerHTML = html`<div class="modal-backdrop">
    <div class="modal ${wide ? "wide" : ""}" role="dialog" aria-modal="true">${content}</div>
  </div>`;
  document.querySelector(".modal input, .modal textarea, .modal button")?.focus();
}
function closeModal() {
  document.querySelector("#modal-root").innerHTML = "";
}
async function openProblemForm(id) {
  let p = id
    ? await api("/problems/" + id)
    : {
        id: "",
        title: "",
        description: "",
        input_description: "",
        output_description: "",
        constraints: "",
        time_limit: 1,
        memory_limit: 128,
        difficulty: "easy",
        tags: [],
        samples: [{ input: "", output: "" }],
        test_cases: [
          {
            case_id: "case_01",
            input: "",
            output: "",
            score: 100,
            is_hidden: true,
          },
        ],
      };
  openModal(
    html`<div class="modal-head">
        <h2>${id ? "编辑题目" : "新建题目"}</h2>
        <button class="close" data-close>×</button>
      </div>
      <form id="problem-form" data-original="${esc(id || "")}">
        <div class="form-row">
          <div class="field"><label>题目编号</label><input name="id" value="${esc(p.id)}" ${id ? "readonly" : ""} required /></div>
          <div class="field"><label>标题</label><input name="title" value="${esc(p.title)}" required /></div>
        </div>
        <div class="field"><label>题目描述</label><textarea name="description" required></textarea></div>
        <div class="form-row">
          <div class="field"><label>输入格式</label><textarea name="input_description" required></textarea></div>
          <div class="field"><label>输出格式</label><textarea name="output_description" required></textarea></div>
        </div>
        <div class="field"><label>数据范围</label><input name="constraints" value="${esc(p.constraints)}" /></div>
        <div class="form-row">
          <div class="field">
            <label>难度</label><select name="difficulty">
              <option value="easy" ${p.difficulty === "easy" ? "selected" : ""}>简单</option>
              <option value="medium" ${p.difficulty === "medium" ? "selected" : ""}>中等</option>
              <option value="hard" ${p.difficulty === "hard" ? "selected" : ""}>困难</option>
            </select>
          </div>
          <div class="field"><label>标签（逗号分隔）</label><input name="tags" value="${esc((p.tags || []).join(", "))}" /></div>
        </div>
        <div class="form-row">
          <div class="field"><label>时间限制（秒）</label><input type="number" step="0.1" min="0.1" name="time_limit" value="${p.time_limit}" required /></div>
          <div class="field"><label>内存限制（MB）</label><input type="number" min="1" name="memory_limit" value="${p.memory_limit}" required /></div>
        </div>
        <div class="field"><label>样例（JSON 数组）</label><textarea name="samples" class="mono" required></textarea></div>
        <div class="field"><label>测试点（JSON 数组，分数总和必须为 100）</label><textarea name="test_cases" class="mono" style="min-height:180px" required></textarea></div>
        <div class="modal-actions"><button type="button" class="button" data-close>取消</button><button class="button primary">保存题目</button></div>
      </form>`,
    true,
  );
  const form = document.querySelector("#problem-form");
  form.elements.description.value = p.description;
  form.elements.input_description.value = p.input_description;
  form.elements.output_description.value = p.output_description;
  form.elements.samples.value = JSON.stringify(p.samples, null, 2);
  form.elements.test_cases.value = JSON.stringify(p.test_cases, null, 2);
}
function updateCodeSize() {
  const ed = document.querySelector("#code-editor"),
    out = document.querySelector("#code-size");
  if (ed && out) out.textContent = new Blob([ed.value]).size + " B / 64 KB";
}
document.addEventListener("input", (e) => {
  if (e.target.id === "problem-search") {
    state.problemSearch = e.target.value;
    drawProblems();
    e.target.focus();
  }
  if (e.target.id === "code-editor") {
    localStorage.setItem("draft:" + location.hash.split("/").pop(), e.target.value);
    updateCodeSize();
  }
});
document.addEventListener("click", async (e) => {
  const el = e.target.closest("[data-action],[data-filter],[data-close],[data-auth-switch],[data-copy]");
  if (!el) return;
  if (el.dataset.close !== undefined || (el.classList.contains("modal-backdrop") && e.target === el)) return closeModal();
  if (el.dataset.authSwitch) {
    e.preventDefault();
    return openAuth(el.dataset.authSwitch);
  }
  if (el.dataset.filter) {
    state.problemFilter = el.dataset.filter;
    return drawProblems();
  }
  if (el.dataset.copy !== undefined) {
    await navigator.clipboard.writeText(el.dataset.copy);
    return toast("样例已复制");
  }
  const action = el.dataset.action;
  try {
    if (action === "toggle-case") {
      const detail = el.closest(".case").querySelector(".case-detail");
      const open = detail.hasAttribute("hidden");
      detail.toggleAttribute("hidden");
      el.textContent = open ? "收起" : "详情";
      return;
    }
    if (action === "login" || action === "register") openAuth(action);
    if (action === "logout") {
      await api("/auth/logout", { method: "POST" });
      state.user = null;
      location.hash = "";
      renderChrome();
      renderWelcome();
      toast("已安全退出");
    }
    if (action === "submit") {
      const code = document.querySelector("#code-editor").value;
      if (!code.trim()) throw new Error("代码不能为空");
      el.disabled = true;
      el.textContent = "正在提交…";
      const data = await api("/submissions", {
        method: "POST",
        body: JSON.stringify({
          problem_id: el.dataset.id,
          language: "python",
          source_code: code,
        }),
      });
      toast("提交成功，正在评测");
      location.hash = "#/submissions/" + data.submission_id;
    }
    if (action === "problem-form") await openProblemForm(el.dataset.id);
    if (action === "rejudge") {
      el.disabled = true;
      el.textContent = "提交中…";
      await api(`/submissions/${encodeURIComponent(el.dataset.id)}/rejudge`, { method: "POST" });
      toast("已进入重评队列");
      renderSubmission(el.dataset.id);
    }
    if (action === "delete-problem") {
      if (confirm(`确定删除题目 ${el.dataset.id}？此操作不可撤销。`)) {
        await api("/problems/" + el.dataset.id, { method: "DELETE" });
        toast("题目已删除");
        renderManage();
      }
    }
    if (action === "backup") {
      el.disabled = true;
      await api("/admin/backups", { method: "POST" });
      toast("备份创建成功");
      renderAdmin();
    }
    if (action === "restore-backup") {
      const backupId = el.dataset.backup;
      if (!confirm(`确定恢复备份 ${backupId}？当前数据库将被覆盖，且需要重新登录。`)) return;
      el.disabled = true;
      el.textContent = "正在恢复…";
      await api(`/admin/backups/${encodeURIComponent(backupId)}/restore`, { method: "POST" });
      toast("备份已恢复，请重新登录");
      state.user = null;
      location.hash = "";
      renderChrome();
      renderWelcome();
    }
    if (action === "edit-user") {
      const u = JSON.parse(el.dataset.user);
      openModal(
        html`<div class="modal-head">
            <h2>设置用户 · ${esc(u.username)}</h2>
            <button class="close" data-close>×</button>
          </div>
          <form id="user-form" data-id="${u.id}">
            <div class="field">
              <label>角色</label><select name="role">
                <option value="student" ${u.role === "student" ? "selected" : ""}>学生</option>
                <option value="teacher" ${u.role === "teacher" ? "selected" : ""}>教师</option>
                <option value="admin" ${u.role === "admin" ? "selected" : ""}>管理员</option>
              </select>
            </div>
            <div class="field">
              <label><input type="checkbox" name="is_active" ${u.is_active ? "checked" : ""} style="width:auto" /> 账号启用</label>
            </div>
            <div class="modal-actions"><button type="button" class="button" data-close>取消</button><button class="button primary">保存设置</button></div>
          </form>`,
      );
    }
  } catch (err) {
    toast(err.message, "error");
    el.disabled = false;
  }
});
document.addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.target,
    button = form.querySelector("[type=submit],button:not([type])");
  if (button) button.disabled = true;
  try {
    if (form.id === "auth-form") {
      const values = Object.fromEntries(new FormData(form));
      if (form.dataset.mode === "register")
        await api("/auth/register", {
          method: "POST",
          body: JSON.stringify(values),
        });
      state.user = await api("/auth/login", {
        method: "POST",
        body: JSON.stringify(values),
      });
      closeModal();
      renderChrome();
      location.hash = "#/problems";
      toast(form.dataset.mode === "register" ? "注册成功，欢迎加入" : "登录成功");
    }
    if (form.id === "problem-form") {
      const v = Object.fromEntries(new FormData(form));
      let samples, test_cases;
      try {
        samples = JSON.parse(v.samples);
        test_cases = JSON.parse(v.test_cases);
      } catch {
        throw new Error("样例或测试点不是有效的 JSON");
      }
      const body = {
        ...v,
        time_limit: Number(v.time_limit),
        memory_limit: Number(v.memory_limit),
        tags: v.tags
          .split(/[,，]/)
          .map((x) => x.trim())
          .filter(Boolean),
        samples,
        test_cases,
      };
      const original = form.dataset.original;
      await api("/problems" + (original ? "/" + encodeURIComponent(original) : ""), { method: original ? "PUT" : "POST", body: JSON.stringify(body) });
      closeModal();
      toast("题目已保存");
      renderManage();
    }
    if (form.id === "user-form") {
      const fd = new FormData(form);
      await api("/users/" + form.dataset.id, {
        method: "PUT",
        body: JSON.stringify({
          role: fd.get("role"),
          is_active: fd.has("is_active"),
        }),
      });
      closeModal();
      toast("用户设置已更新");
      renderAdmin();
    }
  } catch (err) {
    toast(err.message, "error");
    if (button) button.disabled = false;
  }
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeModal();
  if (e.target.id === "code-editor" && e.key === "Tab") {
    e.preventDefault();
    const t = e.target,
      s = t.selectionStart;
    t.value = t.value.slice(0, s) + "    " + t.value.slice(t.selectionEnd);
    t.selectionStart = t.selectionEnd = s + 4;
    t.dispatchEvent(new Event("input", { bubbles: true }));
  }
});
init();
