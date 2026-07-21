/* ═══════════════════════════════════════════════════
   求职投递管理后台 — 前端逻辑
   ═══════════════════════════════════════════════════ */

let currentTab = "pending";
let currentJobId = null;
let jobsCache = [];

// ── API 调用 ──────────────────────────────────────────
async function api(method, path, body) {
    const opts = { method, headers: {} };
    if (body !== undefined) {
        opts.headers["Content-Type"] = "application/json";
        opts.body = JSON.stringify(body);
    }
    const res = await fetch(path, opts);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "请求失败");
    return data;
}

// ── Tab 切换 ──────────────────────────────────────────
document.querySelectorAll(".tab").forEach(tab => {
    tab.addEventListener("click", () => switchTab(tab.dataset.tab));
});

function switchTab(tab) {
    currentTab = tab;
    document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
    document.querySelector(`.tab[data-tab="${tab}"]`).classList.add("active");

    document.querySelectorAll(".view").forEach(v => v.classList.remove("active"));

    if (tab === "replies") {
        document.getElementById("view-replies").classList.add("active");
        loadReplies();
    } else if (tab === "settings") {
        document.getElementById("view-settings").classList.add("active");
        loadSettings();
    } else {
        document.getElementById("view-list").classList.add("active");
        const titles = { pending: "待发送任务", sent: "已发送任务" };
        document.getElementById("list-title").textContent = titles[tab] || "投递任务";
        loadJobs();
    }
}

// ── 加载任务列表 ──────────────────────────────────────
async function loadJobs() {
    try {
        const status = currentTab === "sent" ? "sent" : "pending";
        jobsCache = await api("GET", `/api/jobs?status=${status}`);
        renderJobList();
        updateBadges();
    } catch (e) {
        showToast(e.message, "error");
    }
}

function renderJobList() {
    const container = document.getElementById("job-list");
    const countEl = document.getElementById("list-count");

    if (jobsCache.length === 0) {
        container.innerHTML = '<div class="empty-state">暂无数据</div>';
        countEl.textContent = "";
        return;
    }

    countEl.textContent = `${jobsCache.length} 条`;
    container.innerHTML = jobsCache.map(job => `
        <div class="job-card ${job.id === currentJobId ? "active" : ""}"
             onclick="selectJob(${job.id})">
            <div class="job-card-top">
                <div>
                    <div class="job-card-company">${esc(job.company)}</div>
                    <div class="job-card-position">${esc(job.position)}</div>
                </div>
                <span class="tag tag-${job.status}">${statusText(job.status)}</span>
            </div>
            <div class="job-card-meta">
                ${job.location ? `<span>📍 ${esc(job.location)}</span>` : ""}
                ${job.match_score ? `<span class="stars">${"★".repeat(job.match_score)}${"☆".repeat(5 - job.match_score)}</span>` : ""}
                ${job.receiver_email ? `<span>✉️ ${esc(job.receiver_email)}</span>` : ""}
            </div>
        </div>
    `).join("");
}

function statusText(s) {
    return { pending: "待发送", sent: "已发送", failed: "失败", skipped: "已跳过" }[s] || s;
}

// ── 选中任务 → 显示详情 ────────────────────────────────
function selectJob(id) {
    currentJobId = id;
    renderJobList();
    const job = jobsCache.find(j => j.id === id);
    if (job) renderDetail(job);
}

function renderDetail(job) {
    const panel = document.getElementById("detail-panel");
    const isPending = job.status === "pending";
    const isFailed = job.status === "failed";

    panel.innerHTML = `
    <div class="detail-content">
        <div class="detail-header">
            <div class="detail-title">
                <h2>${esc(job.company)}</h2>
                <div class="subtitle">${esc(job.position)} ${job.location ? "· " + esc(job.location) : ""}</div>
            </div>
            <div class="detail-actions">
                ${isPending ? `
                    <button class="btn btn-outline btn-sm" onclick="skipJob(${job.id})">跳过</button>
                    <button class="btn btn-red btn-sm" onclick="deleteJob(${job.id})">删除</button>
                    <button class="btn btn-green btn-sm" onclick="sendJob(${job.id})">📤 一键发送</button>
                ` : ""}
                ${isFailed ? `
                    <button class="btn btn-green btn-sm" onclick="sendJob(${job.id})">🔁 重新发送</button>
                ` : ""}
            </div>
        </div>

        ${job.error_message ? `
            <div class="detail-section">
                <div style="background:var(--red-bg);color:var(--red);padding:10px 14px;border-radius:8px;font-size:13px;">
                    ⚠️ ${esc(job.error_message)}
                </div>
            </div>
        ` : ""}

        <div class="detail-section">
            <h3>基本信息</h3>
            <div class="detail-info-grid">
                <div class="info-item">
                    <label>收件邮箱</label>
                    <div class="value ${isPending ? "editable" : ""}" contenteditable="${isPending}"
                         field="receiver_email">${esc(job.receiver_email || "（待填写）")}</div>
                </div>
                <div class="info-item">
                    <label>邮件主题</label>
                    <div class="value ${isPending ? "editable" : ""}" contenteditable="${isPending}"
                         field="subject">${esc(job.subject || "（待填写）")}</div>
                </div>
                <div class="info-item">
                    <label>简历版本</label>
                    <div class="value">${job.resume_version === "en" ? "英文 resume_en.pdf" : "中文 resume_zh.pdf"}</div>
                </div>
                <div class="info-item">
                    <label>匹配度</label>
                    <div class="value"><span class="stars">${"★".repeat(job.match_score)}${"☆".repeat(5 - job.match_score)}</span></div>
                </div>
                <div class="info-item">
                    <label>来源公众号</label>
                    <div class="value">${esc(job.source_mp || "-")}</div>
                </div>
                <div class="info-item">
                    <label>创建时间</label>
                    <div class="value">${esc(job.created_at || "-")}</div>
                </div>
                ${job.sent_at ? `
                <div class="info-item">
                    <label>发送时间</label>
                    <div class="value">${esc(job.sent_at)}</div>
                </div>` : ""}
            </div>
        </div>

        ${isPending ? `
        <div class="detail-section">
            <button class="btn btn-outline btn-sm" onclick="saveEdits(${job.id})" style="margin-bottom:10px;">
                💾 保存修改
            </button>
        </div>` : ""}

        ${job.jd_detail ? `
        <div class="detail-section">
            <h3>JOB DESCRIPTION</h3>
            <div class="jd-detail">${esc(job.jd_detail)}</div>
        </div>` : ""}

        ${job.requirements ? `
        <div class="detail-section">
            <h3>任职要求</h3>
            <div class="jd-detail">${esc(job.requirements)}</div>
        </div>` : ""}

        <div class="detail-section">
            <h3>${isPending ? "Cover Letter（可编辑）" : "Cover Letter"}</h3>
            ${isPending
                ? `<textarea class="cover-letter-editor" id="cover-letter-text" onblur="saveCoverLetter(${job.id})">${esc(job.cover_letter || "")}</textarea>`
                : `<div class="jd-detail">${esc(job.cover_letter || "（无）")}</div>`
            }
        </div>

        ${job.source_url ? `
        <div class="detail-section">
            <h3>来源链接</h3>
            <a href="${esc(job.source_url)}" target="_blank" style="color:var(--primary);font-size:13px;">${esc(job.source_url)}</a>
        </div>` : ""}
    </div>`;
}

// ── 保存编辑 ──────────────────────────────────────────
async function saveEdits(id) {
    const edits = {};
    document.querySelectorAll(".value.editable[contenteditable='true']").forEach(el => {
        const field = el.getAttribute("field");
        if (field) edits[field] = el.textContent.trim();
    });
    const clEl = document.getElementById("cover-letter-text");
    if (clEl) edits["cover_letter"] = clEl.value;

    if (Object.keys(edits).length === 0) {
        showToast("没有修改", "error");
        return;
    }
    try {
        await api("PUT", `/api/jobs/${id}`, edits);
        showToast("已保存", "success");
        await loadJobs();
    } catch (e) {
        showToast(e.message, "error");
    }
}

async function saveCoverLetter(id) {
    const el = document.getElementById("cover-letter-text");
    if (!el) return;
    // 静默保存，不弹 toast（用户失焦时触发）
    try {
        await api("PUT", `/api/jobs/${id}`, { cover_letter: el.value });
    } catch (e) { /* 静默失败 */ }
}

// ── 发送邮件 ──────────────────────────────────────────
async function sendJob(id) {
    const job = jobsCache.find(j => j.id === id);
    if (!job) return;

    // 先保存编辑内容
    const edits = {};
    document.querySelectorAll(".value.editable[contenteditable='true']").forEach(el => {
        const field = el.getAttribute("field");
        if (field) edits[field] = el.textContent.trim();
    });
    const clEl = document.getElementById("cover-letter-text");
    if (clEl) edits["cover_letter"] = clEl.value;
    if (Object.keys(edits).length > 0) {
        try { await api("PUT", `/api/jobs/${id}`, edits); } catch (e) {}
    }

    // 确认
    const confirmMsg = `确认发送邮件？\n\n收件人: ${job.receiver_email}\n主题: ${job.subject}\n公司: ${job.company}`;
    if (!confirm(confirmMsg)) return;

    showToast("正在发送...", "");
    try {
        const result = await api("POST", `/api/jobs/${id}/send`);
        showToast("✅ " + result.message, "success");
        currentJobId = null;
        await loadJobs();
        document.getElementById("detail-panel").innerHTML = `
            <div class="empty-state detail-empty">
                <div class="empty-icon">✅</div>
                <p>邮件已成功发送</p>
            </div>`;
    } catch (e) {
        showToast("❌ " + e.message, "error");
        await loadJobs();
    }
}

// ── 跳过 / 删除 ───────────────────────────────────────
async function skipJob(id) {
    try {
        await api("POST", `/api/jobs/${id}/skip`);
        showToast("已跳过", "success");
        currentJobId = null;
        await loadJobs();
    } catch (e) { showToast(e.message, "error"); }
}

async function deleteJob(id) {
    if (!confirm("确定删除此投递任务？")) return;
    try {
        await api("DELETE", `/api/jobs/${id}`);
        showToast("已删除", "success");
        currentJobId = null;
        await loadJobs();
    } catch (e) { showToast(e.message, "error"); }
}

// ── 收件箱回复 ────────────────────────────────────────
async function loadReplies() {
    const container = document.getElementById("replies-list");
    container.innerHTML = '<div class="empty-state">加载中...</div>';
    try {
        const data = await api("GET", "/api/replies");
        const replies = data.replies || [];
        if (replies.length === 0) {
            container.innerHTML = '<div class="empty-state">暂无回复数据</div>';
            return;
        }
        container.innerHTML = replies.map(r => `
            <div class="reply-card ${r.is_interview ? "interview" : ""}">
                <div class="reply-top">
                    <div class="reply-subject">${esc(r.subject)}</div>
                    ${r.is_interview ? '<span class="interview-tag">面试邀请</span>' : ""}
                </div>
                <div class="reply-from">From: ${esc(r.from)}</div>
                <div class="reply-body">${esc(r.body_preview || "")}</div>
                <div class="reply-date" style="margin-top:6px;">${esc(r.date || "")}</div>
            </div>
        `).join("");
    } catch (e) {
        container.innerHTML = `<div class="empty-state">${esc(e.message)}</div>`;
    }
}

// ── 统计 / Badge ──────────────────────────────────────
async function updateBadges() {
    try {
        const s = await api("GET", "/api/stats");
        document.getElementById("badge-pending").textContent = s.pending;
        document.getElementById("badge-sent").textContent = s.sent;
    } catch (e) {}
}

// ── 工具函数 ──────────────────────────────────────────
function esc(str) {
    if (str === null || str === undefined) return "";
    const div = document.createElement("div");
    div.textContent = String(str);
    return div.innerHTML;
}

let toastTimer;
function showToast(msg, type) {
    const t = document.getElementById("toast");
    t.textContent = msg;
    t.className = "toast show " + (type || "");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => t.classList.remove("show"), 3000);
}

async function refreshData() {
    if (currentTab === "replies") {
        await loadReplies();
    } else {
        await loadJobs();
    }
    showToast("已刷新", "success");
}

// ── 初始化 ────────────────────────────────────────────
loadJobs();
// 每30秒自动刷新 badge
setInterval(updateBadges, 30000);

// ══════════════════════════════════════════════════════════
//  设置管理
// ══════════════════════════════════════════════════════════

let providersCache = null;

async function loadProviders() {
    if (!providersCache) {
        try {
            providersCache = await api("GET", "/api/providers");
        } catch (e) {
            providersCache = {};
        }
    }
    return providersCache;
}

async function loadSettings() {
    try {
        const [settings, providers] = await Promise.all([
            api("GET", "/api/settings"),
            loadProviders(),
        ]);

        // LLM 配置
        document.getElementById("set-llm-provider").value = settings.llm_provider || "deepseek";
        await onProviderChange(); // 填充模型列表
        if (settings.llm_model) {
            const modelSelect = document.getElementById("set-llm-model");
            if ([...modelSelect.options].some(o => o.value === settings.llm_model)) {
                modelSelect.value = settings.llm_model;
            }
        }
        document.getElementById("set-llm-api-key").placeholder =
            settings.llm_api_key_set ? "已配置（输入新值可替换）" : "sk-...";

        // we-mp-rss 配置
        document.getElementById("set-werss-url").value = settings.we_mp_rss_url || "";
        document.getElementById("set-werss-user").value = settings.we_mp_rss_user || "";
        document.getElementById("set-werss-pass").value = settings.we_mp_rss_pass || "";

        // 用户信息
        document.getElementById("set-user-name").value = settings.user_name || "";
        document.getElementById("set-user-education").value = settings.user_education || "";
        document.getElementById("set-job-pref").value = settings.job_preferences || "";
        document.getElementById("set-excluded").value = settings.excluded || "";
        document.getElementById("set-work-location").value = settings.work_location || "";
        document.getElementById("set-available-time").value = settings.available_time || "";
        document.getElementById("set-email-subject").value = settings.email_subject_format || "";
    } catch (e) {
        showToast("加载设置失败: " + e.message, "error");
    }
}

async function onProviderChange() {
    const provider = document.getElementById("set-llm-provider").value;
    const providers = await loadProviders();
    const modelSelect = document.getElementById("set-llm-model");
    const models = (providers[provider] || {}).models || [];
    modelSelect.innerHTML = models.map(m => `<option value="${m}">${m}</option>`).join("");
}

async function saveSettings() {
    const data = {
        llm_provider: document.getElementById("set-llm-provider").value,
        llm_model: document.getElementById("set-llm-model").value,
        we_mp_rss_url: document.getElementById("set-werss-url").value,
        we_mp_rss_user: document.getElementById("set-werss-user").value,
        we_mp_rss_pass: document.getElementById("set-werss-pass").value,
        user_name: document.getElementById("set-user-name").value,
        user_education: document.getElementById("set-user-education").value,
        job_preferences: document.getElementById("set-job-pref").value,
        excluded: document.getElementById("set-excluded").value,
        work_location: document.getElementById("set-work-location").value,
        available_time: document.getElementById("set-available-time").value,
        email_subject_format: document.getElementById("set-email-subject").value,
    };
    const apiKey = document.getElementById("set-llm-api-key").value;
    if (apiKey) data.llm_api_key = apiKey;

    try {
        await api("POST", "/api/settings", data);
        showToast("✅ 设置已保存", "success");
    } catch (e) {
        showToast("保存失败: " + e.message, "error");
    }
}

async function testLLM() {
    // 先保存再测试
    await saveSettings();
    showToast("正在测试we-mp-rss连接...", "");
    try {
        const result = await api("POST", "/api/articles/refresh", { limit: 1, analyze: false });
        if (result.message) {
            // 等待后台拉取完成
            await new Promise(r => setTimeout(r, 3000));
            const p = await api("GET", "/api/articles/progress");
            if (p.phase === "done") {
                showToast(`✅ 连接正常，拉取到 ${p.total} 篇文章`, "success");
            } else if (p.phase === "error") {
                showToast("❌ " + p.message, "error");
            } else {
                showToast("✅ 请求已发送，请查看刷新结果", "success");
            }
        }
    } catch (e) {
        showToast("❌ " + e.message, "error");
    }
}

// ══════════════════════════════════════════════════════════
//  文章刷新（拉取 + LLM 分析）
// ══════════════════════════════════════════════════════════

async function refreshArticles() {
    const limit = parseInt(document.getElementById("set-article-limit")?.value) || 10;
    if (!confirm(`确认从公众号拉取最新 ${limit} 篇文章并用AI分析？\n（已投递的文章会自动跳过）`)) return;

    // 禁用刷新按钮防止重复点击
    const btn = event?.target;
    if (btn) { btn.disabled = true; btn.classList.add("btn-loading"); }

    // 显示进度弹窗
    showProgress("🔄 正在刷新文章", "正在连接公众号RSS...", 0, 0);

    try {
        // 发起刷新请求（非阻塞，后台线程处理）
        await api("POST", "/api/articles/refresh", { limit, analyze: true });
        // 开始轮询进度
        pollProgress();
    } catch (e) {
        hideProgress();
        showToast("❌ " + e.message, "error");
        if (btn) { btn.disabled = false; btn.classList.remove("btn-loading"); }
    }
}

let _progressTimer = null;

async function pollProgress() {
    try {
        const p = await api("GET", "/api/articles/progress");

        const percent = p.total > 0 ? Math.round((p.current / p.total) * 100) : 0;
        const phaseText = {
            fetching: "📡 拉取文章中",
            analyzing: "🤖 AI分析中",
            done: "✅ 完成",
            error: "❌ 出错",
            idle: "⏳ 准备中",
        }[p.phase] || p.phase;

        showProgress(phaseText, p.message || p.current_title || "", p.current, p.total, percent);

        // 更新统计徽章
        const badges = [];
        if (p.created > 0) badges.push(`<span class="pbadge pbadge-green">+${p.created} 新任务</span>`);
        if (p.skipped > 0) badges.push(`<span class="pbadge pbadge-gray">${p.skipped} 跳过</span>`);
        if (p.errors.length > 0) badges.push(`<span class="pbadge pbadge-red">${p.errors.length} 失败</span>`);
        document.getElementById("progress-badges").innerHTML = badges.join(" ");

        if (p.phase === "done" || p.phase === "error") {
            // 完成
            clearInterval(_progressTimer);
            _progressTimer = null;

            if (p.phase === "done") {
                showToast("✅ " + p.message, "success");
            } else {
                showToast("❌ " + p.message, "error");
            }

            // 更新进度弹窗为完成状态
            const overlay = document.getElementById("progress-overlay");
            document.getElementById("progress-title").textContent = p.phase === "done" ? "刷新完成" : "刷新失败";
            document.getElementById("progress-icon").textContent = p.phase === "done" ? "✅" : "❌";
            // 添加关闭按钮
            if (!document.getElementById("progress-close-btn")) {
                const modal = overlay.querySelector(".progress-modal");
                const closeBtn = document.createElement("button");
                closeBtn.id = "progress-close-btn";
                closeBtn.className = "btn btn-green progress-close-btn";
                closeBtn.textContent = "关闭";
                closeBtn.onclick = () => {
                    hideProgress();
                    // 重新启用刷新按钮
                    const refreshBtn = document.querySelector('.topbar-right .btn:last-child');
                    if (refreshBtn) { refreshBtn.disabled = false; refreshBtn.classList.remove("btn-loading"); }
                };
                modal.appendChild(closeBtn);
            }

            // 刷新任务列表
            await loadJobs();
            updateBadges();
        } else {
            // 继续轮询
            if (!_progressTimer) {
                _progressTimer = setInterval(pollProgress, 1500);
            }
        }
    } catch (e) {
        clearInterval(_progressTimer);
        _progressTimer = null;
        hideProgress();
        showToast("❌ 进度查询失败: " + e.message, "error");
    }
}

function showProgress(title, subtitle, current, total, percent) {
    const overlay = document.getElementById("progress-overlay");
    overlay.classList.add("show");

    document.getElementById("progress-title").textContent = title;
    document.getElementById("progress-subtitle").textContent = subtitle;

    const pct = percent !== undefined ? percent : (total > 0 ? Math.round((current / total) * 100) : 0);
    document.getElementById("progress-bar").style.width = pct + "%";
    document.getElementById("progress-count").textContent = `${current} / ${total}`;
    document.getElementById("progress-percent").textContent = pct + "%";

    // 详情区
    const detail = document.getElementById("progress-detail");
    if (current > 0 && total > 0) {
        detail.textContent = `正在处理: ${subtitle}`;
    } else if (total === 0) {
        detail.textContent = "";
    }
}

function hideProgress() {
    document.getElementById("progress-overlay").classList.remove("show");
    // 清除关闭按钮
    const closeBtn = document.getElementById("progress-close-btn");
    if (closeBtn) closeBtn.remove();
}
