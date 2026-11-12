'use strict';
(() => {
  const dialog = $('health-dialog');
  let submitting = false, jobId = null, running = false;
  const bytes = value => {
    if (value === null) return 'Unknown';
    const index = value > 0 ? Math.min(4, Math.floor(Math.log(value) / Math.log(1024))) : 0;
    return new Intl.NumberFormat('en', {maximumFractionDigits: 2}).format(value / 1024 ** index) + ' ' + ['B', 'KiB', 'MiB', 'GiB', 'TiB'][index];
  };
  const words = value => String(value).replaceAll('_', ' ').toLowerCase();
  function updateDisabled() {
    $('health-run').disabled = submitting || running || !!busyJob;
    $('health-stop').hidden = !running;
  }
  function render(report) {
    const area = $('health-result'); area.replaceChildren(); area.hidden = false;
    const totals = el('dl', 'health-totals');
    for (const [title, value] of [
      ['Entire workspace', report.usage.workspace_bytes], ['Private state', report.usage.private_state_bytes],
      ['Recovery copies (within private state)', report.usage.recovery_bytes], ['Float storage', report.usage.float_bytes],
      ['Available on volume', report.capacity.free_bytes], ['Backup envelope', report.estimate.backup_envelope_bytes],
    ]) totals.append(el('dt', '', title), el('dd', '', bytes(value)));
    area.append(totals, el('p', 'field-help', report.estimate.basis));
    area.append(el('h3', '', 'Recovery history'), el('p', '', report.history.directories + ' history folders observed.'));
    const statuses = el('ul');
    for (const [status, count] of Object.entries(report.history.statuses)) statuses.append(el('li', '', count + ' ' + words(status)));
    if (statuses.childElementCount) area.append(statuses);
    area.append(el('p', 'field-help', report.history.integrity), el('p', '', 'Operation: ' + words(report.operation.status) + '. Ownership was not tested.'));
    area.append(el('h3', '', 'Filesystem support'), el('p', '', (report.filesystem.filesystem || 'Unknown filesystem') + ' · Hard links: ' + words(report.filesystem.hard_links)),
      el('p', 'field-help', report.filesystem.note));
    const guidance = el('ul');
    for (const advice of report.guidance) guidance.append(el('li', '', advice));
    area.append(el('h3', '', 'Coverage and next steps'), el('p', '', report.coverage.entries + ' entries inspected.'), el('p', 'field-help', report.coverage.basis));
    for (const [code, count] of Object.entries(report.coverage.issues)) area.append(el('p', 'amber', words(code) + ': ' + count));
    area.append(guidance);
    const details = el('details'), raw = el('pre'); raw.textContent = JSON.stringify(report, null, 2);
    details.append(el('summary', '', 'Technical report'), raw); area.append(details);
  }
  $('health-open').onclick = () => { if (!dialog.open) dialog.showModal(); };
  $('health-close').onclick = () => dialog.close();
  dialog.addEventListener('close', () => $('health-open').focus());
  $('health-run').onclick = async () => {
    if (submitting || running || busyJob) return;
    submitting = true; updateDisabled();
    $('health-result').hidden = true;
    $('health-status').textContent = 'Starting read-only storage inspection…';
    try {
      const result = await api('health', {});
      jobId = result.job_id; busyJob = jobId; running = true; $('health-stop').disabled = false;
      $('health-status').textContent = 'Inspecting storage. You can close this panel and return while it runs.';
    } catch (e) { $('health-status').textContent = recovery.text(e.message, 'health'); }
    finally { submitting = false; updateDisabled(); refresh(); }
  };
  $('health-stop').onclick = async () => {
    if (!running || !jobId) return;
    $('health-stop').disabled = true;
    try { await api('jobs/' + jobId + '/cancel', {}); $('health-status').textContent = 'Stop requested. Waiting for the current filesystem read.'; }
    catch (e) { $('health-stop').disabled = false; $('health-status').textContent = recovery.text(e.message, 'health'); }
  };
  window.RiposteHealth = {
    updateDisabled,
    deferCompletion: () => submitting,
    onJob(job) {
      if (job.operation !== 'health') return;
      jobId = job.id; running = ['running', 'queued'].includes(job.state);
      if (running) $('health-status').textContent = job.cancel_requested ? 'Stop requested. Waiting for the current filesystem read.' : job.phase + (job.processed !== undefined ? ' · ' + job.processed + ' entries' : '');
      updateDisabled();
    },
    completed(job) {
      if (job.operation !== 'health') return false;
      if (jobId && job.id !== jobId) return true;
      jobId = job.id; running = false;
      if (['done', 'incomplete'].includes(job.state)) {
        render(job.result);
        $('health-status').textContent = words(job.result.status) + ' · Read-only observation. No files changed.';
      } else {
        $('health-result').hidden = true;
        $('health-status').textContent = job.state === 'cancelled' ? 'Inspection stopped. No files changed. Inspect again when ready.' : recovery.text(job.code, 'health');
      }
      updateDisabled(); return true;
    },
  };
})();
