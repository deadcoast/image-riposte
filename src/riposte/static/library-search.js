'use strict';
(() => {
  const dialog = $('private-search-dialog'), form = $('private-search-form');
  let generation = 0, pending = null, timer = null, report = null, composing = false;
  const fields = ['private-query', 'private-category', 'private-title-state', 'private-year', 'private-month', 'private-size'];
  function invalidate() {
    generation++; clearTimeout(timer); pending?.abort(); pending = null; report = null;
    $('private-results').replaceChildren(); $('private-prev').disabled = true; $('private-next').disabled = true;
    $('private-search-run').disabled = false; $('private-results').setAttribute('aria-busy', 'false');
    $('private-query-clear').hidden = !$('private-query').value;
    $('private-search-error').hidden = true;
    for (const id of fields) $(id).removeAttribute('aria-invalid');
  }
  async function search(offset = 0, revision = null) {
    if (!dialog.open || composing) return;
    invalidate(); const ticket = generation; pending = new AbortController();
    const controller = pending, timeout = setTimeout(() => controller.abort(), 30000);
    $('private-search-run').disabled = true; $('private-results').setAttribute('aria-busy', 'true');
    $('private-search-status').textContent = 'Searching private library…';
    const body = {search: $('private-query').value, category: $('private-category').value,
      title_state: $('private-title-state').value, year: $('private-year').value || null,
      month: $('private-month').value || null, size: $('private-size').value, limit: 50, offset, expected_revision: revision};
    try {
      const result = await api('library-search', body, controller.signal);
      if (ticket !== generation || !dialog.open) return;
      report = result;
      $('private-search-status').textContent = result.total ? `${offset + (result.rows.length ? 1 : 0)}–${offset + result.rows.length} of ${result.total} matches` : 'No matches. Change or clear the filters.';
      for (const row of result.rows) {
        const item = el('li'), name = el('strong', '', row.original_filename || 'Unknown original title');
        item.append(name, el('p', 'field-help', row.category ? 'Category: ' + row.category : 'No trusted category'),
          el('p', '', row.relative), el('p', 'field-help', row.title_state === 'KNOWN' ? 'Saved title matches catalog identity' : 'Original title unavailable · ' + row.provenance.toLowerCase()));
        const open = el('button', 'secondary', 'Inspect image'); open.type = 'button';
        open.onclick = async () => {
          open.disabled = true;
          try {
            // Use the existing canonical inspector; never merge private fields
            // into the ordinary gallery, publication selection or state cache.
            await refresh();
            if (ticket !== generation || !dialog.open) return;
            if (!state.images.some(image => image.id === row.id)) throw Error('IMAGE_NOT_FOUND');
            dialog.close(); setView('library'); select(row.id);
          } catch (e) {
            if (ticket === generation && dialog.open) showError(e.message);
          } finally { open.disabled = false; }
        };
        item.append(open); $('private-results').append(item);
      }
      $('private-prev').disabled = offset === 0;
      $('private-next').disabled = result.next_offset === null;
    } catch (e) {
      if (ticket !== generation || !dialog.open) return;
      showError(e.message); $('private-search-status').textContent = 'Search stopped. Correct the filters or search again.';
      const field = {YEAR_FILTER_INVALID: 'private-year', MONTH_FILTER_INVALID: 'private-month'}[e.message];
      if (field) { $(field).setAttribute('aria-invalid', 'true'); const disclosure = $(field).closest('details'); if (disclosure) disclosure.open = true; $(field).focus(); }
    } finally {
      clearTimeout(timeout);
      if (ticket === generation) { pending = null; $('private-search-run').disabled = false; $('private-results').setAttribute('aria-busy', 'false'); }
    }
  }
  function showError(code) {
    $('private-search-error').textContent = recovery.text(code, 'library-search');
    $('private-search-error').hidden = false;
  }
  function changed() {
    invalidate(); $('private-search-status').textContent = 'Filters changed. Waiting to search…';
    if (!composing) timer = setTimeout(() => search(), 300);
  }
  $('private-search-open').onclick = () => { dialog.showModal(); $('private-query').focus(); search(); };
  $('private-search-close').onclick = () => dialog.close();
  dialog.addEventListener('close', () => { invalidate(); composing = false; form.reset(); $('private-query-clear').hidden = true; $('private-search-status').textContent = 'Ready.'; $('private-search-open').focus(); });
  form.onsubmit = event => { event.preventDefault(); if (!composing && !pending) search(); };
  for (const id of fields) {
    $(id).addEventListener('input', changed);
    $(id).addEventListener('compositionstart', () => { composing = true; invalidate(); });
    $(id).addEventListener('compositionend', () => { composing = false; changed(); });
  }
  $('private-query-clear').onclick = () => { $('private-query').value = ''; search(); $('private-query').focus(); };
  $('private-prev').onclick = () => { if (report) search(Math.max(0, report.offset - report.limit), report.revision); };
  $('private-next').onclick = () => { if (report?.next_offset !== null && report) search(report.next_offset, report.revision); };
})();
