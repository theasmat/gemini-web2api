"""Embedded Web Dashboard for gemini-web2api (/dash)."""
import json

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Gemini Web2API Dashboard</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #090c15;
      --bg-card: rgba(16, 22, 36, 0.75);
      --bg-card-hover: rgba(22, 30, 48, 0.85);
      --bg-input: rgba(10, 14, 24, 0.85);
      --border: rgba(255, 255, 255, 0.08);
      --border-glow: rgba(99, 102, 241, 0.35);
      --text: #f1f5f9;
      --text-muted: #94a3b8;
      --primary: #6366f1;
      --primary-hover: #4f46e5;
      --accent-blue: #38bdf8;
      --accent-purple: #a855f7;
      --accent-emerald: #10b981;
      --accent-amber: #f59e0b;
      --accent-rose: #f43f5e;
      --radius: 14px;
      --radius-sm: 8px;
      --shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5);
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      background-color: var(--bg);
      background-image: 
        radial-gradient(circle at 15% 15%, rgba(99, 102, 241, 0.12) 0%, transparent 40%),
        radial-gradient(circle at 85% 85%, rgba(56, 189, 248, 0.08) 0%, transparent 40%);
      background-attachment: fixed;
      color: var(--text);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      line-height: 1.5;
    }

    /* Navbar */
    header {
      background: rgba(9, 12, 21, 0.85);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      border-bottom: 1px solid var(--border);
      position: sticky;
      top: 0;
      z-index: 50;
      padding: 14px 28px;
    }

    .nav-container {
      max-width: 1400px;
      margin: 0 auto;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
      text-decoration: none;
      color: var(--text);
    }

    .brand-logo {
      width: 38px;
      height: 38px;
      border-radius: 10px;
      background: linear-gradient(135deg, #6366f1, #38bdf8);
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      font-size: 20px;
      color: white;
      box-shadow: 0 4px 15px rgba(99, 102, 241, 0.4);
    }

    .brand-title {
      font-family: 'Outfit', sans-serif;
      font-size: 1.25rem;
      font-weight: 700;
      letter-spacing: -0.02em;
      background: linear-gradient(90deg, #fff, #94a3b8);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }

    .version-tag {
      font-size: 0.72rem;
      padding: 2px 7px;
      background: rgba(99, 102, 241, 0.15);
      border: 1px solid rgba(99, 102, 241, 0.3);
      border-radius: 6px;
      color: var(--accent-blue);
      font-family: 'JetBrains Mono', monospace;
    }

    .nav-status {
      display: flex;
      align-items: center;
      gap: 16px;
    }

    .status-pill {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 6px 14px;
      border-radius: 20px;
      background: rgba(16, 185, 129, 0.1);
      border: 1px solid rgba(16, 185, 129, 0.25);
      font-size: 0.82rem;
      font-weight: 500;
      color: #34d399;
    }

    .status-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #10b981;
      box-shadow: 0 0 10px #10b981;
      animation: pulse 2s infinite;
    }

    @keyframes pulse {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.5; transform: scale(0.85); }
    }

    /* User Profile Pill */
    .user-pill {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 4px 14px 4px 6px;
      border-radius: 24px;
      background: rgba(99, 102, 241, 0.12);
      border: 1px solid rgba(99, 102, 241, 0.35);
      backdrop-filter: blur(8px);
      box-shadow: 0 2px 10px rgba(99, 102, 241, 0.2);
    }

    .user-avatar {
      width: 28px;
      height: 28px;
      border-radius: 50%;
      object-fit: cover;
      border: 1.5px solid var(--accent-blue);
    }

    .user-avatar-fallback {
      width: 28px;
      height: 28px;
      border-radius: 50%;
      background: linear-gradient(135deg, #6366f1, #38bdf8);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 13px;
      font-weight: 700;
      color: white;
      text-transform: uppercase;
    }

    .user-info {
      display: flex;
      flex-direction: column;
      line-height: 1.2;
    }

    .user-name {
      font-size: 0.82rem;
      font-weight: 600;
      color: var(--text);
    }

    .user-email {
      font-size: 0.72rem;
      color: var(--accent-blue);
      font-family: 'JetBrains Mono', monospace;
    }

    .btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      padding: 8px 16px;
      border-radius: var(--radius-sm);
      font-weight: 600;
      font-size: 0.85rem;
      cursor: pointer;
      transition: all 0.2s ease;
      border: 1px solid transparent;
      text-decoration: none;
      font-family: inherit;
    }

    .btn-primary {
      background: linear-gradient(135deg, var(--primary), var(--primary-hover));
      color: white;
      box-shadow: 0 4px 14px rgba(99, 102, 241, 0.35);
    }

    .btn-primary:hover {
      box-shadow: 0 6px 20px rgba(99, 102, 241, 0.5);
      transform: translateY(-1px);
    }

    .btn-secondary {
      background: rgba(255, 255, 255, 0.05);
      color: var(--text);
      border-color: var(--border);
    }

    .btn-secondary:hover {
      background: rgba(255, 255, 255, 0.1);
      border-color: rgba(255, 255, 255, 0.2);
    }

    /* Main Container */
    main {
      max-width: 1400px;
      margin: 24px auto;
      padding: 0 24px;
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 24px;
      width: 100%;
    }

    .grid-3 {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 20px;
    }

    .card {
      background: var(--bg-card);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 22px;
      box-shadow: var(--shadow);
      display: flex;
      flex-direction: column;
      gap: 16px;
      transition: border-color 0.2s ease, transform 0.2s ease;
    }

    .card:hover {
      border-color: var(--border-glow);
    }

    .card-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .card-title {
      font-family: 'Outfit', sans-serif;
      font-size: 1.05rem;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .card-badge {
      font-size: 0.72rem;
      padding: 3px 8px;
      border-radius: 6px;
      font-weight: 600;
    }

    .badge-pro {
      background: rgba(168, 85, 247, 0.15);
      border: 1px solid rgba(168, 85, 247, 0.35);
      color: #c084fc;
    }

    .badge-anon {
      background: rgba(56, 189, 248, 0.15);
      border: 1px solid rgba(56, 189, 248, 0.35);
      color: #38bdf8;
    }

    .badge-warn {
      background: rgba(245, 158, 11, 0.15);
      border: 1px solid rgba(245, 158, 11, 0.35);
      color: #fbbf24;
    }

    .stat-list {
      display: flex;
      flex-direction: column;
      gap: 10px;
    }

    .stat-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 0.85rem;
      padding: 8px 12px;
      background: rgba(0, 0, 0, 0.2);
      border-radius: var(--radius-sm);
      border: 1px solid rgba(255, 255, 255, 0.03);
    }

    .stat-label { color: var(--text-muted); }
    .stat-val { font-family: 'JetBrains Mono', monospace; font-weight: 500; }

    .val-ok { color: var(--accent-emerald); }
    .val-no { color: var(--text-muted); }

    /* Copy box */
    .copy-box {
      display: flex;
      align-items: center;
      background: var(--bg-input);
      border: 1px solid var(--border);
      border-radius: var(--radius-sm);
      padding: 6px 10px;
      gap: 8px;
    }

    .copy-text {
      flex: 1;
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.82rem;
      color: var(--accent-blue);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .copy-btn {
      background: transparent;
      border: none;
      color: var(--text-muted);
      cursor: pointer;
      padding: 4px;
      border-radius: 4px;
      transition: color 0.2s;
    }

    .copy-btn:hover { color: white; }

    /* Tabs Layout */
    .tab-bar {
      display: flex;
      gap: 8px;
      border-bottom: 1px solid var(--border);
      padding-bottom: 8px;
      margin-top: 10px;
    }

    .tab-btn {
      padding: 8px 18px;
      border-radius: var(--radius-sm);
      background: transparent;
      border: 1px solid transparent;
      color: var(--text-muted);
      font-weight: 600;
      font-size: 0.88rem;
      cursor: pointer;
      transition: all 0.2s;
      font-family: inherit;
    }

    .tab-btn.active {
      background: rgba(99, 102, 241, 0.15);
      border-color: rgba(99, 102, 241, 0.35);
      color: white;
    }

    .tab-btn:hover:not(.active) {
      color: var(--text);
      background: rgba(255, 255, 255, 0.04);
    }

    .tab-pane { display: none; }
    .tab-pane.active { display: block; }

    /* Playground */
    .playground-container {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 20px;
    }

    @media (max-width: 900px) {
      .playground-container { grid-template-columns: 1fr; }
    }

    .form-group {
      display: flex;
      flex-direction: column;
      gap: 6px;
      margin-bottom: 14px;
    }

    .form-label {
      font-size: 0.82rem;
      font-weight: 500;
      color: var(--text-muted);
    }

    .form-input, .form-select, .form-textarea {
      width: 100%;
      background: var(--bg-input);
      border: 1px solid var(--border);
      border-radius: var(--radius-sm);
      padding: 10px 14px;
      color: var(--text);
      font-family: inherit;
      font-size: 0.88rem;
      transition: border-color 0.2s;
    }

    .form-input:focus, .form-select:focus, .form-textarea:focus {
      outline: none;
      border-color: var(--primary);
      box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2);
    }

    .form-textarea {
      resize: vertical;
      min-height: 110px;
      font-family: inherit;
    }

    .chat-output-card {
      display: flex;
      flex-direction: column;
      height: 100%;
      min-height: 380px;
    }

    .chat-output {
      flex: 1;
      background: var(--bg-input);
      border: 1px solid var(--border);
      border-radius: var(--radius-sm);
      padding: 16px;
      font-size: 0.9rem;
      line-height: 1.6;
      overflow-y: auto;
      white-space: pre-wrap;
      word-break: break-word;
      font-family: inherit;
    }

    .output-meta {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-top: 10px;
      font-size: 0.78rem;
      color: var(--text-muted);
      font-family: 'JetBrains Mono', monospace;
    }

    /* Logs Table */
    .logs-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.83rem;
      font-family: 'JetBrains Mono', monospace;
    }

    .logs-table th, .logs-table td {
      padding: 10px 14px;
      text-align: left;
      border-bottom: 1px solid var(--border);
    }

    .logs-table th {
      color: var(--text-muted);
      font-weight: 500;
      background: rgba(0, 0, 0, 0.2);
    }

    .logs-table tr:hover td {
      background: rgba(255, 255, 255, 0.02);
    }

    .badge-200 { color: var(--accent-emerald); }
    .badge-400, .badge-401 { color: var(--accent-amber); }
    .badge-500, .badge-502 { color: var(--accent-rose); }

    /* Modals */
    .modal-backdrop {
      position: fixed;
      top: 0; left: 0; width: 100%; height: 100%;
      background: rgba(0, 0, 0, 0.75);
      backdrop-filter: blur(8px);
      display: none;
      align-items: center;
      justify-content: center;
      z-index: 100;
      padding: 20px;
    }

    .modal-backdrop.open { display: flex; }

    .modal-box {
      background: #111728;
      border: 1px solid var(--border);
      border-radius: var(--radius);
      width: 100%;
      max-width: 580px;
      padding: 28px;
      box-shadow: 0 20px 50px rgba(0, 0, 0, 0.7);
      display: flex;
      flex-direction: column;
      gap: 18px;
    }

    .modal-title {
      font-family: 'Outfit', sans-serif;
      font-size: 1.25rem;
      font-weight: 700;
    }

    pre code {
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.82rem;
      background: rgba(0, 0, 0, 0.4);
      padding: 12px;
      border-radius: var(--radius-sm);
      display: block;
      overflow-x: auto;
      border: 1px solid var(--border);
      color: #e2e8f0;
      line-height: 1.4;
    }

    /* Footer */
    footer {
      border-top: 1px solid var(--border);
      padding: 20px;
      text-align: center;
      font-size: 0.8rem;
      color: var(--text-muted);
      margin-top: auto;
    }
  </style>
</head>
<body>

  <!-- Navbar -->
  <header>
    <div class="nav-container">
      <div class="brand">
        <div class="brand-logo">G</div>
        <div>
          <div class="brand-title">Gemini Web2API</div>
        </div>
        <span class="version-tag" id="ver-tag">v1.2.0</span>
      </div>

      <div class="nav-status">
        <div class="status-pill">
          <div class="status-dot"></div>
          <span id="server-status-text">Server Active</span>
        </div>
        <div class="user-pill" id="nav-user-pill" style="display: none;">
          <img id="nav-user-avatar" class="user-avatar" src="" alt="Avatar" style="display: none;" />
          <div id="nav-user-avatar-fallback" class="user-avatar-fallback">👤</div>
          <div class="user-info">
            <span class="user-name" id="nav-user-name">Google User</span>
            <span class="user-email" id="nav-user-email"></span>
          </div>
        </div>
        <button class="btn btn-secondary" onclick="openLoginModal()">🔑 Web Login</button>
        <button class="btn btn-secondary" onclick="openSyncModal()">🔄 Sync JSON</button>
        <button class="btn btn-secondary" id="btn-nav-logout" onclick="logoutAuth()" style="display: none; border-color: rgba(244, 63, 94, 0.4); color: #fda4af;">🚪 Logout</button>
      </div>
    </div>
  </header>

  <!-- Main Body -->
  <main>

    <!-- Top Metric Grid -->
    <div class="grid-3">

      <!-- Auth State Card -->
      <div class="card">
        <div class="card-header">
          <span class="card-title">🛡️ Authentication Status</span>
          <span class="card-badge badge-anon" id="auth-mode-badge">Anonymous</span>
        </div>
        <div class="stat-list">
          <div class="stat-item" style="background: rgba(99, 102, 241, 0.08); border-color: rgba(99, 102, 241, 0.2);">
            <span class="stat-label">Google Account:</span>
            <span class="stat-val" id="stat-account-name">Anonymous</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">Account Email:</span>
            <span class="stat-val" id="stat-account-email">None</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">Google Session:</span>
            <span class="stat-val" id="stat-cookie">Checking...</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">SAPISID Hash Auth:</span>
            <span class="stat-val" id="stat-sapisid">No</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">XSRF Token (SNlM0e):</span>
            <span class="stat-val" id="stat-xsrf">No</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">Account Index (/u/):</span>
            <span class="stat-val" id="stat-authuser">Default (0)</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">Pro Routing:</span>
            <span class="stat-val" id="stat-pro">Inactive (Flash Mode)</span>
          </div>
        </div>
        <div style="display: flex; gap: 8px; margin-top: auto;">
          <button class="btn btn-primary" id="btn-card-login" style="flex: 1;" onclick="triggerAutoLogin()">🚀 Launch Login Helper</button>
          <button class="btn btn-secondary" id="btn-card-logout" style="display: none; border-color: rgba(244, 63, 94, 0.4); color: #fda4af;" onclick="logoutAuth()">🚪 Logout</button>
        </div>
      </div>


      <!-- Quick Connect Card -->
      <div class="card">
        <div class="card-header">
          <span class="card-title">⚡ OpenAI API Endpoints</span>
          <span class="card-badge badge-pro">Drop-in</span>
        </div>
        <div class="form-group">
          <span class="form-label">Base URL (OpenAI clients, Cherry Studio, etc.):</span>
          <div class="copy-box">
            <span class="copy-text" id="base-url-text">http://localhost:8081/v1</span>
            <button class="copy-btn" onclick="copyText('base-url-text')">📋</button>
          </div>
        </div>
        <div class="form-group">
          <span class="form-label">API Key:</span>
          <div class="copy-box">
            <span class="copy-text" id="api-key-text">sk-gemini</span>
            <button class="copy-btn" onclick="copyText('api-key-text')">📋</button>
          </div>
        </div>
        <div class="form-group">
          <span class="form-label">Top Models:</span>
          <div style="display: flex; flex-wrap: wrap; gap: 6px;">
            <span class="version-tag">gemini-3.5-flash-thinking</span>
            <span class="version-tag">gemini-3.6-flash</span>
            <span class="version-tag">gemini-3.1-pro</span>
          </div>
        </div>
      </div>

      <!-- Server Health & Streaming -->
      <div class="card">
        <div class="card-header">
          <span class="card-title">📊 Server Health</span>
          <span class="card-badge badge-pro" id="streaming-badge">httpx SSE</span>
        </div>
        <div class="stat-list">
          <div class="stat-item">
            <span class="stat-label">Port & Host:</span>
            <span class="stat-val" id="stat-host-port">8081 (0.0.0.0)</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">Default Model:</span>
            <span class="stat-val" id="stat-default-model">gemini-3.6-flash</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">Temporary Chats:</span>
            <span class="stat-val" id="stat-temp-chats">Disabled</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">Proxy:</span>
            <span class="stat-val" id="stat-proxy">None</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">Total Requests:</span>
            <span class="stat-val" id="stat-req-count">0</span>
          </div>
        </div>
      </div>

    </div>

    <!-- Tab Bar -->
    <div class="tab-bar">
      <button class="tab-btn active" data-tab="playground" onclick="switchTab('playground', event)">🧪 API Playground</button>
      <button class="tab-btn" data-tab="logs" onclick="switchTab('logs', event)">📜 Live Request Logs</button>
      <button class="tab-btn" data-tab="snippets" onclick="switchTab('snippets', event)">💻 Client Snippets</button>
      <button class="tab-btn" data-tab="settings" onclick="switchTab('settings', event)">⚙️ Configuration</button>
    </div>

    <!-- Tab 1: Playground -->
    <div id="tab-playground" class="tab-pane active">
      <div class="playground-container">
        <div class="card">
          <span class="card-title">Prompt & Options</span>
          <div class="form-group">
            <label class="form-label">Model</label>
            <select class="form-select" id="play-model">
              <option value="gemini-3.5-flash-thinking" selected>gemini-3.5-flash-thinking (Deep Reasoning)</option>
              <option value="gemini-3.6-flash">gemini-3.6-flash (Fast & Accurate)</option>
              <option value="gemini-3.1-pro">gemini-3.1-pro (Gemini Advanced Pro)</option>
              <option value="gemini-auto">gemini-auto (Automatic Routing)</option>
              <option value="gemini-flash-lite">gemini-flash-lite (Lightweight)</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">Thinking Depth (@think=N suffix)</label>
            <select class="form-select" id="play-think">
              <option value="">Default (@think=0 deepest)</option>
              <option value="@think=0">@think=0 (Maximum thinking output)</option>
              <option value="@think=2">@think=2 (Medium depth)</option>
              <option value="@think=4">@think=4 (Fastest response)</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">User Prompt</label>
            <textarea class="form-textarea" id="play-prompt" placeholder="Ask Gemini anything... e.g. 'Explain quantum computing in simple terms.'"></textarea>
          </div>
          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px;">
            <label style="display: inline-flex; align-items: center; gap: 8px; font-size: 0.82rem; color: var(--text-muted); cursor: pointer;">
              <input type="checkbox" id="play-stateful" checked style="accent-color: var(--primary);">
              <span>Keep Conversation History (Stateful Chat)</span>
            </label>
            <span id="play-turn-count" style="font-size: 0.75rem; color: var(--accent-blue); font-family: 'JetBrains Mono', monospace;">0 turns</span>
          </div>
          <div style="display: flex; gap: 8px;">
            <button class="btn btn-primary" id="btn-send-chat" onclick="sendPlaygroundChat()" style="flex: 1;">🚀 Send (Streaming)</button>
            <button class="btn btn-secondary" onclick="clearPlayground()">Clear History</button>
          </div>
        </div>

        <div class="card chat-output-card">
          <div class="card-header">
            <span class="card-title">Conversation Stream</span>
            <button class="btn btn-secondary" style="padding: 4px 10px; font-size: 0.75rem;" onclick="clearPlayground()">🗑️ Reset</button>
          </div>
          <div class="chat-output" id="play-output">Response will appear here in real time...</div>
          <div class="output-meta">
            <span id="output-latency">Latency: -- ms</span>
            <span id="output-tokens">Tokens: -- prompt / -- completion</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Tab 2: Live Logs -->
    <div id="tab-logs" class="tab-pane">
      <div class="card">
        <div class="card-header">
          <span class="card-title">📜 Real-time API Request Log</span>
          <button class="btn btn-secondary" onclick="refreshLogs()">🔄 Refresh</button>
        </div>
        <div style="overflow-x: auto;">
          <table class="logs-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Client</th>
                <th>Method</th>
                <th>Endpoint</th>
                <th>Model</th>
                <th>Status</th>
                <th>Duration</th>
              </tr>
            </thead>
            <tbody id="logs-table-body">
              <tr><td colspan="7" style="text-align: center; color: var(--text-muted);">No requests logged yet</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Tab 3: Client Snippets -->
    <div id="tab-snippets" class="tab-pane">
      <div class="card">
        <span class="card-title">Integration Code Snippets</span>
        <div style="display: flex; flex-direction: column; gap: 16px;">
          <div>
            <div class="form-label" style="margin-bottom: 6px;">Python (OpenAI SDK)</div>
            <pre><code>from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8081/v1",
    api_key="sk-gemini"
)

resp = client.chat.completions.create(
    model="gemini-3.5-flash-thinking",
    messages=[{"role": "user", "content": "Hello Gemini!"}]
)
print(resp.choices[0].message.content)</code></pre>
          </div>

          <div>
            <div class="form-label" style="margin-bottom: 6px;">curl (Bash / macOS / Linux)</div>
            <pre><code>curl http://localhost:8081/v1/chat/completions \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer sk-gemini" \\
  -d '{"model":"gemini-3.5-flash-thinking","messages":[{"role":"user","content":"Hello!"}]}'</code></pre>
          </div>

          <div>
            <div class="form-label" style="margin-bottom: 6px;">Gemini CLI</div>
            <pre><code>export GEMINI_API_KEY=none
export GOOGLE_GEMINI_BASE_URL=http://localhost:8081
gemini</code></pre>
          </div>
        </div>
      </div>
    </div>

    <!-- Tab 4: Configuration -->
    <div id="tab-settings" class="tab-pane">
      <div class="card">
        <span class="card-title">⚙️ Server Runtime Configuration</span>
        <div class="form-group">
          <label class="form-label">Listening Port</label>
          <input type="number" class="form-input" id="cfg-port" value="8081">
        </div>
        <div class="form-group">
          <label class="form-label">Default Model</label>
          <input type="text" class="form-input" id="cfg-default-model" value="gemini-3.6-flash">
        </div>
        <div class="form-group">
          <label class="form-label">HTTP Proxy (e.g. http://127.0.0.1:7890)</label>
          <input type="text" class="form-input" id="cfg-proxy" placeholder="Optional HTTP/HTTPS proxy">
        </div>
        <div class="form-group">
          <label class="form-label">Temporary Chats (Do not save conversations to Google account history)</label>
          <select class="form-select" id="cfg-temp-chats">
            <option value="false">Disabled (Conversations persist in history)</option>
            <option value="true">Enabled (Temporary chats only)</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">API Keys (JSON list or comma separated)</label>
          <input type="text" class="form-input" id="cfg-api-keys" placeholder='e.g. ["sk-gemini"]'>
        </div>
        <div>
          <button class="btn btn-primary" onclick="saveSettings()">Save Configuration</button>
        </div>
      </div>
    </div>

  </main>

  <!-- Login Modal -->
  <div class="modal-backdrop" id="login-modal">
    <div class="modal-box" style="max-width: 540px;">
      <div class="modal-title">🔑 Google Gemini Web Login Helper</div>
      <p style="font-size: 0.88rem; color: var(--text-muted); margin-bottom: 14px;">
        Automatically launch an isolated browser session, sign in to your Google Account at <code>gemini.google.com</code>, and hot-sync session credentials directly to the server.
      </p>

      <!-- Live status card -->
      <div id="login-status-box" style="background: rgba(0, 0, 0, 0.35); border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 14px; margin-bottom: 14px;">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
          <span style="font-size: 0.82rem; font-weight: 600; color: var(--text-muted);">STATUS</span>
          <span id="login-badge" class="card-badge badge-anon" style="font-size: 0.72rem;">Ready</span>
        </div>
        <div id="login-msg" style="font-size: 0.88rem; line-height: 1.5; color: var(--text);">
          Click "Launch Browser" to start login automation.
        </div>
        <div id="login-spinner" style="display: none; align-items: center; gap: 8px; margin-top: 10px; font-size: 0.8rem; color: var(--accent-blue);">
          <div class="status-dot"></div>
          <span>Waiting for Google account sign-in in browser window...</span>
        </div>
      </div>

      <div class="form-group" style="margin-bottom: 14px;">
        <span class="form-label">Or Run in Terminal via CLI:</span>
        <pre><code>gemini-web2api login</code></pre>
      </div>

      <div style="display: flex; gap: 8px; justify-content: flex-end;">
        <button class="btn btn-secondary" onclick="closeLoginModal()">Close</button>
        <button class="btn btn-primary" id="btn-modal-launch" onclick="triggerAutoLogin()">🚀 Launch Browser & Sign In</button>
      </div>
    </div>
  </div>

  <!-- Sync JSON Modal -->
  <div class="modal-backdrop" id="sync-modal">
    <div class="modal-box">
      <div class="modal-title">🔄 Paste gemini-auth.json</div>
      <p style="font-size: 0.88rem; color: var(--text-muted);">
        Paste the contents of <code>gemini-auth.json</code> or browser extension export:
      </p>
      <textarea class="form-textarea" id="sync-json-input" placeholder='{"cookie": "...", "sapisid": "...", "xsrf_token": "...", "auth_user": "0"}' style="min-height: 140px; font-family: 'JetBrains Mono', monospace; font-size: 0.8rem;"></textarea>
      <div style="display: flex; gap: 8px; justify-content: flex-end;">
        <button class="btn btn-secondary" onclick="closeSyncModal()">Cancel</button>
        <button class="btn btn-primary" onclick="submitAuthSync()">Apply & Sync Credentials</button>
      </div>
    </div>
  </div>

  <!-- Footer -->
  <footer>
    Gemini Web2API • OpenAI Compatible Proxy Server • Zero Cost • Cross Platform
  </footer>

  <script>
    let pollTimer = null;

    async function fetchStatus() {
      try {
        const res = await fetch('/api/status');
        if (!res.ok) return;
        const data = await res.json();
        updateUIWithStatus(data);
      } catch (err) {
        console.error('Failed to fetch status:', err);
      }
    }

    function updateUIWithStatus(data) {
      if (!data) return;
      document.getElementById('ver-tag').textContent = 'v' + (data.version || '1.2.0');
      document.getElementById('base-url-text').textContent = window.location.origin + '/v1';
      document.getElementById('stat-host-port').textContent = (data.port || 8081) + ' (' + (data.host || '0.0.0.0') + ')';
      document.getElementById('stat-default-model').textContent = data.default_model || 'gemini-3.6-flash';
      document.getElementById('stat-temp-chats').textContent = data.temporary_chats ? 'Enabled' : 'Disabled';
      document.getElementById('stat-proxy').textContent = data.proxy || 'None';
      document.getElementById('stat-req-count').textContent = data.total_requests || '0';

      const auth = data.auth || {};
      const modeBadge = document.getElementById('auth-mode-badge');
      const isAuth = Boolean(auth.authenticated || auth.has_cookie);

      // Account metadata display
      const navUserPill = document.getElementById('nav-user-pill');
      const navUserName = document.getElementById('nav-user-name');
      const navUserEmail = document.getElementById('nav-user-email');
      const navUserAvatar = document.getElementById('nav-user-avatar');
      const navUserFallback = document.getElementById('nav-user-avatar-fallback');

      const statAccountName = document.getElementById('stat-account-name');
      const statAccountEmail = document.getElementById('stat-account-email');

      if (isAuth) {
        const accName = auth.account_name || (auth.account_email ? auth.account_email.split('@')[0] : 'Google Account');
        const accEmail = auth.account_email || '';
        const accPhoto = auth.account_photo || '';

        statAccountName.textContent = accName;
        statAccountName.className = 'stat-val val-ok';
        statAccountEmail.textContent = accEmail || 'Session Linked';
        statAccountEmail.className = 'stat-val ' + (accEmail ? 'val-ok' : 'val-no');

        if (navUserName) navUserName.textContent = accName;
        if (navUserEmail) {
          navUserEmail.textContent = accEmail;
          navUserEmail.style.display = accEmail ? 'inline' : 'none';
        }
        if (navUserAvatar && navUserFallback) {
          if (accPhoto) {
            navUserAvatar.src = accPhoto;
            navUserAvatar.style.display = 'block';
            navUserFallback.style.display = 'none';
          } else {
            navUserAvatar.style.display = 'none';
            navUserFallback.style.display = 'flex';
            navUserFallback.textContent = accName.charAt(0).toUpperCase() || '👤';
          }
        }
        if (navUserPill) navUserPill.style.display = 'flex';
      } else {
        statAccountName.textContent = 'Anonymous';
        statAccountName.className = 'stat-val val-no';
        statAccountEmail.textContent = 'None';
        statAccountEmail.className = 'stat-val val-no';
        if (navUserPill) navUserPill.style.display = 'none';
      }

      if (auth.pro_ready) {
        modeBadge.textContent = 'Gemini Advanced (Pro Ready)';
        modeBadge.className = 'card-badge badge-pro';
      } else if (auth.authenticated) {
        modeBadge.textContent = 'Authenticated (Standard)';
        modeBadge.className = 'card-badge badge-pro';
      } else {
        modeBadge.textContent = 'Anonymous Mode';
        modeBadge.className = 'card-badge badge-anon';
      }

      // Toggle logout buttons and login button text
      const navLogout = document.getElementById('btn-nav-logout');
      const cardLogout = document.getElementById('btn-card-logout');
      const cardLogin = document.getElementById('btn-card-login');

      if (navLogout) navLogout.style.display = isAuth ? 'inline-flex' : 'none';
      if (cardLogout) cardLogout.style.display = isAuth ? 'inline-flex' : 'none';
      if (cardLogin) cardLogin.textContent = isAuth ? '🔄 Refresh Login' : '🚀 Launch Login Helper';

      const cookieVal = document.getElementById('stat-cookie');
      cookieVal.textContent = auth.has_cookie ? `Present (${auth.cookie_count || 0} cookies)` : 'None';
      cookieVal.className = 'stat-val ' + (auth.has_cookie ? 'val-ok' : 'val-no');

      const sapisidVal = document.getElementById('stat-sapisid');
      sapisidVal.textContent = auth.has_sapisid ? 'Valid' : 'None';
      sapisidVal.className = 'stat-val ' + (auth.has_sapisid ? 'val-ok' : 'val-no');

      const xsrfVal = document.getElementById('stat-xsrf');
      xsrfVal.textContent = auth.has_xsrf ? 'Valid' : 'None';
      xsrfVal.className = 'stat-val ' + (auth.has_xsrf ? 'val-ok' : 'val-no');

      document.getElementById('stat-authuser').textContent = auth.auth_user !== null ? `/u/${auth.auth_user}` : 'Default (0)';
      
      const proVal = document.getElementById('stat-pro');
      proVal.textContent = auth.pro_ready ? 'Active (Pro Enabled)' : 'Fallback to Flash';
      proVal.className = 'stat-val ' + (auth.pro_ready ? 'val-ok' : 'val-no');

      if (data.api_keys && data.api_keys.length > 0) {
        document.getElementById('api-key-text').textContent = data.api_keys[0];
      } else {
        document.getElementById('api-key-text').textContent = 'None (Auth Disabled)';
      }
    }

    async function logoutAuth() {
      if (!confirm('Are you sure you want to log out and clear all saved Google Gemini session credentials?')) return;
      try {
        const res = await fetch('/api/auth/logout', { method: 'POST' });
        const result = await res.json();
        alert(result.message || 'Logged out successfully. Server reset to Anonymous mode.');
        fetchStatus();
      } catch (err) {
        alert('Logout failed: ' + err.message);
      }
    }


    let playgroundHistory = [];

    function escapeHtml(text) {
      const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
      return String(text).replace(/[&<>"']/g, m => map[m]);
    }

    function renderPlaygroundHistory(currentStreamText = '') {
      const outputEl = document.getElementById('play-output');
      const turnCountEl = document.getElementById('play-turn-count');

      if (playgroundHistory.length === 0 && !currentStreamText) {
        outputEl.innerHTML = '<span style="color: var(--text-muted);">Response will appear here in real time...</span>';
        if (turnCountEl) turnCountEl.textContent = '0 turns';
        return;
      }

      let html = '';
      for (const msg of playgroundHistory) {
        if (msg.role === 'user') {
          html += `
            <div style="margin-bottom: 12px; padding: 10px 14px; background: rgba(99, 102, 241, 0.12); border-left: 3px solid var(--primary); border-radius: 6px;">
              <div style="font-size: 0.72rem; font-weight: 700; color: #818cf8; margin-bottom: 4px; font-family: 'JetBrains Mono', monospace;">👤 YOU</div>
              <div style="white-space: pre-wrap; font-size: 0.88rem;">${escapeHtml(msg.content)}</div>
            </div>`;
        } else if (msg.role === 'assistant') {
          html += `
            <div style="margin-bottom: 14px; padding: 12px 14px; background: rgba(0, 0, 0, 0.25); border-left: 3px solid var(--accent-blue); border-radius: 6px;">
              <div style="font-size: 0.72rem; font-weight: 700; color: #38bdf8; margin-bottom: 4px; font-family: 'JetBrains Mono', monospace;">✦ GEMINI</div>
              <div style="white-space: pre-wrap; font-size: 0.88rem; line-height: 1.6;">${escapeHtml(msg.content)}</div>
            </div>`;
        }
      }

      if (currentStreamText) {
        html += `
          <div style="margin-bottom: 14px; padding: 12px 14px; background: rgba(0, 0, 0, 0.25); border-left: 3px solid var(--accent-blue); border-radius: 6px;">
            <div style="font-size: 0.72rem; font-weight: 700; color: #38bdf8; margin-bottom: 4px; font-family: 'JetBrains Mono', monospace;">✦ GEMINI (Streaming...)</div>
            <div style="white-space: pre-wrap; font-size: 0.88rem; line-height: 1.6;">${escapeHtml(currentStreamText)}</div>
          </div>`;
      }

      outputEl.innerHTML = html;
      outputEl.scrollTop = outputEl.scrollHeight;
      if (turnCountEl) turnCountEl.textContent = `${Math.floor(playgroundHistory.length / 2)} turns`;
    }

    async function sendPlaygroundChat() {
      const model = document.getElementById('play-model').value + document.getElementById('play-think').value;
      const promptInput = document.getElementById('play-prompt');
      const prompt = promptInput.value.trim();
      const outputEl = document.getElementById('play-output');
      const sendBtn = document.getElementById('btn-send-chat');
      const isStateful = document.getElementById('play-stateful')?.checked ?? true;

      if (!prompt) {
        alert('Please enter a prompt');
        return;
      }

      if (!isStateful) {
        playgroundHistory = [];
      }

      playgroundHistory.push({ role: 'user', content: prompt });
      promptInput.value = '';
      renderPlaygroundHistory('Thinking and streaming response...');

      sendBtn.disabled = true;
      const startTime = performance.now();
      let promptTokens = Math.ceil(prompt.length / 4);

      // Resolve authorization header
      const headers = { 'Content-Type': 'application/json' };
      const keySpan = document.getElementById('api-key-text');
      const keyVal = keySpan ? keySpan.textContent.trim() : '';
      if (keyVal && !keyVal.startsWith('None') && keyVal !== '') {
        headers['Authorization'] = 'Bearer ' + keyVal;
      } else {
        headers['Authorization'] = 'Bearer sk-gemini';
      }

      try {
        const res = await fetch('/v1/chat/completions', {
          method: 'POST',
          headers: headers,
          body: JSON.stringify({
            model: model,
            messages: isStateful ? playgroundHistory : [{ role: 'user', content: prompt }],
            stream: true
          })
        });

        if (!res.ok) {
          const err = await res.json();
          const errText = 'Error: ' + (err.error?.message || JSON.stringify(err));
          playgroundHistory.push({ role: 'assistant', content: errText });
          renderPlaygroundHistory();
          return;
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let fullText = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split(String.fromCharCode(10));
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const dataStr = line.slice(6).trim();
              if (dataStr === '[DONE]') continue;
              try {
                const json = JSON.parse(dataStr);
                if (json.error) {
                  const errMsg = json.error.message || JSON.stringify(json.error);
                  fullText += String.fromCharCode(10, 10) + '⚠️ Error: ' + errMsg;
                  renderPlaygroundHistory(fullText);
                  continue;
                }
                const delta = json.choices?.[0]?.delta?.content || '';
                fullText += delta;
                renderPlaygroundHistory(fullText);
              } catch (e) {}
            }
          }
        }

        playgroundHistory.push({ role: 'assistant', content: fullText });
        renderPlaygroundHistory();

        const duration = Math.round(performance.now() - startTime);
        document.getElementById('output-latency').textContent = `Latency: ${duration} ms`;
        document.getElementById('output-tokens').textContent = `Tokens: ~${promptTokens} prompt / ~${Math.ceil(fullText.length / 4)} completion`;
        refreshLogs();
      } catch (err) {
        playgroundHistory.push({ role: 'assistant', content: 'Network error: ' + err.message });
        renderPlaygroundHistory();
      } finally {
        sendBtn.disabled = false;
      }
    }

    function clearPlayground() {
      playgroundHistory = [];
      document.getElementById('play-prompt').value = '';
      renderPlaygroundHistory();
    }

    async function refreshLogs() {
      try {
        const res = await fetch('/api/logs');
        if (!res.ok) return;
        const logs = await res.json();
        const tbody = document.getElementById('logs-table-body');
        if (!logs || logs.length === 0) {
          tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-muted);">No requests logged yet</td></tr>';
          return;
        }
        tbody.innerHTML = logs.map(l => `
          <tr>
            <td>${l.time || '-'}</td>
            <td>${l.client || '-'}</td>
            <td><strong>${l.method || '-'}</strong></td>
            <td>${l.path || '-'}</td>
            <td>${l.model || '-'}</td>
            <td><span class="badge-${l.status || 200}">${l.status || 200}</span></td>
            <td>${l.duration_ms !== undefined ? l.duration_ms + 'ms' : '-'}</td>
          </tr>
        `).join('');
      } catch (e) {}
    }

    async function submitAuthSync() {
      const input = document.getElementById('sync-json-input').value.trim();
      if (!input) return;
      try {
        const payload = JSON.parse(input);
        const res = await fetch('/v1/auth/sync', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const result = await res.json();
        if (res.ok) {
          alert('Authentication synced successfully!');
          closeSyncModal();
          fetchStatus();
        } else {
          alert('Sync failed: ' + (result.error?.message || JSON.stringify(result)));
        }
      } catch (e) {
        alert('Invalid JSON: ' + e.message);
      }
    }

    let loginPollTimer = null;

    async function triggerAutoLogin() {
      const launchBtn = document.getElementById('btn-modal-launch');
      const badge = document.getElementById('login-badge');
      const msg = document.getElementById('login-msg');
      const spinner = document.getElementById('login-spinner');

      openLoginModal();
      if (launchBtn) launchBtn.disabled = true;
      if (badge) {
        badge.textContent = 'Launching...';
        badge.className = 'card-badge badge-pro';
      }
      if (msg) msg.textContent = 'Starting browser with dedicated profile...';
      if (spinner) spinner.style.display = 'flex';

      try {
        const res = await fetch('/api/auth/login', { method: 'POST' });
        const data = await res.json();
        if (msg) msg.textContent = data.message || 'Browser launched! Please sign in to Google / Gemini in the opened browser window.';

        // Start polling login status
        if (loginPollTimer) clearInterval(loginPollTimer);
        loginPollTimer = setInterval(pollLoginStatus, 1500);
      } catch (e) {
        if (msg) msg.textContent = 'Could not trigger login helper: ' + e.message;
        if (badge) {
          badge.textContent = 'Error';
          badge.className = 'card-badge badge-anon';
        }
        if (spinner) spinner.style.display = 'none';
        if (launchBtn) launchBtn.disabled = false;
      }
    }

    async function pollLoginStatus() {
      try {
        const res = await fetch('/api/auth/login-status');
        if (!res.ok) return;
        const data = await res.json();
        const badge = document.getElementById('login-badge');
        const msg = document.getElementById('login-msg');
        const spinner = document.getElementById('login-spinner');
        const launchBtn = document.getElementById('btn-modal-launch');

        if (data.status === 'running') {
          if (badge) {
            badge.textContent = 'Running';
            badge.className = 'card-badge badge-pro';
          }
          if (msg) msg.textContent = data.message || 'Waiting for login...';
          if (spinner) spinner.style.display = 'flex';
        } else if (data.status === 'success') {
          if (loginPollTimer) { clearInterval(loginPollTimer); loginPollTimer = null; }
          if (badge) {
            badge.textContent = 'Authenticated!';
            badge.className = 'card-badge badge-pro';
          }
          const accName = data.auth?.account_name || 'User';
          const accEmail = data.auth?.account_email || '';
          const accStr = accEmail ? `${accName} (${accEmail})` : accName;
          if (msg) msg.innerHTML = `✅ <strong>Login Successful!</strong><br>Authenticated as ${accStr}. Credentials hot-synced with server.`;
          if (spinner) spinner.style.display = 'none';
          if (launchBtn) launchBtn.disabled = false;
          fetchStatus();
          setTimeout(() => {
            closeLoginModal();
          }, 2500);
        } else if (data.status === 'error') {
          if (loginPollTimer) { clearInterval(loginPollTimer); loginPollTimer = null; }
          if (badge) {
            badge.textContent = 'Failed';
            badge.className = 'card-badge badge-anon';
          }
          if (msg) msg.textContent = '❌ ' + (data.message || 'Login failed or timed out.');
          if (spinner) spinner.style.display = 'none';
          if (launchBtn) launchBtn.disabled = false;
        }
      } catch (err) {}
    }

    async function saveSettings() {
      const port = parseInt(document.getElementById('cfg-port').value, 10);
      const defaultModel = document.getElementById('cfg-default-model').value.trim();
      const proxy = document.getElementById('cfg-proxy').value.trim() || null;
      const tempChats = document.getElementById('cfg-temp-chats').value === 'true';
      const apiKeysRaw = document.getElementById('cfg-api-keys').value.trim();

      let apiKeys = [];
      if (apiKeysRaw) {
        try {
          apiKeys = JSON.parse(apiKeysRaw);
        } catch {
          apiKeys = apiKeysRaw.split(',').map(s => s.trim()).filter(Boolean);
        }
      }

      try {
        const res = await fetch('/api/config', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            port: port,
            default_model: defaultModel,
            proxy: proxy,
            temporary_chats: tempChats,
            api_keys: apiKeys
          })
        });
        if (res.ok) {
          alert('Configuration updated successfully!');
          fetchStatus();
        } else {
          const err = await res.json();
          alert('Failed to save config: ' + (err.error?.message || JSON.stringify(err)));
        }
      } catch (e) {
        alert('Error saving config: ' + e.message);
      }
    }

    function switchTab(name, evt) {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
      let btn = evt ? (evt.currentTarget || evt.target) : null;
      if (!btn) {
        btn = document.querySelector(`.tab-btn[data-tab="${name}"]`) || document.querySelector(`.tab-btn[onclick*="${name}"]`);
      }
      if (btn) btn.classList.add('active');
      const pane = document.getElementById('tab-' + name);
      if (pane) pane.classList.add('active');
      if (name === 'logs') refreshLogs();
    }

    function copyText(id) {
      const text = document.getElementById(id).textContent;
      navigator.clipboard.writeText(text);
      alert('Copied: ' + text);
    }

    function openLoginModal() { document.getElementById('login-modal').classList.add('open'); }
    function closeLoginModal() { document.getElementById('login-modal').classList.remove('open'); }
    function openSyncModal() { document.getElementById('sync-modal').classList.add('open'); }
    function closeSyncModal() { document.getElementById('sync-modal').classList.remove('open'); }

    // Init
    fetchStatus();
    pollTimer = setInterval(fetchStatus, 5000);
  </script>
</body>
</html>
"""

def render_dashboard() -> str:
    """Return the standalone dashboard HTML."""
    return HTML_TEMPLATE
