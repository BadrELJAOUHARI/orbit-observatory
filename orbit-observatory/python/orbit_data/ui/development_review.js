'use strict';
(() => {
  const packet = JSON.parse(document.getElementById('packet-data').textContent);
  const rows = packet.rows;
  const responseFields = packet.response_fields;
  const key = 'orbit-development-review-v2:' + packet.packet_id;
  const byId = new Map(rows.map(row => [row.candidate_id, row]));
  const articles = [...document.querySelectorAll('article')];
  const status = document.getElementById('save-status');
  const importStatus = document.getElementById('import-status');
  const filterStatus = document.getElementById('status-filter');
  const filterQuality = document.getElementById('quality-filter');
  const search = document.getElementById('search');
  const annotator = document.getElementById('annotator');
  const dimensions = [['actor-filter','actor_id'],['lens-filter','lens_id'],['period-filter','event_date'],['label-filter','ai_suggested_label']].map(([id, field]) => ({id, field, control: document.getElementById(id)})).filter(x => x.control);
  const allowed = {
    human_label: ['', 'support', 'oppose', 'no_stance', 'mixed', 'unresolved', 'not_applicable'],
    human_independent: ['false'],
    human_source_eligibility: ['', 'eligible', 'ineligible', 'needs_review'],
    human_text_quality: ['', 'usable', 'defective', 'needs_review'],
    human_attribution: ['', 'attributable', 'wrong_actor', 'needs_review'],
    human_scope: ['', 'exact_target_met', 'partial_scope', 'no_relevant_stance', 'needs_review']
  };
  let responses = Object.fromEntries(rows.map(row => [row.candidate_id, Object.fromEntries(responseFields.map(field => [field, String(row[field] ?? '')]))]));
  const cell = value => value == null ? '' : String(value);
  const hasInput = response => responseFields.some(field => field !== 'human_independent' && response[field] !== '');
  const completed = response => !!(response.human_label && response.human_annotator_id.trim() && response.human_review_notes.trim());
  const settings = () => ({status: filterStatus.value, quality: filterQuality.value, search: search.value, annotator: annotator.value, ...Object.fromEntries(dimensions.map(x => [x.id,x.control.value]))});
  function signal(message, bad = false) {
    status.textContent = message;
    status.className = bad ? 'error' : 'ok';
  }
  function backup() {
    return {format: 'orbit-development-responses-v2', packet_id: packet.packet_id,
      saved_at: new Date().toISOString(), provenance: 'AI-assisted and non-independent',
      settings: settings(), responses: Object.fromEntries(Object.entries(responses).filter(([, value]) => hasInput(value)))};
  }
  function save() {
    try {
      const value = backup();
      localStorage.setItem(key, JSON.stringify(value));
      signal('Saved locally at ' + new Date(value.saved_at).toLocaleTimeString() + '.');
    } catch (error) {
      signal('Local saving unavailable. Export a progress backup or CSV before closing. ' + error.message, true);
    }
  }
  function showResponses() {
    articles.forEach(article => {
      const row = rows[Number(article.dataset.index)];
      article.querySelectorAll('[data-field]').forEach(control => { control.value = responses[row.candidate_id][control.dataset.field]; });
    });
  }
  function applyFilters() {
    const query = search.value.toLowerCase();
    let visible = 0;
    articles.forEach(article => {
      const row = rows[Number(article.dataset.index)];
      const reviewed = !!row.existing_annotation_id || completed(responses[row.candidate_id]);
      // Completing a note must not hide the textarea while the reviewer types.
      const stateMatches = filterStatus.value === 'all' || article.contains(document.activeElement) || (filterStatus.value === 'reviewed' ? reviewed : !reviewed);
      const qualityMatches = filterQuality.value === 'all' || (filterQuality.value === 'clean' ? row.quarantine === 'false' : row.quarantine === 'true');
      const dimensionsMatch = dimensions.every(x => !x.control.value || (x.field === 'event_date' ? row[x.field].slice(0,4) : row[x.field]) === x.control.value);
      article.hidden = !(stateMatches && qualityMatches && dimensionsMatch && article.textContent.toLowerCase().includes(query));
      if (!article.hidden) visible++;
    });
    const newDecisions = Object.values(responses).filter(completed).length;
    const oldDecisions = rows.filter(row => row.existing_annotation_id).length;
    document.getElementById('count').textContent = `${visible} visible / ${rows.length} development records · ${newDecisions} new decisions · ${oldDecisions} previous judgments`;
  }
  function validateResponse(id, input) {
    if (!byId.has(id)) throw new Error('Unknown or non-development candidate: ' + id);
    if (!input || typeof input !== 'object' || Array.isArray(input)) throw new Error('Invalid response for ' + id);
    if (Object.keys(input).some(field => !responseFields.includes(field))) throw new Error('Response contains read-only or unknown fields.');
    const result = {...responses[id]};
    responseFields.forEach(field => {
      if (!(field in input)) return;
      if (typeof input[field] !== 'string') throw new Error('Response values must be text.');
      if (allowed[field] && !allowed[field].includes(input[field])) throw new Error('Invalid ' + field + ' for ' + id);
      result[field] = input[field];
    });
    return result;
  }
  function merge(imported, replace) {
    const pending = {};
    for (const [id, input] of Object.entries(imported)) {
      const value = validateResponse(id, input);
      const current = responses[id];
      if (responseFields.some(field => current[field] && field !== 'human_independent' && value[field] !== current[field]) && !replace) {
        throw new Error('Different local responses exist for ' + byId.get(id).row_id + '. Export your current backup, then enable replacement if intended.');
      }
      pending[id] = value;
    }
    responses = {...responses, ...pending};
  }
  function restoreSettings(value) {
    if (!value || typeof value !== 'object') return;
    if (['unreviewed', 'all', 'reviewed'].includes(value.status)) filterStatus.value = value.status;
    if (['clean', 'all', 'quarantined'].includes(value.quality)) filterQuality.value = value.quality;
    if (typeof value.search === 'string') search.value = value.search;
    if (typeof value.annotator === 'string') annotator.value = value.annotator;
    dimensions.forEach(x => { if (typeof value[x.id] === 'string' && [...x.control.options].some(o => o.value === value[x.id])) x.control.value = value[x.id]; });
  }
  function readBackup(value) {
    if (value.format !== 'orbit-development-responses-v2' || value.packet_id !== packet.packet_id) throw new Error('This backup belongs to a different review packet.');
    if (!value.responses || typeof value.responses !== 'object' || Array.isArray(value.responses)) throw new Error('Invalid response backup.');
    return value.responses;
  }
  // RFC-style quoted CSV: preserve commas, newlines, quotes, Unicode and CRLF.
  function parseCSV(source) {
    const text = source.replace(/^\uFEFF/, '');
    const table = []; let row = [], field = '', quoted = false, closed = false;
    for (let i = 0; i < text.length; i++) {
      const ch = text[i];
      if (quoted) {
        if (ch === '"' && text[i + 1] === '"') { field += '"'; i++; }
        else if (ch === '"') { quoted = false; closed = true; }
        else field += ch;
      } else if (ch === '"') {
        if (field || closed) throw new Error('Invalid CSV quotation.');
        quoted = true;
      } else if (ch === ',' || ch === '\n' || ch === '\r') {
        row.push(field); field = ''; closed = false;
        if (ch !== ',') {
          table.push(row); row = [];
          if (ch === '\r' && text[i + 1] === '\n') i++;
        }
      } else {
        if (closed) throw new Error('Unexpected text after CSV quotation.');
        field += ch;
      }
    }
    if (quoted) throw new Error('Unclosed CSV quotation.');
    if (field || row.length || closed) { row.push(field); table.push(row); }
    const columns = table.shift();
    const expected = Object.keys(rows[0]);
    if (!columns || new Set(columns).size !== columns.length || columns.length !== expected.length || expected.some(field => !columns.includes(field))) throw new Error('CSV columns do not match this packet.');
    if (table.length !== rows.length) throw new Error('CSV must contain all development rows; export is independent of filters.');
    const imported = {}; const seen = new Set();
    table.forEach(values => {
      if (values.length !== columns.length) throw new Error('CSV row has a different number of fields.');
      const item = Object.fromEntries(columns.map((column, i) => [column, values[i]]));
      const id = item.candidate_id;
      if (!byId.has(id) || seen.has(id)) throw new Error('Unknown or duplicate candidate in CSV.');
      seen.add(id);
      const original = byId.get(id);
      if (expected.some(field => !responseFields.includes(field) && item[field] !== cell(original[field]))) throw new Error('Read-only evidence, provenance or suggestions were changed in the CSV.');
      const response = Object.fromEntries(responseFields.map(field => [field, item[field]]));
      if (hasInput(response)) imported[id] = response;
    });
    return imported;
  }
  function download(name, data, type) {
    const url = URL.createObjectURL(new Blob([data], {type}));
    const anchor = document.createElement('a'); anchor.href = url; anchor.download = name; anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  articles.forEach(article => {
    article.addEventListener('focusout', () => setTimeout(applyFilters, 0));
    article.querySelectorAll('[data-field]').forEach(control => {
      control.addEventListener('input', () => {
        const row = rows[Number(article.dataset.index)];
        const id = row.candidate_id;
        responses[id][control.dataset.field] = control.value;
        if (control.dataset.field === 'human_label' && control.value && !responses[id].human_annotator_id && annotator.value.trim()) {
          responses[id].human_annotator_id = annotator.value.trim();
          article.querySelector('[data-field="human_annotator_id"]').value = annotator.value.trim();
        }
        save(); applyFilters();
      });
    });
  });
  [filterStatus, filterQuality, search, annotator, ...dimensions.map(x => x.control)].forEach(control => control.addEventListener('input', () => { save(); applyFilters(); }));
  document.getElementById('export-json').addEventListener('click', () => {
    save(); download('orbit-development-progress.json', JSON.stringify(backup(), null, 2), 'application/json');
  });
  document.getElementById('export-csv').addEventListener('click', () => {
    save(); const columns = Object.keys(rows[0]); const quote = value => '"' + cell(value).replaceAll('"', '""') + '"';
    const exported = rows.map(row => ({...row, ...responses[row.candidate_id]}));
    const csv = '\uFEFF' + [columns.map(quote).join(','), ...exported.map(row => columns.map(field => quote(row[field])).join(','))].join('\r\n');
    download('orbit-development-review-return.csv', csv, 'text/csv;charset=utf-8');
  });
  document.getElementById('import-button').addEventListener('click', () => document.getElementById('import-file').click());
  document.getElementById('import-file').addEventListener('change', async event => {
    const file = event.target.files[0]; if (!file) return;
    try {
      const text = await file.text();
      let imported;
      if (file.name.toLowerCase().endsWith('.json')) imported = readBackup(JSON.parse(text));
      else imported = parseCSV(text);
      merge(imported, document.getElementById('allow-replace').checked);
      showResponses(); save(); applyFilters();
      importStatus.textContent = 'Imported ' + Object.keys(imported).length + ' response records. Evidence and prior annotations unchanged.';
      importStatus.className = 'ok';
    } catch (error) {
      importStatus.textContent = 'Import failed: ' + error.message + ' Local responses were preserved.';
      importStatus.className = 'error';
    } finally { event.target.value = ''; }
  });
  try {
    const value = localStorage.getItem(key);
    if (value) {
      const stored = JSON.parse(value); merge(readBackup(stored), true); restoreSettings(stored.settings);
      signal('Restored saved progress from ' + new Date(stored.saved_at).toLocaleString() + '.');
    } else {
      localStorage.setItem(key, JSON.stringify(backup())); signal('Ready. Changes will save automatically in this browser.');
    }
  } catch (error) {
    signal('Could not restore/save local progress. Use Import to resume from a backup, and export before closing. ' + error.message, true);
  }
  showResponses(); applyFilters();
})();
