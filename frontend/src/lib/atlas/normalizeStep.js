/**
 * Normalize API / socket step row for Atlas widgets (shared numeric fields).
 */
export function normalizeStep(raw, fallbackIndex) {
  const r = raw && typeof raw === 'object' ? raw : {};
  const n = r.step ?? r.number ?? fallbackIndex;
  let _n = typeof n === 'number' ? n : parseInt(String(n), 10);
  if (!Number.isFinite(_n)) _n = fallbackIndex;

  let _ts = NaN;
  const ts = r.timestamp ?? r.ts;
  if (ts != null && ts !== '') {
    const d = new Date(ts);
    if (!Number.isNaN(+d)) _ts = +d;
  }

  let status_num = 0;
  const sc = r.status_code ?? r.status;
  if (sc !== undefined && sc !== null && sc !== '') {
    const p = parseInt(String(sc), 10);
    if (!Number.isNaN(p)) status_num = p;
  }

  const text = r.text ?? r.struct_text ?? '';
  const text_length =
    typeof r.text_length === 'number' ? r.text_length : String(text).length;

  let semantic_words = [];
  if (Array.isArray(r.semantic_words)) semantic_words = r.semantic_words;
  else if (typeof r.semantic_words === 'string' && r.semantic_words.trim())
    semantic_words = r.semantic_words.split(/\s+/);

  return {
    ...r,
    _n,
    _ts,
    text_length,
    status_num,
    text,
    url: r.url ?? r.current_url ?? '',
    src_url: r.src_url ?? r.src ?? '',
    words: r.words || [],
    tags: r.tags || [],
    semantic_words,
    hrases: r.hrases || r.noun_phrases || [],
    phrases: r.phrases || [],
    error: r.error || '',
  };
}
