function hostFromUrl(u) {
  if (!u || typeof u !== 'string') return '';
  try {
    const url = new URL(u.startsWith('http') ? u : `https://${u}`);
    return url.hostname || '';
  } catch {
    return '';
  }
}

/**
 * Aggregate prev-host → current-host counts for Sankey.
 * @returns {{ nodes: { name: string }[], links: { source: number, target: number, value: number }[] }}
 */
export function aggregateHostFlows(steps, opts = {}) {
  const maxNodes = opts.maxNodes ?? 34;
  const flows = new Map();
  const hostCounts = new Map();

  for (const row of steps || []) {
    const cur = row.url || row.current_url || '';
    const src = row.src_url || row.src || '';
    if (!cur) continue;
    const hFrom = hostFromUrl(src) || hostFromUrl(cur);
    const hTo = hostFromUrl(cur);
    if (!hFrom || !hTo || hFrom === hTo) continue;

    const key = `${hFrom}\0${hTo}`;
    flows.set(key, (flows.get(key) || 0) + 1);
    hostCounts.set(hFrom, (hostCounts.get(hFrom) || 0) + 1);
    hostCounts.set(hTo, (hostCounts.get(hTo) || 0) + 1);
  }

  const sortedHosts = [...hostCounts.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, maxNodes)
    .map(([name]) => name);

  const idx = new Map(sortedHosts.map((name, i) => [name, i]));
  const links = [];
  for (const [key, v] of flows) {
    const [s, t] = key.split('\0');
    if (!idx.has(s) || !idx.has(t)) continue;
    links.push({ source: idx.get(s), target: idx.get(t), value: v });
  }

  const nodes = sortedHosts.map((name) => ({ name }));
  return { nodes, links };
}
