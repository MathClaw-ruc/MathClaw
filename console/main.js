const NAV_GROUPS = [
  {
    label: "学生工作台",
    items: [
      { id: "chat", icon: "◻", tone: "brand", label: "解题工作台", hint: "AI 对话与工具轨迹" },
      { id: "cron-jobs", icon: "◷", tone: "amber", label: "学习计划", hint: "定时任务与提醒" },
      { id: "status", icon: "∿", tone: "violet", label: "运行状态", hint: "健康检查与依赖" },
      { id: "memory", icon: "◎", tone: "green", label: "记忆", hint: "知识点与错题图谱" },
    ],
  },
  {
    label: "系统控制台",
    items: [
      { id: "channels", icon: "◉", tone: "blue", label: "频道", hint: "多通道连接" },
      { id: "heartbeat", icon: "♡", tone: "danger", label: "心跳", hint: "检查与提醒" },
      { id: "skills", icon: "✣", tone: "brand", label: "Skills", hint: "Skill 生命周期" },
      { id: "mcp", icon: "⌘", tone: "teal", label: "MCP", hint: "MCP 工具连接" },
      { id: "agent-config", icon: "⚙", tone: "violet", label: "Agent 配置", hint: "提示词与策略" },
      { id: "models", icon: "▣", tone: "blue", label: "模型配置", hint: "模型与提供商" },
    ],
  },
];

const PAGE_META = {
  chat: {
    title: "解题工作台",
    description: "拍题、提问、批改与引导讲解都在这里完成。",
  },
  "cron-jobs": {
    title: "学习计划",
    description: "根据每日总结、每周计划和图谱重点，给出更清楚的学习节奏。",
  },
  status: {
    title: "运行状态",
    description: "只给管理员看的系统稳定性概览。",
  },
  channels: {
    title: "频道",
    description: "查看企业微信、QQ、飞书和前端工作台的连接与活跃情况。",
  },
  heartbeat: {
    title: "心跳",
    description: "查看每日总结、每周总结和定时任务是否正常执行。",
  },
  memory: {
    title: "知识图谱",
    description: "",
  },
  skills: {
    title: "Skills",
    description: "管理附件回复后的额外输出风格。",
  },
  mcp: {
    title: "Tools",
    description: "只读查看当前可用的搜索、文档理解、图片解析与记忆工具。",
  },
  "agent-config": {
    title: "Agent 配置",
    description: "只读查看当前推理和工作区配置。",
  },
  models: {
    title: "模型配置",
    description: "只展示当前使用中的模型链路，不显示密钥。",
  },
};

const GRAPH_STAGE = { width: 1400, height: 820 };

const GRAPH_SEED = {
  knowledge: {
    title: "知识点图",
    file: "memory/graphs/knowledge_graph.json",
    accent: "knowledge",
    legend: ["前置知识点", "相似知识点", "包含关系", "相关联知识点"],
    nodes: [
      {
        id: "kp-monotonic",
        label: "函数单调性",
        badge: "风险 0.86",
        size: 132,
        x: 680,
        y: 370,
        summary: "参数题和复合函数场景最不稳定，判断路径经常跳步。",
        metrics: [
          ["风险度", "0.86"],
          ["掌握度", "0.34"],
          ["重要度", "0.92"],
          ["最近出现", "03-29"],
        ],
        highlights: ["定义域检查经常滞后", "单调区间和导数符号没有联动思考"],
        examples: ["求导后直接下结论，漏了定义域限制", "参数区间变化时没有重新检查增减性"],
      },
      {
        id: "kp-derivative",
        label: "导数符号",
        badge: "前置",
        size: 96,
        x: 370,
        y: 270,
        summary: "前置知识点稳定性不足时，单调性判断会连续失真。",
        metrics: [
          ["风险度", "0.61"],
          ["掌握度", "0.53"],
          ["重要度", "0.76"],
          ["最近出现", "03-28"],
        ],
        highlights: ["正负号表容易漏掉区间切分"],
        examples: ["只看导数结果，没有配合区间表确认"],
      },
      {
        id: "kp-parity",
        label: "奇偶性判断",
        badge: "相似",
        size: 104,
        x: 980,
        y: 260,
        summary: "和单调性一起出现时，容易混淆对称性与定义域的先后顺序。",
        metrics: [
          ["风险度", "0.73"],
          ["掌握度", "0.48"],
          ["重要度", "0.72"],
          ["最近出现", "03-29"],
        ],
        highlights: ["先套模板，后补定义域"],
        examples: ["f(-x) 变形时忽略根式范围"],
      },
      {
        id: "kp-domain",
        label: "定义域约束",
        badge: "关联",
        size: 90,
        x: 940,
        y: 520,
        summary: "一旦定义域同步失败，高风险知识点会成片失真。",
        metrics: [
          ["风险度", "0.58"],
          ["掌握度", "0.46"],
          ["重要度", "0.74"],
          ["最近出现", "03-27"],
        ],
        highlights: ["习惯在最后才回头看定义域"],
        examples: ["根式函数直接讨论单调性"],
      },
      {
        id: "kp-interval",
        label: "单调区间",
        badge: "包含",
        size: 84,
        x: 1110,
        y: 390,
        summary: "结论层节点，常受前置链条波动影响。",
        metrics: [
          ["风险度", "0.63"],
          ["掌握度", "0.41"],
          ["重要度", "0.66"],
          ["最近出现", "03-29"],
        ],
        highlights: ["端点处理最容易丢失"],
        examples: ["开闭区间没有和定义域同步"],
      },
      {
        id: "kp-composite",
        label: "复合函数单调",
        badge: "扩展",
        size: 100,
        x: 500,
        y: 570,
        summary: "复合结构下，局部规则能记住，但组合顺序不稳定。",
        metrics: [
          ["风险度", "0.67"],
          ["掌握度", "0.39"],
          ["重要度", "0.81"],
          ["最近出现", "03-26"],
        ],
        highlights: ["内外层函数关系没有拆开分析"],
        examples: ["复合函数只判断一层增减性"],
      },
    ],
    edges: [
      { id: "ke-1", source: "kp-derivative", target: "kp-monotonic", label: "前置", curve: -0.18 },
      { id: "ke-2", source: "kp-parity", target: "kp-monotonic", label: "相似", curve: -0.1 },
      { id: "ke-3", source: "kp-domain", target: "kp-monotonic", label: "关联", curve: 0.12 },
      { id: "ke-4", source: "kp-monotonic", target: "kp-interval", label: "包含", curve: 0.14 },
      { id: "ke-5", source: "kp-composite", target: "kp-monotonic", label: "扩展", curve: 0.08 },
    ],
  },
  error: {
    title: "错题图",
    file: "memory/graphs/error_graph.json",
    accent: "error",
    legend: ["对应知识点", "相似错误", "纠正建议", "重复出现"],
    nodes: [
      {
        id: "err-sign",
        label: "符号方向反了",
        badge: "严重 0.82",
        size: 128,
        x: 660,
        y: 350,
        summary: "当前最常见错误模式，重复出现次数最高。",
        metrics: [
          ["严重度", "0.82"],
          ["错误次数", "6"],
          ["重复出现", "是"],
          ["最近出现", "03-29"],
        ],
        highlights: ["不等号翻转遗漏", "符号表和结论没有同步"],
        examples: ["f'(x) > 0 推区间时写反", "讨论参数时把减区间写成增区间"],
      },
      {
        id: "err-endpoint",
        label: "区间端点漏写",
        badge: "次数 4",
        size: 100,
        x: 970,
        y: 260,
        summary: "和单调区间相关的结论收口不完整。",
        metrics: [
          ["严重度", "0.69"],
          ["错误次数", "4"],
          ["重复出现", "是"],
          ["最近出现", "03-28"],
        ],
        highlights: ["端点开闭没有和定义域联动"],
        examples: ["根式边界没有写入区间结果"],
      },
      {
        id: "err-domain",
        label: "定义域未检查",
        badge: "次数 3",
        size: 92,
        x: 970,
        y: 540,
        summary: "这类错误会把多个知识点一起带偏。",
        metrics: [
          ["严重度", "0.64"],
          ["错误次数", "3"],
          ["重复出现", "否"],
          ["最近出现", "03-27"],
        ],
        highlights: ["把定义域当成最后补充项"],
        examples: ["奇偶性判断前未先过滤定义域"],
      },
      {
        id: "err-skip",
        label: "步骤跳写",
        badge: "习惯性",
        size: 82,
        x: 440,
        y: 580,
        summary: "中间推导跳过时，检查点一起消失。",
        metrics: [
          ["严重度", "0.56"],
          ["错误次数", "2"],
          ["重复出现", "否"],
          ["最近出现", "03-26"],
        ],
        highlights: ["想法是对的，但轨迹无法复盘"],
        examples: ["从导数符号直接跳到最终区间"],
      },
      {
        id: "err-correction",
        label: "纠错策略",
        badge: "建议集",
        size: 88,
        x: 1180,
        y: 400,
        summary: "用于收纳可复用的纠错动作，不长期保留题目截图。",
        metrics: [
          ["策略数", "4"],
          ["近 15 天样本", "保留"],
          ["重复触发", "高"],
          ["最近更新", "03-29"],
        ],
        highlights: ["先列符号表再写结论", "定义域前置检查"],
        examples: ["进入题目先写定义域", "写结论前二次核对区间方向"],
      },
      {
        id: "err-cause",
        label: "错误归因不明",
        badge: "待拆分",
        size: 94,
        x: 360,
        y: 250,
        summary: "当错误没有拆成可执行模式时，图谱会继续膨胀。",
        metrics: [
          ["严重度", "0.62"],
          ["错误次数", "3"],
          ["重复出现", "是"],
          ["最近出现", "03-25"],
        ],
        highlights: ["题目错了，但没有沉淀成模式"],
        examples: ["只记录错题，不记录错因"],
      },
    ],
    edges: [
      { id: "ee-1", source: "err-sign", target: "err-endpoint", label: "相似错误", curve: -0.14 },
      { id: "ee-2", source: "err-sign", target: "err-domain", label: "对应知识点", curve: 0.1 },
      { id: "ee-3", source: "err-endpoint", target: "err-correction", label: "纠正建议", curve: 0.16 },
      { id: "ee-4", source: "err-domain", target: "err-correction", label: "纠正建议", curve: -0.12 },
      { id: "ee-5", source: "err-cause", target: "err-sign", label: "重复出现", curve: 0.08 },
      { id: "ee-6", source: "err-skip", target: "err-correction", label: "纠正建议", curve: 0.1 },
    ],
  },
};

const state = {
  memoryGraph: "knowledge",
  memoryView: "focus",
  hoveredNodes: {
    knowledge: null,
    error: null,
  },
  selectedNodes: {
    knowledge: null,
    error: null,
  },
  views: {
    knowledge: { x: -110, y: -10, scale: 0.9 },
    error: { x: -120, y: -10, scale: 0.9 },
  },
  graphs: JSON.parse(JSON.stringify(GRAPH_SEED)),
  interaction: null,
  suppressClick: false,
  memoryLoading: false,
  memoryLoaded: false,
  memoryError: "",
  memoryDeleting: false,
};

const CHAT_API_PATH = "/api/chat/messages";
const CHAT_UPLOADS_PATH = "/api/chat/uploads";
const DASHBOARD_API_PATH = "/api/dashboard";
const MEMORY_GRAPHS_API_PATH = "/api/memory/graphs";
const MEMORY_GRAPH_DELETE_API_PATH = "/api/memory/graphs/delete";
const CUSTOM_OUTPUT_SKILLS_API_PATH = "/api/custom-output-skills";
const chatState = {
  messages: [],
  draft: "",
  error: "",
  loading: false,
  loaded: false,
  sending: false,
  pendingUserText: "",
  pendingAttachments: [],
  attachments: [],
  dragActive: false,
};
const skillsState = {
  skills: [],
  limit: 2,
  draft: "",
  loading: false,
  loaded: false,
  saving: false,
  error: "",
  notice: "",
};
const dashboardState = {
  data: null,
  loading: false,
  loaded: false,
  error: "",
};

let disposeChatPage = null;
let disposeMemoryPage = null;
let disposeSkillsPage = null;
let disposeDashboardPage = null;

function currentPage() {
  const pageId = window.location.hash.replace(/^#\/?/, "");
  const knownPages = NAV_GROUPS.flatMap((group) => group.items).map((item) => item.id);
  return knownPages.includes(pageId) ? pageId : "chat";
}

function renderNav(activeId) {
  const renderGroup = (group) => `
    <section class="nav-group">
      <div class="nav-label">${group.label}</div>
      ${group.items
        .map((item) => `
          <button class="nav-item${item.id === activeId ? " active" : ""}" data-page="${item.id}">
            <span class="nav-icon" data-tone="${item.tone || "brand"}">${item.icon}</span>
            <span class="nav-copy">
              <strong>${item.label}</strong>
              <span>${item.hint}</span>
            </span>
          </button>
        `)
        .join("")}
    </section>
  `;

  const [studentGroup, adminGroup] = NAV_GROUPS;
  return `
    <div class="nav-top">${renderGroup(studentGroup)}</div>
    <div class="nav-bottom">${renderGroup(adminGroup)}</div>
  `;
}

function truncateText(text, maxLength = 120) {
  const value = cleanDisplayText(text);
  if (!value) {
    return "";
  }
  return value.length > maxLength ? `${value.slice(0, maxLength - 1)}…` : value;
}

function escapeList(items, emptyText = "暂无内容") {
  if (!Array.isArray(items) || !items.length) {
    return `<li>${emptyText}</li>`;
  }
  return items.map((item) => `<li>${escapeHtml(cleanDisplayText(item))}</li>`).join("");
}

function formatDateTimeLabel(value) {
  if (!value) {
    return "暂无";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  return date.toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function renderPlanPage() {
  const student = dashboardState.data?.student || {};
  const daily = student.daily || {};
  const weekly = student.weekly || {};
  const focus = Array.isArray(student.highlights?.focus) ? student.highlights.focus : [];
  const mistakes = Array.isArray(student.highlights?.mistakes) ? student.highlights.mistakes : [];

  return `
    <section class="page-head">
      <div>
        <h2>学习计划</h2>
        <p>把今天最值得花时间的内容排清楚，先做重点，再决定练多少。</p>
      </div>
    </section>
    <section class="dashboard-stack">
      <section class="dashboard-grid dashboard-grid--hero">
        <article class="panel hero-panel">
          <div class="card-head">
            <span class="card-icon">✦</span>
            <div>
              <span class="page-kicker">今日状态</span>
              <h3>${escapeHtml(daily.date || "暂无今日总结")}</h3>
            </div>
          </div>
          <p>${escapeHtml(daily.learning_status_summary || "今天还没有新的学习总结，先从一道题开始。")}</p>
        </article>
        <article class="panel hero-side-card">
          <div class="card-head">
            <span class="card-icon">◎</span>
            <div>
              <span class="page-kicker">本周计划</span>
              <strong>${escapeHtml(weekly.title || "本周节奏待生成")}</strong>
            </div>
          </div>
          <ul class="info-list">${escapeList((weekly.goals || []).slice(0, 3), "等待下一个周度总结生成。")}</ul>
        </article>
      </section>
      <section class="dashboard-grid dashboard-grid--3">
        <article class="panel info-card">
          <div class="card-head card-head--compact">
            <span class="card-icon">☼</span>
            <h3>明日建议</h3>
          </div>
          <ul class="info-list">${escapeList(daily.tomorrow_study_suggestions || [], "今天先完成当前题目练习。")}</ul>
        </article>
        <article class="panel info-card">
          <div class="card-head card-head--compact">
            <span class="card-icon">◌</span>
            <h3>优先复习知识点</h3>
          </div>
          <ul class="info-list">${escapeList(focus.map((item) => `${item.label} · ${truncateText(item.summary, 30)}`), "图谱还没有聚焦点。")}</ul>
        </article>
        <article class="panel info-card">
          <div class="card-head card-head--compact">
            <span class="card-icon">!</span>
            <h3>重点纠错方向</h3>
          </div>
          <ul class="info-list">${escapeList(mistakes.map((item) => `${item.label} · ${truncateText(item.summary, 30)}`), "错题图还没有新的提醒。")}</ul>
        </article>
      </section>
      <section class="dashboard-grid dashboard-grid--2">
        <article class="panel info-card">
          <div class="card-head card-head--compact">
            <span class="card-icon">→</span>
            <h3>每天建议主题</h3>
          </div>
          <ul class="info-list">${escapeList(weekly.daily_topics || [], "本周主题会在周总结生成后出现在这里。")}</ul>
        </article>
        <article class="panel info-card">
          <div class="card-head card-head--compact">
            <span class="card-icon">▣</span>
            <h3>练习量与难度</h3>
          </div>
          <ul class="info-list">${escapeList([...(weekly.exercise_load || []), ...(weekly.difficulty_adjustment || [])], "先以高质量完成 1 到 2 道题为主。")}</ul>
        </article>
      </section>
    </section>
  `;
}

function renderStatusPage() {
  const admin = dashboardState.data?.admin || {};
  const runtime = admin.runtime || {};
  const gateway = runtime.gateway || {};
  const consoleRuntime = runtime.console || {};

  return `
    <section class="page-head">
      <div>
        <h2>运行状态</h2>
        <p>这里给管理员看系统是否稳定，学生侧不会直接看到这些底层状态。</p>
      </div>
    </section>
    <section class="dashboard-grid dashboard-grid--4">
      <article class="panel dashboard-metric-card">
        <span>网关</span>
        <strong>${gateway.online ? "运行中" : "未连接"}</strong>
        <small>PID ${escapeHtml(String(gateway.pid || "-"))}</small>
      </article>
      <article class="panel dashboard-metric-card">
        <span>前端控制台</span>
        <strong>${consoleRuntime.online ? "运行中" : "未连接"}</strong>
        <small>PID ${escapeHtml(String(consoleRuntime.pid || "-"))}</small>
      </article>
      <article class="panel dashboard-metric-card">
        <span>当前主模型</span>
        <strong>${escapeHtml(runtime.model || "-")}</strong>
        <small>${escapeHtml(runtime.provider || "")}</small>
      </article>
      <article class="panel dashboard-metric-card">
        <span>自定义输出 Skill</span>
        <strong>${escapeHtml(String(runtime.custom_skill_count || 0))}</strong>
        <small>仅在附件回复后追加</small>
      </article>
    </section>
    <section class="dashboard-grid dashboard-grid--2">
      <article class="panel info-card">
        <h3>附件处理链路</h3>
        <ul class="info-list">
          <li>文档：${escapeHtml(runtime.doc_model || "qwen-doc-turbo")}</li>
          <li>图片：${escapeHtml(runtime.image_pipeline || "原图 + Markdown 转写 + qwen3.5")}</li>
          <li>时区：${escapeHtml(runtime.timezone || "Asia/Shanghai")}</li>
        </ul>
      </article>
      <article class="panel info-card">
        <h3>管理提示</h3>
        <ul class="info-list">
          <li>学生端只显示学习相关内容，不暴露这些底层状态。</li>
          <li>如果某个通道异常，先看频道页，再看心跳与定时任务。</li>
          <li>模型和环境变量只在管理后台做只读展示。</li>
        </ul>
      </article>
    </section>
  `;
}

function renderChannelsPage() {
  const channels = Array.isArray(dashboardState.data?.admin?.channels) ? dashboardState.data.admin.channels : [];
  return `
    <section class="page-head">
      <div>
        <h2>频道</h2>
        <p>查看企业微信、QQ、飞书和前端工作台的连接状态与今日活跃情况。</p>
      </div>
    </section>
    <section class="channel-grid">
      ${channels.map((channel) => `
        <article class="panel channel-card">
          <div class="channel-card__head">
            <strong>${escapeHtml(channel.label || channel.id)}</strong>
            <span class="status-pill${channel.enabled ? " status-pill--online" : ""}">${channel.enabled ? "已启用" : "未启用"}</span>
          </div>
          <div class="channel-stats">
            <div><span>今日消息</span><strong>${escapeHtml(String(channel.messages_today || 0))}</strong></div>
            <div><span>附件回合</span><strong>${escapeHtml(String(channel.attachments_today || 0))}</strong></div>
            <div><span>活跃会话</span><strong>${escapeHtml(String(channel.sessions_today || 0))}</strong></div>
            <div><span>最近消息</span><strong>${escapeHtml(formatDateTimeLabel(channel.last_message_at))}</strong></div>
          </div>
        </article>
      `).join("")}
    </section>
  `;
}

function renderHeartbeatPage() {
  const schedules = Array.isArray(dashboardState.data?.admin?.schedules) ? dashboardState.data.admin.schedules : [];
  return `
    <section class="page-head">
      <div>
        <h2>心跳</h2>
        <p>自动发送的日总结、周总结和定时任务是否正常执行，都从这里看。</p>
      </div>
    </section>
    <section class="schedule-stack">
      ${schedules.map((item) => `
        <article class="panel schedule-card">
          <div class="schedule-card__head">
            <strong>${escapeHtml(item.name || "未命名任务")}</strong>
            <span class="status-pill${item.enabled ? " status-pill--online" : ""}">${item.enabled ? "启用中" : "已停用"}</span>
          </div>
          <div class="schedule-meta">
            <span>表达式：${escapeHtml(item.expr || "-")}</span>
            <span>时区：${escapeHtml(item.timezone || "Asia/Shanghai")}</span>
          </div>
          <div class="schedule-meta">
            <span>下次执行：${escapeHtml(formatDateTimeLabel(item.next_run))}</span>
            <span>上次执行：${escapeHtml(formatDateTimeLabel(item.last_run))}</span>
            <span>结果：${escapeHtml(item.last_status || "暂无")}</span>
          </div>
        </article>
      `).join("")}
    </section>
  `;
}

function renderConfigPage(pageId) {
  const admin = dashboardState.data?.admin || {};
  const settings = admin.settings || {};
  const runtime = admin.runtime || {};
  const tools = Array.isArray(settings.tools) ? settings.tools : [];
  if (pageId === "models") {
    return `
      <section class="page-head">
        <div>
          <h2>模型配置</h2>
          <p>这里只展示当前在用的模型链路，不暴露密钥值。</p>
        </div>
      </section>
      <section class="dashboard-grid dashboard-grid--3">
        <article class="panel info-card"><h3>主模型</h3><p>${escapeHtml(runtime.model || "-")}</p></article>
        <article class="panel info-card"><h3>文档模型</h3><p>${escapeHtml(runtime.doc_model || "qwen-doc-turbo")}</p></article>
        <article class="panel info-card"><h3>图片链路</h3><p>${escapeHtml(runtime.image_pipeline || "-")}</p></article>
      </section>
    `;
  }
  if (pageId === "agent-config") {
    return `
      <section class="page-head">
        <div>
          <h2>Agent 配置</h2>
          <p>面向管理员的只读配置视图，学生端不会看到这些参数。</p>
        </div>
      </section>
      <section class="dashboard-grid dashboard-grid--4">
        <article class="panel dashboard-metric-card"><span>上下文窗口</span><strong>${escapeHtml(String(settings.context_window_tokens || "-"))}</strong><small>tokens</small></article>
        <article class="panel dashboard-metric-card"><span>工具迭代</span><strong>${escapeHtml(String(settings.max_iterations || "-"))}</strong><small>每轮上限</small></article>
        <article class="panel dashboard-metric-card"><span>工作区限制</span><strong>${settings.restrict_to_workspace ? "开启" : "关闭"}</strong><small>文件读写边界</small></article>
        <article class="panel dashboard-metric-card"><span>时区</span><strong>${escapeHtml(runtime.timezone || "Asia/Shanghai")}</strong><small>学习计划与总结</small></article>
      </section>
    `;
  }
  if (pageId === "mcp") {
    return `
      <section class="page-head">
        <div>
          <h2>Tools</h2>
          <p>这里集中展示当前回复链路会用到的搜索、文档理解、图片解析与记忆工具。</p>
        </div>
      </section>
      <section class="dashboard-grid dashboard-grid--3">
        ${tools.map((tool) => `
          <article class="panel info-card tool-card">
            <div class="card-head card-head--compact">
              <span class="card-icon">⌘</span>
              <h3>${escapeHtml(tool.label || "工具")}</h3>
            </div>
            <p>${escapeHtml(tool.detail || "暂无说明")}</p>
          </article>
        `).join("")}
      </section>
    `;
  }
  return `
    <section class="page-head">
      <div>
        <h2>${PAGE_META[pageId].title}</h2>
        <p>${PAGE_META[pageId].description}</p>
      </div>
    </section>
  `;
}

function renderDashboardPage(pageId) {
  if (dashboardState.loading && !dashboardState.loaded) {
    return `
      <section class="page-head">
        <div>
          <h2>${PAGE_META[pageId].title}</h2>
          <p>${PAGE_META[pageId].description}</p>
        </div>
      </section>
      <section class="panel simple-panel">
        <div class="placeholder">
          <div>
            <strong>正在同步页面数据...</strong>
            <p>MathClaw 正在读取最新的学习摘要、图谱和系统状态。</p>
          </div>
        </div>
      </section>
    `;
  }
  if (dashboardState.error && !dashboardState.loaded) {
    return `
      <section class="page-head">
        <div>
          <h2>${PAGE_META[pageId].title}</h2>
          <p>${PAGE_META[pageId].description}</p>
        </div>
      </section>
      <section class="panel simple-panel">
        <div class="placeholder">
          <div>
            <strong>页面数据加载失败</strong>
            <p>${escapeHtml(dashboardState.error)}</p>
          </div>
        </div>
      </section>
    `;
  }
  if (pageId === "cron-jobs") {
    return renderPlanPage();
  }
  if (pageId === "status") {
    return renderStatusPage();
  }
  if (pageId === "channels") {
    return renderChannelsPage();
  }
  if (pageId === "heartbeat") {
    return renderHeartbeatPage();
  }
  if (["mcp", "agent-config", "models"].includes(pageId)) {
    return renderConfigPage(pageId);
  }
  return "";
}

function renderChat() {
  return '<section data-chat-root class="chat-root"></section>';
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function formatChatTime(timestamp) {
  if (!timestamp) {
    return "";
  }

  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) {
    return "";
  }

  return date.toLocaleTimeString("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function normalizeMessageContent(value) {
  return String(value || "")
    .replace(/\[(?:图片|image):[^\]]+\]/gi, "")
    .replace(/\[(?:附件|file):[^\]]+\]/gi, "")
    .replace(/\r\n?/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function sanitizeHref(url) {
  const value = String(url || "").trim();
  return /^https?:\/\//i.test(value) ? value : "";
}

function renderInlineMarkdown(text) {
  const placeholders = [];
  const stash = (html) => {
    const token = `@@MD_TOKEN_${placeholders.length}@@`;
    placeholders.push(html);
    return token;
  };

  let value = String(text || "");

  value = value.replace(/!\[([^\]]*)\]\((https?:\/\/[^\s)]+)\)/g, (match, alt, url) => {
    const href = sanitizeHref(url);
    if (!href) {
      return match;
    }
    return stash(
      `<a class="msg-md__image-link" href="${escapeHtml(href)}" target="_blank" rel="noreferrer noopener">${escapeHtml(alt || href)}</a>`,
    );
  });

  value = value.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, (match, label, url) => {
    const href = sanitizeHref(url);
    if (!href) {
      return match;
    }
    return stash(
      `<a href="${escapeHtml(href)}" target="_blank" rel="noreferrer noopener">${escapeHtml(label)}</a>`,
    );
  });

  value = value.replace(/`([^`\n]+)`/g, (_, code) => stash(`<code>${escapeHtml(code)}</code>`));

  value = escapeHtml(value)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/__(.+?)__/g, "<strong>$1</strong>")
    .replace(/~~(.+?)~~/g, "<del>$1</del>")
    .replace(/(^|[\s(>])((?:https?:\/\/)[^\s<]+)/g, (match, prefix, url) => {
      const href = sanitizeHref(url);
      if (!href) {
        return match;
      }
      return `${prefix}<a href="${escapeHtml(href)}" target="_blank" rel="noreferrer noopener">${escapeHtml(url)}</a>`;
    })
    .replace(/\n/g, "<br>");

  return value.replace(/@@MD_TOKEN_(\d+)@@/g, (_, index) => placeholders[Number(index)] || "");
}

function splitMarkdownTableRow(line) {
  return line
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((cell) => cell.trim());
}

function isMarkdownTableSeparator(line) {
  return /^\s*\|?(?:\s*:?-{3,}:?\s*\|)+(?:\s*:?-{3,}:?\s*)\|?\s*$/.test(line || "");
}

function isMarkdownTableStart(lines, index) {
  if (index + 1 >= lines.length) {
    return false;
  }
  return lines[index].includes("|") && isMarkdownTableSeparator(lines[index + 1]);
}

function renderMarkdownTable(lines, index) {
  const headers = splitMarkdownTableRow(lines[index]);
  const aligners = splitMarkdownTableRow(lines[index + 1]).map((cell) => {
    const trimmed = cell.trim();
    if (trimmed.startsWith(":") && trimmed.endsWith(":")) {
      return "center";
    }
    if (trimmed.endsWith(":")) {
      return "right";
    }
    return "left";
  });

  const rows = [];
  let cursor = index + 2;
  while (cursor < lines.length && lines[cursor].includes("|") && lines[cursor].trim()) {
    rows.push(splitMarkdownTableRow(lines[cursor]));
    cursor += 1;
  }

  const headerHtml = headers
    .map((cell, cellIndex) => `<th style="text-align:${aligners[cellIndex] || "left"}">${renderInlineMarkdown(cell)}</th>`)
    .join("");

  const bodyHtml = rows
    .map((row) => `
      <tr>
        ${headers
          .map((_, cellIndex) => {
            const value = row[cellIndex] || "";
            return `<td style="text-align:${aligners[cellIndex] || "left"}">${renderInlineMarkdown(value)}</td>`;
          })
          .join("")}
      </tr>
    `)
    .join("");

  return {
    html: `
      <div class="msg-md__table-wrap">
        <table class="msg-md__table">
          <thead><tr>${headerHtml}</tr></thead>
          <tbody>${bodyHtml}</tbody>
        </table>
      </div>
    `,
    nextIndex: cursor,
  };
}

function isMarkdownListLine(line) {
  return /^(\s*)([-*+]|\d+\.)\s+/.test(line || "");
}

function renderMarkdownList(lines, index) {
  const ordered = /^\s*\d+\.\s+/.test(lines[index]);
  const tag = ordered ? "ol" : "ul";
  const items = [];
  let cursor = index;

  while (cursor < lines.length && isMarkdownListLine(lines[cursor])) {
    const match = lines[cursor].match(/^(\s*)([-*+]|\d+\.)\s+(.+)$/);
    if (!match) {
      break;
    }

    const parts = [match[3].trim()];
    let probe = cursor + 1;
    while (
      probe < lines.length &&
      lines[probe].trim() &&
      !isMarkdownListLine(lines[probe]) &&
      !/^\s*(?:#{1,6}\s+|```|~~~|>|(?:-{3,}|\*{3,}|_{3,})\s*$)/.test(lines[probe]) &&
      !isMarkdownTableStart(lines, probe)
    ) {
      parts.push(lines[probe].trim());
      probe += 1;
    }

    items.push(`<li>${renderInlineMarkdown(parts.join("\n"))}</li>`);
    cursor = probe;
  }

  return {
    html: `<${tag}>${items.join("")}</${tag}>`,
    nextIndex: cursor,
  };
}

function renderMarkdownBlocks(content) {
  const lines = String(content || "").split("\n");
  const blocks = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index];
    const trimmed = line.trim();

    if (!trimmed) {
      index += 1;
      continue;
    }

    const heading = trimmed.match(/^(#{1,6})\s+(.+)$/);
    if (heading) {
      const level = Math.min(heading[1].length + 1, 6);
      blocks.push(`<h${level}>${renderInlineMarkdown(heading[2].trim())}</h${level}>`);
      index += 1;
      continue;
    }

    if (/^(```|~~~)/.test(trimmed)) {
      const fence = trimmed.slice(0, 3);
      const codeLines = [];
      index += 1;
      while (index < lines.length && !lines[index].trim().startsWith(fence)) {
        codeLines.push(lines[index]);
        index += 1;
      }
      if (index < lines.length) {
        index += 1;
      }
      blocks.push(`<pre><code>${escapeHtml(codeLines.join("\n"))}</code></pre>`);
      continue;
    }

    if (/^(?:-{3,}|\*{3,}|_{3,})$/.test(trimmed)) {
      blocks.push("<hr>");
      index += 1;
      continue;
    }

    if (isMarkdownTableStart(lines, index)) {
      const table = renderMarkdownTable(lines, index);
      blocks.push(table.html);
      index = table.nextIndex;
      continue;
    }

    if (/^\s*>\s?/.test(line)) {
      const quoteLines = [];
      while (index < lines.length && /^\s*>\s?/.test(lines[index])) {
        quoteLines.push(lines[index].replace(/^\s*>\s?/, ""));
        index += 1;
      }
      blocks.push(`<blockquote>${renderMarkdownBlocks(quoteLines.join("\n"))}</blockquote>`);
      continue;
    }

    if (isMarkdownListLine(line)) {
      const list = renderMarkdownList(lines, index);
      blocks.push(list.html);
      index = list.nextIndex;
      continue;
    }

    const paragraph = [trimmed];
    index += 1;
    while (
      index < lines.length &&
      lines[index].trim() &&
      !/^\s*(?:#{1,6}\s+|```|~~~|>\s?|(?:-{3,}|\*{3,}|_{3,})\s*$)/.test(lines[index]) &&
      !isMarkdownListLine(lines[index]) &&
      !isMarkdownTableStart(lines, index)
    ) {
      paragraph.push(lines[index].trim());
      index += 1;
    }
    blocks.push(`<p>${renderInlineMarkdown(paragraph.join("\n"))}</p>`);
  }

  return blocks.join("");
}

function renderMessageContent(message) {
  const content = normalizeMessageContent(message.content || "");
  if (!content) {
    return "";
  }

  if (message.role === "user") {
    return `<div class="msg-bubble__text">${escapeHtml(content)}</div>`;
  }

  return `<div class="msg-bubble__markdown">${renderMarkdownBlocks(content)}</div>`;
}

function normalizeChatMessages(messages) {
  if (!Array.isArray(messages)) {
    return [];
  }

  return messages
    .filter((message) => message && typeof message === "object")
    .map((message, index) => ({
      id: message.id || `${message.role || "assistant"}-${index}`,
      role: message.role === "user" ? "user" : "assistant",
      content: normalizeMessageContent(typeof message.content === "string" ? message.content : ""),
      attachments: Array.isArray(message.attachments)
        ? message.attachments
          .filter((item) => item && typeof item === "object")
          .map((item) => ({
            kind: item.kind === "image" ? "image" : "file",
            name: String(item.name || "附件"),
            url: typeof item.url === "string" ? item.url : "",
          }))
        : [],
      timestamp: message.timestamp || "",
    }));
}

function chatRenderMessages() {
  const messages = [...chatState.messages];

  if (chatState.pendingUserText || chatState.pendingAttachments.length) {
    messages.push({
      id: "pending-user",
      role: "user",
      content: chatState.pendingUserText,
      attachments: chatState.pendingAttachments,
      timestamp: new Date().toISOString(),
      pending: true,
    });
  }

  return messages;
}

function renderChatMessage(message) {
  const isUser = message.role === "user";
  const roleClass = isUser ? "user" : "assistant";
  const avatar = isUser ? "你" : "MC";
  const time = formatChatTime(message.timestamp);
  const attachments = Array.isArray(message.attachments) ? message.attachments : [];
  const content = renderMessageContent(message);

  return `
    <div class="msg ${roleClass}${message.pending ? " is-pending" : ""}">
      <div class="msg-avatar">${avatar}</div>
      <div class="msg-body">
        <div class="msg-bubble">
          ${attachments.length ? renderChatBubbleAttachments(attachments) : ""}
          ${content}
        </div>
        ${time ? `<div class="msg-meta">${time}</div>` : ""}
      </div>
    </div>
  `;
}

function renderTypingIndicator() {
  if (!chatState.sending) {
    return "";
  }

  return `
    <div class="msg assistant">
      <div class="msg-avatar">MC</div>
      <div class="msg-body">
        <div class="msg-bubble msg-bubble--typing">
          <span></span><span></span><span></span>
        </div>
      </div>
    </div>
  `;
}

function buildAttachmentLabel(attachment) {
  return escapeHtml(attachment.name || "附件");
}

function buildPendingPreview(content, attachments) {
  return normalizeMessageContent(content);
}

function cleanDisplayText(value) {
  return normalizeMessageContent(value);
}

function createDraftAttachment(file) {
  const kind = file.type.startsWith("image/") ? "image" : "file";
  return {
    id: `${file.name}:${file.size}:${file.lastModified}`,
    file,
    kind,
    name: file.name,
    size: file.size,
    lastModified: file.lastModified,
    previewUrl: kind === "image" ? URL.createObjectURL(file) : "",
  };
}

function isAcceptedChatFile(file) {
  if (!file) {
    return false;
  }

  if (file.type.startsWith("image/")) {
    return true;
  }

  return /\.(pdf|ppt|pptx|doc|docx)$/i.test(file.name || "");
}

function formatFileSize(bytes) {
  if (!Number.isFinite(bytes) || bytes <= 0) {
    return "0 B";
  }

  const units = ["B", "KB", "MB", "GB"];
  let value = bytes;
  let unitIndex = 0;
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }

  const digits = value >= 10 || unitIndex === 0 ? 0 : 1;
  return `${value.toFixed(digits)} ${units[unitIndex]}`;
}

function draftAttachmentBadge(attachment) {
  if (attachment.kind === "image") {
    return "IMG";
  }

  const extension = String(attachment.name || "").split(".").pop();
  return extension ? extension.slice(0, 4).toUpperCase() : "FILE";
}

function mergeDraftFiles(fileList) {
  const files = Array.from(fileList || []);
  if (!files.length) {
    return 0;
  }

  const existing = new Set(
    chatState.attachments.map((file) => `${file.name}:${file.size}:${file.lastModified}`),
  );

  let added = 0;
  let invalid = false;
  let overflow = false;
  chatState.error = "";

  for (const file of files) {
    if (!isAcceptedChatFile(file)) {
      invalid = true;
      continue;
    }

    if (chatState.attachments.length >= 6) {
      overflow = true;
      break;
    }

    const key = `${file.name}:${file.size}:${file.lastModified}`;
    if (existing.has(key)) {
      continue;
    }

    existing.add(key);
    chatState.attachments.push(createDraftAttachment(file));
    added += 1;
  }

  if (overflow) {
    chatState.error = "单次最多上传 6 个文件。";
  } else if (invalid) {
    chatState.error = "仅支持图片、PDF、PPT 和 Word 文档。";
  }

  return added;
}

function releaseDraftAttachment(attachment) {
  if (attachment?.previewUrl) {
    URL.revokeObjectURL(attachment.previewUrl);
  }
}

function renderChatBubbleAttachments(attachments) {
  return `
    <div class="msg-bubble__attachments">
      ${attachments.map((attachment) => {
        const imageUrl = attachment.url || attachment.previewUrl || "";
        if (attachment.kind === "image" && imageUrl) {
          return `<img class="msg-inline-image" src="${escapeHtml(imageUrl)}" alt="${escapeHtml(attachment.name)}" />`;
        }
        return `<div class="msg-inline-file">${escapeHtml(attachment.name || "附件")}</div>`;
      }).join("")}
    </div>
  `;
}

function renderAttachmentList() {
  if (!chatState.attachments.length) {
    return "";
  }

  return `
    <div class="chat-pending-files">
      ${chatState.attachments
        .map((attachment, index) => `
          <div class="chat-pending-item">
            ${attachment.kind === "image" && attachment.previewUrl
              ? `<img class="chat-pending-thumb" src="${escapeHtml(attachment.previewUrl)}" alt="${buildAttachmentLabel(attachment)}" />`
              : `<div class="chat-pending-icon">${draftAttachmentBadge(attachment)}</div>`}
            <div class="chat-pending-meta">
              <div class="chat-pending-name">${buildAttachmentLabel(attachment)}</div>
              <div class="chat-pending-size">${formatFileSize(attachment.size)}</div>
            </div>
            <button type="button" class="chat-pending-remove" data-remove-attachment="${index}">×</button>
          </div>
        `)
        .join("")}
    </div>
  `;
}

function captureChatScroll(root) {
  const scroller = root.querySelector("[data-chat-scroll]");
  if (!scroller) {
    return null;
  }

  return {
    top: scroller.scrollTop,
    atBottom: scroller.scrollHeight - scroller.clientHeight - scroller.scrollTop < 48,
  };
}

function restoreChatScroll(root, snapshot, forceScrollBottom = false) {
  const scroller = root.querySelector("[data-chat-scroll]");
  if (!scroller) {
    return;
  }

  requestAnimationFrame(() => {
    if (forceScrollBottom || !snapshot || snapshot.atBottom) {
      scroller.scrollTop = scroller.scrollHeight;
      return;
    }
    scroller.scrollTop = snapshot.top;
  });
}

function renderChatPage(root, options = {}) {
  const scrollSnapshot = options.scrollSnapshot ?? captureChatScroll(root);
  const messages = chatRenderMessages();
  const sendDisabled =
    chatState.loading ||
    chatState.sending ||
    (!chatState.draft.trim() && chatState.attachments.length === 0);

  root.innerHTML = `
    <section class="chat-page-shell">
      <section class="panel chat-shell">
        <div class="chat-container${chatState.dragActive ? " drag-active" : ""}" data-chat-dropzone>
          ${chatState.dragActive ? '<div class="chat-drop-overlay">拖拽文件到此处</div>' : ""}
          <div class="chat-toolbar">
            <div class="chat-toolbar-session">当前工作台：单对话模式</div>
          </div>
          <div class="messages" data-chat-scroll>
            ${messages.length
              ? messages.map(renderChatMessage).join("")
              : `
                <div class="chat-empty">
                  <div class="chat-empty-icon">⌁</div>
                  <h3>${chatState.loading ? "正在连接 MathClaw..." : "拖拽文件到此处"}</h3>
                  <p>${chatState.loading ? "正在加载当前会话。" : "上传图片或 PDF，MathClaw 会帮你解析题目并继续解题。"}</p>
                </div>
              `}
            ${renderTypingIndicator()}
          </div>
          ${chatState.error ? `<div class="chat-alert">${escapeHtml(chatState.error)}</div>` : ""}
          <div class="chat-input-wrap">
            ${renderAttachmentList()}
            <form class="chat-input-bar" data-chat-form>
              <label class="upload-button btn-secondary">
                <input
                  type="file"
                  data-chat-files
                  multiple
                  accept=".png,.jpg,.jpeg,.gif,.webp,.pdf,.ppt,.pptx,.doc,.docx"
                  hidden
                />
                上传文件
              </label>
              <textarea
                class="chat-input"
                data-chat-input
                rows="1"
                placeholder="输入问题，或上传图片/PDF..."
                ${chatState.loading || chatState.sending ? "disabled" : ""}
              ></textarea>
              <button class="primary-button" type="submit" data-chat-send ${sendDisabled ? "disabled" : ""}>
                ${chatState.sending ? "发送中..." : "发送"}
              </button>
            </form>
            <div class="chat-input-hint">支持拖拽图片或 PDF 到这里，单次最多上传 6 个文件。</div>
          </div>
        </div>
      </section>
    </section>
  `;

  const input = root.querySelector("[data-chat-input]");
  if (input) {
    input.value = chatState.draft;
    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, 160)}px`;
  }

  restoreChatScroll(root, scrollSnapshot, Boolean(options.forceScrollBottom));
}

async function requestJson(path, options = {}) {
  const response = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  const text = await response.text();
  let data = {};

  if (text) {
    try {
      data = JSON.parse(text);
    } catch (error) {
      data = {};
    }
  }

  if (!response.ok) {
    throw new Error(data.error || `请求失败（${response.status}）`);
  }

  return data;
}

async function requestChat(path, options = {}) {
  return requestJson(path, options);
}

async function loadDashboard(onDone, options = {}) {
  const silent = Boolean(options.silent);
  if (!silent) {
    dashboardState.loading = true;
    dashboardState.error = "";
  }
  try {
    dashboardState.data = await requestJson(DASHBOARD_API_PATH, { method: "GET" });
    dashboardState.loaded = true;
    dashboardState.error = "";
  } catch (error) {
    dashboardState.error = error.message || "加载页面数据失败";
  } finally {
    dashboardState.loading = false;
    if (typeof onDone === "function") {
      onDone();
    }
  }
}

async function uploadChatFiles(files) {
  const formData = new FormData();
  files.forEach((attachment) => {
    const file = attachment.file || attachment;
    formData.append("files", file, file.name);
  });

  const response = await fetch(CHAT_UPLOADS_PATH, {
    method: "POST",
    body: formData,
  });
  const text = await response.text();
  let data = {};

  if (text) {
    try {
      data = JSON.parse(text);
    } catch (error) {
      data = {};
    }
  }

  if (!response.ok) {
    throw new Error(data.error || `上传失败（${response.status}）`);
  }

  return Array.isArray(data.files) ? data.files : [];
}

async function loadChatHistory(root, options = {}) {
  const silent = Boolean(options.silent);
  if (!silent) {
    chatState.loading = true;
    chatState.error = "";
    if (root.isConnected) {
      renderChatPage(root);
    }
  }

  try {
    const data = await requestChat(CHAT_API_PATH, { method: "GET" });
    chatState.messages = normalizeChatMessages(data.messages);
    chatState.loaded = true;
  } catch (error) {
    chatState.error = error.message || "加载会话失败";
  } finally {
    chatState.loading = false;
    if (root.isConnected) {
      renderChatPage(root, { forceScrollBottom: Boolean(options.forceScrollBottom) });
    }
  }
}

async function submitChat(root) {
  const content = chatState.draft.trim();
  const attachments = [...chatState.attachments];
  if ((!content && attachments.length === 0) || chatState.sending) {
    return;
  }

  chatState.pendingUserText = buildPendingPreview(content, attachments);
  chatState.pendingAttachments = attachments.map((attachment) => ({
    kind: attachment.kind,
    name: attachment.name,
    url: attachment.previewUrl || "",
  }));
  chatState.draft = "";
  chatState.sending = true;
  chatState.error = "";
  if (root.isConnected) {
    renderChatPage(root, { forceScrollBottom: true });
  }

  try {
    let media = [];
    let uploaded = [];
    if (attachments.length) {
      uploaded = await uploadChatFiles(attachments);
      media = uploaded.map((item) => item.path).filter(Boolean);
    }
    const data = await requestChat(CHAT_API_PATH, {
      method: "POST",
      body: JSON.stringify({ content, media }),
    });
    chatState.messages = normalizeChatMessages(data.messages);
    if (attachments.length) {
      const lastUser = [...chatState.messages].reverse().find((message) => message.role === "user");
      if (lastUser && lastUser.content === cleanDisplayText(content)) {
        lastUser.attachments = uploaded.map((item, index) => ({
          kind: attachments[index]?.kind || "file",
          name: item.name || attachments[index]?.name || "附件",
          url: item.url || "",
        }));
      }
    }
    chatState.loaded = true;
    chatState.attachments.forEach(releaseDraftAttachment);
    chatState.attachments = [];
  } catch (error) {
    chatState.draft = content;
    chatState.error = error.message || "发送失败";
  } finally {
    chatState.pendingUserText = "";
    chatState.pendingAttachments = [];
    chatState.sending = false;
    if (root.isConnected) {
      renderChatPage(root, { forceScrollBottom: true });
    }
  }
}

function mountChatPage(root) {
  let dragDepth = 0;

  const handleSubmit = (event) => {
    const form = event.target.closest("[data-chat-form]");
    if (!form) {
      return;
    }
    event.preventDefault();
    void submitChat(root);
  };

  const handleInput = (event) => {
    const input = event.target.closest("[data-chat-input]");
    if (!input) {
      return;
    }

    chatState.draft = input.value;
    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, 160)}px`;

    const sendButton = root.querySelector("[data-chat-send]");
    if (sendButton) {
      sendButton.disabled =
        chatState.loading ||
        chatState.sending ||
        (!chatState.draft.trim() && chatState.attachments.length === 0);
    }
  };

  const handleFileChange = (event) => {
    const input = event.target.closest("[data-chat-files]");
    if (!input || !input.files?.length) {
      return;
    }

    mergeDraftFiles(input.files);
    input.value = "";
    renderChatPage(root);
  };

  const handleClick = (event) => {
    const removeButton = event.target.closest("[data-remove-attachment]");
    if (!removeButton) {
      return;
    }

    const index = Number(removeButton.dataset.removeAttachment);
    if (Number.isNaN(index)) {
      return;
    }

    const [removed] = chatState.attachments.splice(index, 1);
    releaseDraftAttachment(removed);
    renderChatPage(root);
  };

  const handleKeyDown = (event) => {
    const input = event.target.closest("[data-chat-input]");
    if (!input) {
      return;
    }

    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      const form = input.closest("form");
      if (form) {
        form.requestSubmit();
      }
    }
  };

  const handleDragEnter = (event) => {
    if (!event.dataTransfer?.types?.includes("Files")) {
      return;
    }
    event.preventDefault();
    dragDepth += 1;
    if (!chatState.dragActive) {
      chatState.dragActive = true;
      renderChatPage(root);
    }
  };

  const handleDragOver = (event) => {
    if (!event.dataTransfer?.types?.includes("Files")) {
      return;
    }
    event.preventDefault();
    event.dataTransfer.dropEffect = "copy";
  };

  const handleDragLeave = (event) => {
    if (!event.dataTransfer?.types?.includes("Files")) {
      return;
    }
    dragDepth = Math.max(dragDepth - 1, 0);
    if (!dragDepth && chatState.dragActive) {
      chatState.dragActive = false;
      renderChatPage(root);
    }
  };

  const handleDrop = (event) => {
    if (!event.dataTransfer?.files?.length) {
      return;
    }
    event.preventDefault();
    dragDepth = 0;
    chatState.dragActive = false;
    mergeDraftFiles(event.dataTransfer.files);
    renderChatPage(root);
  };

  root.addEventListener("submit", handleSubmit);
  root.addEventListener("input", handleInput);
  root.addEventListener("change", handleFileChange);
  root.addEventListener("click", handleClick);
  root.addEventListener("keydown", handleKeyDown);
  root.addEventListener("dragenter", handleDragEnter);
  root.addEventListener("dragover", handleDragOver);
  root.addEventListener("dragleave", handleDragLeave);
  root.addEventListener("drop", handleDrop);

  renderChatPage(root, { forceScrollBottom: true });
  if (!chatState.loaded && !chatState.loading) {
    void loadChatHistory(root, { forceScrollBottom: true });
  }

  return () => {
    dragDepth = 0;
    chatState.dragActive = false;
    chatState.attachments.forEach(releaseDraftAttachment);
    root.removeEventListener("submit", handleSubmit);
    root.removeEventListener("input", handleInput);
    root.removeEventListener("change", handleFileChange);
    root.removeEventListener("click", handleClick);
    root.removeEventListener("keydown", handleKeyDown);
    root.removeEventListener("dragenter", handleDragEnter);
    root.removeEventListener("dragover", handleDragOver);
    root.removeEventListener("dragleave", handleDragLeave);
    root.removeEventListener("drop", handleDrop);
  };
}

function normalizeCustomOutputSkills(payload) {
  const skills = Array.isArray(payload.skills) ? payload.skills : [];
  return {
    skills: skills
      .filter((skill) => skill && typeof skill === "object")
      .map((skill) => ({
        id: String(skill.id || ""),
        title: String(skill.title || ""),
        description: String(skill.description || ""),
        instruction: String(skill.instruction || ""),
        enabled: Boolean(skill.enabled),
        createdAt: String(skill.created_at || ""),
      }))
      .filter((skill) => skill.id && skill.title && skill.instruction),
    limit: Number(payload.limit || 2) || 2,
  };
}

function formatSkillTime(timestamp) {
  if (!timestamp) {
    return "";
  }
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  return date.toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function renderCustomOutputSkillCard(skill) {
  return `
    <article class="skill-box-card">
      <div class="skill-box-card__head">
        <div>
          <div class="skill-box-card__title">${escapeHtml(skill.title)}</div>
          <p class="skill-box-card__desc">${escapeHtml(skill.description)}</p>
        </div>
        <label class="skill-toggle">
          <input type="checkbox" data-skill-toggle="${escapeHtml(skill.id)}" ${skill.enabled ? "checked" : ""} />
          <span>${skill.enabled ? "已启用" : "已停用"}</span>
        </label>
      </div>
      <div class="skill-box-card__body">${escapeHtml(skill.instruction)}</div>
      <div class="skill-box-card__foot">
        <span>${formatSkillTime(skill.createdAt) || "刚刚创建"}</span>
        <button type="button" class="ghost-button skill-box-card__delete" data-skill-delete="${escapeHtml(skill.id)}">删除</button>
      </div>
    </article>
  `;
}

function syncSkillSubmitState(root) {
  const submit = root.querySelector("[data-skill-submit]");
  if (!submit) {
    return;
  }
  submit.disabled =
    skillsState.saving ||
    skillsState.skills.length >= skillsState.limit ||
    skillsState.draft.trim().length < 8;
}

function renderSkillsPage(root) {
  const remaining = Math.max(0, skillsState.limit - skillsState.skills.length);
  const disabled = skillsState.saving || skillsState.skills.length >= skillsState.limit;

  root.innerHTML = `
    <section class="page-head">
      <div>
        <h2>Skills</h2>
        <p>这里管理企业微信、QQ、飞书里在附件回复后追加的自定义输出框，最多 2 个。</p>
      </div>
    </section>
    <section class="skills-shell">
      <section class="panel skills-pane">
        <div class="skills-pane__head">
          <div>
            <strong>三通道附加输出</strong>
            <p>正常输出保留不动，只有带附件时才会按启用顺序追加在最后。</p>
          </div>
          <div class="skills-counter">${skillsState.skills.length}/${skillsState.limit}</div>
        </div>
        <div class="skills-flow">
          <span class="skills-flow__chip">正常输出</span>
          <span class="skills-flow__arrow">+</span>
          <span class="skills-flow__chip">自定义框 1</span>
          <span class="skills-flow__arrow">+</span>
          <span class="skills-flow__chip">自定义框 2</span>
        </div>
        ${skillsState.error ? `<div class="skills-status skills-status--error">${escapeHtml(skillsState.error)}</div>` : ""}
        ${skillsState.notice ? `<div class="skills-status skills-status--success">${escapeHtml(skillsState.notice)}</div>` : ""}
        <form class="skills-creator" data-skill-form>
          <label class="skills-creator__label" for="custom-output-skill-input">新增 1 个自定义输出 Skill</label>
          <textarea
            id="custom-output-skill-input"
            class="skills-creator__input"
            data-skill-input
            rows="5"
            placeholder="例：我想要一个更像竞赛教练的追问式讲解输出框，先指出关键突破口，再给学生两个反问，引导自己发现思路。"
            ${disabled ? "disabled" : ""}
          >${escapeHtml(skillsState.draft)}</textarea>
          <div class="skills-creator__foot">
            <span>${disabled ? "已达到 2 个上限，请先删除旧 Skill。" : `每次只生成 1 个，还可新增 ${remaining} 个。`}</span>
            <button
              type="submit"
              class="primary-button"
              data-skill-submit
              ${disabled || skillsState.draft.trim().length < 8 ? "disabled" : ""}
            >
              ${skillsState.saving ? "生成中..." : "生成并加入"}
            </button>
          </div>
        </form>
      </section>
      <section class="panel skills-list-panel">
        <div class="skills-list-panel__head">
          <strong>当前已保存的自定义输出 Skill</strong>
          <span>对企业微信、QQ、飞书生效</span>
        </div>
        <div class="skills-list">
          ${skillsState.skills.length
            ? skillsState.skills.map(renderCustomOutputSkillCard).join("")
            : `
              <div class="skills-empty">
                <strong>还没有自定义输出 Skill</strong>
                <p>添加后，企业微信、QQ、飞书的附件回复会在正常输出后面追加对应风格的额外输出框。</p>
              </div>
            `}
        </div>
      </section>
    </section>
  `;
}

async function loadCustomOutputSkills(root, options = {}) {
  const silent = Boolean(options.silent);
  if (!silent) {
    skillsState.loading = true;
    skillsState.error = "";
    if (root.isConnected) {
      renderSkillsPage(root);
    }
  }

  try {
    const data = await requestJson(CUSTOM_OUTPUT_SKILLS_API_PATH, { method: "GET" });
    const normalized = normalizeCustomOutputSkills(data);
    skillsState.skills = normalized.skills;
    skillsState.limit = normalized.limit;
    skillsState.loaded = true;
  } catch (error) {
    skillsState.error = error.message || "加载自定义输出 Skill 失败";
  } finally {
    skillsState.loading = false;
    if (root.isConnected) {
      renderSkillsPage(root);
    }
  }
}

async function submitCustomOutputSkill(root) {
  const requirement = skillsState.draft.trim();
  if (!requirement || skillsState.saving || skillsState.skills.length >= skillsState.limit) {
    return;
  }

  skillsState.saving = true;
  skillsState.error = "";
  skillsState.notice = "";
  if (root.isConnected) {
    renderSkillsPage(root);
  }

  try {
    const data = await requestJson(CUSTOM_OUTPUT_SKILLS_API_PATH, {
      method: "POST",
      body: JSON.stringify({ requirement }),
    });
    const normalized = normalizeCustomOutputSkills(data);
    skillsState.skills = normalized.skills;
    skillsState.limit = normalized.limit;
    skillsState.draft = "";
    skillsState.notice = "已新增 1 个自定义输出 Skill。";
  } catch (error) {
    skillsState.error = error.message || "新增失败";
  } finally {
    skillsState.saving = false;
    if (root.isConnected) {
      renderSkillsPage(root);
    }
  }
}

async function toggleCustomOutputSkill(root, skillId, enabled) {
  try {
    const data = await requestJson(`${CUSTOM_OUTPUT_SKILLS_API_PATH}/toggle`, {
      method: "POST",
      body: JSON.stringify({ id: skillId, enabled }),
    });
    const normalized = normalizeCustomOutputSkills(data);
    skillsState.skills = normalized.skills;
    skillsState.limit = normalized.limit;
    skillsState.notice = enabled ? "已启用自定义输出 Skill。" : "已停用自定义输出 Skill。";
    skillsState.error = "";
  } catch (error) {
    skillsState.error = error.message || "切换失败";
  } finally {
    if (root.isConnected) {
      renderSkillsPage(root);
    }
  }
}

async function deleteCustomOutputSkill(root, skillId) {
  try {
    const data = await requestJson(`${CUSTOM_OUTPUT_SKILLS_API_PATH}/delete`, {
      method: "POST",
      body: JSON.stringify({ id: skillId }),
    });
    const normalized = normalizeCustomOutputSkills(data);
    skillsState.skills = normalized.skills;
    skillsState.limit = normalized.limit;
    skillsState.notice = "已删除自定义输出 Skill。";
    skillsState.error = "";
  } catch (error) {
    skillsState.error = error.message || "删除失败";
  } finally {
    if (root.isConnected) {
      renderSkillsPage(root);
    }
  }
}

function mountSkillsPage(root) {
  const handleSubmit = (event) => {
    const form = event.target.closest("[data-skill-form]");
    if (!form) {
      return;
    }
    event.preventDefault();
    void submitCustomOutputSkill(root);
  };

  const handleInput = (event) => {
    const input = event.target.closest("[data-skill-input]");
    if (!input) {
      return;
    }
    skillsState.draft = input.value;
    syncSkillSubmitState(root);
  };

  const handleChange = (event) => {
    const toggle = event.target.closest("[data-skill-toggle]");
    if (!toggle) {
      return;
    }
    void toggleCustomOutputSkill(root, toggle.dataset.skillToggle, toggle.checked);
  };

  const handleClick = (event) => {
    const removeButton = event.target.closest("[data-skill-delete]");
    if (!removeButton) {
      return;
    }
    event.preventDefault();
    void deleteCustomOutputSkill(root, removeButton.dataset.skillDelete);
  };

  root.addEventListener("submit", handleSubmit);
  root.addEventListener("input", handleInput);
  root.addEventListener("change", handleChange);
  root.addEventListener("click", handleClick);

  renderSkillsPage(root);
  if (!skillsState.loaded && !skillsState.loading) {
    void loadCustomOutputSkills(root);
  }

  return () => {
    root.removeEventListener("submit", handleSubmit);
    root.removeEventListener("input", handleInput);
    root.removeEventListener("change", handleChange);
    root.removeEventListener("click", handleClick);
  };
}

function mountDashboardPage(root, pageId) {
  const rerender = () => {
    if (root.isConnected) {
      root.innerHTML = renderDashboardPage(pageId);
    }
  };

  const pollTimer = window.setInterval(() => {
    void loadDashboard(rerender, { silent: true });
  }, 30000);

  rerender();
  if (!dashboardState.loaded && !dashboardState.loading) {
    void loadDashboard(rerender);
  }

  return () => {
    window.clearInterval(pollTimer);
  };
}

function renderPageBody(pageId) {
  if (pageId === "chat") {
    return renderChat();
  }
  if (pageId === "memory") {
    return '<section data-memory-root class="memory-root"></section>';
  }
  if (pageId === "skills") {
    return '<section data-skills-root class="skills-root"></section>';
  }
  return '<section data-dashboard-root class="dashboard-root"></section>';
}

function renderApp() {
  if (disposeChatPage) {
    disposeChatPage();
    disposeChatPage = null;
  }

  if (disposeMemoryPage) {
    disposeMemoryPage();
    disposeMemoryPage = null;
  }

  if (disposeSkillsPage) {
    disposeSkillsPage();
    disposeSkillsPage = null;
  }
  if (disposeDashboardPage) {
    disposeDashboardPage();
    disposeDashboardPage = null;
  }

  const pageId = currentPage();
  const app = document.getElementById("app");

  app.innerHTML = `
    <div class="shell">
      <aside class="sidebar">
        <div class="brand">
          <div class="brand-mark">
            <img class="brand-mark-img" src="./logo.png" alt="MathClaw 标志" />
          </div>
          <div class="brand-copy">
            <h1>MathClaw</h1>
          </div>
        </div>
        <div class="nav-scroll">${renderNav(pageId)}</div>
      </aside>
      <main class="main">
        <div class="frame">${renderPageBody(pageId)}</div>
      </main>
    </div>
  `;

  app.querySelectorAll("[data-page]").forEach((button) => {
    button.addEventListener("click", () => {
      window.location.hash = `#/${button.dataset.page}`;
    });
  });

  if (pageId === "chat") {
    const root = app.querySelector("[data-chat-root]");
    disposeChatPage = mountChatPage(root);
  }

  if (pageId === "memory") {
    const root = app.querySelector("[data-memory-root]");
    try {
      disposeMemoryPage = mountMemoryPage(root);
    } catch (error) {
      root.innerHTML = `
        <section class="panel detail-panel">
          <div class="detail-empty">
            <strong>知识图谱暂时没有渲染出来</strong>
            <p>${escapeHtml(error?.message || String(error) || "未知错误")}</p>
          </div>
        </section>
      `;
      console.error("memory page render failed", error);
    }
  }

  if (pageId === "skills") {
    const root = app.querySelector("[data-skills-root]");
    disposeSkillsPage = mountSkillsPage(root);
  }
  if (!["chat", "memory", "skills"].includes(pageId)) {
    const root = app.querySelector("[data-dashboard-root]");
    disposeDashboardPage = mountDashboardPage(root, pageId);
  }
}

function graphTitle(graphKey) {
  return graphKey === "error" ? "错题图" : "知识点图";
}

function graphFile(graphKey) {
  return graphKey === "error"
    ? "memory/graphs/error_graph.json"
    : "memory/graphs/knowledge_graph.json";
}

function graphLegend(graphKey) {
  return graphKey === "error"
    ? ["对应知识点", "相似错误", "纠正建议", "重复出现"]
    : ["前置知识点", "相似知识点", "包含关系", "相关联知识点"];
}

function graphViewLabel(viewKey) {
  return viewKey === "total" ? "总览" : "焦点";
}

function graphRelationLabel(graphKey, relation) {
  const knowledgeMap = {
    prerequisite: "前置",
    similar: "相似",
    contains: "包含",
    related: "关联",
  };
  const errorMap = {
    corresponds_to: "对应知识点",
    similar_error: "相似错误",
  };
  const lookup = graphKey === "error" ? errorMap : knowledgeMap;
  return lookup[relation] || relation || "关联";
}

function graphRelationPriority(graphKey, relation) {
  const knowledgeOrder = ["prerequisite", "contains", "related", "similar"];
  const errorOrder = ["corresponds_to", "similar_error"];
  const order = graphKey === "error" ? errorOrder : knowledgeOrder;
  const index = order.indexOf(relation);
  return index === -1 ? order.length : index;
}

function mergedRelationLabel(graphKey, relations) {
  const ordered = [...new Set((relations || []).filter(Boolean))]
    .sort((left, right) => graphRelationPriority(graphKey, left) - graphRelationPriority(graphKey, right));
  const labels = ordered.map((relation) => graphRelationLabel(graphKey, relation));
  return labels.join(" / ") || "关联";
}

function formatGraphDate(value) {
  if (!value) {
    return "--";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value).slice(5, 10);
  }
  return date.toLocaleDateString("zh-CN", { month: "2-digit", day: "2-digit" });
}

function readExampleTexts(examples) {
  if (!Array.isArray(examples)) {
    return ["暂无代表样本"];
  }
  const items = examples
    .map((item) => {
      if (item && typeof item === "object") {
        return item.text || "";
      }
      return typeof item === "string" ? item : "";
    })
    .filter(Boolean);
  return items.length ? items : ["暂无代表样本"];
}

function readClassicExample(example, examples) {
  if (example && typeof example === "object") {
    const text = example.text || example.content || "";
    return typeof text === "string" && text.trim() ? text.trim() : "暂无经典例题";
  }
  if (typeof example === "string" && example.trim()) {
    return example.trim();
  }
  const fallbackExamples = readExampleTexts(examples);
  if (fallbackExamples.length && fallbackExamples[0] !== "暂无代表样本") {
    return fallbackExamples[0];
  }
  return "暂无经典例题";
}

function metricPairsForNode(graphKey, node) {
  if (graphKey === "error") {
    return [
      ["严重度", Number(node.severity || 0).toFixed(2)],
      ["错误次数", String(node.error_count || 0)],
      ["重复出现", node.repeated ? "是" : "否"],
      ["最近出现", formatGraphDate(node.last_seen)],
    ];
  }
  return [
    ["风险度", Number(node.risk || 0).toFixed(2)],
    ["掌握度", Number(node.mastery || 0).toFixed(2)],
    ["重要度", Number(node.importance || 0).toFixed(2)],
    ["最近出现", formatGraphDate(node.last_seen)],
  ];
}

function badgeForNode(graphKey, node) {
  if (graphKey === "error") {
    if (node.repeated) {
      return `重复 ${node.error_count || 1}`;
    }
    return `严重 ${Number(node.severity || 0).toFixed(2)}`;
  }
  if (node.risk != null) {
    return `风险 ${Number(node.risk || 0).toFixed(2)}`;
  }
  return `重要 ${Number(node.importance || 0).toFixed(2)}`;
}

function highlightsForNode(graphKey, node) {
  const items = [];
  if (typeof node.notes === "string" && node.notes.trim()) {
    items.push(node.notes.trim());
  }
  const related =
    graphKey === "error"
      ? node.correction_suggestions || node.related_knowledge_points
      : node.prerequisites || node.related_points;
  if (Array.isArray(related)) {
    related.filter(Boolean).slice(0, 3).forEach((item) => {
      items.push(String(item));
    });
  }
  return items.length ? items : ["暂无额外观察"];
}

function nodeSignalScore(graphKey, node) {
  if (graphKey === "error") {
    return clamp(
      Number(node.severity || 0) * 0.72
      + Math.min(Number(node.error_count || 0), 5) * 0.05
      + (node.repeated ? 0.14 : 0),
      0,
      1,
    );
  }

  return clamp(
    Number(node.risk || 0) * 0.78
    + Number(node.importance || 0) * 0.22,
    0,
    1,
  );
}

function clampNodeSize(graphKey, node) {
  const score = nodeSignalScore(graphKey, node);
  return Math.round(56 + score * 86);
}

function radialPosition(index, graphKey, size) {
  const centerX = GRAPH_STAGE.width / 2;
  const centerY = GRAPH_STAGE.height / 2;
  if (index === 0) {
    return { x: centerX, y: centerY };
  }
  let remaining = index - 1;
  let ring = 0;
  let capacity = 6;
  while (remaining >= capacity) {
    remaining -= capacity;
    ring += 1;
    capacity = 6 + ring * 4;
  }
  const angle = (remaining / capacity) * Math.PI * 2 - Math.PI / 2;
  const radius = 220 + ring * 148 + (graphKey === "error" ? 22 : 0);
  return {
    x: clamp(centerX + Math.cos(angle) * radius, size / 2 + 24, GRAPH_STAGE.width - size / 2 - 24),
    y: clamp(centerY + Math.sin(angle) * radius, size / 2 + 24, GRAPH_STAGE.height - size / 2 - 24),
  };
}

function normalizeGraphPayload(graphKey, payload, previousGraph) {
  const previousPositions = new Map(
    (previousGraph?.nodes || []).map((node) => [node.id, { x: node.x, y: node.y }]),
  );
  const rawNodes = Array.isArray(payload?.nodes) ? payload.nodes : [];
  const rawEdges = Array.isArray(payload?.edges) ? payload.edges : [];
  const focusIds = Array.isArray(payload?.focus_node_ids) ? payload.focus_node_ids : [];

  const rankedNodes = [...rawNodes].sort((left, right) => {
    const leftScore = nodeSignalScore(graphKey, left);
    const rightScore = nodeSignalScore(graphKey, right);
    return rightScore - leftScore;
  });

  const nodes = rankedNodes.map((node, index) => {
    const size = clampNodeSize(graphKey, node);
    const previous = previousPositions.get(node.id);
    const position = previous || radialPosition(index, graphKey, size);
    return {
      id: node.id,
      label: node.label || "未命名节点",
      badge: badgeForNode(graphKey, node),
      size,
      x: position.x,
      y: position.y,
      summary: node.notes || "暂无节点说明",
      metrics: metricPairsForNode(graphKey, node),
      highlights: highlightsForNode(graphKey, node),
      examples: readExampleTexts(node.examples),
      classicExample: readClassicExample(node.classic_example, node.examples),
      status: node.status || "active",
      strength: nodeSignalScore(graphKey, node),
      lastSeen: node.last_seen || null,
      isFocus: focusIds.includes(node.id),
    };
  });

  const nodeIds = new Set(nodes.map((node) => node.id));
  const uniqueEdges = new Map();
  rawEdges
    .filter((edge) => edge && nodeIds.has(edge.source) && nodeIds.has(edge.target) && edge.source !== edge.target)
    .forEach((edge, index) => {
      const pair = [edge.source, edge.target].sort();
      const relation = edge.relation || "related";
      const key = `${pair[0]}::${pair[1]}`;
      const nextEdge = {
        id: edge.id || `${pair[0]}-${pair[1]}-${index}`,
        source: pair[0],
        target: pair[1],
        relations: [relation],
        label: mergedRelationLabel(graphKey, [relation]),
        curve: 0,
        strength: Number(edge.strength || 0.35),
        status: edge.status || "active",
      };
      const existing = uniqueEdges.get(key);
      if (!existing) {
        uniqueEdges.set(key, nextEdge);
        return;
      }
      if (!existing.relations.includes(relation)) {
        existing.relations.push(relation);
        existing.label = mergedRelationLabel(graphKey, existing.relations);
      }
      existing.strength = Math.max(existing.strength, nextEdge.strength);
      existing.status = existing.status === "active" || nextEdge.status === "active" ? "active" : "candidate";
    });
  const edges = [...uniqueEdges.values()];

  return {
    title: graphTitle(graphKey),
    file: graphFile(graphKey),
    accent: graphKey === "error" ? "error" : "knowledge",
    legend: graphLegend(graphKey),
    updatedAt: payload?.updated_at || null,
    focusIds,
    stats: payload?.stats || {
      active: nodes.filter((node) => node.status === "active").length,
      candidate: nodes.filter((node) => node.status === "candidate").length,
      archived: 0,
    },
    nodes,
    edges,
  };
}

function applyMemoryGraphs(payload) {
  ["knowledge", "error"].forEach((graphKey) => {
    state.graphs[graphKey] = normalizeGraphPayload(
      graphKey,
      payload?.[graphKey] || {},
      state.graphs[graphKey],
    );
    const selectedId = state.selectedNodes[graphKey];
    const hasSelected = state.graphs[graphKey].nodes.some((node) => node.id === selectedId);
    if (!hasSelected) {
      state.selectedNodes[graphKey] = null;
    }
  });
}

async function loadMemoryGraphs(root, options = {}) {
  const silent = Boolean(options.silent);
  if (!silent) {
    state.memoryLoading = true;
    state.memoryError = "";
    if (root.isConnected) {
      renderMemoryPage(root);
    }
  }

  try {
    const payload = await requestChat(MEMORY_GRAPHS_API_PATH, { method: "GET" });
    applyMemoryGraphs(payload);
    state.memoryLoaded = true;
  } catch (error) {
    state.memoryError = error.message || "图谱加载失败";
  } finally {
    state.memoryLoading = false;
    if (root.isConnected) {
      renderMemoryPage(root);
    }
  }
}

function getGraph(graphKey = state.memoryGraph) {
  const graph = state.graphs[graphKey] || {};
  const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
  const edges = Array.isArray(graph.edges) ? graph.edges : [];

  return {
    title: graph.title || graphTitle(graphKey),
    file: graph.file || graphFile(graphKey),
    accent: graph.accent || (graphKey === "error" ? "error" : "knowledge"),
    legend: Array.isArray(graph.legend) ? graph.legend : graphLegend(graphKey),
    updatedAt: graph.updatedAt || null,
    focusIds: Array.isArray(graph.focusIds) ? graph.focusIds : [],
    stats: graph.stats || {
      active: nodes.filter((node) => node.status === "active").length,
      candidate: nodes.filter((node) => node.status === "candidate").length,
      archived: nodes.filter((node) => node.status === "archived").length,
    },
    nodes,
    edges,
  };
}

function rankedActiveNodes(graphKey = state.memoryGraph) {
  return [...getGraph(graphKey).nodes]
    .filter((node) => node.status === "active")
    .sort((left, right) => right.strength - left.strength);
}

function graphSubset(graph, nodeIds) {
  const allowed = new Set(nodeIds);
  const nodes = graph.nodes.filter((node) => allowed.has(node.id));
  const nodeSet = new Set(nodes.map((node) => node.id));
  const edges = graph.edges.filter((edge) => nodeSet.has(edge.source) && nodeSet.has(edge.target));
  return {
    ...graph,
    nodes,
    edges,
  };
}

function displayNodeIds(graphKey = state.memoryGraph) {
  const graph = getGraph(graphKey);
  const nodeById = new Map(graph.nodes.map((node) => [node.id, node]));
  const activeNodes = rankedActiveNodes(graphKey);
  const candidateNodes = graph.nodes
    .filter((node) => node.status === "candidate")
    .sort((left, right) => right.strength - left.strength);
  const activeIds = activeNodes
    .filter((node, index) => node.strength >= (graphKey === "error" ? 0.48 : 0.42) || index < (graphKey === "error" ? 10 : 12))
    .map((node) => node.id);
  const candidateIds = candidateNodes
    .filter((node, index) => node.strength >= 0.55 || index < 4)
    .map((node) => node.id);

  if (state.memoryView === "total") {
    return activeIds.length ? activeIds : candidateIds;
  }

  const seedIds = [];
  const selectedId = state.selectedNodes[graphKey];
  const hoveredId = state.hoveredNodes[graphKey];
  if (hoveredId) {
    seedIds.push(hoveredId);
  }
  if (selectedId) {
    seedIds.push(selectedId);
  }
  seedIds.push(
    ...graph.focusIds.filter((nodeId) => {
      const node = nodeById.get(nodeId);
      return node && node.strength >= (graphKey === "error" ? 0.48 : 0.42);
    }),
  );
  seedIds.push(...activeIds.slice(0, 6));

  const merged = [];
  const seen = new Set();
  seedIds.forEach((nodeId) => {
    if (nodeId && !seen.has(nodeId)) {
      seen.add(nodeId);
      merged.push(nodeId);
    }
  });

  const focusIds = [];
  merged.forEach((nodeId) => {
    if (focusIds.length >= 10) {
      return;
    }
    focusIds.push(nodeId);
    graph.edges.forEach((edge) => {
      if (focusIds.length >= 10) {
        return;
      }
      if (edge.source === nodeId && !seen.has(edge.target)) {
        seen.add(edge.target);
        focusIds.push(edge.target);
      }
      if (edge.target === nodeId && !seen.has(edge.source)) {
        seen.add(edge.source);
        focusIds.push(edge.source);
      }
    });
  });

  return focusIds.length ? focusIds : (activeIds.length ? activeIds.slice(0, 10) : candidateIds.slice(0, 10));
}

function getDisplayGraph(graphKey = state.memoryGraph) {
  return graphSubset(getGraph(graphKey), displayNodeIds(graphKey));
}

function getView(graphKey = state.memoryGraph) {
  return state.views[graphKey];
}

function getSelectedNode(graphKey = state.memoryGraph) {
  const graph = getDisplayGraph(graphKey);
  const selectedId = state.selectedNodes[graphKey];
  return graph.nodes.find((node) => node.id === selectedId) || null;
}

function getHighlightNode(graphKey = state.memoryGraph) {
  const graph = getDisplayGraph(graphKey);
  const hoveredId = state.hoveredNodes[graphKey];
  if (hoveredId) {
    const hovered = graph.nodes.find((node) => node.id === hoveredId);
    if (hovered) {
      return hovered;
    }
  }
  return getSelectedNode(graphKey);
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function resetView(graphKey = state.memoryGraph) {
  state.views[graphKey] = { x: -110, y: -10, scale: 0.9 };
  if (graphKey === "error") {
    state.views[graphKey] = { x: -120, y: -10, scale: 0.9 };
  }
}

function connectedEdgeIds(graph, nodeId) {
  return new Set(
    graph.edges
      .filter((edge) => edge.source === nodeId || edge.target === nodeId)
      .map((edge) => edge.id),
  );
}

function connectedNodeIds(graph, nodeId) {
  const ids = new Set([nodeId]);
  graph.edges.forEach((edge) => {
    if (edge.source === nodeId) {
      ids.add(edge.target);
    }
    if (edge.target === nodeId) {
      ids.add(edge.source);
    }
  });
  return ids;
}

function edgeGeometry(source, target, curve = 0) {
  const dx = target.x - source.x;
  const dy = target.y - source.y;
  const distance = Math.max(Math.hypot(dx, dy), 1);

  const normalX = -dy / distance;
  const normalY = dx / distance;
  const offset = clamp(distance * 0.18, 40, 120) * curve;
  const controlX = (source.x + target.x) / 2 + normalX * offset;
  const controlY = (source.y + target.y) / 2 + normalY * offset;

  const labelX = 0.25 * source.x + 0.5 * controlX + 0.25 * target.x;
  const labelY = 0.25 * source.y + 0.5 * controlY + 0.25 * target.y;

  return {
    path: `M ${source.x} ${source.y} Q ${controlX} ${controlY} ${target.x} ${target.y}`,
    labelX,
    labelY,
  };
}

function renderGraphEdges(graph, highlightNode) {
  const edgeIds = highlightNode ? connectedEdgeIds(graph, highlightNode.id) : new Set();
  const activeNodeIds = highlightNode ? connectedNodeIds(graph, highlightNode.id) : null;

  return graph.edges
    .map((edge) => {
      const source = graph.nodes.find((node) => node.id === edge.source);
      const target = graph.nodes.find((node) => node.id === edge.target);
      if (!source || !target) {
        return "";
      }

      const geometry = edgeGeometry(source, target, edge.curve);
      const isActive = edgeIds.has(edge.id);
      const isMuted = activeNodeIds && !isActive;
      const strokeWidth = (edge.strength || 0.35) > 0.75 ? 3.4 : (edge.strength || 0.35) > 0.55 ? 2.6 : 1.9;

      return `
        <path
          class="graph-edge${isActive ? " is-active" : ""}${isMuted ? " is-muted" : ""}${edge.status === "candidate" ? " is-candidate" : ""}"
          d="${geometry.path}"
          style="stroke-width:${strokeWidth}px"
        ></path>
        <text
          class="graph-edge-label${isActive ? " is-active" : ""}${isMuted ? " is-muted" : ""}${edge.status === "candidate" ? " is-candidate" : ""}"
          x="${geometry.labelX}"
          y="${geometry.labelY}"
        >${edge.label}</text>
      `;
    })
    .join("");
}

function renderGraphNodes(graph, highlightNode, selectedNode) {
  const activeNodeIds = highlightNode ? connectedNodeIds(graph, highlightNode.id) : null;

  return graph.nodes
    .map((node) => {
      const isActive = highlightNode?.id === node.id;
      const isSelected = selectedNode?.id === node.id;
      const isMuted = activeNodeIds && !activeNodeIds.has(node.id);

      return `
        <button
          class="graph-node graph-node--${graph.accent}${isActive ? " is-active" : ""}${isSelected ? " is-selected" : ""}${isMuted ? " is-muted" : ""}${node.status === "candidate" ? " is-candidate" : ""}${node.isFocus ? " is-focus" : ""}"
          type="button"
          data-node-id="${node.id}"
          style="left:${node.x}px; top:${node.y}px; width:${node.size}px; height:${node.size}px;"
        >
          <span class="graph-node__title">${node.label}</span>
          <span class="graph-node__badge">${node.badge}</span>
        </button>
      `;
    })
    .join("");
}

function renderRelationList(graph, nodeId) {
  return graph.edges
    .filter((edge) => edge.source === nodeId || edge.target === nodeId)
    .map((edge) => {
      const peerId = edge.source === nodeId ? edge.target : edge.source;
      const peer = graph.nodes.find((item) => item.id === peerId);
      return `
        <li class="detail-list__item">
          <span class="detail-list__label">${edge.label}</span>
          <strong>${peer ? peer.label : "未命名节点"}</strong>
        </li>
      `;
    })
    .join("");
}

function renderMetrics(metrics) {
  return metrics
    .map(([label, value]) => `
      <div class="metric-card">
        <span>${label}</span>
        <strong>${value}</strong>
      </div>
    `)
    .join("");
}

function renderTextList(items) {
  return items.map((item) => `<li>${item}</li>`).join("");
}

function renderDetailPanel(graph, node) {
  if (!node) {
    return `
      <div class="detail-empty">
        <strong>点击节点查看详情</strong>
        <p>支持拖动节点、拖动画布和滚轮缩放。</p>
      </div>
    `;
  }

  const relations = renderRelationList(graph, node.id);

  return `
    <div class="detail-header">
      <div>
        <h3>${node.label}</h3>
        <p>${node.summary}</p>
      </div>
      <div class="detail-header__actions">
        <button
          class="detail-delete"
          type="button"
          data-memory-action="delete-node"
          ${state.memoryDeleting ? "disabled" : ""}
        >${state.memoryDeleting ? "删除中..." : "删除"}</button>
        <button class="detail-close" type="button" data-memory-action="clear-selection">×</button>
      </div>
    </div>
    <div class="detail-tags">
      <span class="detail-tag">${node.status === "candidate" ? "候选节点" : "活跃节点"}</span>
      <span class="detail-tag">${node.lastSeen ? `最近更新 ${formatGraphDate(node.lastSeen)}` : "最近更新 --"}</span>
    </div>
    <section class="metric-grid">${renderMetrics(node.metrics)}</section>
    <section class="detail-section">
      <h4>关键观察</h4>
      <ul class="detail-list">${renderTextList(node.highlights)}</ul>
    </section>
    ${graph.accent === "error" ? `
      <section class="detail-section">
        <h4>经典例题</h4>
        <div class="detail-example-card">${escapeHtml(node.classicExample || "暂无经典例题")}</div>
      </section>
    ` : ""}
    <section class="detail-section">
      <h4>连接关系</h4>
      <ul class="detail-list">${relations || '<li>当前没有连接边。</li>'}</ul>
    </section>
    <section class="detail-section">
      <h4>近 15 天代表样本</h4>
      <ul class="detail-list">${renderTextList(node.examples)}</ul>
    </section>
  `;
}

async function deleteSelectedMemoryNode(root) {
  const graphKey = state.memoryGraph;
  const graph = getGraph(graphKey);
  const selectedId = state.selectedNodes[graphKey];
  const node = graph.nodes.find((item) => item.id === selectedId);
  if (!node || state.memoryDeleting) {
    return;
  }

  const confirmed = window.confirm(`删除「${node.label}」及其关联连边？这会清除它在当前图谱里的数据。`);
  if (!confirmed) {
    return;
  }

  state.memoryDeleting = true;
  state.memoryError = "";
  if (root.isConnected) {
    renderMemoryPage(root);
  }

  try {
    const payload = await requestJson(MEMORY_GRAPH_DELETE_API_PATH, {
      method: "POST",
      body: JSON.stringify({
        graph: graphKey,
        node_id: node.id,
      }),
    });
    applyMemoryGraphs(payload);
    state.selectedNodes[graphKey] = null;
    state.hoveredNodes[graphKey] = null;
  } catch (error) {
    state.memoryError = error.message || "删除节点失败";
  } finally {
    state.memoryDeleting = false;
    if (root.isConnected) {
      renderMemoryPage(root);
    }
  }
}

function renderLegend(graph) {
  return graph.legend.map((label) => `<span class="legend-chip">${label}</span>`).join("");
}

function renderGraphStats(graph) {
  const stats = graph.stats || { active: 0, candidate: 0, archived: 0 };
  return `
    <div class="graph-stats">
      <span class="graph-stat"><strong>${stats.active || 0}</strong><span>活跃</span></span>
      <span class="graph-stat"><strong>${stats.candidate || 0}</strong><span>候选</span></span>
      <span class="graph-stat"><strong>${stats.archived || 0}</strong><span>归档</span></span>
    </div>
  `;
}

function renderMemoryPage(root) {
  const fullGraph = getGraph();
  const graph = getDisplayGraph();
  const view = getView();
  const selectedNode = getSelectedNode();
  const highlightNode = getHighlightNode();
  const isPanning = state.interaction?.type === "pan";
  const updatedLabel = fullGraph.updatedAt
    ? `已连接真实图谱 · 更新于 ${new Date(fullGraph.updatedAt).toLocaleString("zh-CN", {
        hour12: false,
      })}`
    : state.memoryLoaded
      ? "已连接真实图谱"
      : "正在加载真实图谱...";
  const toolbarHint = state.memoryError
    ? `图谱加载失败：${escapeHtml(state.memoryError)}`
    : state.memoryLoading && !state.memoryLoaded
      ? "正在同步知识图谱..."
      : `${updatedLabel} · ${state.memoryView === "focus" ? "只看最近更新和核心关联" : "查看全部活跃节点"}`;
  const emptyState = !graph.nodes.length
    ? `
      <div class="detail-empty">
        <strong>${state.memoryLoading ? "正在同步图谱" : "还没有图谱数据"}</strong>
        <p>${state.memoryLoading ? "正在读取最新知识点图和错题图。" : "等用户产生学习记录后，这里会自动出现真实图谱节点。"}</p>
      </div>
    `
    : "";

  root.innerHTML = `
    <section class="page-head page-head--memory">
      <div>
        <h2>${PAGE_META.memory.title}</h2>
        ${PAGE_META.memory.description ? `<p>${PAGE_META.memory.description}</p>` : ""}
      </div>
    </section>
    <section class="panel graph-workspace">
      <div class="graph-toolbar">
        <div class="toolbar-left">
          <div class="segmented">
            <button class="segment${state.memoryGraph === "knowledge" ? " active" : ""}" type="button" data-graph-key="knowledge">知识点图</button>
            <button class="segment${state.memoryGraph === "error" ? " active" : ""}" type="button" data-graph-key="error">错题图</button>
          </div>
          <div class="segmented">
            <button class="segment${state.memoryView === "focus" ? " active" : ""}" type="button" data-view-key="focus">焦点</button>
            <button class="segment${state.memoryView === "total" ? " active" : ""}" type="button" data-view-key="total">总览</button>
          </div>
          <div class="graph-hint">${toolbarHint}</div>
        </div>
        <div class="toolbar-actions">
          ${renderGraphStats(fullGraph)}
          <button class="icon-button" type="button" data-memory-action="zoom-out">－</button>
          <button class="icon-button" type="button" data-memory-action="zoom-in">＋</button>
          <button class="ghost-button" type="button" data-memory-action="reset-view">重置视图</button>
        </div>
      </div>
      <div class="graph-board">
        <div class="graph-stage">
          <div class="graph-viewport${isPanning ? " is-panning" : ""}" data-viewport>
            <div class="graph-world" style="transform: translate(${view.x}px, ${view.y}px) scale(${view.scale});">
              <svg class="graph-svg" viewBox="0 0 ${GRAPH_STAGE.width} ${GRAPH_STAGE.height}" aria-hidden="true">
                ${renderGraphEdges(graph, highlightNode)}
              </svg>
              <div class="graph-node-layer">
                ${renderGraphNodes(graph, highlightNode, selectedNode)}
              </div>
            </div>
            ${emptyState}
            <div class="graph-overlay">
              <div class="graph-overlay__label">${graph.title} · ${graphViewLabel(state.memoryView)}视图</div>
              <div class="graph-overlay__legend">${renderLegend(graph)}</div>
            </div>
          </div>
        </div>
        <aside class="panel detail-panel">
          ${renderDetailPanel(graph, selectedNode)}
        </aside>
      </div>
    </section>
  `;
}

function mountMemoryPage(root) {
  const pollTimer = window.setInterval(() => {
    void loadMemoryGraphs(root, { silent: true });
  }, 15000);

  const handleClick = (event) => {
    if (state.suppressClick) {
      state.suppressClick = false;
      return;
    }

    const graphKeyButton = event.target.closest("[data-graph-key]");
    if (graphKeyButton) {
      state.memoryGraph = graphKeyButton.dataset.graphKey;
      renderMemoryPage(root);
      return;
    }

    const viewKeyButton = event.target.closest("[data-view-key]");
    if (viewKeyButton) {
      state.memoryView = viewKeyButton.dataset.viewKey;
      renderMemoryPage(root);
      return;
    }

    const nodeButton = event.target.closest("[data-node-id]");
    if (nodeButton) {
      state.selectedNodes[state.memoryGraph] = nodeButton.dataset.nodeId;
      renderMemoryPage(root);
      return;
    }

    const actionButton = event.target.closest("[data-memory-action]");
    if (actionButton) {
      const action = actionButton.dataset.memoryAction;
      if (action === "delete-node") {
        void deleteSelectedMemoryNode(root);
        return;
      }
      if (action === "zoom-in") {
        getView().scale = clamp(getView().scale * 1.08, 0.55, 1.8);
      }
      if (action === "zoom-out") {
        getView().scale = clamp(getView().scale * 0.92, 0.55, 1.8);
      }
      if (action === "reset-view") {
        resetView();
      }
      if (action === "clear-selection") {
        state.selectedNodes[state.memoryGraph] = null;
      }
      renderMemoryPage(root);
      return;
    }
  };

  const handlePointerDown = (event) => {
    const nodeButton = event.target.closest("[data-node-id]");
    if (nodeButton) {
      const node = getGraph().nodes.find((item) => item.id === nodeButton.dataset.nodeId);
      if (!node) {
        return;
      }
      state.selectedNodes[state.memoryGraph] = node.id;
      state.interaction = {
        type: "node",
        nodeId: node.id,
        startX: event.clientX,
        startY: event.clientY,
        originX: node.x,
        originY: node.y,
        moved: false,
      };
      return;
    }

    if (event.target.closest("[data-viewport]")) {
      const view = getView();
      state.interaction = {
        type: "pan",
        startX: event.clientX,
        startY: event.clientY,
        originX: view.x,
        originY: view.y,
        moved: false,
      };
      renderMemoryPage(root);
    }
  };

  const handlePointerMove = (event) => {
    if (!state.interaction) {
      const hoveredId = event.target instanceof Element
        ? event.target.closest("[data-node-id]")?.dataset.nodeId || null
        : null;
      if (state.hoveredNodes[state.memoryGraph] !== hoveredId) {
        state.hoveredNodes[state.memoryGraph] = hoveredId;
        renderMemoryPage(root);
      }
      return;
    }

    const deltaX = event.clientX - state.interaction.startX;
    const deltaY = event.clientY - state.interaction.startY;

    if (Math.abs(deltaX) > 4 || Math.abs(deltaY) > 4) {
      state.interaction.moved = true;
    }

    if (state.interaction.type === "pan") {
      const view = getView();
      view.x = state.interaction.originX + deltaX;
      view.y = state.interaction.originY + deltaY;
      renderMemoryPage(root);
      return;
    }

    if (state.interaction.type === "node") {
      const view = getView();
      const node = getGraph().nodes.find((item) => item.id === state.interaction.nodeId);
      if (!node) {
        return;
      }
      node.x = clamp(state.interaction.originX + deltaX / view.scale, 90, GRAPH_STAGE.width - 90);
      node.y = clamp(state.interaction.originY + deltaY / view.scale, 90, GRAPH_STAGE.height - 90);
      renderMemoryPage(root);
    }
  };

  const handlePointerLeave = () => {
    if (!state.interaction && state.hoveredNodes[state.memoryGraph]) {
      state.hoveredNodes[state.memoryGraph] = null;
      renderMemoryPage(root);
    }
  };

  const handlePointerUp = (event) => {
    if (!state.interaction) {
      return;
    }

    if (state.interaction.type === "node") {
      state.selectedNodes[state.memoryGraph] = state.interaction.nodeId;
    }

    if (
      state.interaction.type === "pan"
      && !state.interaction.moved
      && event.target instanceof Element
      && event.target.closest("[data-viewport]")
    ) {
      state.selectedNodes[state.memoryGraph] = null;
    }

    if (state.interaction.moved) {
      state.suppressClick = true;
    }

    state.interaction = null;
    renderMemoryPage(root);
  };

  const handleWheel = (event) => {
    const viewport = event.target.closest("[data-viewport]");
    if (!viewport) {
      return;
    }

    event.preventDefault();

    const view = getView();
    const bounds = viewport.getBoundingClientRect();
    const pointerX = event.clientX - bounds.left;
    const pointerY = event.clientY - bounds.top;
    const graphX = (pointerX - view.x) / view.scale;
    const graphY = (pointerY - view.y) / view.scale;
    const nextScale = clamp(view.scale * (event.deltaY < 0 ? 1.08 : 0.92), 0.55, 1.8);

    view.x = pointerX - graphX * nextScale;
    view.y = pointerY - graphY * nextScale;
    view.scale = nextScale;

    renderMemoryPage(root);
  };

  root.addEventListener("click", handleClick);
  root.addEventListener("pointerdown", handlePointerDown);
  root.addEventListener("pointermove", handlePointerMove);
  root.addEventListener("pointerleave", handlePointerLeave);
  root.addEventListener("wheel", handleWheel, { passive: false });
  window.addEventListener("pointerup", handlePointerUp);

  renderMemoryPage(root);
  void loadMemoryGraphs(root, { silent: state.memoryLoaded });

  return () => {
    window.clearInterval(pollTimer);
    root.removeEventListener("click", handleClick);
    root.removeEventListener("pointerdown", handlePointerDown);
    root.removeEventListener("pointermove", handlePointerMove);
    root.removeEventListener("pointerleave", handlePointerLeave);
    root.removeEventListener("wheel", handleWheel);
    window.removeEventListener("pointerup", handlePointerUp);
  };
}

window.addEventListener("hashchange", renderApp);
window.addEventListener("DOMContentLoaded", renderApp);

if (!window.location.hash) {
  window.location.hash = "#/chat";
}
