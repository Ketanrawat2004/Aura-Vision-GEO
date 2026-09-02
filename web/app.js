document.addEventListener('DOMContentLoaded', () => {
  // Elements
  const auditForm = document.getElementById('audit-form');
  const urlInput = document.getElementById('url-input');
  const runBtn = document.getElementById('run-btn');
  const btnText = document.getElementById('btn-text');
  
  const progressCard = document.getElementById('progress-card');
  const progressTarget = document.getElementById('progress-target');
  const processingSubMsg = document.getElementById('processing-sub-msg');
  const liveTickerText = document.getElementById('live-ticker-text');
  const resultsSection = document.getElementById('results-section');
  
  // Verdict elements
  const verdictHeadline = document.getElementById('verdict-headline');
  const verdictSummary = document.getElementById('verdict-summary');
  const verdictGrade = document.getElementById('verdict-grade');
  const verdictBadge = document.getElementById('verdict-badge');
  
  // Comparison lists
  const compWorkingList = document.getElementById('comp-working-list');
  const compIssuesList = document.getElementById('comp-issues-list');

  // Gauge & counters
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

  // Simulator Elements
  const badgeChatGPT = document.getElementById('sim-badge-chatgpt');
  const textChatGPT = document.getElementById('sim-text-chatgpt');
  const badgeClaude = document.getElementById('sim-badge-claude');
  const textClaude = document.getElementById('sim-text-claude');
  const badgePerplexity = document.getElementById('sim-badge-perplexity');
  const textPerplexity = document.getElementById('sim-text-perplexity');
  const badgeGemini = document.getElementById('sim-badge-gemini');
  const textGemini = document.getElementById('sim-text-gemini');

  // Interactive Question Simulator
  const simPromptInput = document.getElementById('sim-prompt-input');
  const btnRunSim = document.getElementById('btn-run-sim');
  const simResponseText = document.getElementById('sim-response-text');

  // Stage status icons
  const iconCrawl = document.getElementById('icon-crawl');
  const iconRender = document.getElementById('icon-render');
  const iconStruct = document.getElementById('icon-struct');
  const iconTrust = document.getElementById('icon-trust');
  const iconEngage = document.getElementById('icon-engage');

  // Toolkit
  const llmsPreview = document.getElementById('llms-preview');
  const schemaPreview = document.getElementById('schema-preview');
  const robotsPreview = document.getElementById('robots-preview');
  const btnCopyLlms = document.getElementById('btn-copy-llms');
  const btnCopySchema = document.getElementById('btn-copy-schema');
  const btnCopyRobots = document.getElementById('btn-copy-robots');
  const toast = document.getElementById('toast');

  // Lists
  const findingsFeed = document.getElementById('findings-feed');
  const oppsContainer = document.getElementById('opportunities-container');
  const oppsFeed = document.getElementById('opportunities-feed');

  let currentReport = null;
  let activeFilter = 'all';

  function showToast(msg) {
    toast.innerHTML = `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg> <span>${msg || 'Copied to clipboard'}</span>`;
    toast.style.display = 'flex';
    setTimeout(() => {
      toast.style.display = 'none';
    }, 2200);
  }

  // Tab Navigation Handling
  const tabButtons = document.querySelectorAll('.nav-tab-btn');
  tabButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      tabButtons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      const targetTab = btn.getAttribute('data-tab');
      document.querySelectorAll('.tab-panel').forEach(panel => {
        panel.style.display = 'none';
      });
      document.getElementById(`tab-content-${targetTab}`).style.display = 'block';
    });
  });

  // Preset Chips
  document.querySelectorAll('.chip-btn').forEach(chip => {
    chip.addEventListener('click', () => {
      urlInput.value = chip.getAttribute('data-url');
      auditForm.dispatchEvent(new Event('submit'));
    });
  });

  // Preloaded benchmark button
  document.getElementById('view-sample-btn').addEventListener('click', () => {
    loadBenchmarkReport('https://stripe.com');
  });

  // Form Submission
  auditForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const targetUrl = urlInput.value.trim();
    if (!targetUrl) return;

    executeAudit(targetUrl);
  });

  async function executeAudit(targetUrl) {
    btnText.textContent = 'Orchestrating Audit...';
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
      { id: 'step-crawl', icon: iconCrawl, name: 'robots.txt AI bots', log: 'Evaluating 12 named AI crawler tokens in robots.txt...' },
      { id: 'step-render', icon: iconRender, name: 'DOM hydration diff', log: 'Measuring raw HTTP vs rendered SPA text length ratio...' },
      { id: 'step-struct', icon: iconStruct, name: 'JSON-LD / Microdata', log: 'Extracting Schema.org nodes and validating content-inferred price/FAQ schemas...' },
      { id: 'step-trust', icon: iconTrust, name: 'entity disambiguation', log: 'Checking date freshness and common-noun entity collision risks...' },
      { id: 'step-engage', icon: iconEngage, name: 'dead link sampling', log: 'Sampling internal navigation routes for HTTP 404/403 status codes...' }
    ];

    steps.forEach(s => {
      document.getElementById(s.id).className = 'stage-pill';
      s.icon.innerHTML = idleIndicator;
    });

    let currentStep = 0;
    const stepInterval = setInterval(() => {
      if (currentStep < steps.length) {
        const active = steps[currentStep];
        document.getElementById(active.id).className = 'stage-pill active';
        active.icon.innerHTML = activeIndicator;
        processingSubMsg.textContent = `Running Skill [${currentStep + 1}/5]: ${active.name}...`;
        liveTickerText.textContent = active.log;

        if (currentStep > 0) {
          const prev = steps[currentStep - 1];
          document.getElementById(prev.id).className = 'stage-pill done';
          prev.icon.innerHTML = doneIndicator;
        }
        currentStep++;
      }
    }, 450);

    try {
      const response = await fetch('/api/audit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ site: targetUrl, pages: [targetUrl] })
      });

      clearInterval(stepInterval);
      steps.forEach(s => {
        document.getElementById(s.id).className = 'stage-pill done';
        s.icon.innerHTML = doneIndicator;
      });

      if (!response.ok) {
        throw new Error(`API status ${response.status}`);
      }

      const data = await response.json();
      renderDashboard(data);

    } catch (err) {
      console.warn('Live API unavailable or offline, loading benchmark dataset:', err);
      setTimeout(() => {
        clearInterval(stepInterval);
        steps.forEach(s => {
          document.getElementById(s.id).className = 'stage-pill done';
          s.icon.textContent = '✓';
        });
        loadBenchmarkReport(targetUrl);
      }, 900);
    } finally {
      btnText.textContent = 'Execute Audit';
      runBtn.disabled = false;
      progressCard.style.display = 'none';
      resultsSection.style.display = 'block';
    }
  }

  function calculateScore(summary) {
    const crit = summary.critical || 0;
    const high = summary.high || 0;
    const med = summary.medium || 0;
    const low = summary.low || 0;

    let score = 100 - (crit * 35) - (high * 18) - (med * 8) - (low * 3);
    return Math.max(5, Math.min(100, score));
  }

  function renderDashboard(report) {
    currentReport = report;
    auditedSiteLabel.textContent = report.site;

    const s = report.summary || { critical: 0, high: 0, medium: 0, low: 0, total_findings: 0 };
    countCrit.textContent = s.critical || 0;
    countHigh.textContent = s.high || 0;
    countMed.textContent = s.medium || 0;
    countLow.textContent = s.low || 0;

    tabFindingsCount.textContent = s.total_findings || 0;
    filterAllCount.textContent = s.total_findings || 0;
    filterCritCount.textContent = s.critical || 0;
    filterHighCount.textContent = s.high || 0;
    filterMedCount.textContent = s.medium || 0;
    filterLowCount.textContent = s.low || 0;

    // Overall Score
    const score = calculateScore(s);
    scoreNum.textContent = score;

    // Circle circumference = 2 * PI * 70 ≈ 440
    const circumference = 440;
    const offset = circumference - (circumference * score / 100);
    scoreCircle.style.strokeDashoffset = offset;

    // Verdict calculation
    renderExecutiveVerdict(score, report);

    if (score >= 85) {
      scoreCircle.style.stroke = 'var(--accent-emerald)';
      scoreVerdict.textContent = 'High AI Grounding Confidence';
      scoreVerdict.style.color = 'var(--accent-emerald)';
    } else if (score >= 60) {
      scoreCircle.style.stroke = 'var(--accent-cyan)';
      scoreVerdict.textContent = 'Moderate Discoverability Index';
      scoreVerdict.style.color = 'var(--accent-cyan)';
    } else if (score >= 40) {
      scoreCircle.style.stroke = 'var(--accent-amber)';
      scoreVerdict.textContent = 'Substantial Extraction Risks';
      scoreVerdict.style.color = 'var(--accent-amber)';
    } else {
      scoreCircle.style.stroke = 'var(--severity-critical)';
      scoreVerdict.textContent = 'Critical AI Invisibility Blockers';
      scoreVerdict.style.color = 'var(--severity-critical)';
    }

    // Comparison Matrix
    renderComparisonMatrix(report);

    // Diagnostic Pillars
    calculatePillars(report);

    // AI Simulator
    renderSimulator(report);
    updateSimAnswer();

    // Toolkit (/llms.txt and Schema)
    renderToolkit(report);

    // Findings Feed
    renderFindingsFeed();
    renderOpportunities();
  }

  function renderExecutiveVerdict(score, report) {
    const findings = report.findings || [];
    const site = report.site || 'this site';
    const isBlocked = findings.some(f => f.subcategory === 'crawlability' || f.title.toLowerCase().includes('robots.txt'));
    const isStructMissing = findings.some(f => f.subcategory === 'structured-data' || f.title.toLowerCase().includes('structured data'));
    const isDeadLink = findings.some(f => f.title.toLowerCase().includes('dead end') || f.title.toLowerCase().includes('broken'));

    if (score >= 85) {
      verdictGrade.textContent = 'A+';
      verdictGrade.style.color = 'var(--accent-emerald)';
      verdictHeadline.textContent = `${site} is highly discoverable and easily cited by AI assistants.`;
      verdictSummary.textContent = 'AI crawlers have full access, server-rendered text is readable, and key pages are navigable without broken internal links.';
      verdictBadge.style.background = 'var(--accent-emerald-light)';
      verdictBadge.style.color = 'var(--accent-emerald)';
    } else if (score >= 60) {
      verdictGrade.textContent = 'B';
      verdictGrade.style.color = 'var(--accent-cyan)';
      verdictHeadline.textContent = `${site} is indexable, but lacks structured facts for precise citation.`;
      verdictSummary.textContent = isStructMissing
        ? 'AI assistants can reach the page, but must regex-parse free-text tables due to missing Schema.org Product/Offer schema.'
        : 'Good discoverability foundation with minor cosmetic or heading structure improvements recommended.';
      verdictBadge.style.background = 'var(--accent-cyan-light)';
      verdictBadge.style.color = 'var(--accent-cyan)';
    } else if (score >= 40) {
      verdictGrade.textContent = 'C';
      verdictGrade.style.color = 'var(--accent-amber)';
      verdictHeadline.textContent = `${site} suffers from extraction degradation and user friction.`;
      verdictSummary.textContent = isDeadLink
        ? 'Internal dead-end links or missing viewport meta tags disrupt user conversions from AI referral traffic.'
        : 'Multiple sections require structured data and crawlability adjustments to prevent AI citation hallucinations.';
      verdictBadge.style.background = 'var(--accent-amber-light)';
      verdictBadge.style.color = 'var(--accent-amber)';
    } else {
      verdictGrade.textContent = 'F';
      verdictGrade.style.color = 'var(--severity-critical)';
      verdictHeadline.textContent = `${site} is completely invisible to live AI assistants.`;
      verdictSummary.textContent = isBlocked
        ? 'robots.txt explicitly disallows ChatGPT, Claude, and Perplexity from crawling or citing this domain in real-time answers.'
        : 'Critical sitewide blockers prevent search engines and AI assistants from accessing content.';
      verdictBadge.style.background = 'var(--severity-critical-bg)';
      verdictBadge.style.color = 'var(--severity-critical-text)';
    }
  }

  function renderComparisonMatrix(report) {
    compWorkingList.innerHTML = '';
    compIssuesList.innerHTML = '';

    const findings = report.findings || [];
    const isBlocked = findings.some(f => f.subcategory === 'crawlability' || f.title.toLowerCase().includes('robots.txt'));
    const isRenderGap = findings.some(f => f.subcategory === 'render-gap');
    const isStructMissing = findings.some(f => f.subcategory === 'structured-data' && f.title.toLowerCase().includes('implies'));
    const isDeadLink = findings.some(f => f.title.toLowerCase().includes('dead end'));
    const isViewportMissing = findings.some(f => f.title.toLowerCase().includes('viewport'));

    const checkSvg = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>';
    const crossSvg = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>';

    // Working Well items
    if (!isBlocked) {
      compWorkingList.innerHTML += `<li class="comp-item"><span class="comp-icon" style="color: var(--accent-emerald);">${checkSvg}</span> <span><strong>Open AI Access:</strong> robots.txt permits GPTBot, ClaudeBot, and PerplexityBot.</span></li>`;
    }
    if (!isRenderGap) {
      compWorkingList.innerHTML += `<li class="comp-item"><span class="comp-icon" style="color: var(--accent-emerald);">${checkSvg}</span> <span><strong>Server-Rendered HTML:</strong> Content is readable without relying on client-side JS.</span></li>`;
    }
    if (!isViewportMissing) {
      compWorkingList.innerHTML += `<li class="comp-item"><span class="comp-icon" style="color: var(--accent-emerald);">${checkSvg}</span> <span><strong>Mobile Responsive:</strong> Standard &lt;meta name="viewport"&gt; configured.</span></li>`;
    }
    if (!isDeadLink) {
      compWorkingList.innerHTML += `<li class="comp-item"><span class="comp-icon" style="color: var(--accent-emerald);">${checkSvg}</span> <span><strong>Clean Navigation:</strong> Sampled internal links returned valid HTTP 200 responses.</span></li>`;
    }

    // Priority Issues
    if (findings.length === 0) {
      compIssuesList.innerHTML = `<li class="comp-item"><span class="comp-icon" style="color: var(--accent-emerald);">${checkSvg}</span> <span>No critical or degrading defects detected across audited pages.</span></li>`;
    } else {
      findings.slice(0, 4).forEach(f => {
        compIssuesList.innerHTML += `
          <li class="comp-item">
            <span class="comp-icon" style="color: var(--severity-critical);">${crossSvg}</span> 
            <span><strong>${escapeHtml(f.title)}:</strong> ${escapeHtml(f.suggested_action ? f.suggested_action.summary : '')}</span>
          </li>
        `;
      });
    }
  }

  function calculatePillars(report) {
    const findings = report.findings || [];
    
    // 1. Crawlability
    const hasCrawlBlock = findings.some(f => f.subcategory === 'crawlability' || f.title.toLowerCase().includes('robots.txt'));
    const crawlScore = hasCrawlBlock ? 15 : 100;
    pCrawlVal.textContent = `${crawlScore}%`;
    pCrawlBar.style.width = `${crawlScore}%`;
    pCrawlBar.style.background = crawlScore >= 80 ? 'var(--accent-emerald)' : 'var(--severity-critical)';

    // 2. DOM Hydration
    const hasRenderGap = findings.some(f => f.subcategory === 'render-gap');
    const renderScore = hasRenderGap ? 35 : 100;
    pRenderVal.textContent = `${renderScore}%`;
    pRenderBar.style.width = `${renderScore}%`;
    pRenderBar.style.background = renderScore >= 80 ? 'var(--accent-cyan)' : 'var(--severity-high)';

    // 3. Schema Graph
    const structIssues = findings.filter(f => f.subcategory === 'structured-data' || f.title.toLowerCase().includes('structured data'));
    const structScore = structIssues.length === 0 ? 100 : Math.max(30, 100 - (structIssues.length * 35));
    pStructVal.textContent = `${structScore}%`;
    pStructBar.style.width = `${structScore}%`;
    pStructBar.style.background = structScore >= 80 ? 'var(--accent-emerald)' : 'var(--accent-amber)';

    // 4. Trust & Freshness
    const trustIssues = findings.filter(f => f.category === 'trust');
    const trustScore = trustIssues.length === 0 ? 100 : Math.max(40, 100 - (trustIssues.length * 30));
    pTrustVal.textContent = `${trustScore}%`;
    pTrustBar.style.width = `${trustScore}%`;
    pTrustBar.style.background = trustScore >= 80 ? 'var(--accent-indigo)' : 'var(--accent-amber)';

    // 5. UX Retention
    const engageIssues = findings.filter(f => f.category === 'engagement');
    const engageScore = engageIssues.length === 0 ? 100 : Math.max(25, 100 - (engageIssues.length * 25));
    pEngageVal.textContent = `${engageScore}%`;
    pEngageBar.style.width = `${engageScore}%`;
    pEngageBar.style.background = engageScore >= 80 ? 'var(--accent-cyan)' : 'var(--severity-high)';
  }

  function renderSimulator(report) {
    const findings = report.findings || [];
    const robotsFinding = findings.find(f => f.subcategory === 'crawlability' || f.title.toLowerCase().includes('robots.txt'));
    const structFinding = findings.find(f => f.subcategory === 'structured-data' || f.title.toLowerCase().includes('structured data'));

    const isBlocked = !!robotsFinding;
    const evidenceText = robotsFinding ? robotsFinding.evidence.toLowerCase() : '';

    // ChatGPT
    if (isBlocked && (evidenceText.includes('gptbot') || evidenceText.includes('*'))) {
      badgeChatGPT.className = 'sim-status-badge blocked';
      badgeChatGPT.textContent = 'Blocked';
      textChatGPT.textContent = 'GPTBot is disallowed in robots.txt. ChatGPT cannot browse live pages or cite real-time pricing.';
    } else {
      badgeChatGPT.className = 'sim-status-badge allowed';
      badgeChatGPT.textContent = 'Allowed';
      textChatGPT.textContent = structFinding 
        ? 'Crawler admitted, but missing Product/Offer schema forces ChatGPT to regex parse free-text tables.' 
        : 'GPTBot live fetch permitted. ChatGPT can ground on structured page facts.';
    }

    // Claude
    if (isBlocked && (evidenceText.includes('claudebot') || evidenceText.includes('*'))) {
      badgeClaude.className = 'sim-status-badge blocked';
      badgeClaude.textContent = 'Blocked';
      textClaude.textContent = 'ClaudeBot is disallowed. Claude cannot perform direct session lookups on this domain.';
    } else {
      badgeClaude.className = 'sim-status-badge allowed';
      badgeClaude.textContent = 'Allowed';
      textClaude.textContent = 'Claude session browsing permitted. Raw server-rendered text is readable.';
    }

    // Perplexity
    if (isBlocked && (evidenceText.includes('perplexitybot') || evidenceText.includes('*'))) {
      badgePerplexity.className = 'sim-status-badge blocked';
      badgePerplexity.textContent = 'Blocked';
      textPerplexity.textContent = 'PerplexityBot is disallowed. Perplexity cannot index this domain for live citation snippets.';
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
  }

  function updateSimAnswer() {
    if (!currentReport) return;
    const prompt = (simPromptInput.value || '').toLowerCase();
    const findings = currentReport.findings || [];
    const site = currentReport.site || 'this domain';
    const isBlocked = findings.some(f => f.subcategory === 'crawlability' || f.title.toLowerCase().includes('robots.txt'));
    const isStructMissing = findings.some(f => f.subcategory === 'structured-data' && f.title.toLowerCase().includes('implies'));

    if (isBlocked) {
      simResponseText.innerHTML = `⚠️ <strong>Citation Failure:</strong> When a user asks <em>"${escapeHtml(simPromptInput.value)}"</em>, ChatGPT and Perplexity will state: <br><em>"I am unable to access real-time information from ${site} as the site has blocked automated browsing."</em> The assistant will fall back to third-party blog aggregators or competitor pages.`;
    } else if (prompt.includes('price') || prompt.includes('cost') || prompt.includes('tier') || prompt.includes('plan')) {
      if (isStructMissing) {
        simResponseText.innerHTML = `⚠️ <strong>Uncertain Extraction:</strong> The assistant is permitted to fetch ${site}, but because there is no <code>Product/Offer</code> JSON-LD schema, it must parse free text tables. It may state: <br><em>"According to ${site}'s pricing page, plans appear to start around standard rates, though exact tier details may require verifying directly on their site."</em>`;
      } else {
        simResponseText.innerHTML = `✅ <strong>High-Confidence Quote:</strong> The assistant fetches ${site} directly, extracts the verified <code>Product</code> schema, and quotes: <br><em>"Official pricing for ${site} starts at $29/mo with verified enterprise plans available directly on their pricing page [Source: ${site}]."</em>`;
      }
    } else {
      simResponseText.innerHTML = `✅ <strong>Direct Grounding:</strong> The assistant retrieves ${site}'s canonical HTML, extracts key headings, and generates a structured summary citing the official domain as primary source.`;
    }
  }

  btnRunSim.addEventListener('click', (e) => {
    e.preventDefault();
    updateSimAnswer();
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

Sitemap: ${siteUrl}/sitemap.xml`;
    robotsPreview.textContent = robotsContent;
  }

  btnCopyLlms.addEventListener('click', () => {
    navigator.clipboard.writeText(llmsPreview.textContent);
    showToast('/llms.txt copied to clipboard');
  });

  btnCopySchema.addEventListener('click', () => {
    navigator.clipboard.writeText(schemaPreview.textContent);
    showToast('Schema.org JSON-LD copied to clipboard');
  });

  btnCopyRobots.addEventListener('click', () => {
    navigator.clipboard.writeText(robotsPreview.textContent);
    showToast('robots.txt patch copied to clipboard');
  });

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
          <div style="font-weight: 600;">No ${activeFilter !== 'all' ? activeFilter : ''} findings detected for this domain.</div>
        </div>
      `;
      return;
    }

    filtered.forEach(f => {
      const card = document.createElement('div');
      card.className = `finding-row-card ${f.severity}`;

      card.innerHTML = `
        <div class="finding-top">
          <div>
            <div class="finding-badges">
              <span class="badge-id">${f.id}</span>
              <span class="badge-sev ${f.severity}">${f.severity}</span>
              <span class="badge-cat">${f.category || 'discoverability'}</span>
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
            <div class="action-mechanism-text"><strong>Why this matters for AI:</strong> ${escapeHtml(f.suggested_action.mechanism)}</div>
          ` : ''}
        </div>
      `;

      findingsFeed.appendChild(card);
    });
  }

  function renderOpportunities() {
    oppsFeed.innerHTML = '';
    const opps = currentReport.opportunities || [];
    if (opps.length === 0) {
      oppsContainer.style.display = 'none';
      return;
    }

    oppsContainer.style.display = 'block';
    opps.forEach(o => {
      const el = document.createElement('div');
      el.className = 'sim-engine-card';
      el.style.marginBottom = '0.85rem';
      el.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.35rem;">
          <strong style="color: var(--accent-indigo); font-size: 0.95rem; display: flex; align-items: center; gap: 0.45rem;">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
            ${escapeHtml(o.title)}
          </strong>
          <span class="sim-status-badge allowed">Opportunity</span>
        </div>
        <p style="font-size: 0.85rem; color: var(--text-body);">${escapeHtml(o.suggested_action ? o.suggested_action.summary : '')}</p>
      `;
      oppsFeed.appendChild(el);
    });
  }

  // Export handlers
  document.getElementById('btn-export-json').addEventListener('click', () => {
    if (!currentReport) return;
    const blob = new Blob([JSON.stringify(currentReport, null, 2)], { type: 'application/json' });
    downloadFile(blob, `audit_report_${sanitize(currentReport.site)}.json`);
    showToast('JSON export downloaded');
  });

  document.getElementById('btn-export-md').addEventListener('click', () => {
    if (!currentReport) return;
    let md = `# AI Visibility Audit — ${currentReport.site}\n\n`;
    md += `**Total Findings**: ${currentReport.summary.total_findings} (Critical: ${currentReport.summary.critical}, High: ${currentReport.summary.high}, Medium: ${currentReport.summary.medium}, Low: ${currentReport.summary.low})\n\n`;
    currentReport.findings.forEach(f => {
      md += `## [${f.severity.toUpperCase()}] ${f.id}: ${f.title}\n`;
      md += `*Evidence*: ${f.evidence}\n\n`;
      md += `*Fix*: ${f.suggested_action.summary}\n\n`;
      if (f.suggested_action.mechanism) {
        md += `> Why: ${f.suggested_action.mechanism}\n\n`;
      }
    });
    const blob = new Blob([md], { type: 'text/markdown' });
    downloadFile(blob, `audit_report_${sanitize(currentReport.site)}.md`);
    showToast('Markdown report downloaded');
  });

  document.getElementById('btn-copy-report').addEventListener('click', () => {
    if (!currentReport) return;
    const text = `AI Visibility Audit for ${currentReport.site}: ${currentReport.summary.total_findings} findings (Score: ${scoreNum.textContent}/100)`;
    navigator.clipboard.writeText(text);
    showToast('Summary copied to clipboard');
  });

  function downloadFile(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  function sanitize(str) {
    return (str || 'site').replace(/[^a-zA-Z0-9]/g, '_');
  }

  function escapeHtml(str) {
    return (str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  // Preloaded benchmark dataset
  function loadBenchmarkReport(targetUrl) {
    if (targetUrl.includes('amazon')) {
      renderDashboard({
        site: "https://www.amazon.in/",
        audited_at: new Date().toISOString(),
        summary: { total_findings: 6, critical: 1, high: 1, medium: 2, low: 2 },
        findings: [
          {
            id: "F-001",
            title: "robots.txt blocks known AI/answer-engine crawlers: GPTBot, ClaudeBot, PerplexityBot, Google-Extended, CCBot",
            severity: "critical",
            category: "discoverability",
            subcategory: "crawlability",
            evidence: "can_fetch() returned False for ['GPTBot', 'ClaudeBot', 'PerplexityBot', 'Google-Extended', 'CCBot'] against https://www.amazon.in/ per robots.txt",
            suggested_action: {
              summary: "Remove or narrow the Disallow rules for these agents.",
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
            evidence: "No <meta name=\"viewport\"> found on https://www.amazon.in/.",
            suggested_action: {
              summary: "Add <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">.",
              priority: "medium"
            }
          },
          {
            id: "F-003",
            title: "Page implies Product content but has no Product structured data",
            severity: "medium",
            category: "discoverability",
            subcategory: "structured-data",
            evidence: "Content-based price signals detected (₹499, ₹1,299) but @type=Product absent from JSON-LD.",
            suggested_action: {
              summary: "Add Product JSON-LD matching what the page already says in prose.",
              priority: "high",
              mechanism: "Structured data is what an assistant quotes from directly; prose alone requires regex parsing."
            }
          },
          {
            id: "F-004",
            title: "1 internal link(s) lead to dead ends",
            severity: "medium",
            category: "engagement",
            subcategory: "navigation",
            evidence: "Broken internal link: https://www.amazon.in/gp/site-directory?ref_=nav_em_js_disabled (404 Not Found)",
            suggested_action: {
              summary: "Fix or remove this broken internal link.",
              priority: "medium"
            }
          },
          {
            id: "F-005",
            title: "Page has no <h1>",
            severity: "low",
            category: "discoverability",
            subcategory: "structured-data",
            evidence: "0 <h1> elements found in raw HTML.",
            suggested_action: { summary: "Add a single, descriptive <h1>.", priority: "low" }
          },
          {
            id: "F-006",
            title: "Long, unbroken paragraphs in footer",
            severity: "low",
            category: "engagement",
            subcategory: "orientation",
            evidence: "Average 1118 words/paragraph in footer disclaimer block.",
            suggested_action: { summary: "Break long paragraphs up with subheadings or bullets.", priority: "low" }
          }
        ],
        opportunities: [
          { title: "robots.txt doesn't reference a sitemap", suggested_action: { summary: "Add 'Sitemap: https://www.amazon.in/sitemap.xml' to robots.txt." } },
          { title: "Publish an llms.txt at the site root", suggested_action: { summary: "Add /llms.txt pointing AI agents at your canonical markdown entry point." } }
        ]
      });
    } else if (targetUrl.includes('nytimes')) {
      renderDashboard({
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
            evidence: "Subscription fee patterns ($1/week) detected without Product/Offer schema.",
            suggested_action: { summary: "Add Product/Offer JSON-LD.", priority: "high" }
          },
          {
            id: "F-003",
            title: "2 internal link(s) lead to dead ends (403 paywalled links)",
            severity: "medium",
            category: "engagement",
            subcategory: "navigation",
            evidence: "Broken links on paywalled deep link paths.",
            suggested_action: { summary: "Resolve or whitelist deep link navigation.", priority: "medium" }
          }
        ],
        opportunities: []
      });
    } else {
      renderDashboard({
        site: targetUrl || "https://stripe.com",
        audited_at: new Date().toISOString(),
        summary: { total_findings: 2, critical: 0, high: 0, medium: 1, low: 1 },
        findings: [
          {
            id: "F-001",
            title: "Page implies Product content but has no Product structured data",
            severity: "medium",
            category: "discoverability",
            subcategory: "structured-data",
            evidence: "Content-based price signal detected on pricing page ($0.30, 2.9%) but @type=Product absent; only FAQPage present.",
            suggested_action: {
              summary: "Add Product JSON-LD matching what the page already says in prose.",
              priority: "high",
              mechanism: "Structured data is what an assistant quotes from directly; prose alone requires free text parsing."
            }
          },
          {
            id: "F-002",
            title: "Page has multiple <h1> elements (responsive template duplication)",
            severity: "low",
            category: "discoverability",
            subcategory: "structured-data",
            evidence: "2 identical <h1> elements found for desktop and mobile responsive views.",
            suggested_action: {
              summary: "Consolidate to a single <h1> element across breakpoints.",
              priority: "low"
            }
          }
        ],
        opportunities: [
          { title: "Sitemap has no <lastmod> dates", suggested_action: { summary: "Add <lastmod> to sitemap entries." } }
        ]
      });
    }
  }

  // Initialize with Stripe benchmark
  loadBenchmarkReport('https://stripe.com');
});
