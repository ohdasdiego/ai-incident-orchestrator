const SAMPLES = {
  db: `CPU usage on prod-db-01 spiked to 98% at 03:42 UTC. Multiple slow query alerts firing in Datadog. Redis connection pool exhausted (0/100 available). API response times degraded from 120ms to 4200ms. Users reporting checkout timeouts and cart failures. PagerDuty alert ID: PD-8821.`,
  network: `Network packet loss detected on edge-router-02 at 14:17 UTC. Loss rate 23% on all traffic through AS65001. BGP session dropped to upstream peer 203.0.113.1. Downstream: payment gateway unreachable, CDN origin pulls failing. 3 customer-facing services returning 502s.`,
  security: `Multiple failed SSH login attempts detected on bastion-host-01 — 847 attempts in 10 minutes from IP 185.234.219.44. One attempt succeeded at 02:11 UTC using credentials for service account svc-deploy. Immediate activity: lateral movement attempt to prod-k8s-master. SIEM alert CRIT-0044.`,
  k8s: `OOMKilled events on 6 pods in the analytics namespace over the past 20 minutes. Pod analytics-worker-7d8f9b replicated 3x, each killed within 90 seconds. Node prod-worker-03 memory at 94%. HPA not triggering — suspected misconfiguration. Prometheus alert: KubePodCrashLooping.`
};

const STAGE_ORDER = ['triage', 'analyst', 'escalation', 'runbook', 'summary'];
let running = false;

document.querySelectorAll('.sample-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.getElementById('incidentInput').value = SAMPLES[btn.dataset.sample] || '';
  });
});

document.getElementById('runBtn').addEventListener('click', runPipeline);

function runPipeline() {
  if (running) return;
  const incident = document.getElementById('incidentInput').value.trim();
  if (!incident) {
    alert('Please describe the incident first.');
    return;
  }

  running = true;
  const btn = document.getElementById('runBtn');
  btn.disabled = true;
  document.getElementById('runBtnText').textContent = 'RUNNING...';

  resetUI();

  // Show pipeline, scroll to it
  const pipelineSection = document.getElementById('pipelineSection');
  pipelineSection.style.display = 'block';
  document.getElementById('reportSection').style.display = 'none';
  setTimeout(() => pipelineSection.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100);

  // Set all stages to waiting state visually
  STAGE_ORDER.forEach(s => setStageStatus(s, 'waiting'));

  fetch('/api/orchestrate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ incident })
  }).then(response => {
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    function read() {
      reader.read().then(({ done, value }) => {
        if (done) {
          finishRun(btn);
          return;
        }

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop(); // keep incomplete line

        lines.forEach(line => {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              handleEvent(data);
            } catch (e) { /* ignore parse errors */ }
          }
        });

        read();
      }).catch(err => {
        console.error('Read error:', err);
        finishRun(btn);
      });
    }

    read();
  }).catch(err => {
    console.error('Fetch error:', err);
    finishRun(btn);
  });
}

function finishRun(btn) {
  running = false;
  btn.disabled = false;
  document.getElementById('runBtnText').textContent = 'RUN PIPELINE';
}

function handleEvent(data) {
  switch (data.type) {
    case 'stage':
      setStageStatus(data.stage, data.status);
      break;
    case 'stage_result':
      setStageResult(data.stage, data.status, data.result);
      break;
    case 'complete':
      break;
    case 'error':
      console.error('Pipeline error:', data.message);
      break;
  }
}

function setStageStatus(stage, status) {
  const card  = document.getElementById(`stage-${stage}`);
  const badge = document.getElementById(`badge-${stage}`);
  const spinner = document.getElementById(`spinner-${stage}`);
  if (!card || !badge) return;

  card.className  = `stage-card ${status}`;
  badge.className = `stage-badge ${status}`;

  const labels = {
    running:  'RUNNING',
    waiting:  'WAITING',
    done:     'DONE',
    skipped:  'SKIPPED',
    escalated:'ESCALATED',
    auto:     'AUTO'
  };
  badge.textContent = labels[status] || status.toUpperCase();

  if (spinner) spinner.style.display = status === 'running' ? 'inline' : 'none';
}

function setStageResult(stage, status, result) {
  setStageStatus(stage, status);
  const output = document.getElementById(`output-${stage}`);
  if (!output) return;
  output.classList.add('visible');

  if (stage === 'triage')     renderTriage(output, result);
  else if (stage === 'analyst')    renderAnalyst(output, result);
  else if (stage === 'escalation') renderEscalation(output, result);
  else if (stage === 'runbook')    renderRunbook(output, result);
  else if (stage === 'summary')    renderSummary(result);
}

// ── Renderers ──

function row(key, val, valClass = '') {
  return `<div class="output-row"><span class="output-key">${key}</span><span class="output-val ${valClass}">${val}</span></div>`;
}

function severityClass(sev) { return `sev-${(sev||'').toLowerCase()}`; }

function renderTriage(el, r) {
  const sev = (r.severity || '').toLowerCase();
  el.innerHTML = `
    ${row('severity',        (r.severity||'—').toUpperCase(), severityClass(sev))}
    ${row('category',        r.category || '—')}
    ${row('affected_service',r.affected_service || '—')}
    ${row('keywords',        (r.keywords||[]).join(', '))}
    ${row('summary',         r.summary || '—')}
  `;
}

function renderAnalyst(el, r) {
  const causes = (r.root_causes||[]).map((c,i) => `${i+1}. ${c}`).join('<br>');
  el.innerHTML = `
    ${row('root_causes',         causes || '—')}
    ${row('blast_radius',        r.blast_radius || '—')}
    ${row('escalate_recommended',r.escalate_recommended ? 'YES' : 'NO', r.escalate_recommended ? 'sev-high' : 'sev-low')}
    ${row('confidence',          (r.confidence||'—').toUpperCase())}
    ${r.escalation_reason ? row('escalation_reason', r.escalation_reason) : ''}
  `;
}

function renderEscalation(el, r) {
  const isEsc = r.decision === 'escalate';
  const card  = document.getElementById('stage-escalation');
  const badge = document.getElementById('badge-escalation');
  if (isEsc) {
    card.className  = 'stage-card escalated';
    badge.className = 'stage-badge escalated';
    badge.textContent = 'ESCALATED';
  } else {
    badge.className = 'stage-badge auto';
    badge.textContent = 'AUTO';
  }
  el.innerHTML = `
    ${row('decision', isEsc ? '🔴 ESCALATE TO HUMAN' : '🟢 AUTO-REMEDIATE', isEsc ? 'decision-escalate' : 'decision-auto')}
    ${row('reason',   r.reason || '—')}
    ${row('severity', (r.severity||'—').toUpperCase(), severityClass(r.severity))}
  `;
}

function renderRunbook(el, r) {
  if (r.message) { el.innerHTML = row('status', r.message); return; }
  el.innerHTML = `
    ${row('query_sent',  r.query_sent || '—')}
    ${row('source',      r.source || '—')}
    ${row('api_status',  r.status || '—')}
    <div class="output-row" style="flex-direction:column;gap:4px">
      <span class="output-key">runbook_response</span>
      <span class="output-val" style="white-space:pre-wrap">${r.runbook_response || '—'}</span>
    </div>
  `;
}

function renderSummary(r) {
  const reportSection = document.getElementById('reportSection');
  const reportCard    = document.getElementById('reportCard');
  reportSection.style.display = 'block';

  const statusClass = (r.status||'').replace(/-/g, '-');
  const actions = (r.actions_taken||[]).map(a => `<li>${a}</li>`).join('');
  const steps   = (r.next_steps||[]).map(s => `<li>${s}</li>`).join('');
  const runbookSection = r.runbook_steps
    ? `<div><div class="report-section-label">Runbook Steps</div><div class="runbook-box">${r.runbook_steps}</div></div>`
    : '';

  reportCard.innerHTML = `
    <div class="report-title">${r.title || 'Incident Report'}</div>
    <div class="report-meta">
      <span class="report-tag sev">SEV: ${(r.severity||'—').toUpperCase()}</span>
      <span class="report-tag ${statusClass}">${(r.status||'—').replace(/-/g,' ').toUpperCase()}</span>
    </div>
    <div class="report-divider"></div>
    <div>
      <div class="report-section-label">Executive Summary</div>
      <div class="report-text">${r.executive_summary || '—'}</div>
    </div>
    <div>
      <div class="report-section-label">Root Cause</div>
      <div class="report-text">${r.root_cause || '—'}</div>
    </div>
    ${runbookSection}
    <div>
      <div class="report-section-label">Actions Taken</div>
      <ul class="report-list">${actions || '<li>None recorded</li>'}</ul>
    </div>
    <div>
      <div class="report-section-label">Next Steps</div>
      <ul class="report-list">${steps || '<li>None</li>'}</ul>
    </div>
  `;

  setTimeout(() => reportSection.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100);
}

function resetUI() {
  STAGE_ORDER.forEach(stage => {
    const card    = document.getElementById(`stage-${stage}`);
    const badge   = document.getElementById(`badge-${stage}`);
    const output  = document.getElementById(`output-${stage}`);
    const spinner = document.getElementById(`spinner-${stage}`);
    if (card)    card.className = 'stage-card';
    if (badge)   { badge.className = 'stage-badge'; badge.textContent = 'WAITING'; }
    if (output)  { output.classList.remove('visible'); output.innerHTML = ''; }
    if (spinner) spinner.style.display = 'none';
  });
  document.getElementById('reportCard').innerHTML = '';
}
