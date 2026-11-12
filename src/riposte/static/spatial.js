/* Private source-bound masks. Shared API, errors and publishing selection own
   the boundaries; this disclosure owns only its transient upload/preview state. */
'use strict';
window.RiposteSpatial = (() => {
  const masks = new Map();
  let rows = [], selected = new Set(), selectionKey = '', epoch = 0, uploading = false, controller = null, pageOffset = 0, pageTotal = 0;
  const active = () => rows.filter(row => selected.has(row.id) && masks.has(row.sha256));
  function invalidate() {
    ++epoch; controller?.abort(); controller = null; uploading = false;
    pageOffset = 0; pageTotal = 0;
    if ($('spatial-previews').children.length) $('spatial-status').textContent = 'Selection or settings changed. Preview masks again.';
    $('spatial-previews').replaceChildren();
    controls();
  }
  function controls() {
    const has = active().length > 0;
    $('spatial-file').disabled = uploading || !$('spatial-image').value;
    $('spatial-preview').disabled = uploading || !has || !!controller;
    $('spatial-export').disabled = uploading || !has;
    $('spatial-image').disabled = uploading || !rows.some(row => selected.has(row.id));
    $('spatial-file').setAttribute('aria-busy', String(uploading));
    $('spatial-cancel').hidden = !uploading && !controller;
    $('spatial-pages').hidden = pageTotal <= 3;
    $('spatial-prev').disabled = uploading || !!controller || pageOffset === 0;
    $('spatial-next').disabled = uploading || !!controller || pageOffset + 3 >= pageTotal;
    window.RipostePublish?.budgetChanged();
  }
  function showError(error) {
    const node = $('spatial-error'); node.textContent = recovery.text(error.message, 'publish'); node.hidden = false;
    $('spatial-file').setAttribute('aria-invalid', String(['ARTIST_MASK_PNG_INVALID','ARTIST_MASK_ASPECT_MISMATCH'].includes(error.message))); node.focus();
  }
  function render() {
    const list = $('spatial-masks'); list.replaceChildren();
    for (const row of active()) {
      const entry = masks.get(row.sha256), item = el('li'), remove = el('button', 'text-link', 'Remove mask');
      item.append(el('span', '', shortName(row) + ' · ' + entry.name));
      remove.type = 'button'; remove.setAttribute('aria-label', 'Remove mask from ' + shortName(row));
      remove.onclick = () => { masks.delete(row.sha256); invalidate(); render(); $('spatial-error').hidden = true; $('spatial-file').removeAttribute('aria-invalid'); $('spatial-status').textContent = 'Mask removed. Automatic limits apply to that artwork.'; $('spatial-file').focus(); };
      item.append(remove); list.append(item);
    }
    controls();
  }
  function sync(images, ids) {
    const key = JSON.stringify([images.map(row => [row.id, row.sha256]), [...ids]]);
    if (key === selectionKey) return;
    selectionKey = key; rows = images; selected = new Set(ids); invalidate();
    const current = $('spatial-image').value, select = $('spatial-image'); select.replaceChildren();
    for (const row of rows.filter(row => selected.has(row.id))) {
      const option = el('option', '', shortName(row) + ' · ' + row.width + ' × ' + row.height); option.value = row.id; select.append(option);
    }
    if (!select.options.length) { const option = el('option', '', 'Select artwork first'); option.value = ''; select.append(option); }
    if ([...select.options].some(option => option.value === current)) select.value = current;
    for (const hash of masks.keys()) if (!rows.some(row => row.sha256 === hash)) masks.delete(hash);
    $('spatial-status').textContent = active().length ? 'Masks retained. Preview this selection at its current sizes.' : 'No masks on this selection. Automatic limits apply.';
    render();
  }
  function payload(ids) {
    const chosen = new Set(ids), hashes = new Set();
    return rows.filter(row => chosen.has(row.id) && masks.has(row.sha256) && !hashes.has(row.sha256) && hashes.add(row.sha256)).map(row => masks.get(row.sha256).mask);
  }
  $('spatial-image').onchange = () => { $('spatial-file').value = ''; controls(); };
  $('spatial-file').onchange = async () => {
    const file = $('spatial-file').files[0], row = rows.find(row => row.id === $('spatial-image').value);
    if (!file || !row || uploading) return;
    invalidate(); const current = epoch; uploading = true; controls();
    $('spatial-error').hidden = true; $('spatial-file').removeAttribute('aria-invalid'); $('spatial-status').textContent = 'Checking mask…';
    let timer;
    try {
      if (!/\.png$/i.test(file.name) || !file.size || file.size > 2097152) throw new Error('ARTIST_MASK_PNG_INVALID');
      const bytes = new Uint8Array(await file.arrayBuffer());
      if (current !== epoch) return;
      let binary = ''; for (let offset = 0; offset < bytes.length; offset += 8192) binary += String.fromCharCode(...bytes.subarray(offset, offset + 8192));
      controller = new AbortController(); const pending = controller; timer = setTimeout(() => pending.abort(), 30000);
      const result = await api('artist-mask', {image_id: row.id, png: btoa(binary)}, controller.signal);
      if (current !== epoch) return;
      const total = [...masks.entries()].filter(([hash]) => hash !== row.sha256).reduce((sum, [, value]) => sum + value.mask.width * value.mask.height, 0);
      if (total + result.mask.width * result.mask.height > 4194304) throw new Error('ARTIST_MASK_SELECTION_INVALID');
      masks.set(row.sha256, {mask: result.mask, name: file.name});
      $('spatial-status').textContent = 'Mask attached. Preview it at each publishing size before starting.';
    } catch (error) {
      if (current === epoch) { showError(error); $('spatial-status').textContent = 'Mask was not attached. Any previously attached mask is retained. Choose a corrected PNG to retry.'; }
    } finally {
      clearTimeout(timer);
      if (current === epoch) { uploading = false; controller = null; $('spatial-file').value = ''; render(); }
    }
  };
  async function previewPage(offset = 0) {
    if (uploading || controller || !active().length) return;
    invalidate(); const current = epoch; controller = new AbortController(); controls();
    const pending = controller, timer = setTimeout(() => pending.abort(), 30000);
    $('spatial-error').hidden = true; $('spatial-status').textContent = 'Rendering masks at final publishing sizes…';
    try {
      const result = await api('publish', {...window.RipostePublish.request(), plan_only: true, budget_offset: offset}, pending.signal);
      if (current !== epoch) return;
      for (const preview of result.budget_previews || []) {
        const figure = el('figure'), picture = el('img'), caption = el('figcaption');
        picture.src = 'data:image/png;base64,' + preview.overlay_png;
        picture.alt = 'Artist restraint overlay for ' + preview.width + ' by ' + preview.height + ' output. Cyan indicates reduced allowance.';
        picture.width = preview.width; picture.height = preview.height;
        await picture.decode();
        if (current !== epoch) return;
        caption.textContent = preview.width + ' × ' + preview.height + ' · ' + preview.unchanged_pixels.toLocaleString() + ' pixels unchanged · peak allowance ' + preview.maximum_channel_change_255 + '/255';
        const link = el('a', 'text-link', 'Download exact cap raster');
        link.href = 'data:image/png;base64,' + preview.caps_png; link.download = 'riposte-budget-' + preview.width + 'x' + preview.height + '.png';
        figure.append(picture, caption, link); $('spatial-previews').append(figure);
      }
      pageOffset = result.budget_preview_offset || 0; pageTotal = result.budget_preview_total || 0;
      $('spatial-status').textContent = 'Previews ' + (pageOffset + 1) + '–' + Math.min(pageOffset + 3, pageTotal) + ' of ' + pageTotal + '. Cyan shows artist restraint. Counts also include automatic white/edge limits. Cap PNG values are literal 0–16 channel levels. This is a budget preview, not an output approval.';
    } catch (error) { if (current === epoch) { $('spatial-previews').replaceChildren(); showError(error); $('spatial-status').textContent = 'Preview unavailable. Masks are retained; choose Preview masks to retry.'; } }
    finally { clearTimeout(timer); if (current === epoch) controller = null; controls(); }
  }
  $('spatial-preview').onclick = () => previewPage();
  $('spatial-prev').onclick = () => previewPage(Math.max(0, pageOffset - 3));
  $('spatial-next').onclick = () => previewPage(pageOffset + 3);
  $('spatial-export').onclick = () => {
    if (uploading || !active().length) return;
    const data = JSON.stringify({schema: 1, masks: payload(selected)}, null, 2), url = URL.createObjectURL(new Blob([data], {type: 'application/json'}));
    const link = el('a'); link.href = url; link.download = 'riposte-private-mask-map.json'; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    $('spatial-status').textContent = 'Private mask map exported for --budget-map. It contains source hashes and mask pixels; keep it out of public image packs.';
  };
  $('spatial-cancel').onclick = () => {
    invalidate(); uploading = false; $('spatial-file').value = ''; controls();
    $('spatial-status').textContent = 'Mask check cancelled. Attached masks are retained.';
    $('spatial-file').focus();
  };
  return {sync, payload, invalidate, pending: () => uploading};
})();
