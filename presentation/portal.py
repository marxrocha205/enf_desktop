"""Interface Web Moderna para Cadastro de Medicamentos, Leitura de QR Code e Gestão de Estoque."""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["Portal Web (Medicamentos & Estoque)"])

PORTAL_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Medica - Sentinela Enf &bull; Gestão de Lotes, Validade e Estoque IoT</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <script src="https://unpkg.com/html5-qrcode@2.3.8/html5-qrcode.min.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
  <style>
    :root {
      --bg-dark: #0b0f19;
      --bg-card: rgba(18, 24, 38, 0.78);
      --bg-input: rgba(11, 15, 25, 0.65);
      --border-color: rgba(255, 255, 255, 0.08);
      --border-focus: #06b6d4;
      --primary: #06b6d4;
      --primary-hover: #0891b2;
      --primary-gradient: linear-gradient(135deg, #06b6d4 0%, #3b82f6 100%);
      --accent-gradient: linear-gradient(135deg, #8b5cf6 0%, #d946ef 100%);
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
      --success: #10b981;
      --error: #ef4444;
      --warning: #f59e0b;
      --radius-sm: 8px;
      --radius-md: 14px;
      --radius-lg: 22px;
      --shadow-glow: 0 0 35px rgba(6, 182, 212, 0.22);
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
      background-color: var(--bg-dark);
      color: var(--text-main);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 32px 16px;
      position: relative;
      overflow-x: hidden;
    }

    .glow-orb-1 {
      position: absolute;
      top: -120px;
      left: -120px;
      width: 500px;
      height: 500px;
      background: radial-gradient(circle, rgba(6, 182, 212, 0.16) 0%, transparent 70%);
      pointer-events: none;
      z-index: 0;
    }
    .glow-orb-2 {
      position: absolute;
      bottom: -120px;
      right: -120px;
      width: 550px;
      height: 550px;
      background: radial-gradient(circle, rgba(139, 92, 246, 0.16) 0%, transparent 70%);
      pointer-events: none;
      z-index: 0;
    }

    .container {
      width: 100%;
      max-width: 720px;
      position: relative;
      z-index: 10;
    }

    .brand-header {
      text-align: center;
      margin-bottom: 24px;
    }

    .brand-badge {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 6px 14px;
      background: rgba(6, 182, 212, 0.1);
      border: 1px solid rgba(6, 182, 212, 0.3);
      border-radius: 9999px;
      font-size: 0.8rem;
      font-weight: 600;
      color: var(--primary);
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 12px;
    }

    .brand-badge .dot {
      width: 8px;
      height: 8px;
      background-color: var(--success);
      border-radius: 50%;
      box-shadow: 0 0 8px var(--success);
      animation: pulse 2s infinite;
    }

    @keyframes pulse {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.5; transform: scale(1.1); }
    }

    .brand-header h1 {
      font-size: 2.1rem;
      font-weight: 800;
      background: linear-gradient(135deg, #ffffff 40%, #94a3b8 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      letter-spacing: -0.02em;
    }

    .brand-header p {
      color: var(--text-muted);
      font-size: 0.95rem;
      margin-top: 6px;
    }

    .portal-card {
      background: var(--bg-card);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-lg);
      padding: 30px;
      box-shadow: 0 20px 40px -15px rgba(0, 0, 0, 0.6), var(--shadow-glow);
      transition: all 0.3s ease;
    }

    .qr-banner {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 14px 16px;
      background: linear-gradient(135deg, rgba(139, 92, 246, 0.14) 0%, rgba(6, 182, 212, 0.14) 100%);
      border: 1px solid rgba(139, 92, 246, 0.35);
      border-radius: var(--radius-md);
      margin-bottom: 20px;
    }

    .qr-banner-info h3 {
      font-size: 0.95rem;
      font-weight: 700;
      color: #e2e8f0;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .qr-banner-info p {
      font-size: 0.78rem;
      color: var(--text-muted);
      margin-top: 2px;
    }

    .btn-qr-scan {
      padding: 10px 16px;
      border: none;
      border-radius: var(--radius-sm);
      background: var(--accent-gradient);
      color: #ffffff;
      font-size: 0.85rem;
      font-weight: 700;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      white-space: nowrap;
      box-shadow: 0 4px 14px rgba(139, 92, 246, 0.35);
      transition: all 0.2s ease;
    }

    .btn-qr-scan:hover {
      transform: translateY(-2px);
      box-shadow: 0 6px 20px rgba(139, 92, 246, 0.5);
    }

    .form-section {
      display: flex;
      flex-direction: column;
      gap: 16px;
      animation: fadeIn 0.3s ease;
    }

    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(6px); }
      to { opacity: 1; transform: translateY(0); }
    }

    .input-group {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .input-group label {
      font-size: 0.85rem;
      font-weight: 600;
      color: #cbd5e1;
    }

    .input-row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }

    .input-field {
      width: 100%;
      padding: 12px 14px;
      background: var(--bg-input);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-sm);
      color: var(--text-main);
      font-family: inherit;
      font-size: 0.95rem;
      outline: none;
      transition: all 0.2s ease;
    }

    .input-field:focus, .input-field.highlight-qr {
      border-color: var(--border-focus);
      box-shadow: 0 0 0 3px rgba(6, 182, 212, 0.2);
      background: rgba(11, 15, 25, 0.85);
    }

    select.input-field {
      cursor: pointer;
      appearance: none;
      background-image: url("data:image/svg+xml;charset=UTF-8,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%2394a3b8' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3e%3cpolyline points='6 9 12 15 18 9'%3e%3c/polyline%3e%3c/svg%3e");
      background-repeat: no-repeat;
      background-position: right 14px center;
      background-size: 16px;
    }

    select.input-field option {
      background-color: #1e293b;
      color: #ffffff;
    }

    .btn-submit {
      width: 100%;
      padding: 14px;
      border: none;
      border-radius: var(--radius-sm);
      background: var(--primary-gradient);
      color: #ffffff;
      font-size: 1rem;
      font-weight: 700;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      transition: all 0.2s ease;
      box-shadow: 0 4px 16px rgba(6, 182, 212, 0.35);
      margin-top: 4px;
    }

    .btn-submit:hover {
      transform: translateY(-2px);
      box-shadow: 0 6px 20px rgba(6, 182, 212, 0.45);
    }

    .btn-submit:disabled {
      opacity: 0.6;
      cursor: not-allowed;
      transform: none;
    }

    .feedback-box {
      display: none;
      padding: 14px;
      border-radius: var(--radius-sm);
      font-size: 0.875rem;
      line-height: 1.4;
      margin-top: 18px;
      animation: fadeIn 0.3s ease;
    }

    .feedback-box.success {
      display: block;
      background: rgba(16, 185, 129, 0.12);
      border: 1px solid rgba(16, 185, 129, 0.3);
      color: #34d399;
    }

    .feedback-box.error {
      display: block;
      background: rgba(239, 68, 68, 0.12);
      border: 1px solid rgba(239, 68, 68, 0.3);
      color: #f87171;
    }

    /* Medication Table & Cards */
    .med-list-container {
      margin-top: 12px;
      max-height: 320px;
      overflow-y: auto;
      border: 1px solid var(--border-color);
      border-radius: var(--radius-sm);
      background: rgba(11, 15, 25, 0.4);
    }

    .med-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.85rem;
    }

    .med-table th {
      background: rgba(15, 23, 42, 0.8);
      color: var(--text-muted);
      text-align: left;
      padding: 10px 12px;
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      border-bottom: 1px solid var(--border-color);
      position: sticky;
      top: 0;
      z-index: 2;
    }

    .med-table td {
      padding: 10px 12px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.04);
      color: #e2e8f0;
    }

    .status-pill {
      display: inline-block;
      padding: 3px 8px;
      border-radius: 9999px;
      font-size: 0.7rem;
      font-weight: 700;
    }
    .status-ok { background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); }
    .status-low { background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); }
    .status-out { background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); }

    .btn-action-sm {
      padding: 4px 8px;
      border-radius: 4px;
      border: 1px solid var(--border-color);
      background: rgba(255, 255, 255, 0.05);
      color: #93c5fd;
      cursor: pointer;
      font-size: 0.75rem;
      font-weight: 600;
      transition: all 0.2s ease;
    }
    .btn-action-sm:hover {
      background: rgba(6, 182, 212, 0.2);
      border-color: var(--primary);
    }

    /* Native Dialog Modals */
    dialog.qr-modal {
      margin: auto;
      width: 94%;
      max-width: 520px;
      background: #111827;
      color: var(--text-main);
      border: 1px solid rgba(6, 182, 212, 0.35);
      border-radius: var(--radius-lg);
      padding: 24px;
      box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.85), var(--shadow-glow);
    }

    dialog.qr-modal::backdrop {
      background: rgba(5, 8, 17, 0.78);
      backdrop-filter: blur(6px);
    }

    .modal-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 16px;
      padding-bottom: 12px;
      border-bottom: 1px solid var(--border-color);
    }

    .modal-header h3 {
      font-size: 1.1rem;
      font-weight: 700;
      color: #f8fafc;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .btn-close-modal {
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid var(--border-color);
      color: var(--text-muted);
      width: 32px;
      height: 32px;
      border-radius: 8px;
      cursor: pointer;
      font-weight: 700;
      font-size: 1rem;
    }
    .btn-close-modal:hover {
      color: #fff;
      background: rgba(239, 68, 68, 0.25);
      border-color: rgba(239, 68, 68, 0.4);
    }

    .scanner-controls {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
      margin-bottom: 14px;
    }

    .btn-scanner-ctrl {
      padding: 10px 12px;
      border-radius: var(--radius-sm);
      border: 1px solid var(--border-color);
      background: rgba(255, 255, 255, 0.06);
      color: #e2e8f0;
      font-size: 0.82rem;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      transition: all 0.2s ease;
    }
    .btn-scanner-ctrl:hover, .btn-scanner-ctrl.active {
      background: rgba(6, 182, 212, 0.2);
      border-color: var(--primary);
      color: #fff;
    }

    #qr-reader {
      width: 100%;
      min-height: 220px;
      background: #070a12;
      border: 1px dashed rgba(6, 182, 212, 0.35);
      border-radius: var(--radius-md);
      overflow: hidden;
      display: flex;
      align-items: center;
      justify-content: center;
      color: var(--text-muted);
      font-size: 0.85rem;
      text-align: center;
      padding: 12px;
    }

    .qr-result-panel {
      display: none;
      margin-top: 16px;
      padding: 14px;
      background: rgba(16, 185, 129, 0.1);
      border: 1px solid rgba(16, 185, 129, 0.35);
      border-radius: var(--radius-md);
      animation: fadeIn 0.25s ease;
    }

    .qr-result-panel h4 {
      font-size: 0.9rem;
      color: #34d399;
      margin-bottom: 6px;
    }

    .qr-quick-actions {
      display: flex;
      gap: 8px;
      margin-top: 12px;
      flex-wrap: wrap;
    }

    .qr-display-box {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 12px;
      padding: 20px;
      background: #ffffff;
      border-radius: var(--radius-md);
      margin: 12px 0;
    }

    .portal-footer {
      text-align: center;
      margin-top: 24px;
      font-size: 0.8rem;
      color: var(--text-muted);
    }

    .portal-footer a {
      color: var(--primary);
      text-decoration: none;
      font-weight: 600;
    }
    .portal-footer a:hover { text-decoration: underline; }

    /* ==================== TELA DE CARREGAMENTO (SPLASH SCREEN) ==================== */
    .splash-overlay {
      position: fixed;
      inset: 0;
      z-index: 9999;
      background: radial-gradient(circle at center, #111827 0%, #060911 100%);
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 24px;
      transition: opacity 0.55s ease, visibility 0.55s ease;
    }
    .splash-overlay.hidden {
      opacity: 0;
      visibility: hidden;
      pointer-events: none;
    }
    .splash-card {
      width: 100%;
      max-width: 420px;
      background: rgba(18, 24, 38, 0.9);
      border: 1px solid rgba(6, 182, 212, 0.35);
      border-radius: var(--radius-lg);
      padding: 32px 28px;
      text-align: center;
      box-shadow: 0 25px 60px rgba(0, 0, 0, 0.8), 0 0 40px rgba(6, 182, 212, 0.2);
    }
    .splash-icon {
      width: 64px;
      height: 64px;
      margin: 0 auto 16px;
      border-radius: 18px;
      background: var(--primary-gradient);
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 0 25px rgba(6, 182, 212, 0.45);
      animation: pulseGlow 1.8s infinite ease-in-out;
    }
    @keyframes pulseGlow {
      0%, 100% { transform: scale(1); box-shadow: 0 0 20px rgba(6, 182, 212, 0.4); }
      50% { transform: scale(1.06); box-shadow: 0 0 34px rgba(6, 182, 212, 0.75); }
    }
    .splash-title {
      font-size: 1.55rem;
      font-weight: 800;
      letter-spacing: -0.02em;
      background: linear-gradient(135deg, #ffffff 0%, #38bdf8 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      margin-bottom: 6px;
    }
    .splash-subtitle {
      font-size: 0.82rem;
      color: var(--text-muted);
      margin-bottom: 22px;
    }
    .splash-progress-track {
      width: 100%;
      height: 8px;
      background: rgba(255, 255, 255, 0.08);
      border-radius: 9999px;
      overflow: hidden;
      margin-bottom: 12px;
    }
    .splash-progress-bar {
      height: 100%;
      width: 0%;
      background: var(--primary-gradient);
      border-radius: 9999px;
      transition: width 0.3s ease;
    }
    .splash-status {
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.75rem;
      color: #38bdf8;
      min-height: 18px;
    }
  </style>
</head>
<body>

  <!-- Tela de Carregamento Antes de Iniciar o Sistema -->
  <div id="splash-screen" class="splash-overlay">
    <div class="splash-card">
      <div class="splash-icon">
        <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="#ffffff" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
          <path d="M22 12h-4l-3 9L9 3l-3 9H2"></path>
        </svg>
      </div>
      <div class="splash-title">Medica - Sentinela Enf</div>
      <div class="splash-subtitle">Sistema Inteligente de Enfermagem, Lotes, Validade e IoT</div>
      <div class="splash-progress-track">
        <div id="splash-bar" class="splash-progress-bar"></div>
      </div>
      <div id="splash-status" class="splash-status">Inicializando módulos do sistema...</div>
    </div>
  </div>

  <div class="glow-orb-1"></div>
  <div class="glow-orb-2"></div>

  <div class="container">
    <header class="brand-header">
      <div class="brand-badge">
        <span class="dot"></span>
        Medica - Sentinela Enf &bull; IoT
      </div>
      <h1>Medica - Sentinela Enf</h1>
      <p>Monitoramento térmico de enfermagem, controle de lotes, validade (FEFO) e alertas Arduino</p>
    </header>

    <main class="portal-card">
      <!-- Banner de Leitura de QR Code -->
      <div class="qr-banner">
        <div class="qr-banner-info">
          <h3>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#c084fc" stroke-width="2"><rect x="3" y="3" width="7" height="7"></rect><rect x="14" y="3" width="7" height="7"></rect><rect x="14" y="14" width="7" height="7"></rect><rect x="3" y="14" width="7" height="7"></rect></svg>
            Leitor Inteligente de QR Code
          </h3>
          <p>Escaneie pela câmera ou envie foto do QR Code para cadastrar ou movimentar o estoque</p>
        </div>
        <button type="button" class="btn-qr-scan" onclick="openQrScannerModal()">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M3 7V5a2 2 0 0 1 2-2h2"></path><path d="M17 3h2a2 2 0 0 1 2 2v2"></path><path d="M21 17v2a2 2 0 0 1-2 2h-2"></path><path d="M7 21H5a2 2 0 0 1-2-2v-2"></path><line x1="7" y1="12" x2="17" y2="12"></line></svg>
          Ler QR Code
        </button>
      </div>

      <!-- Cadastro de Medicamentos & Estoque -->
      <form id="form-meds" class="form-section" onsubmit="handleCreateMedication(event)">
        <div class="input-row">
          <div class="input-group">
            <label for="med-name">Medicamento</label>
            <input type="text" id="med-name" class="input-field" placeholder="Ex: Paracetamol" required minlength="2">
          </div>
          <div class="input-group">
            <label for="med-dosage">Dosagem</label>
            <input type="text" id="med-dosage" class="input-field" placeholder="Ex: 750mg" required>
          </div>
        </div>

        <div class="input-row">
          <div class="input-group">
            <label for="med-unit">Apresentação</label>
            <select id="med-unit" class="input-field">
              <option value="caixa" selected>Caixa</option>
              <option value="comprimido">Comprimido</option>
              <option value="gotas">Gotas</option>
              <option value="ml">Mililitros (ml)</option>
              <option value="ampola">Ampola</option>
              <option value="capsula">Cápsula</option>
            </select>
          </div>
          <div class="input-group">
            <label for="med-stock">Qtd. no Lote Inicial</label>
            <input type="number" id="med-stock" class="input-field" placeholder="Ex: 50 caixas" value="50" min="0" required>
          </div>
        </div>

        <div class="input-row">
          <div class="input-group">
            <label for="med-batch">Código do Lote *</label>
            <input type="text" id="med-batch" class="input-field" placeholder="Ex: LOTE-2026A" required>
          </div>
          <div class="input-group">
            <label for="med-exp">Data de Validade do Lote *</label>
            <input type="date" id="med-exp" class="input-field" required>
          </div>
        </div>

        <div class="input-row">
          <div class="input-group">
            <label for="med-min-stock">Estoque Mínimo de Alerta</label>
            <input type="number" id="med-min-stock" class="input-field" placeholder="Mínimo" value="15" min="0" required>
          </div>
          <div class="input-group">
            <label for="med-desc">Indicação / Descrição</label>
            <input type="text" id="med-desc" class="input-field" placeholder="Ex: Febre > 37.8°C">
          </div>
        </div>

        <button type="submit" id="btn-submit-med" class="btn-submit">
          <span>Cadastrar Medicamento &amp; Lote Inicial</span>
        </button>

        <div style="display:flex; justify-content:space-between; align-items:center; margin-top:12px;">
          <span style="font-size:0.85rem; font-weight:700; color:#38bdf8;">Estoque, Lotes &amp; Validades (FEFO + LEDs Arduino)</span>
          <button type="button" class="btn-action-sm" onclick="loadMedicationsList()">Atualizar Lista</button>
        </div>

        <div class="med-list-container">
          <table class="med-table">
            <thead>
              <tr>
                <th>Medicamento</th>
                <th>Lotes &amp; Validade</th>
                <th>Saldo</th>
                <th>Status / LED</th>
                <th>Ações / Lotes</th>
              </tr>
            </thead>
            <tbody id="med-tbody">
              <tr><td colspan="5" style="text-align:center; color:var(--text-muted);">Carregando catálogo...</td></tr>
            </tbody>
          </table>
        </div>
      </form>

      <!-- Feedback Banner -->
      <div id="feedback" class="feedback-box"></div>
    </main>

    <footer class="portal-footer">
      <p>Desenvolvido com FastAPI &bull; Monitoramento Térmico &amp; Gestão Farmacêutica IoT</p>
      <p style="margin-top: 4px;">Documentação interativa disponível em <a href="/docs">/docs</a> &bull; CLI: <code>python manage_medications.py</code></p>
    </footer>
  </div>

  <!-- Modal Leitor de QR Code (Câmera + Upload de Imagem) -->
  <dialog id="qr-scanner-modal" class="qr-modal">
    <div class="modal-header">
      <h3>
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" stroke-width="2"><path d="M3 7V5a2 2 0 0 1 2-2h2"></path><path d="M17 3h2a2 2 0 0 1 2 2v2"></path><path d="M21 17v2a2 2 0 0 1-2 2h-2"></path><path d="M7 21H5a2 2 0 0 1-2-2v-2"></path><line x1="7" y1="12" x2="17" y2="12"></line></svg>
        Escanear QR Code de Medicamento
      </h3>
      <button type="button" class="btn-close-modal" onclick="closeQrScannerModal()" title="Fechar">&times;</button>
    </div>

    <div class="scanner-controls">
      <button type="button" id="btn-start-cam" class="btn-scanner-ctrl" onclick="toggleCameraScanner()">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"></path><circle cx="12" cy="13" r="4"></circle></svg>
        <span id="cam-btn-label">Iniciar Câmera</span>
      </button>

      <label for="qr-file-input" class="btn-scanner-ctrl" style="cursor:pointer;">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="17 8 12 3 7 8"></polyline><line x1="12" y1="3" x2="12" y2="15"></line></svg>
        Ler Imagem / Foto
      </label>
      <input type="file" id="qr-file-input" accept="image/*" style="display:none;" onchange="handleQrImageUpload(event)">
    </div>

    <div id="qr-reader">
      <span>Clique em <strong>Iniciar Câmera</strong> para escanear ao vivo ou em <strong>Ler Imagem / Foto</strong> para enviar um arquivo de QR Code.</span>
    </div>

    <div style="display:flex; justify-content:space-between; align-items:center; margin-top:10px; gap:8px;">
      <span style="font-size:0.75rem; color:var(--text-muted);">Formatos aceitos: JSON, <code>Nome|Dosagem|Unidade</code> ou texto</span>
      <button type="button" class="btn-action-sm" onclick="simulateSampleQrScan()" style="color:#c084fc;">Simular QR de Exemplo</button>
    </div>

    <!-- Resultado Interpretado pela API -->
    <div id="qr-result-panel" class="qr-result-panel">
      <h4 id="qr-result-title">QR Code Lido com Sucesso!</h4>
      <div id="qr-result-details" style="font-size:0.83rem; color:#e2e8f0; line-height:1.5;"></div>
      <div id="qr-result-actions" class="qr-quick-actions"></div>
    </div>
  </dialog>

  <!-- Modal Gerador de Etiqueta QR Code do Medicamento -->
  <dialog id="qr-label-modal" class="qr-modal">
    <div class="modal-header">
      <h3 id="qr-label-title">Etiqueta QR Code</h3>
      <button type="button" class="btn-close-modal" onclick="document.getElementById('qr-label-modal').close()">&times;</button>
    </div>
    <p style="font-size:0.83rem; color:var(--text-muted);">Escaneie este QR Code com a câmera ou baixe a imagem para testar no leitor:</p>
    <div class="qr-display-box">
      <div id="qr-code-canvas"></div>
      <div id="qr-code-caption" style="color:#0f172a; font-weight:700; font-size:0.9rem;"></div>
    </div>
    <div style="display:flex; gap:10px;">
      <button type="button" class="btn-submit" onclick="downloadQrCodeImage()" style="margin-top:0;">Baixar Imagem PNG</button>
    </div>
  </dialog>

  <script>
    let html5QrScanner = null;
    let isCameraRunning = false;
    let lastScannedResolved = null;

    function showFeedback(message, isSuccess = true) {
      const feedback = document.getElementById("feedback");
      feedback.textContent = message;
      feedback.className = "feedback-box " + (isSuccess ? "success" : "error");
      feedback.style.display = "block";
    }

    // ==================== LEITOR DE QR CODE ====================
    function openQrScannerModal() {
      const modal = document.getElementById("qr-scanner-modal");
      document.getElementById("qr-result-panel").style.display = "none";
      modal.showModal();
    }

    async function closeQrScannerModal() {
      await stopCameraScanner();
      document.getElementById("qr-scanner-modal").close();
    }

    async function toggleCameraScanner() {
      if (isCameraRunning) {
        await stopCameraScanner();
      } else {
        await startCameraScanner();
      }
    }

    async function startCameraScanner() {
      const readerEl = document.getElementById("qr-reader");
      const btnLabel = document.getElementById("cam-btn-label");
      const btnCam = document.getElementById("btn-start-cam");

      if (typeof Html5Qrcode === "undefined") {
        alert("Biblioteca de leitura QR não carregada. Verifique sua conexão com a internet.");
        return;
      }

      try {
        readerEl.innerHTML = "";
        html5QrScanner = new Html5Qrcode("qr-reader");
        await html5QrScanner.start(
          { facingMode: "environment" },
          { fps: 10, qrbox: { width: 220, height: 220 } },
          async (decodedText) => {
            await stopCameraScanner();
            await processScannedQrCode(decodedText);
          },
          () => {}
        );
        isCameraRunning = true;
        btnLabel.textContent = "Parar Câmera";
        btnCam.classList.add("active");
      } catch (err) {
        readerEl.innerHTML = "<span style='color:#f87171;'>Não foi possível acessar a câmera (" + err + "). Você pode usar o botão <strong>Ler Imagem / Foto</strong> acima.</span>";
      }
    }

    async function stopCameraScanner() {
      if (html5QrScanner && isCameraRunning) {
        try {
          await html5QrScanner.stop();
          await html5QrScanner.clear();
        } catch (e) {}
      }
      isCameraRunning = false;
      document.getElementById("cam-btn-label").textContent = "Iniciar Câmera";
      document.getElementById("btn-start-cam").classList.remove("active");
    }

    async function handleQrImageUpload(event) {
      const file = event.target.files[0];
      if (!file) return;

      await stopCameraScanner();
      const readerEl = document.getElementById("qr-reader");

      // 1. Tenta BarcodeDetector nativo se disponível
      if ("BarcodeDetector" in window) {
        try {
          const detector = new BarcodeDetector({ formats: ["qr_code"] });
          const bitmap = await createImageBitmap(file);
          const barcodes = await detector.detect(bitmap);
          if (barcodes && barcodes.length > 0) {
            await processScannedQrCode(barcodes[0].rawValue);
            event.target.value = "";
            return;
          }
        } catch (e) {}
      }

      // 2. Usa Html5Qrcode.scanFile
      if (typeof Html5Qrcode !== "undefined") {
        try {
          readerEl.innerHTML = "";
          const fileScanner = new Html5Qrcode("qr-reader");
          const decodedText = await fileScanner.scanFile(file, true);
          await processScannedQrCode(decodedText);
        } catch (err) {
          readerEl.innerHTML = "<span style='color:#f87171;'>Nenhum QR Code válido encontrado na imagem selecionada.</span>";
        }
      }
      event.target.value = "";
    }

    async function simulateSampleQrScan() {
      const samplePayload = JSON.stringify({
        name: "Ibuprofeno Gotas",
        dosage: "100mg/ml",
        unit: "gotas",
        initial_stock: 40,
        minimum_stock: 10,
        description: "Antitérmico e anti-inflamatório lido via QR Code"
      });
      await processScannedQrCode(samplePayload);
    }

    async function processScannedQrCode(rawText) {
      const panel = document.getElementById("qr-result-panel");
      const titleEl = document.getElementById("qr-result-title");
      const detailsEl = document.getElementById("qr-result-details");
      const actionsEl = document.getElementById("qr-result-actions");

      try {
        const res = await fetch("/api/v1/medications/qrcode/resolve", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ raw_data: rawText })
        });
        const data = await res.json();
        if (!res.ok) {
          alert(data.message || data.detail || "Erro ao interpretar QR Code.");
          return;
        }

        lastScannedResolved = data;
        panel.style.display = "block";

        if (data.found && data.medication) {
          const med = data.medication;
          const mb = data.matched_batch;
          const batchInfoHtml = mb
            ? `<div style="margin-top:4px; padding:4px 8px; background:rgba(6,182,212,0.15); border-radius:6px; font-size:0.78rem;">
                 📦 <strong>Caixa vinculada ao Lote: ${mb.batch_number}</strong> &bull; Validade: <strong>${mb.expiration_date}</strong> (${mb.quantity} ${med.unit} no lote)
               </div>`
            : "";
          const batchParam = mb ? `'${mb.batch_number}'` : "null";
          titleEl.textContent = mb ? "Caixa Identificada (Medicamento + Lote Específico)!" : "Medicamento Encontrado no Estoque!";
          detailsEl.innerHTML = `
            <div><strong>${med.name}</strong> (${med.dosage}) &bull; Saldo total: <strong>${med.current_stock} ${med.unit}(s)</strong></div>
            ${batchInfoHtml}
            <div style="font-size:0.76rem; color:var(--text-muted); margin-top:2px;">ID: ${med.id}</div>
          `;
          actionsEl.innerHTML = `
            <button type="button" class="btn-action-sm" style="background:rgba(16,185,129,0.2); color:#34d399; border-color:rgba(16,185,129,0.4);" onclick="quickStockFromQr('${med.id}', '${med.name.replace(/'/g, "\\'")}', 'ENTRADA', ${batchParam})">+ Entrada neste Lote</button>
            <button type="button" class="btn-action-sm" style="background:rgba(245,158,11,0.2); color:#fbbf24; border-color:rgba(245,158,11,0.4);" onclick="quickStockFromQr('${med.id}', '${med.name.replace(/'/g, "\\'")}', 'SAIDA', ${batchParam})">- Dar Baixa deste Lote</button>
            <button type="button" class="btn-action-sm" onclick="fillFormFromQr()">Preencher Formulário</button>
          `;
        } else {
          const p = data.parsed_data;
          titleEl.textContent = "Novo Medicamento Identificado no QR Code!";
          detailsEl.innerHTML = `
            <div><strong>${p.name}</strong> &bull; Dosagem: <strong>${p.dosage}</strong> (${p.unit})</div>
            <div>Estoque Inicial sugerido: <strong>${p.initial_stock}</strong> | Mínimo: <strong>${p.minimum_stock}</strong></div>
          `;
          fillFormFromQr(false);
          actionsEl.innerHTML = `
            <button type="button" class="btn-action-sm" style="background:rgba(6,182,212,0.25); color:#38bdf8; border-color:#06b6d4;" onclick="registerDirectlyFromQr()">Cadastrar Agora com 1 Clique</button>
            <button type="button" class="btn-action-sm" onclick="closeQrScannerModal()">Revisar no Formulário</button>
          `;
        }
      } catch (err) {
        alert("Falha na comunicação com a API ao processar o QR Code.");
      }
    }

    function fillFormFromQr(closeModal = true) {
      if (!lastScannedResolved || !lastScannedResolved.parsed_data) return;
      const p = lastScannedResolved.parsed_data;

      const nameInput = document.getElementById("med-name");
      const dosageInput = document.getElementById("med-dosage");
      const unitSelect = document.getElementById("med-unit");
      const stockInput = document.getElementById("med-stock");
      const minStockInput = document.getElementById("med-min-stock");
      const descInput = document.getElementById("med-desc");

      nameInput.value = p.name || "";
      dosageInput.value = p.dosage || "";
      if (p.unit) {
        const validUnits = ["comprimido", "gotas", "ml", "ampola", "capsula"];
        if (validUnits.includes(p.unit.toLowerCase())) {
          unitSelect.value = p.unit.toLowerCase();
        }
      }
      stockInput.value = p.initial_stock ?? 50;
      minStockInput.value = p.minimum_stock ?? 15;
      descInput.value = p.description || "";

      [nameInput, dosageInput, stockInput, minStockInput, descInput].forEach(el => {
        el.classList.add("highlight-qr");
        setTimeout(() => el.classList.remove("highlight-qr"), 2500);
      });

      if (closeModal) {
        closeQrScannerModal();
        showFeedback("Campos preenchidos via QR Code! Clique em Cadastrar Medicamento para confirmar.", true);
      }
    }

    async function registerDirectlyFromQr() {
      fillFormFromQr(false);
      await closeQrScannerModal();
      document.getElementById("btn-submit-med").click();
    }

    async function quickStockFromQr(medId, medName, movementType, batchNumber = null) {
      await closeQrScannerModal();
      await promptStockUpdate(medId, medName, movementType, batchNumber);
    }

    // ==================== GERAÇÃO DE ETIQUETA QR CODE (MEDICAMENTO + LOTE) ====================
    function showMedicationQrLabel(id, name, dosage, unit, minStock, batchNumber = null, expDate = null) {
      const modal = document.getElementById("qr-label-modal");
      const canvasContainer = document.getElementById("qr-code-canvas");
      canvasContainer.innerHTML = "";

      const loteSuffix = batchNumber ? " • Lote: " + batchNumber : "";
      document.getElementById("qr-label-title").textContent = "QR Code: " + name + loteSuffix;
      document.getElementById("qr-code-caption").textContent =
        name + " • " + dosage + (batchNumber ? " | Lote: " + batchNumber + " (Val: " + expDate + ")" : " (" + unit + ")");

      const payloadObj = {
        id: id,
        name: name,
        dosage: dosage,
        unit: unit,
        minimum_stock: minStock
      };
      if (batchNumber) payloadObj.batch_number = batchNumber;
      if (expDate) payloadObj.expiration_date = expDate;

      const qrPayload = JSON.stringify(payloadObj);

      if (typeof QRCode !== "undefined") {
        new QRCode(canvasContainer, {
          text: qrPayload,
          width: 200,
          height: 200,
          colorDark: "#0b0f19",
          colorLight: "#ffffff",
          correctLevel: QRCode.CorrectLevel.M
        });
      } else {
        canvasContainer.textContent = qrPayload;
      }

      modal.showModal();
    }

    function downloadQrCodeImage() {
      const img = document.querySelector("#qr-code-canvas img") || document.querySelector("#qr-code-canvas canvas");
      if (!img) return;
      const src = img.src || img.toDataURL("image/png");
      const a = document.createElement("a");
      a.href = src;
      a.download = "qrcode_medicamento.png";
      a.click();
    }

    // ==================== GESTÃO DE MEDICAMENTOS & ESTOQUE ====================
    async function handleCreateMedication(event) {
      event.preventDefault();
      const btn = document.getElementById("btn-submit-med");
      btn.disabled = true;

      const payload = {
        name: document.getElementById("med-name").value.trim(),
        dosage: document.getElementById("med-dosage").value.trim(),
        unit: document.getElementById("med-unit").value,
        initial_stock: parseInt(document.getElementById("med-stock").value) || 0,
        minimum_stock: parseInt(document.getElementById("med-min-stock").value) || 10,
        batch_number: document.getElementById("med-batch").value.trim() || null,
        expiration_date: document.getElementById("med-exp").value || null,
        description: document.getElementById("med-desc").value.trim() || null
      };

      try {
        const res = await fetch("/api/v1/medications/", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (res.ok) {
          const loteInfo = (data.batches && data.batches.length > 0) ? " | Lote: " + data.batches[0].batch_number + " (Val: " + data.batches[0].expiration_date + ")" : "";
          showFeedback("Medicamento " + data.name + " (" + data.dosage + ") cadastrado! Saldo: " + data.current_stock + " " + data.unit + "(s)" + loteInfo, true);
          document.getElementById("med-name").value = "";
          document.getElementById("med-dosage").value = "";
          document.getElementById("med-batch").value = "";
          document.getElementById("med-desc").value = "";
          loadMedicationsList();
        } else {
          showFeedback(data.message || data.detail || "Erro ao cadastrar medicamento.", false);
        }
      } catch (err) {
        showFeedback("Falha na conexão ao cadastrar medicamento.", false);
      } finally {
        btn.disabled = false;
      }
    }

    async function loadMedicationsList() {
      const tbody = document.getElementById("med-tbody");
      tbody.innerHTML = "<tr><td colspan='5' style='text-align:center; color:var(--text-muted);'>Carregando...</td></tr>";

      try {
        const res = await fetch("/api/v1/medications/?limit=50");
        const list = await res.json();

        if (!list || list.length === 0) {
          tbody.innerHTML = "<tr><td colspan='5' style='text-align:center; color:var(--text-muted);'>Nenhum medicamento cadastrado.</td></tr>";
          return;
        }

        tbody.innerHTML = "";
        list.forEach(m => {
          let statusClass = "status-ok";
          let statusText = "OK";
          if (m.stock_status === "LOW") {
            statusClass = "status-low";
            statusText = "BAIXO";
          } else if (m.stock_status === "OUT_OF_STOCK") {
            statusClass = "status-out";
            statusText = "ESGOTADO";
          }

          let ledIcon = "🟢";
          if (m.alert_led === "RED") ledIcon = "🔴";
          else if (m.alert_led === "YELLOW") ledIcon = "🟡";

          const safeName = m.name.replace(/'/g, "\\'");
          const safeDosage = m.dosage.replace(/'/g, "\\'");
          const safeDesc = (m.description || "").replace(/'/g, "\\'");

          let batchHtml = "<span style='color:var(--text-muted); font-size:0.75rem;'>Sem lote</span>";
          if (m.batches && m.batches.length > 0) {
            batchHtml = m.batches.map(b => {
              let expBadge = "status-ok";
              let expLabel = "VÁLIDO";
              if (b.expiration_status === "EXPIRED") {
                expBadge = "status-out";
                expLabel = "VENCIDO";
              } else if (b.expiration_status === "EXPIRING_SOON") {
                expBadge = "status-low";
                expLabel = "VENCE EM " + b.days_until_expiration + "d";
              }
              const safeBatch = b.batch_number.replace(/'/g, "\\'");
              return `<div style="margin-bottom:4px; font-size:0.76rem; display:flex; align-items:center; gap:6px; flex-wrap:wrap;">
                <span><strong>${b.batch_number}</strong> (${b.quantity} ${m.unit}) &bull; Val: ${b.expiration_date}</span>
                <span class="status-pill ${expBadge}" style="font-size:0.62rem; padding:1px 6px;">${expLabel}</span>
                <button type="button" class="btn-action-sm" style="font-size:0.65rem; padding:1px 5px; color:#38bdf8;" onclick="showMedicationQrLabel('${m.id}', '${safeName}', '${safeDosage}', '${m.unit}', ${m.minimum_stock}, '${safeBatch}', '${b.expiration_date}')" title="Gerar Etiqueta QR desta Caixa/Lote">QR Lote</button>
              </div>`;
            }).join("");
          }

          const tr = document.createElement("tr");
          tr.innerHTML = `
            <td>
              <div style="font-weight:600;">${m.name}</div>
              <div style="font-size:0.75rem; color:var(--text-muted);">${m.dosage}</div>
            </td>
            <td>${batchHtml}</td>
            <td><strong>${m.current_stock}</strong> <span style="font-size:0.75rem; color:var(--text-muted);">${m.unit}</span></td>
            <td>
              <span title="LED no Arduino: ${m.alert_led}">${ledIcon}</span>
              <span class="status-pill ${statusClass}">${statusText}</span>
            </td>
            <td>
              <button type="button" class="btn-action-sm" onclick="promptAddBatch('${m.id}', '${safeName}', '${m.unit}')" style="color:#34d399; border-color:rgba(16,185,129,0.4);">+ Novo Lote</button>
              <button type="button" class="btn-action-sm" onclick="promptStockUpdate('${m.id}', '${safeName}', 'SAIDA')" style="margin-left:4px; color:#fbbf24;">- Baixa (FEFO)</button>
              <button type="button" class="btn-action-sm" onclick="promptEditMedication('${m.id}', '${safeName}', '${safeDosage}', '${m.unit}', ${m.minimum_stock}, '${safeDesc}')" style="margin-left:4px; color:#a78bfa;">Editar</button>
              <button type="button" class="btn-action-sm" onclick="showMedicationQrLabel('${m.id}', '${safeName}', '${safeDosage}', '${m.unit}', ${m.minimum_stock})" style="margin-left:4px; color:#38bdf8;" title="Gerar Etiqueta QR Code">QR</button>
              <button type="button" class="btn-action-sm" onclick="promptDeleteMedication('${m.id}', '${safeName}', '${safeDosage}')" style="margin-left:4px; color:#f87171;" title="Apagar Cadastro">Excluir</button>
            </td>
          `;
          tbody.appendChild(tr);
        });
      } catch (err) {
        tbody.innerHTML = "<tr><td colspan='5' style='text-align:center; color:#f87171;'>Erro ao carregar estoque.</td></tr>";
      }
    }

    async function promptAddBatch(medId, medName, medUnit) {
      const batchNumber = prompt("Novo Lote para " + medName + ":\\nInforme o Código do Lote:", "LOTE-2026B");
      if (!batchNumber) return;

      const qtyStr = prompt("Quantidade de " + medUnit + "(s) neste lote (ex: 50 caixas):", "50");
      if (!qtyStr) return;
      const qty = parseInt(qtyStr);
      if (isNaN(qty) || qty <= 0) {
        alert("A quantidade deve ser maior que zero.");
        return;
      }

      const defaultExp = new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString().split("T")[0];
      const expDate = prompt("Data de Validade do Lote (formato AAAA-MM-DD):", defaultExp);
      if (!expDate) return;

      try {
        const res = await fetch("/api/v1/medications/" + medId + "/batches", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            batch_number: batchNumber.trim(),
            quantity: qty,
            expiration_date: expDate.trim(),
            reason: "Entrada de novo lote via Portal Web"
          })
        });
        const data = await res.json();
        if (res.ok) {
          showFeedback("Lote " + data.batch_number + " (" + data.quantity + " " + medUnit + "s | Validade: " + data.expiration_date + ") adicionado com sucesso!", true);
          loadMedicationsList();
        } else {
          showFeedback(data.message || data.detail || "Falha ao cadastrar lote.", false);
        }
      } catch (err) {
        showFeedback("Erro de conexão ao cadastrar lote.", false);
      }
    }

    async function promptStockUpdate(medId, medName, movementType, defaultBatchNumber = null) {
      const actionText = movementType === "ENTRADA" ? "ADICIONAR" : "BAIXAR/SUBTRAIR (FEFO)";
      const qtyStr = prompt("Comando de " + movementType + " para " + medName + ":\\nDigite a quantidade a " + actionText + ":", "5");
      if (!qtyStr) return;

      const qty = parseInt(qtyStr);
      if (isNaN(qty) || qty <= 0) {
        alert("Quantidade inválida! Deve ser um número maior que zero.");
        return;
      }

      const batchNum = prompt("Código do Lote específico (deixe em branco para usar FEFO automático pelo lote que vence primeiro):", defaultBatchNumber || "");
      const reason = prompt("Informe o motivo/justificativa da movimentação:", movementType === "ENTRADA" ? "Reposição de lote" : "Dispensação ao paciente");

      try {
        const res = await fetch("/api/v1/medications/" + medId + "/stock", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            movement_type: movementType,
            quantity: qty,
            batch_number: batchNum ? batchNum.trim() : null,
            reason: reason || "Movimentação via Portal Web"
          })
        });
        const data = await res.json();
        if (res.ok) {
          const batchUsed = data.batch_number ? " (Lote: " + data.batch_number + ")" : "";
          showFeedback("Comando " + movementType + " executado" + batchUsed + "! Saldo anterior: " + data.previous_stock + " \u2192 Novo saldo: " + data.new_stock, true);
          loadMedicationsList();
        } else {
          showFeedback(data.message || data.detail || "Falha ao executar comando de estoque.", false);
        }
      } catch (err) {
        showFeedback("Erro ao enviar comando de estoque.", false);
      }
    }

    async function promptEditMedication(medId, currentName, currentDosage, currentUnit, currentMinStock, currentDesc) {
      const newName = prompt("Nome do medicamento:", currentName);
      if (newName === null) return;
      const newDosage = prompt("Dosagem:", currentDosage);
      if (newDosage === null) return;
      const newMinStockStr = prompt("Estoque Mínimo de Alerta:", currentMinStock);
      if (newMinStockStr === null) return;
      const newDesc = prompt("Descrição / Observações:", currentDesc || "");
      if (newDesc === null) return;

      const payload = {
        name: newName.trim(),
        dosage: newDosage.trim(),
        unit: currentUnit,
        minimum_stock: parseInt(newMinStockStr) || 0,
        description: newDesc.trim() || null
      };

      try {
        const res = await fetch("/api/v1/medications/" + medId, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (res.ok) {
          showFeedback("Medicamento " + data.name + " (" + data.dosage + ") atualizado com sucesso!", true);
          loadMedicationsList();
        } else {
          showFeedback(data.message || data.detail || "Erro ao atualizar dados do medicamento.", false);
        }
      } catch (err) {
        showFeedback("Falha na conexão ao atualizar medicamento.", false);
      }
    }

    async function promptDeleteMedication(medId, medName, medDosage) {
      const ok = confirm("Tem certeza que deseja apagar o cadastro de " + medName + " (" + medDosage + ") e todo o seu histórico de movimentações?");
      if (!ok) return;

      try {
        const res = await fetch("/api/v1/medications/" + medId, {
          method: "DELETE"
        });
        const data = await res.json();
        if (res.ok) {
          showFeedback(data.message || "Medicamento apagado com sucesso!", true);
          loadMedicationsList();
        } else {
          showFeedback(data.message || data.detail || "Erro ao apagar medicamento.", false);
        }
      } catch (err) {
        showFeedback("Falha na conexão ao apagar medicamento.", false);
      }
    }

    window.addEventListener("DOMContentLoaded", () => {
      const bar = document.getElementById("splash-bar");
      const status = document.getElementById("splash-status");
      const splash = document.getElementById("splash-screen");

      const steps = [
        { pct: 30, text: "Conectando ao banco de dados de medicamentos..." },
        { pct: 65, text: "Verificando validade dos lotes (FEFO) e estoque..." },
        { pct: 100, text: "Sincronizando alertas LED e Teclado Arduino..." }
      ];

      steps.forEach((step, idx) => {
        setTimeout(() => {
          if (bar) bar.style.width = step.pct + "%";
          if (status) status.textContent = step.text;
        }, idx * 420);
      });

      loadMedicationsList().finally(() => {
        setTimeout(() => {
          if (splash) splash.classList.add("hidden");
        }, 1400);
      });
    });
  </script>
</body>
</html>
"""


@router.get("/portal", response_class=HTMLResponse, summary="Portal Web de Medicamentos, QR Code e Estoque")
@router.get("/", response_class=HTMLResponse, summary="Página Inicial / Gestão de Medicamentos")
def get_portal_page() -> HTMLResponse:
    """Retorna a interface web interativa para cadastro, leitura de QR Code e gestão de estoque de medicamentos."""
    return HTMLResponse(content=PORTAL_HTML, status_code=200)
