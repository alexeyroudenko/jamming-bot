/**
 * Map storage-service /get/latest rows into atlas viz shape.
 */

function parseTokenList(val) {
  if (val == null || val === '') return [];
  if (Array.isArray(val)) return val.map((x) => String(x)).filter(Boolean);
  const str = String(val).trim();
  if (!str) return [];
  if (str.startsWith('[')) {
    try {
      const v = JSON.parse(str);
      return Array.isArray(v) ? v.map((x) => String(x)).filter(Boolean) : [];
    } catch {
      /* fall through */
    }
  }
  return str.split(/[,|\s]+/).filter((t) => t.length > 0);
}

function parseTimestamp(raw) {
  if (raw == null || raw === '') return NaN;
  const s = String(raw).trim();
  const parsed = Date.parse(s);
  if (!Number.isNaN(parsed)) return parsed;
  const num = parseFloat(s);
  if (!Number.isFinite(num)) return NaN;
  return num < 1e12 ? num * 1000 : num;
}

/**
 * @param {Record<string, string>} row
 * @param {number} fallbackIndex
 */
export function normalizeStepRow(row, fallbackIndex) {
  if (row == null || typeof row !== 'object') {
    return {
      _n: fallbackIndex,
      _ts: NaN,
      text_length: 0,
      status_num: 0,
      text: '',
      url: '',
      src_url: '',
      error: '',
      words: [],
      tags: [],
      semantic_words: [],
      hrases: [],
    phrases: [],
    };
  }
  const n = parseInt(String(row.number ?? ''), 10);
  const status_num = parseInt(String(row.status_code ?? ''), 10);
  const tlRaw = parseInt(String(row.text_length ?? ''), 10);
  const text = String(row.text ?? '');
  const text_length = Number.isFinite(tlRaw) ? tlRaw : text.length;

  return {
    _n: Number.isFinite(n) ? n : fallbackIndex,
    _ts: parseTimestamp(row.timestamp),
    text_length,
    status_num: Number.isFinite(status_num) ? status_num : 0,
    text,
    url: String(row.url ?? ''),
    src_url: String(row.src ?? row.src_url ?? ''),
    error: String(row.error ?? ''),
    words: parseTokenList(row.words),
    tags: parseTokenList(row.tags),
    semantic_words: parseTokenList(row.semantic_words),
    hrases: [...parseTokenList(row.hrases), ...parseTokenList(row.phrases)],
    phrases: parseTokenList(row.phrases),
  };
}
