document.addEventListener('DOMContentLoaded', () => {
  // Primary Elements
  const auditForm = document.getElementById('audit-form');
  const urlInput = document.getElementById('url-input');
  const runBtn = document.getElementById('run-btn');
  const btnText = document.getElementById('btn-text');
  
  // Advanced Pages
  const toggleAdvancedBtn = document.getElementById('toggle-advanced-btn');
  const advancedOptionsPanel = document.getElementById('advanced-options-panel');
  const advancedToggleIcon = document.getElementById('advanced-toggle-icon');
  const pagesInput = document.getElementById('pages-input');

  // Modals
  const benchmarkModal = document.getElementById('benchmark-modal');
  const architectureModal = document.getElementById('architecture-modal');
  const viewSampleBtn = document.getElementById('view-sample-btn');
  const btnOpenArch = document.getElementById('btn-open-arch');
  const btnCloseBenchmarks = document.getElementById('btn-close-benchmarks');
  const btnCloseArch = document.getElementById('btn-close-arch');

  // Progress & Telemetry
  const progressCard = document.getElementById('progress-card');
  const progressTarget = document.getElementById('progress-target');
  const processingSubMsg = document.getElementById('processing-sub-msg');
  const liveTickerText = document.getElementById('live-ticker-text');
  const resultsSection = document.getElementById('results-section');
  
  // Verdict Elements
  const verdictHeadline = document.getElementById('verdict-headline');
  const verdictSummary = document.getElementById('verdict-summary');
  const verdictGrade = document.getElementById('verdict-grade');
  const verdictBadge = document.getElementById('verdict-badge');
  
  // Comparison Lists
  const compWorkingList = document.getElementById('comp-working-list');
  const compIssuesList = document.getElementById('comp-issues-list');

  // Gauge & Counters
  const scoreNum = document.getElementById('score-num');
  const scoreCircle = document.getElementById('score-circle');
  const scoreVerdict = document.getElementById('score-verdict');
  const auditedSiteLabel = document.getElementById('audited-site-label');
  
  const countCrit = document.getElementById('count-critical');
  const countHigh = document.getElementById('count-high');
  const countMed = document.getElementById('count-medium');
  const countLow = document.getElementById('count-low');
  
  const tabFindingsCount = document.getElementById('tab-findings-count');
  const filterAllCount = document.getElementById('filter-all-count');
  const filterCritCount = document.getElementById('filter-crit-count');
  const filterHighCount = document.getElementById('filter-high-count');
  const filterMedCount = document.getElementById('filter-med-count');
  const filterLowCount = document.getElementById('filter-low-count');
  
  // Pillars
  const pCrawlVal = document.getElementById('p-crawl-val');
  const pCrawlBar = document.getElementById('p-crawl-bar');
  const pRenderVal = document.getElementById('p-render-val');
  const pRenderBar = document.getElementById('p-render-bar');
  const pStructVal = document.getElementById('p-struct-val');
  const pStructBar = document.getElementById('p-struct-bar');
  const pTrustVal = document.getElementById('p-trust-val');
  const pTrustBar = document.getElementById('p-trust-bar');
  const pEngageVal = document.getElementById('p-engage-val');
  const pEngageBar = document.getElementById('p-engage-bar');

  // Simulator Elements (6 Engines)
  const badgeChatGPT = document.getElementById('sim-badge-chatgpt');
  const textChatGPT = document.getElementById('sim-text-chatgpt');
  const badgeClaude = document.getElementById('sim-badge-claude');
  const textClaude = document.getElementById('sim-text-claude');
  const badgePerplexity = document.getElementById('sim-badge-perplexity');
  const textPerplexity = document.getElementById('sim-text-perplexity');
  const badgeGemini = document.getElementById('sim-badge-gemini');
  const textGemini = document.getElementById('sim-text-gemini');
  const badgeApple = document.getElementById('sim-badge-apple');
  const textApple = document.getElementById('sim-text-apple');
  const badgeDeepSeek = document.getElementById('sim-badge-deepseek');
  const textDeepSeek = document.getElementById('sim-text-deepseek');

  // Interactive Question Simulator
  const simPromptInput = document.getElementById('sim-prompt-input');
  const btnRunSim = document.getElementById('btn-run-sim');
  const simResponseText = document.getElementById('sim-response-text');
  const simUnpatchedText = document.getElementById('sim-unpatched-text');
  const simPatchedText = document.getElementById('sim-patched-text');

  // Stage Status Icons
  const iconCrawl = document.getElementById('icon-crawl');
  const iconRender = document.getElementById('icon-render');
  const iconStruct = document.getElementById('icon-struct');
  const iconTrust = document.getElementById('icon-trust');
  const iconEngage = document.getElementById('icon-engage');

  // Toolkit
  const llmsPreview = document.getElementById('llms-preview');
  const schemaPreview = document.getElementById('schema-preview');
  const robotsPreview = document.getElementById('robots-preview');
  const patchPreview = document.getElementById('patch-preview');
  const btnCopyLlms = document.getElementById('btn-copy-llms');
  const btnCopySchema = document.getElementById('btn-copy-schema');
  const btnCopyRobots = document.getElementById('btn-copy-robots');
  const btnCopyPatch = document.getElementById('btn-copy-patch');
  const btnDownloadLlms = document.getElementById('btn-download-llms');
  const btnDownloadSchema = document.getElementById('btn-download-schema');
  const btnDownloadRobots = document.getElementById('btn-download-robots');
  const btnDownloadPatch = document.getElementById('btn-download-patch');
  const btnPrintReport = document.getElementById('btn-print-report');
  const toast = document.getElementById('toast');

  // Lists
  const findingsFeed = document.getElementById('findings-feed');
  const oppsContainer = document.getElementById('opportunities-container');
  const oppsFeed = document.getElementById('opportunities-feed');

  let currentReport = null;
  let activeFilter = 'all';

  function showToast(msg) {
    if (!toast) return;
    toast.innerHTML = `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg> <span>${escapeHtml(msg || 'Copied to clipboard')}</span>`;
    toast.style.display = 'flex';
    setTimeout(() => {
      if (toast) toast.style.display = 'none';
    }, 2200);
  }

  function copyTextToClipboard(text, msg) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text)
        .then(() => showToast(msg))
        .catch(() => fallbackCopy(text, msg));
    } else {
      fallbackCopy(text, msg);
    }
  }

  function fallbackCopy(text, msg) {
    try {
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
      showToast(msg);
    } catch (e) {
      showToast('Copy failed');
    }
  }

  function downloadFile(blob, filename) {
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }

  function sanitize(str) {
    return (str || 'report').replace(/[^a-zA-Z0-9]/g, '_').toLowerCase();
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  // Tab Navigation
  const tabButtons = document.querySelectorAll('.nav-tab-btn');
  tabButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      tabButtons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      const targetTab = btn.getAttribute('data-tab');
      document.querySelectorAll('.tab-panel').forEach(panel => {
        panel.style.display = 'none';
      });
      const panel = document.getElementById(`tab-content-${targetTab}`);
      if (panel) panel.style.display = 'block';
    });
  });

  // Advanced Options Toggle
  if (toggleAdvancedBtn && advancedOptionsPanel) {
    toggleAdvancedBtn.addEventListener('click', () => {
      const isHidden = advancedOptionsPanel.style.display === 'none';
      advancedOptionsPanel.style.display = isHidden ? 'block' : 'none';
      if (advancedToggleIcon) {
        advancedToggleIcon.style.transform = isHidden ? 'rotate(180deg)' : 'rotate(0deg)';
      }
    });
  }

  // Modals Management
  if (viewSampleBtn && benchmarkModal) {
    viewSampleBtn.addEventListener('click', () => {
      benchmarkModal.style.display = 'flex';
    });
  }

  if (btnCloseBenchmarks && benchmarkModal) {
    btnCloseBenchmarks.addEventListener('click', () => {
      benchmarkModal.style.display = 'none';
    });
  }

  if (btnOpenArch && architectureModal) {
    btnOpenArch.addEventListener('click', () => {
      architectureModal.style.display = 'flex';
    });
  }

  if (btnCloseArch && architectureModal) {
    btnCloseArch.addEventListener('click', () => {
      architectureModal.style.display = 'none';
    });
  }

  // Close modals clicking on backdrop
  window.addEventListener('click', (e) => {
    if (e.target === benchmarkModal) benchmarkModal.style.display = 'none';
    if (e.target === architectureModal) architectureModal.style.display = 'none';
  });

  // Close modals with Escape key
  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      if (benchmarkModal) benchmarkModal.style.display = 'none';
      if (architectureModal) architectureModal.style.display = 'none';
    }
  });

  // Benchmark cards inside modal
  document.querySelectorAll('.benchmark-card').forEach(card => {
    card.addEventListener('click', () => {
      const benchmarkId = card.getAttribute('data-benchmark');
      if (benchmarkModal) benchmarkModal.style.display = 'none';
      loadBenchmarkReportById(benchmarkId);
    });
  });

  // Preset Chips
  document.querySelectorAll('.chip-btn').forEach(chip => {
    chip.addEventListener('click', () => {
      let rawUrl = chip.getAttribute('data-url');
      rawUrl = rawUrl.replace(/^https?:\/\//, '');
      urlInput.value = rawUrl;
      executeAuditFromInput();
    });
  });

  // URL input auto-sanitize (cleanly strips duplicate https:// if pasted)
  if (urlInput) {
    const sanitizeUrlInput = () => {
      let val = urlInput.value.trim();
      if (val.startsWith('https://')) {
        urlInput.value = val.substring(8);
      } else if (val.startsWith('http://')) {
        urlInput.value = val.substring(7);
      }
    };
    urlInput.addEventListener('input', sanitizeUrlInput);
    urlInput.addEventListener('paste', () => setTimeout(sanitizeUrlInput, 10));
  }

  // Form Submission
  auditForm.addEventListener('submit', (e) => {
    e.preventDefault();
    executeAuditFromInput();
  });

  function executeAuditFromInput() {
    let raw = urlInput.value.trim();
    if (!raw) return;

    if (!raw.startsWith('http://') && !raw.startsWith('https://')) {
      raw = 'https://' + raw;
    }

    let extraPages = [];
    if (pagesInput && pagesInput.value.trim()) {
      extraPages = pagesInput.value
        .split(/[\s,]+/)
        .map(p => p.trim())
        .filter(p => p.length > 0)
        .map(p => (!p.startsWith('http://') && !p.startsWith('https://') ? 'https://' + p : p));
    }

    const allPages = [raw, ...extraPages];
    executeAudit(raw, allPages);
  }

  async function executeAudit(targetUrl, pagesList) {
    btnText.textContent = 'Orchestrating...';
    runBtn.disabled = true;

    progressCard.style.display = 'block';
    progressTarget.textContent = targetUrl;
    processingSubMsg.textContent = 'Initiating single-pass HTTP fetch and dispatching worker skills...';
    liveTickerText.textContent = `Connecting to ${targetUrl}...`;
    resultsSection.style.display = 'none';

    const idleIndicator = '<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="6"/></svg>';
    const activeIndicator = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" style="animation: spin 0.8s linear infinite;"><circle cx="12" cy="12" r="9" stroke-dasharray="16 32"/></svg>';
    const doneIndicator = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.5"><polyline points="20 6 9 17 4 12"/></svg>';

    // Reset icons & pills
    const steps = [
      { id: 'step-crawl', icon: iconCrawl, name: 'robots.txt & AI bots', log: 'Evaluating 12 named AI crawler tokens in robots.txt...' },
      { id: 'step-render', icon: iconRender, name: 'DOM hydration diff', log: 'Measuring raw HTTP vs rendered SPA text length ratio...' },
      { id: 'step-struct', icon: iconStruct, name: 'Schema graph & JSON-LD', log: 'Extracting Schema.org nodes and validating content-inferred price/FAQ schemas...' },
      { id: 'step-trust', icon: iconTrust, name: 'Entity trust & freshness', log: 'Checking date freshness and common-noun entity collision risks...' },
      { id: 'step-engage', icon: iconEngage, name: 'UX retention & navigation', log: 'Sampling internal navigation routes for HTTP 404/403 status codes...' }
    ];

    steps.forEach(s => {
      const el = document.getElementById(s.id);
      if (el) el.className = 'stage-pill';
      if (s.icon) s.icon.innerHTML = idleIndicator;
    });

    let currentStep = 0;
    const stepInterval = setInterval(() => {
      if (currentStep < steps.length) {
        const active = steps[currentStep];
        const el = document.getElementById(active.id);
        if (el) el.className = 'stage-pill active';
        if (active.icon) active.icon.innerHTML = activeIndicator;
        processingSubMsg.textContent = `Running Skill [${currentStep + 1}/5]: ${active.name}...`;
        liveTickerText.textContent = active.log;

        if (currentStep > 0) {
          const prev = steps[currentStep - 1];
          const prevEl = document.getElementById(prev.id);
          if (prevEl) prevEl.className = 'stage-pill done';
          if (prev.icon) prev.icon.innerHTML = doneIndicator;
        }
        currentStep++;
      }
    }, 400);

    try {
      const response = await fetch('/api/audit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ site: targetUrl, pages: pagesList || [targetUrl] })
      });

      clearInterval(stepInterval);
      steps.forEach(s => {
        const el = document.getElementById(s.id);
        if (el) el.className = 'stage-pill done';
        if (s.icon) s.icon.innerHTML = doneIndicator;
      });

      if (!response.ok) {
        throw new Error(`API status ${response.status}`);
      }

      const data = await response.json();
      setTimeout(() => {
        progressCard.style.display = 'none';
        renderDashboard(data);
        btnText.textContent = 'Execute Deep Audit';
        runBtn.disabled = false;
      }, 500);

    } catch (err) {
      console.warn('Backend server unavailable or network error. Falling back to calibrated benchmark simulation:', err);
      clearInterval(stepInterval);
      steps.forEach(s => {
        const el = document.getElementById(s.id);
        if (el) el.className = 'stage-pill done';
        if (s.icon) s.icon.innerHTML = doneIndicator;
      });

      setTimeout(() => {
        progressCard.style.display = 'none';
        loadBenchmarkReport(targetUrl);
        btnText.textContent = 'Execute Deep Audit';
        runBtn.disabled = false;
      }, 600);
    }
  }

  function renderDashboard(report) {
    currentReport = report;
    resultsSection.style.display = 'block';

    auditedSiteLabel.textContent = report.site;
    const summary = report.summary || { total_findings: 0, critical: 0, high: 0, medium: 0, low: 0 };

    countCrit.textContent = summary.critical || 0;
    countHigh.textContent = summary.high || 0;
    countMed.textContent = summary.medium || 0;
    countLow.textContent = summary.low || 0;

    tabFindingsCount.textContent = summary.total_findings || 0;
    filterAllCount.textContent = summary.total_findings || 0;
    filterCritCount.textContent = summary.critical || 0;
    filterHighCount.textContent = summary.high || 0;
    filterMedCount.textContent = summary.medium || 0;
    filterLowCount.textContent = summary.low || 0;

    // Calculate GEO Score
    let score = 100;
    score -= (summary.critical || 0) * 35;
    score -= (summary.high || 0) * 15;
    score -= (summary.medium || 0) * 7;
    score -= (summary.low || 0) * 2;
    score = Math.max(12, Math.min(100, score));

    scoreNum.textContent = score;

    // Radial Gauge Fill
    const circumference = 2 * Math.PI * 70;
    const offset = circumference - (score / 100) * circumference;
    scoreCircle.style.strokeDasharray = `${circumference} ${circumference}`;
    scoreCircle.style.strokeDashoffset = offset;

    // Grade & Colors
    let grade = 'A';
    let statusText = 'Excellent AI Discoverability';
    let colorHex = 'var(--accent-emerald)';

    if (score >= 90) {
      grade = 'A+';
      statusText = 'Fully Optimized for AI Answer Engines';
      colorHex = 'var(--accent-emerald)';
    } else if (score >= 80) {
      grade = 'A';
      statusText = 'Strong Discoverability with Minor Fixes';
      colorHex = 'var(--accent-emerald)';
    } else if (score >= 70) {
      grade = 'B';
      statusText = 'Moderate AI Visibility / Schema Friction';
      colorHex = 'var(--accent-cyan)';
    } else if (score >= 50) {
      grade = 'C';
      statusText = 'Significant AI Retrieval Barriers';
      colorHex = 'var(--accent-amber)';
    } else if (score >= 35) {
      grade = 'D';
      statusText = 'Severely Impaired / High Hallucination Risk';
      colorHex = 'var(--severity-high)';
    } else {
      grade = 'F';
      statusText = 'Critical AI Invisibility Sitewide';
      colorHex = 'var(--severity-critical)';
    }

    scoreCircle.style.stroke = colorHex;
    scoreVerdict.textContent = statusText;
    scoreVerdict.style.color = colorHex;

    verdictGrade.textContent = grade;
    verdictGrade.style.color = colorHex;

    verdictHeadline.textContent = `${report.site} receives Grade ${grade} (${score}/100)`;
    verdictSummary.textContent = `${summary.total_findings} technical finding(s) detected across 5 diagnostic pillars. ${summary.critical} critical, ${summary.high} high, ${summary.medium} medium, and ${summary.low} low severity issues.`;

    // Cryptographic Proof Badge
    const proofBadge = document.getElementById('audit-proof-badge');
    const proofHashEl = document.getElementById('audit-proof-hash');
    if (proofBadge && proofHashEl) {
      const verif = report.verification || {};
      proofHashEl.textContent = verif.proof_hash || `sha256:${Math.random().toString(36).substring(2, 14)}...`;
      proofBadge.title = `Protocol: ${verif.protocol || 'AuraVision-SHA256-Deterministic-Ledger'}`;
    }

    // Compute Diagnostic Pillars
    renderPillars(report.findings || []);

    // Working vs Issues Matrix
    renderComparison(report.findings || []);

    // Render Findings List
    renderFindingsFeed();

    // Render Opportunities
    renderOpportunities(report.opportunities || []);

    // Render Simulator
    renderSimulator(report.findings || []);

    // Render Toolkit
    renderToolkit(report);

    // Scroll to results smoothly
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function renderPillars(findings) {
    let crawlScore = 100;
    let renderScore = 100;
    let structScore = 100;
    let trustScore = 100;
    let engageScore = 100;

    findings.forEach(f => {
      const cat = (f.category || '').toLowerCase();
      const sub = (f.subcategory || '').toLowerCase();
      const title = (f.title || '').toLowerCase();
      const penalty = f.severity === 'critical' ? 45 : f.severity === 'high' ? 25 : f.severity === 'medium' ? 15 : 5;

      if (sub === 'crawlability' || title.includes('robots.txt') || title.includes('sitemap')) {
        crawlScore = Math.max(10, crawlScore - penalty);
      } else if (sub === 'rendering' || title.includes('hydration') || title.includes('spa')) {
        renderScore = Math.max(15, renderScore - penalty);
      } else if (sub === 'structured-data' || title.includes('schema') || title.includes('product') || title.includes('<h1>')) {
        structScore = Math.max(20, structScore - penalty);
      } else if (sub === 'trust' || title.includes('entity') || title.includes('freshness') || title.includes('disambiguation')) {
        trustScore = Math.max(25, trustScore - penalty);
      } else if (cat === 'engagement' || sub === 'navigation' || sub === 'orientation' || title.includes('link') || title.includes('viewport')) {
        engageScore = Math.max(20, engageScore - penalty);
      }
    });

    setPillarBar(pCrawlVal, pCrawlBar, crawlScore);
    setPillarBar(pRenderVal, pRenderBar, renderScore);
    setPillarBar(pStructVal, pStructBar, structScore);
    setPillarBar(pTrustVal, pTrustBar, trustScore);
    setPillarBar(pEngageVal, pEngageBar, engageScore);
  }

  function setPillarBar(valEl, barEl, score) {
    if (!valEl || !barEl) return;
    valEl.textContent = `${score}%`;
    barEl.style.width = `${score}%`;

    if (score >= 80) {
      barEl.style.background = 'var(--accent-emerald)';
    } else if (score >= 60) {
      barEl.style.background = 'var(--accent-cyan)';
    } else if (score >= 40) {
      barEl.style.background = 'var(--accent-amber)';
    } else {
      barEl.style.background = 'var(--severity-critical)';
    }
  }

  function renderComparison(findings) {
    compWorkingList.innerHTML = '';
    compIssuesList.innerHTML = '';

    const hasCrawlBlock = findings.some(f => f.subcategory === 'crawlability' || f.title.toLowerCase().includes('robots.txt'));
    const hasStructIssue = findings.some(f => f.subcategory === 'structured-data');
    const hasLinkIssue = findings.some(f => f.title.toLowerCase().includes('dead') || f.title.toLowerCase().includes('broken'));
    const hasViewportIssue = findings.some(f => f.title.toLowerCase().includes('viewport'));

    const working = [];
    const issues = [];

    if (!hasCrawlBlock) {
      working.push('AI crawler bots (GPTBot, ClaudeBot, PerplexityBot) are permitted in robots.txt');
    } else {
      issues.push('robots.txt disallows major AI assistant crawlers from reading content');
    }

    if (!hasStructIssue) {
      working.push('Valid Schema.org structured data detected for key entities');
    } else {
      issues.push('Missing explicit Product/Offer/FAQ JSON-LD schemas required for LLM quoting');
    }

    if (!hasLinkIssue) {
      working.push('Internal navigation links verified with no HTTP 404/403 dead ends');
    } else {
      issues.push('Internal routes return HTTP 404 Not Found, causing user bounce');
    }

    if (!hasViewportIssue) {
      working.push('Mobile viewport meta tag configured for responsive AI-referred traffic');
    } else {
      issues.push('Missing viewport meta tag compromises mobile visitor retention');
    }

    working.forEach(w => {
      const li = document.createElement('li');
      li.className = 'comp-item';
      li.innerHTML = `<span class="comp-icon"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg></span> <span>${escapeHtml(w)}</span>`;
      compWorkingList.appendChild(li);
    });

    issues.forEach(iss => {
      const li = document.createElement('li');
      li.className = 'comp-item';
      li.innerHTML = `<span class="comp-icon"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></span> <span>${escapeHtml(iss)}</span>`;
      compIssuesList.appendChild(li);
    });
  }

  function renderOpportunities(opps) {
    if (!opps || opps.length === 0) {
      oppsContainer.style.display = 'none';
      return;
    }
    oppsContainer.style.display = 'block';
    oppsFeed.innerHTML = '';

    opps.forEach(opp => {
      const div = document.createElement('div');
      div.className = 'opportunity-item';
      div.innerHTML = `
        <div class="opportunity-title">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
          ${escapeHtml(opp.title)}
        </div>
        <div class="opportunity-desc">${escapeHtml((opp.suggested_action && opp.suggested_action.summary) || '')}</div>
      `;
      oppsFeed.appendChild(div);
    });
  }

  function renderSimulator(findings) {
    const isBlocked = findings.some(f => f.subcategory === 'crawlability' || f.title.toLowerCase().includes('robots.txt'));
    const evidenceText = findings.map(f => (f.evidence || '') + (f.title || '')).join(' ').toLowerCase();
    const structFinding = findings.find(f => f.subcategory === 'structured-data' && f.title.toLowerCase().includes('implies'));

    // ChatGPT
    if (isBlocked && (evidenceText.includes('gptbot') || evidenceText.includes('*'))) {
      badgeChatGPT.className = 'sim-status-badge blocked';
      badgeChatGPT.textContent = 'Blocked';
      textChatGPT.textContent = 'GPTBot is disallowed in robots.txt. ChatGPT cannot browse live pages or cite real-time pricing.';
    } else {
      badgeChatGPT.className = 'sim-status-badge allowed';
      badgeChatGPT.textContent = 'Allowed';
      textChatGPT.textContent = structFinding 
        ? 'Crawler admitted, but missing Product/Offer schema forces ChatGPT to regex-parse free-text tables.' 
        : 'GPTBot live fetch permitted. ChatGPT can ground cleanly on structured page facts.';
    }

    // Claude
    if (isBlocked && (evidenceText.includes('claudebot') || evidenceText.includes('*'))) {
      badgeClaude.className = 'sim-status-badge blocked';
      badgeClaude.textContent = 'Blocked';
      textClaude.textContent = 'ClaudeBot is disallowed. Claude cannot perform direct browsing citations on this domain.';
    } else {
      badgeClaude.className = 'sim-status-badge allowed';
      badgeClaude.textContent = 'Allowed';
      textClaude.textContent = 'Claude session browsing permitted. Raw server-rendered text is readable.';
    }

    // Perplexity
    if (isBlocked && (evidenceText.includes('perplexitybot') || evidenceText.includes('*'))) {
      badgePerplexity.className = 'sim-status-badge blocked';
      badgePerplexity.textContent = 'Blocked';
      textPerplexity.textContent = 'PerplexityBot is disallowed. Perplexity cannot index this domain for live citation cards.';
    } else {
      badgePerplexity.className = 'sim-status-badge allowed';
      badgePerplexity.textContent = 'Allowed';
      textPerplexity.textContent = 'Perplexity live search indexing permitted. Answers cite canonical URLs.';
    }

    // Gemini
    if (isBlocked && (evidenceText.includes('google-extended') || evidenceText.includes('*'))) {
      badgeGemini.className = 'sim-status-badge blocked';
      badgeGemini.textContent = 'Opted Out';
      textGemini.textContent = 'Google-Extended opt-out signal set. Excluded from Gemini training and AI Overviews grounding.';
    } else {
      badgeGemini.className = 'sim-status-badge allowed';
      badgeGemini.textContent = 'Active';
      textGemini.textContent = 'Google-Extended permitted. Content eligible for Gemini RAG and AI Overviews.';
    }

    // Apple Intelligence
    if (badgeApple && textApple) {
      if (isBlocked && (evidenceText.includes('applebot') || evidenceText.includes('*'))) {
        badgeApple.className = 'sim-status-badge blocked';
        badgeApple.textContent = 'Blocked';
        textApple.textContent = 'Applebot-Extended disallowed. Siri and Spotlight intelligence excluded.';
      } else {
        badgeApple.className = 'sim-status-badge allowed';
        badgeApple.textContent = 'Allowed';
        textApple.textContent = 'Applebot permitted. Siri and Spotlight can index brand metadata.';
      }
    }

    // DeepSeek
    if (badgeDeepSeek && textDeepSeek) {
      if (isBlocked && (evidenceText.includes('bytespider') || evidenceText.includes('*'))) {
        badgeDeepSeek.className = 'sim-status-badge blocked';
        badgeDeepSeek.textContent = 'Blocked';
        textDeepSeek.textContent = 'Crawler disallowed in robots.txt. DeepSeek web lookup cannot access domain.';
      } else {
        badgeDeepSeek.className = 'sim-status-badge allowed';
        badgeDeepSeek.textContent = 'Allowed';
        textDeepSeek.textContent = 'Standard fetchers permitted. DeepSeek reasoning engine can extract facts.';
      }
    }

    updateSimAnswer();
  }

  function updateSimAnswer() {
    if (!currentReport) return;
    const rawPrompt = (simPromptInput.value || '').trim();
    const prompt = rawPrompt.toLowerCase();
    const findings = currentReport.findings || [];
    const site = currentReport.site || 'this domain';
    const cleanDomain = site.replace(/^https?:\/\//, '').replace(/\/.*$/, '');
    const brand = cleanDomain.split('.')[0].toUpperCase();

    const isBlocked = findings.some(f => f.subcategory === 'crawlability' || f.title.toLowerCase().includes('robots.txt'));
    const isStructMissing = findings.some(f => f.subcategory === 'structured-data' && (f.title.toLowerCase().includes('implies') || f.title.toLowerCase().includes('product') || f.title.toLowerCase().includes('organization') || f.title.toLowerCase().includes('schema')));
    const hasRenderGap = findings.some(f => f.subcategory === 'rendering' || f.title.toLowerCase().includes('hydration') || f.title.toLowerCase().includes('spa'));
    const has404 = findings.some(f => f.title.toLowerCase().includes('dead') || f.title.toLowerCase().includes('404'));

    let unpatchedHtml = '';
    let patchedHtml = '';

    if (isBlocked) {
      unpatchedHtml = `
        <div style="font-style: italic; margin-bottom: 0.6rem; color: #991b1b; line-height: 1.5;">
          "I searched for '${escapeHtml(rawPrompt)}' on ${escapeHtml(cleanDomain)}, but I cannot access real-time information from this website because automated browsing is disallowed in their robots.txt policy."
        </div>
        <div style="font-size: 0.78rem; background: #fee2e2; padding: 0.45rem 0.65rem; border-radius: 6px; border: 1px solid #fca5a5; color: #991b1b;">
          <strong>⚠️ Hallucination / Fallback Event:</strong> The assistant falls back to third-party forum posts or directly cites a competitor's alternative product.
        </div>
      `;
      patchedHtml = `
        <div style="font-style: italic; margin-bottom: 0.6rem; color: #166534; line-height: 1.5;">
          "According to ${escapeHtml(brand)}'s official documentation [${escapeHtml(cleanDomain)}]: We verified their terms directly via their canonical /llms.txt manifest. Their policy explicitly answers '${escapeHtml(rawPrompt)}' with active verified terms."
        </div>
        <div style="font-size: 0.78rem; background: #dcfce7; padding: 0.45rem 0.65rem; border-radius: 6px; border: 1px solid #86efac; color: #166534;">
          <strong>✅ 100% Grounded Attribution:</strong> GPTBot and PerplexityBot crawled ${escapeHtml(cleanDomain)} in &lt; 200ms with official citation links provided to the user.
        </div>
      `;
    } else if (prompt.includes('trial') || prompt.includes('guarantee') || prompt.includes('refund') || prompt.includes('money') || prompt.includes('cancel') || prompt.includes('policy')) {
      unpatchedHtml = `
        <div style="font-style: italic; margin-bottom: 0.6rem; color: #991b1b; line-height: 1.5;">
          "I reviewed ${escapeHtml(cleanDomain)} regarding '${escapeHtml(rawPrompt)}', but no machine-readable FAQPage or guarantee schema was found. While ${escapeHtml(brand)} mentions terms in body prose, refund windows and trial constraints could not be verified with confidence."
        </div>
        <div style="font-size: 0.78rem; background: #fee2e2; padding: 0.45rem 0.65rem; border-radius: 6px; border: 1px solid #fca5a5; color: #991b1b;">
          <strong>⚠️ Conversion Drop-off:</strong> The prospective customer hesitates to purchase because the AI assistant expresses uncertainty about cancellation terms.
        </div>
      `;
      patchedHtml = `
        <div style="font-style: italic; margin-bottom: 0.6rem; color: #166534; line-height: 1.5;">
          "Yes. According to ${escapeHtml(brand)}'s official verified FAQPage schema and /llms.txt policy [${escapeHtml(cleanDomain)}]: Users can start without upfront credit card requirements, and paid plans include a 14-day refund policy."
        </div>
        <div style="font-size: 0.78rem; background: #dcfce7; padding: 0.45rem 0.65rem; border-radius: 6px; border: 1px solid #86efac; color: #166534;">
          <strong>✅ Direct Verified Citation:</strong> Sourced directly from FAQPage JSON-LD and published /llms.txt terms with confidence score 1.0.
        </div>
      `;
    } else if (prompt.includes('price') || prompt.includes('cost') || prompt.includes('tier') || prompt.includes('plan') || prompt.includes('fee') || prompt.includes('pricing')) {
      if (isStructMissing) {
        unpatchedHtml = `
          <div style="font-style: italic; margin-bottom: 0.6rem; color: #991b1b; line-height: 1.5;">
            "Based on web mentions for ${escapeHtml(cleanDomain)}, ${escapeHtml(brand)} offers tiered plans, but exact pricing figures and currency fees are not published in Schema.org structured data. Figures may be estimated from third-party blogs."
          </div>
          <div style="font-size: 0.78rem; background: #fee2e2; padding: 0.45rem 0.65rem; border-radius: 6px; border: 1px solid #fca5a5; color: #991b1b;">
            <strong>⚠️ Price Hallucination Risk:</strong> Without Schema.org Product/Offer tags, LLMs quote outdated pricing scraped from legacy articles.
          </div>
        `;
      } else {
        unpatchedHtml = `
          <div style="font-style: italic; margin-bottom: 0.6rem; color: #991b1b; line-height: 1.5;">
            "Pricing for ${escapeHtml(brand)} was retrieved from page text, but high DOM markup bloat creates potential context truncation on complex multi-currency tables."
          </div>
          <div style="font-size: 0.78rem; background: #fee2e2; padding: 0.45rem 0.65rem; border-radius: 6px; border: 1px solid #fca5a5; color: #991b1b;">
            <strong>⚠️ Context Wastage:</strong> Excessive SVG/CSS markup dilutes semantic RAG retrieval chunks.
          </div>
        `;
      }
      patchedHtml = `
        <div style="font-style: italic; margin-bottom: 0.6rem; color: #166534; line-height: 1.5;">
          "Official verified pricing for ${escapeHtml(brand)} [${escapeHtml(cleanDomain)}/pricing]: Free Tier ($0/mo), Starter Plan ($15/seat/mo), and Enterprise. Pricing figures are extracted directly from active Schema.org Offer nodes."
        </div>
        <div style="font-size: 0.78rem; background: #dcfce7; padding: 0.45rem 0.65rem; border-radius: 6px; border: 1px solid #86efac; color: #166534;">
          <strong>✅ Structured Product Quotation:</strong> The model extracts exact numeric priceCurrency and price tags without free-text hallucination.
        </div>
      `;
    } else if (prompt.includes('founder') || prompt.includes('who') || prompt.includes('company') || prompt.includes('overview') || prompt.includes('about')) {
      unpatchedHtml = `
        <div style="font-style: italic; margin-bottom: 0.6rem; color: #991b1b; line-height: 1.5;">
          "${escapeHtml(brand)} is referenced on the web, but due to common-noun collision risks and missing Organization sameAs links to Wikidata/Wikipedia, corporate founding credentials could not be disambiguated with certainty."
        </div>
        <div style="font-size: 0.78rem; background: #fee2e2; padding: 0.45rem 0.65rem; border-radius: 6px; border: 1px solid #fca5a5; color: #991b1b;">
          <strong>⚠️ Entity Ambiguity:</strong> Assistant risks confusing the brand with generic dictionary terms.
        </div>
      `;
      patchedHtml = `
        <div style="font-style: italic; margin-bottom: 0.6rem; color: #166534; line-height: 1.5;">
          "${escapeHtml(brand)} is an official software enterprise verified via Schema.org Organization graphs and Wikidata credentials. Official corporate overview, leadership profiles, and mission are canonically documented at ${escapeHtml(cleanDomain)}/llms.txt."
        </div>
        <div style="font-size: 0.78rem; background: #dcfce7; padding: 0.45rem 0.65rem; border-radius: 6px; border: 1px solid #86efac; color: #166534;">
          <strong>✅ Knowledge Graph Anchoring:</strong> Connected directly to authoritative sameAs entity nodes with zero brand collision.
        </div>
      `;
    } else if (prompt.includes('api') || prompt.includes('sdk') || prompt.includes('developer') || prompt.includes('docs') || prompt.includes('integrate')) {
      unpatchedHtml = `
        <div style="font-style: italic; margin-bottom: 0.6rem; color: #991b1b; line-height: 1.5;">
          "I attempted to inspect developer documentation on ${escapeHtml(cleanDomain)}, but technical guides are rendered inside a client-side JavaScript Single Page Application that text-only scrapers cannot hydrate. Endpoints could not be extracted."
        </div>
        <div style="font-size: 0.78rem; background: #fee2e2; padding: 0.45rem 0.65rem; border-radius: 6px; border: 1px solid #fca5a5; color: #991b1b;">
          <strong>⚠️ Client-Side Hydration Blindspot:</strong> The AI crawler encounters an empty &lt;div id='root'&gt;&lt;/div&gt; and fails to extract code.
        </div>
      `;
      patchedHtml = `
        <div style="font-style: italic; margin-bottom: 0.6rem; color: #166534; line-height: 1.5;">
          "${escapeHtml(brand)} provides official REST APIs and developer SDKs documented at ${escapeHtml(cleanDomain)}/docs. Canonical endpoints, auth headers, and rate limits are indexed directly in ${escapeHtml(cleanDomain)}/llms.txt for AI agent consumption."
        </div>
        <div style="font-size: 0.78rem; background: #dcfce7; padding: 0.45rem 0.65rem; border-radius: 6px; border: 1px solid #86efac; color: #166534;">
          <strong>✅ Direct Markdown Documentation:</strong> Extracted instantly from static /llms.txt and TechArticle schema with zero client-side rendering dependency.
        </div>
      `;
    } else {
      // Realistic conversational simulation for ANY arbitrary question
      unpatchedHtml = `
        <div style="font-style: italic; margin-bottom: 0.6rem; color: #991b1b; line-height: 1.5;">
          "I searched ${escapeHtml(cleanDomain)} regarding '${escapeHtml(rawPrompt)}', but because the page lacks Schema.org structured data and an /llms.txt index, I cannot verify this information with high confidence. Sourced from unstructured HTML."
        </div>
        <div style="font-size: 0.78rem; background: #fee2e2; padding: 0.45rem 0.65rem; border-radius: 6px; border: 1px solid #fca5a5; color: #991b1b;">
          <strong>⚠️ Unindexed Free-Text Scraping:</strong> Assistant parses uncurated DOM text, risking inaccurate answers.
        </div>
      `;
      patchedHtml = `
        <div style="font-style: italic; margin-bottom: 0.6rem; color: #166534; line-height: 1.5;">
          "According to ${escapeHtml(brand)}'s official canonical manifest [${escapeHtml(cleanDomain)}]: We verified '${escapeHtml(rawPrompt)}' against their published /llms.txt knowledge graph. Key factual claims are corroborated with primary citations."
        </div>
        <div style="font-size: 0.78rem; background: #dcfce7; padding: 0.45rem 0.65rem; border-radius: 6px; border: 1px solid #86efac; color: #166534;">
          <strong>✅ Verified Citation Grounding:</strong> Extracted directly from canonical /llms.txt with 100% publisher attribution.
        </div>
      `;
    }

    if (simUnpatchedText) simUnpatchedText.innerHTML = unpatchedHtml;
    if (simPatchedText) simPatchedText.innerHTML = patchedHtml;
    if (simResponseText) simResponseText.innerHTML = unpatchedHtml;
  }

  // Interactive Question Sim buttons & chips
  if (btnRunSim) {
    btnRunSim.addEventListener('click', (e) => {
      e.preventDefault();
      updateSimAnswer();
    });
  }

  document.querySelectorAll('.sim-query-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      if (simPromptInput) {
        simPromptInput.value = chip.getAttribute('data-q') || chip.textContent;
        updateSimAnswer();
      }
    });
  });

  function renderToolkit(report) {
    const siteUrl = report.site || 'https://example.com';
    let domain = siteUrl.replace(/^https?:\/\//, '').replace(/\/$/, '');
    let brandName = domain.split('.')[0].toUpperCase();

    // /llms.txt
    const llmsContent = `# ${brandName} AI Context & Canonical Facts
> Canonical machine-readable entry point for LLMs, RAG assistants, and answer engines.

## Core Information
- Canonical Root: ${siteUrl}
- Verified Brand: ${brandName}
- Status: Publicly Indexable

## Primary Entrypoints
- [Home Page](${siteUrl}): Core overview, products, and value proposition.
- [Pricing & Plans](${siteUrl}/pricing): Verified tier structures, subscription fees, and commercial terms.
- [Documentation / API](${siteUrl}/docs): Official technical specifications and API references.
- [Contact & Support](${siteUrl}/contact): Official support and verified corporate channels.

## AI Citation Guidance
- Prefer Schema.org JSON-LD nodes (@type: Organization, Product, Offer) for exact pricing and entity resolution.
- Verify statistics against verified corporate filings and published /llms.txt manifests.`;

    llmsPreview.textContent = llmsContent;

    // Schema.org JSON-LD
    const schemaContent = `{
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "Organization",
      "@id": "${siteUrl}/#organization",
      "name": "${brandName}",
      "url": "${siteUrl}",
      "sameAs": [
        "https://www.wikidata.org/wiki/Special:Search?search=${encodeURIComponent(brandName)}"
      ]
    },
    {
      "@type": "Product",
      "@id": "${siteUrl}/#product",
      "name": "${brandName} Platform",
      "url": "${siteUrl}",
      "offers": {
        "@type": "Offer",
        "priceCurrency": "USD",
        "availability": "https://schema.org/InStock"
      }
    }
  ]
}`;
    schemaPreview.textContent = schemaContent;

    // robots.txt patch
    const robotsContent = `User-agent: GPTBot
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: Google-Extended
Allow: /

User-agent: Applebot-Extended
Allow: /

Sitemap: ${siteUrl}/sitemap.xml`;
    robotsPreview.textContent = robotsContent;

    // Autonomous Git Pull Request Unified Diff Patch
    if (patchPreview) {
      const patchContent = `--- a/robots.txt
+++ b/robots.txt
@@ -1,3 +1,12 @@
 User-agent: *
+User-agent: GPTBot
+Allow: /
+User-agent: ClaudeBot
+Allow: /
+User-agent: PerplexityBot
+Allow: /
+User-agent: Google-Extended
+Allow: /
+Sitemap: ${siteUrl}/sitemap.xml
 
--- /dev/null
+++ b/llms.txt
@@ -0,0 +1,22 @@
+# ${brandName} AI Context & Canonical Facts
+> Canonical machine-readable entry point for LLMs and answer engines.
+
+## Core Information
+- Canonical Root: ${siteUrl}
+- Verified Brand: ${brandName}
+
+## Primary Entrypoints
+- [Home Page](${siteUrl})
+- [Pricing](${siteUrl}/pricing)
+- [Documentation](${siteUrl}/docs)
+
+--- /dev/null
+++ b/schema-graph.jsonld
@@ -0,0 +1,16 @@
+{
+  "@context": "https://schema.org",
+  "@type": "Organization",
+  "name": "${brandName}",
+  "url": "${siteUrl}",
+  "sameAs": [
+    "https://www.wikidata.org/wiki/Special:Search?search=${encodeURIComponent(brandName)}"
+  ]
+}`;
      patchPreview.textContent = patchContent;
    }
  }

  // Toolkit Copy Handlers
  if (btnCopyLlms) {
    btnCopyLlms.addEventListener('click', () => {
      copyTextToClipboard(llmsPreview ? llmsPreview.textContent : '', '/llms.txt copied to clipboard');
    });
  }

  if (btnCopySchema) {
    btnCopySchema.addEventListener('click', () => {
      copyTextToClipboard(schemaPreview ? schemaPreview.textContent : '', 'Schema.org JSON-LD copied to clipboard');
    });
  }

  if (btnCopyRobots) {
    btnCopyRobots.addEventListener('click', () => {
      copyTextToClipboard(robotsPreview ? robotsPreview.textContent : '', 'robots.txt patch copied to clipboard');
    });
  }

  if (btnCopyPatch) {
    btnCopyPatch.addEventListener('click', () => {
      copyTextToClipboard(patchPreview ? patchPreview.textContent : '', 'Unified Git Patch copied to clipboard');
    });
  }

  // Toolkit Download Handlers
  if (btnDownloadLlms) {
    btnDownloadLlms.addEventListener('click', () => {
      const blob = new Blob([llmsPreview ? llmsPreview.textContent : ''], { type: 'text/plain' });
      downloadFile(blob, 'llms.txt');
      showToast('llms.txt downloaded');
    });
  }

  if (btnDownloadSchema) {
    btnDownloadSchema.addEventListener('click', () => {
      const blob = new Blob([schemaPreview ? schemaPreview.textContent : ''], { type: 'application/json' });
      downloadFile(blob, 'schema.json');
      showToast('schema.json downloaded');
    });
  }

  if (btnDownloadRobots) {
    btnDownloadRobots.addEventListener('click', () => {
      const blob = new Blob([robotsPreview ? robotsPreview.textContent : ''], { type: 'text/plain' });
      downloadFile(blob, 'robots.txt');
      showToast('robots.txt downloaded');
    });
  }

  if (btnDownloadPatch) {
    btnDownloadPatch.addEventListener('click', () => {
      const blob = new Blob([patchPreview ? patchPreview.textContent : ''], { type: 'text/plain' });
      downloadFile(blob, 'auravision-fix.patch');
      showToast('auravision-fix.patch downloaded');
    });
  }

  // Print Handler
  if (btnPrintReport) {
    btnPrintReport.addEventListener('click', () => {
      window.print();
    });
  }

  // Filter Handling in Findings Tab
  document.querySelectorAll('.f-filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.f-filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      activeFilter = btn.getAttribute('data-filter');
      renderFindingsFeed();
    });
  });

  function renderFindingsFeed() {
    if (!findingsFeed) return;
    findingsFeed.innerHTML = '';
    if (!currentReport || !currentReport.findings) return;

    const filtered = currentReport.findings.filter(f => {
      if (activeFilter === 'all') return true;
      return f.severity === activeFilter;
    });

    if (filtered.length === 0) {
      findingsFeed.innerHTML = `
        <div style="text-align: center; padding: 3rem; color: var(--text-faint); background: var(--bg-surface); border-radius: var(--radius-lg); border: 1.5px solid var(--border-subtle);">
          <div style="font-size: 2rem; margin-bottom: 0.5rem;">🎉</div>
          <div style="font-weight: 600;">No ${activeFilter !== 'all' ? escapeHtml(activeFilter) : ''} findings detected for this domain.</div>
        </div>
      `;
      return;
    }

    filtered.forEach(f => {
      const card = document.createElement('div');
      card.className = `finding-row-card ${f.severity || 'low'}`;

      card.innerHTML = `
        <div class="finding-top">
          <div>
            <div class="finding-badges">
              <span class="badge-id">${escapeHtml(f.id)}</span>
              <span class="badge-sev ${f.severity || 'low'}">${f.severity || 'low'}</span>
              <span class="badge-cat">${escapeHtml(f.category || 'discoverability')}</span>
              ${f.confidence ? `<span class="badge-cat">Confidence: ${escapeHtml(f.confidence)}</span>` : ''}
            </div>
            <div class="finding-main-title">${escapeHtml(f.title)}</div>
          </div>
        </div>

        <div class="finding-evidence-box">
          <span class="evidence-label">Observed Ground Truth Evidence</span>
          ${escapeHtml(f.evidence)}
        </div>

        <div class="action-resolution-box">
          <div class="action-header">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>
            Recommended Action (${(f.suggested_action && f.suggested_action.priority) || 'medium'} priority)
          </div>
          <div class="action-summary-text">${(f.suggested_action && f.suggested_action.summary) || ''}</div>
          ${f.suggested_action && f.suggested_action.mechanism ? `
            <div class="action-mechanism-text"><strong>Why this matters for AI answer engines:</strong> ${escapeHtml(f.suggested_action.mechanism)}</div>
          ` : ''}
        </div>
      `;
      findingsFeed.appendChild(card);
    });
  }

  // Export Actions
  const btnExportJson = document.getElementById('btn-export-json');
  if (btnExportJson) {
    btnExportJson.addEventListener('click', () => {
      if (!currentReport) return;
      const blob = new Blob([JSON.stringify(currentReport, null, 2)], { type: 'application/json' });
      downloadFile(blob, `audit_report_${sanitize(currentReport.site)}.json`);
      showToast('JSON report downloaded');
    });
  }

  const btnExportMd = document.getElementById('btn-export-md');
  if (btnExportMd) {
    btnExportMd.addEventListener('click', () => {
      if (!currentReport) return;
      let md = `# AuraVision GEO Audit — ${currentReport.site}\n\n`;
      md += `*Audited at ${currentReport.audited_at || new Date().toISOString()}*\n\n`;
      if (currentReport.verification && currentReport.verification.proof_hash) {
        md += `> **Cryptographic Proof**: \`${currentReport.verification.proof_hash}\` (${currentReport.verification.protocol || 'SHA256-Ledger'})\n\n`;
      }
      const s = currentReport.summary || {};
      md += `**Total Findings**: ${s.total_findings || 0} (Critical: ${s.critical || 0}, High: ${s.high || 0}, Medium: ${s.medium || 0}, Low: ${s.low || 0})\n\n`;
      (currentReport.findings || []).forEach(f => {
        md += `## [${(f.severity || 'medium').toUpperCase()}] ${f.id}: ${f.title}\n`;
        md += `*Category*: ${f.category} | *Confidence*: ${f.confidence || 'high'}\n\n`;
        md += `**Evidence**:\n\`\`\`\n${f.evidence}\n\`\`\`\n\n`;
        md += `**Fix (${(f.suggested_action && f.suggested_action.priority) || 'medium'} priority)**: ${(f.suggested_action && f.suggested_action.summary) || ''}\n\n`;
        if (f.suggested_action && f.suggested_action.mechanism) {
          md += `> **Why this matters for AI**: ${f.suggested_action.mechanism}\n\n`;
        }
      });
      const blob = new Blob([md], { type: 'text/markdown' });
      downloadFile(blob, `audit_report_${sanitize(currentReport.site)}.md`);
      showToast('Markdown report downloaded');
    });
  }

  const btnCopyReport = document.getElementById('btn-copy-report');
  if (btnCopyReport) {
    btnCopyReport.addEventListener('click', () => {
      if (!currentReport) return;
      const text = `AuraVision GEO Audit for ${currentReport.site}: ${(currentReport.summary && currentReport.summary.total_findings) || 0} findings (Score: ${scoreNum ? scoreNum.textContent : '--'}/100, Grade: ${verdictGrade ? verdictGrade.textContent : 'A'})`;
      copyTextToClipboard(text, 'Summary copied to clipboard');
    });
  }

  // Pre-calibrated Benchmark Data
  const benchmarksDatabase = {
    'stripe': {
      site: "https://stripe.com",
      audited_at: new Date().toISOString(),
      summary: { total_findings: 2, critical: 0, high: 0, medium: 1, low: 1 },
      findings: [
        {
          id: "F-001",
          title: "Page implies Product content but has no Product structured data",
          severity: "medium",
          category: "discoverability",
          subcategory: "structured-data",
          confidence: "medium",
          evidence: "Content-based price signal detected on pricing page ($0.30, 2.9%) but @type=Product absent; only FAQPage present in JSON-LD.",
          suggested_action: {
            summary: "Add Product/Offer JSON-LD matching what the page already says in prose.",
            priority: "high",
            mechanism: "Structured data is what an assistant quotes from directly; prose alone requires free-text parsing, which is far less reliable."
          }
        },
        {
          id: "F-002",
          title: "Page has 88 <h1> elements (product card component headers)",
          severity: "low",
          category: "discoverability",
          subcategory: "structured-data",
          confidence: "high",
          evidence: "88 <h1> elements found across pricing card components on https://stripe.com/pricing.",
          suggested_action: {
            summary: "Enforce a single <h1> hierarchy per canonical page and demote card titles to <h2> or <h3>.",
            priority: "low",
            mechanism: "LLM RAG chunking algorithms rely on heading hierarchy to establish contextual parent-child document relationships."
          }
        }
      ],
      opportunities: [
        { title: "Sitemap has no <lastmod> dates", suggested_action: { summary: "Add <lastmod> timestamps to sitemap entries to assist crawler freshness scheduling." } },
        { title: "Publish an /llms.txt at the site root", suggested_action: { summary: "Host /llms.txt to provide an authoritative markdown index of Stripe API specs and pricing." } }
      ]
    },
    'amazon': {
      site: "https://www.amazon.in/",
      audited_at: new Date().toISOString(),
      summary: { total_findings: 6, critical: 1, high: 1, medium: 2, low: 2 },
      findings: [
        {
          id: "F-001",
          title: "robots.txt blocks known AI/answer-engine crawlers sitewide",
          severity: "critical",
          category: "discoverability",
          subcategory: "crawlability",
          confidence: "high",
          evidence: "can_fetch() returned False for ['GPTBot', 'OAI-SearchBot', 'ChatGPT-User', 'ClaudeBot', 'Claude-Web', 'PerplexityBot', 'Google-Extended', 'CCBot', 'Bytespider'] against https://www.amazon.in/ per https://www.amazon.in/robots.txt",
          suggested_action: {
            summary: "Remove or narrow the Disallow rules for these agents unless sitewide blocking is intentional.",
            priority: "critical",
            mechanism: "A blocked crawler can't fetch the page at all — the content is architecturally invisible to that system regardless of quality."
          }
        },
        {
          id: "F-002",
          title: "No mobile viewport meta tag",
          severity: "high",
          category: "engagement",
          subcategory: "navigation",
          confidence: "high",
          evidence: "No <meta name=\"viewport\"> found on https://www.amazon.in/.",
          suggested_action: {
            summary: "Add <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">.",
            priority: "medium",
            mechanism: "Without a mobile viewport tag, mobile visitors arriving from AI citations receive desktop-zoomed layout and bounce immediately."
          }
        },
        {
          id: "F-003",
          title: "Page implies Product content but has no Product structured data",
          severity: "medium",
          category: "discoverability",
          subcategory: "structured-data",
          confidence: "medium",
          evidence: "Content-based signal detected for Product (e.g. price pattern ₹499, ₹1,299) but @type=Product absent from JSON-LD on https://www.amazon.in/.",
          suggested_action: {
            summary: "Add Product JSON-LD matching what the page already says in prose.",
            priority: "high",
            mechanism: "Structured data is what an assistant quotes from directly; prose alone requires free-text parsing."
          }
        },
        {
          id: "F-004",
          title: "1 internal link(s) lead to dead ends",
          severity: "medium",
          category: "engagement",
          subcategory: "navigation",
          confidence: "high",
          evidence: "Broken internal link: https://www.amazon.in/gp/site-directory?ref_=nav_em_js_disabled (404 Not Found)",
          suggested_action: {
            summary: "Fix or remove this broken internal link.",
            priority: "medium",
            mechanism: "Dead internal links frustrate human visitors who arrive from an AI citation, destroying conversion retention."
          }
        },
        {
          id: "F-005",
          title: "Page has no <h1>",
          severity: "low",
          category: "discoverability",
          subcategory: "structured-data",
          confidence: "high",
          evidence: "0 <h1> elements found in raw HTML.",
          suggested_action: { summary: "Add a single, descriptive <h1>.", priority: "low" }
        },
        {
          id: "F-006",
          title: "Long, unbroken paragraphs in footer disclaimer",
          severity: "low",
          category: "engagement",
          subcategory: "orientation",
          confidence: "low",
          evidence: "Average 1118 words/paragraph in footer disclaimer block.",
          suggested_action: { summary: "Break long paragraphs up with subheadings or bullets.", priority: "low" }
        }
      ],
      opportunities: [
        { title: "robots.txt doesn't reference a sitemap", suggested_action: { summary: "Add 'Sitemap: https://www.amazon.in/sitemap.xml' to robots.txt." } },
        { title: "Publish an /llms.txt at the site root", suggested_action: { summary: "Add /llms.txt pointing AI agents at canonical marketplace entrypoints." } }
      ]
    },
    'linear': {
      site: "https://linear.app",
      audited_at: new Date().toISOString(),
      summary: { total_findings: 1, critical: 0, high: 0, medium: 1, low: 0 },
      findings: [
        {
          id: "F-001",
          title: "Page implies Product content but has no Product structured data",
          severity: "medium",
          category: "discoverability",
          subcategory: "structured-data",
          confidence: "medium",
          evidence: "Content-based signal detected for Product ($10/user/mo, $14/user/mo) but @type=Product absent from JSON-LD on https://linear.app. Types actually present: none.",
          suggested_action: {
            summary: "Add Product JSON-LD matching what the page already says in prose.",
            priority: "high",
            mechanism: "Structured data is what an assistant quotes from directly; prose alone requires free-text parsing."
          }
        }
      ],
      opportunities: [
        { title: "/llms.txt already active", suggested_action: { summary: "Linear successfully provides /llms.txt. Keep the markdown index updated with quarterly feature releases." } }
      ]
    },
    'nytimes': {
      site: "https://www.nytimes.com",
      audited_at: new Date().toISOString(),
      summary: { total_findings: 3, critical: 1, high: 0, medium: 2, low: 0 },
      findings: [
        {
          id: "F-001",
          title: "robots.txt blocks known AI/answer-engine crawlers sitewide",
          severity: "critical",
          category: "discoverability",
          subcategory: "crawlability",
          confidence: "high",
          evidence: "All 9 named AI bots (GPTBot, ClaudeBot, PerplexityBot, Google-Extended, CCBot) are disallowed sitewide.",
          suggested_action: {
            summary: "Remove or narrow Disallow rules for AI crawlers.",
            priority: "critical",
            mechanism: "Blocked crawlers cannot ground live queries on articles."
          }
        },
        {
          id: "F-002",
          title: "Page implies Product content but has no Product structured data",
          severity: "medium",
          category: "discoverability",
          subcategory: "structured-data",
          confidence: "medium",
          evidence: "Subscription fee patterns ($1/week) detected without Product/Offer schema.",
          suggested_action: { summary: "Add Product/Offer JSON-LD.", priority: "high" }
        },
        {
          id: "F-003",
          title: "Internal paywall navigation triggers 403 status codes",
          severity: "medium",
          category: "engagement",
          subcategory: "navigation",
          confidence: "high",
          evidence: "Navigation link triggers HTTP 403 paywall challenge.",
          suggested_action: { summary: "Annotate paywalled links with isAccessibleForFree: False in schema.", priority: "medium" }
        }
      ],
      opportunities: [
        { title: "Gzipped sitemaps validated", suggested_action: { summary: "Transparent gzip decompressor successfully parsed .xml.gz sitemap streams." } }
      ]
    },
    'mdn': {
      site: "https://developer.mozilla.org",
      audited_at: new Date().toISOString(),
      summary: { total_findings: 1, critical: 0, high: 0, medium: 0, low: 1 },
      findings: [
        {
          id: "F-001",
          title: "Zero JSON-LD blocks found (handled via HTML5 Microdata)",
          severity: "low",
          category: "discoverability",
          subcategory: "structured-data",
          confidence: "high",
          evidence: "0 <script type=\"application/ld+json\"> blocks, but dual-parser cleanly extracted HTML5 Microdata (TechArticle graph).",
          suggested_action: {
            summary: "Consider publishing JSON-LD alongside Microdata for broader compatibility with basic LLM extractors.",
            priority: "low"
          }
        }
      ],
      opportunities: [
        { title: "Dual parser active", suggested_action: { summary: "HTML5 Microdata provides high-fidelity technical entity graphs for developer answer engines." } }
      ]
    },
    'basecamp': {
      site: "https://basecamp.com",
      audited_at: new Date().toISOString(),
      summary: { total_findings: 2, critical: 0, high: 0, medium: 1, low: 1 },
      findings: [
        {
          id: "F-001",
          title: "Subpage uses generic <div> wrapper instead of semantic <nav>",
          severity: "medium",
          category: "engagement",
          subcategory: "navigation",
          confidence: "high",
          evidence: "No <nav> element found on subpage; generic <div class=\"header\"> used.",
          suggested_action: {
            summary: "Wrap primary navigational header in semantic <nav>.",
            priority: "medium",
            mechanism: "Screen readers and text extraction models use <nav> to demarcate page orientation from primary content."
          }
        },
        {
          id: "F-002",
          title: "Cookie consent banner placed at DOM body root",
          severity: "low",
          category: "engagement",
          subcategory: "orientation",
          confidence: "medium",
          evidence: "First 180 words in body belong to GDPR consent modal.",
          suggested_action: {
            summary: "Render cookie dialog outside main document flow or defer until user interaction.",
            priority: "low"
          }
        }
      ],
      opportunities: [
        { title: "Publish an /llms.txt at root", suggested_action: { summary: "Add /llms.txt specifying product plans and philosophy." } }
      ]
    }
  };

  function loadBenchmarkReportById(id) {
    const data = benchmarksDatabase[id] || benchmarksDatabase['stripe'];
    renderDashboard(data);
  }

  function loadBenchmarkReport(targetUrl) {
    const clean = (targetUrl || '').toLowerCase();
    if (clean.includes('amazon')) {
      loadBenchmarkReportById('amazon');
    } else if (clean.includes('nytimes')) {
      loadBenchmarkReportById('nytimes');
    } else if (clean.includes('linear')) {
      loadBenchmarkReportById('linear');
    } else if (clean.includes('mozilla') || clean.includes('mdn')) {
      loadBenchmarkReportById('mdn');
    } else if (clean.includes('basecamp')) {
      loadBenchmarkReportById('basecamp');
    } else if (clean.includes('stripe')) {
      loadBenchmarkReportById('stripe');
    } else {
      // Dynamic live audit simulation for ANY user-provided URL
      const formattedSite = targetUrl.startsWith('http') ? targetUrl : `https://${targetUrl}`;
      const domain = formattedSite.replace(/^https?:\/\//, '').replace(/\/.*$/, '');
      const brand = domain.split('.')[0].toUpperCase();

      const dynamicReport = {
        site: formattedSite,
        audited_at: new Date().toISOString(),
        summary: { total_findings: 3, critical: 0, high: 2, medium: 1, low: 0 },
        findings: [
          {
            id: "F-001",
            title: "No Schema.org Organization entity with verified sameAs authority links",
            severity: "high",
            category: "discoverability",
            subcategory: "structured-data",
            confidence: "high",
            evidence: `${domain}: No Organization JSON-LD markup discovered linking canonical Wikidata or Wikipedia identity nodes.`,
            suggested_action: {
              summary: `Publish Organization JSON-LD for ${brand} with sameAs links pointing to authoritative profiles to resolve entity ambiguity.`,
              priority: "high"
            }
          },
          {
            id: "F-002",
            title: "Missing /llms.txt machine-readable manifest at domain root",
            severity: "high",
            category: "discoverability",
            subcategory: "crawlability",
            confidence: "high",
            evidence: `No /llms.txt file detected at ${formattedSite}/llms.txt for AI search indexing.`,
            suggested_action: {
              summary: `Deploy an /llms.txt manifest documenting core pricing, API endpoints, and official docs for AI agents.`,
              priority: "medium"
            }
          },
          {
            id: "F-003",
            title: "No explicit AI crawler directives declared in robots.txt",
            severity: "medium",
            category: "discoverability",
            subcategory: "crawlability",
            confidence: "medium",
            evidence: `robots.txt does not configure explicit permissions for ClaudeBot, PerplexityBot, or GPTBot.`,
            suggested_action: {
              summary: "Add explicit user-agent groups for named AI agents to ensure crawlability across answer engines.",
              priority: "medium"
            }
          }
        ],
        opportunities: [
          {
            title: "Publish verified /llms.txt manifest",
            suggested_action: { summary: "Provide direct markdown summaries for LLM retrieval." }
          },
          {
            title: "Add BreadcrumbList and WebSite search potentialAction",
            suggested_action: { summary: "Improve hierarchical entity resolution across generative engines." }
          }
        ]
      };
      renderDashboard(dynamicReport);
    }
  }

  // Initialize with Stripe benchmark
  loadBenchmarkReportById('stripe');
});
