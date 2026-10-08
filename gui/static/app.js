/* ────────────────────────────────────────────
   Web Scraper 3.0 — Enterprise GUI JavaScript
   ──────────────────────────────────────────── */

const socket = io();
let selectedEngine = 'fast';
let jobRunning = false;
let pagesScraped = 0;
let recordsFound = 0;

/* ══════════════════════════════════
   Socket.IO Event Handlers
   ══════════════════════════════════ */

socket.on('connect', () => {
  setConnectionBadge(true);
});
socket.on('disconnect', () => {
  setConnectionBadge(false);
});

socket.on('log', (data) => {
  appendLog(data.message, data.level || 'info');
  // Count pages from log messages
  if (data.message.includes('Scraped') || data.message.includes('scraped')) {
    pagesScraped++;
    document.getElementById('stat-pages').textContent = pagesScraped;
  }
});

socket.on('job_started', () => {
  jobRunning = true;
  pagesScraped = 0;
  recordsFound = 0;
  document.getElementById('stat-pages').textContent = '0';
  document.getElementById('stat-records').textContent = '0';
  document.getElementById('stat-files').textContent = '0';
  setStatus('Running', 'var(--warning)');
  document.getElementById('launch-btn').classList.add('running');
  document.getElementById('launch-btn').querySelector('span').textContent = '⏳';
  document.getElementById('launch-btn').childNodes[1].textContent = ' Scraping...';
  document.getElementById('stop-btn').classList.remove('hidden');
  document.getElementById('results-panel').classList.add('hidden');
});

socket.on('job_complete', (data) => {
  jobRunning = false;
  setStatus('Complete', 'var(--success)');
  document.getElementById('launch-btn').classList.remove('running');
  document.getElementById('launch-btn').querySelector('span').textContent = '🚀';
  document.getElementById('launch-btn').childNodes[1].textContent = ' Launch Scraper';
  document.getElementById('stop-btn').classList.add('hidden');

  const pages = data.pages_scraped || 0;
  document.getElementById('stat-pages').textContent = pages;
  document.getElementById('stat-files').textContent = data.files ? data.files.length : 0;

  appendLog(`✅ Job complete! ${pages} pages scraped, ${data.files.length} files exported.`, 'success');
  renderResults(data.files || []);
});

socket.on('job_error', (data) => {
  jobRunning = false;
  setStatus('Error', 'var(--danger)');
  document.getElementById('launch-btn').classList.remove('running');
  document.getElementById('launch-btn').querySelector('span').textContent = '🚀';
  document.getElementById('launch-btn').childNodes[1].textContent = ' Launch Scraper';
  document.getElementById('stop-btn').classList.add('hidden');
  appendLog(`❌ Error: ${data.message}`, 'error');
});


/* ══════════════════════════════════
   UI Helpers
   ══════════════════════════════════ */

function setConnectionBadge(connected) {
  const badge = document.getElementById('connection-badge');
  const dot = badge.querySelector('.status-dot');
  if (connected) {
    dot.style.background = 'var(--success)';
    dot.style.boxShadow = '0 0 6px var(--success)';
    badge.innerHTML = `<span class="status-dot"></span> Connected`;
  } else {
    dot.style.background = 'var(--danger)';
    dot.style.boxShadow = '0 0 6px var(--danger)';
    badge.innerHTML = `<span class="status-dot"></span> Disconnected`;
  }
}

function setStatus(text, color) {
  const el = document.getElementById('stat-status');
  el.textContent = text;
  el.style.color = color;
}

function appendLog(message, level = 'info') {
  const body = document.getElementById('log-body');
  const div = document.createElement('div');
  div.className = `log-entry log-${level}`;
  div.textContent = message;
  body.appendChild(div);
  body.scrollTop = body.scrollHeight;
}

function clearLog() {
  document.getElementById('log-body').innerHTML = '';
}

function humanSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function renderResults(files) {
  const panel = document.getElementById('results-panel');
  const grid = document.getElementById('results-grid');
  grid.innerHTML = '';
  files.forEach(f => {
    const row = document.createElement('div');
    row.className = 'result-file';
    row.innerHTML = `
      <span class="result-name">${f.name}</span>
      <div class="result-meta">
        <span class="result-folder">${f.folder || '—'}</span>
        <span class="result-size">${humanSize(f.size)}</span>
        <button class="download-btn" onclick="window.location='/api/download/${encodeURIComponent(f.rel_path)}'">⬇ Download</button>
      </div>`;
    grid.appendChild(row);
  });
  panel.classList.remove('hidden');
  document.getElementById('stat-files').textContent = files.length;
}


/* ══════════════════════════════════
   Tab Navigation
   ══════════════════════════════════ */

function showTab(tabName, btn) {
  document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.getElementById('tab-' + tabName).classList.add('active');
  btn.classList.add('active');

  const titles = {
    scraper: 'New Scraping Job',
    history: 'Run History',
    about: 'About & Features',
  };
  document.getElementById('page-title').textContent = titles[tabName] || '';

  if (tabName === 'history') loadHistory();
}


/* ══════════════════════════════════
   Engine Selection
   ══════════════════════════════════ */

function selectEngine(engine) {
  selectedEngine = engine;
  document.getElementById('engine-fast').classList.toggle('selected', engine === 'fast');
  document.getElementById('engine-browser').classList.toggle('selected', engine === 'browser');
}


/* ══════════════════════════════════
   Checkbox Items
   ══════════════════════════════════ */

document.querySelectorAll('.checkbox-item').forEach(item => {
  item.addEventListener('click', () => {
    item.classList.toggle('checked');
    const cb = item.querySelector('input[type=checkbox]');
    cb.checked = !cb.checked;
  });
});


/* ══════════════════════════════════
   Toggle Switches
   ══════════════════════════════════ */

function toggleSwitch(el) {
  el.classList.toggle('on');
}


/* ══════════════════════════════════
   Custom CSS Selectors
   ══════════════════════════════════ */

let selectorCount = 0;

function addSelector() {
  selectorCount++;
  const list = document.getElementById('selectors-list');
  const id = `sel-${selectorCount}`;
  const row = document.createElement('div');
  row.className = 'selector-row';
  row.id = id;
  row.innerHTML = `
    <input type="text" class="input-field" placeholder="Label (e.g. price)" style="font-size:0.75rem;padding:0.45rem 0.7rem" />
    <input type="text" class="input-field" placeholder="CSS selector (e.g. .price_color)" style="font-size:0.75rem;padding:0.45rem 0.7rem" />
    <button class="btn-del" onclick="document.getElementById('${id}').remove()">✕</button>`;
  list.appendChild(row);
}

function getCustomSelectors() {
  const rows = document.querySelectorAll('#selectors-list .selector-row');
  const result = {};
  rows.forEach(row => {
    const inputs = row.querySelectorAll('input');
    const label = inputs[0].value.trim();
    const sel = inputs[1].value.trim();
    if (label && sel) result[label] = sel;
  });
  return result;
}


/* ══════════════════════════════════
   Build Job Config & Launch
   ══════════════════════════════════ */

function launchJob() {
  if (jobRunning) return;

  const url = document.getElementById('url-input').value.trim();
  if (!url) {
    appendLog('⚠ Please enter a target URL.', 'warning');
    document.getElementById('url-input').focus();
    return;
  }

  const extractOptions = [];
  document.querySelectorAll('#card-target ~ .card .checkbox-grid .checkbox-item').forEach(item => {
    if (item.classList.contains('checked')) {
      extractOptions.push(item.dataset.value);
    }
  });

  // Collect extraction checkboxes (first checkbox-grid under "Data to Extract" card)
  const dataChecks = [];
  document.querySelectorAll('.checkbox-item').forEach(item => {
    const val = item.dataset.value;
    if (['metadata','text','ecommerce','ai_insights','headings','images','links','tables'].includes(val) && item.classList.contains('checked')) {
      dataChecks.push(val);
    }
  });

  // Collect format checkboxes
  const formats = [];
  document.querySelectorAll('.checkbox-item').forEach(item => {
    const val = item.dataset.value;
    if (['csv','excel','json','jsonl','sqlite'].includes(val) && item.classList.contains('checked')) {
      formats.push(val);
    }
  });

  const config = {
    url,
    engine: selectedEngine,
    max_pages: parseInt(document.getElementById('max-pages').value) || 50,
    depth: parseInt(document.getElementById('max-depth').value) || 3,
    extract_options: dataChecks.length ? dataChecks : ['metadata', 'text', 'links'],
    extract_patterns: document.getElementById('toggle-patterns').classList.contains('on'),
    save_html: document.getElementById('toggle-html').classList.contains('on'),
    download_images: document.getElementById('toggle-images').classList.contains('on'),
    proxy: document.getElementById('proxy-input').value.trim() || null,
    custom_selectors: getCustomSelectors(),
    formats: formats.length ? formats : ['csv', 'excel'],
  };

  appendLog(`🚀 Launching job: ${url}`, 'info');
  appendLog(`   Engine: ${config.engine === 'fast' ? 'Fast (HTTPX)' : 'Browser (Playwright)'}`, 'info');
  appendLog(`   Max pages: ${config.max_pages}, Depth: ${config.depth}`, 'info');
  appendLog(`   Extracting: ${config.extract_options.join(', ')}`, 'info');
  appendLog(`   Formats: ${config.formats.join(', ').toUpperCase()}`, 'info');

  socket.emit('start_job', config);
}

function stopJob() {
  socket.emit('stop_job');
}


/* ══════════════════════════════════
   Run History
   ══════════════════════════════════ */

async function loadHistory() {
  const list = document.getElementById('history-list');
  list.innerHTML = '<div class="empty-state">Loading...</div>';
  try {
    const res = await fetch('/api/runs');
    const runs = await res.json();
    if (!runs.length) {
      list.innerHTML = '<div class="empty-state">No previous runs found. Start your first scraping job!</div>';
      return;
    }
    list.innerHTML = '';
    runs.forEach(run => {
      const item = document.createElement('div');
      item.className = 'history-item';
      item.innerHTML = `
        <div>
          <div class="history-site">🌐 ${run.site}</div>
          <div class="history-run">${run.run}</div>
        </div>
        <span class="history-badge">${run.file_count} files</span>`;
      item.addEventListener('click', () => loadRunFiles(run.site, run.run, item));
      list.appendChild(item);
    });
  } catch (e) {
    list.innerHTML = '<div class="empty-state">Failed to load history.</div>';
  }
}

async function loadRunFiles(site, run, parentEl) {
  // Toggle
  const existingFiles = parentEl.nextElementSibling;
  if (existingFiles && existingFiles.classList.contains('history-files')) {
    existingFiles.classList.toggle('open');
    return;
  }

  const filesDiv = document.createElement('div');
  filesDiv.className = 'history-files open';
  filesDiv.innerHTML = '<div class="empty-state" style="font-size:0.75rem">Loading files...</div>';
  parentEl.insertAdjacentElement('afterend', filesDiv);

  try {
    const res = await fetch(`/api/run_files/${site}/${run}`);
    const files = await res.json();
    filesDiv.innerHTML = '';
    files.forEach(f => {
      const row = document.createElement('div');
      row.className = 'result-file';
      row.innerHTML = `
        <span class="result-name">${f.name}</span>
        <div class="result-meta">
          <span class="result-folder">${f.folder}</span>
          <span class="result-size">${humanSize(f.size)}</span>
          <button class="download-btn" onclick="window.location='/api/download/${encodeURIComponent(f.rel_path)}'">⬇ Download</button>
        </div>`;
      filesDiv.appendChild(row);
    });
  } catch (e) {
    filesDiv.innerHTML = '<div class="empty-state" style="font-size:0.75rem">Failed to load files.</div>';
  }
}
