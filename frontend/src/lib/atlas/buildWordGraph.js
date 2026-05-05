/**
 * Co-occurrence of tokens from recent steps for force-directed graph.
 * @returns {{ nodes: { id: string, count: number }[], links: { source: string, target: string, weight: number }[] }}
 */
export function buildWordCooccurrence(steps, opts = {}) {
  const maxSteps = opts.maxSteps ?? 350;
  const maxNodes = opts.maxNodes ?? 64;
  const slice = (steps || []).slice(-maxSteps);
  const tokenRe = /[\w\u0400-\u04FF]{3,}/g;

  const counts = new Map();
  const pairCounts = new Map();

  function bumpPair(a, b) {
    let x = String(a);
    let y = String(b);
    if (x > y) [x, y] = [y, x];
    const key = `${x}\0${y}`;
    pairCounts.set(key, (pairCounts.get(key) || 0) + 1);
  }

  for (const row of slice) {
    const bag = [];
    for (const w of [...(row.words || []), ...(row.tags || [])]) {
      const t = String(w).trim().toLowerCase();
      if (t.length >= 3 && t.length <= 36) bag.push(t);
    }
    const txt = row.text || '';
    let m;
    const re = new RegExp(tokenRe.source, 'g');
    while ((m = re.exec(txt)) !== null) bag.push(m[0].toLowerCase());

    const uniq = [...new Set(bag)].slice(0, 48);
    for (const t of uniq) counts.set(t, (counts.get(t) || 0) + 1);
    for (let i = 0; i < uniq.length; i += 1) {
      for (let j = i + 1; j < uniq.length; j += 1) bumpPair(uniq[i], uniq[j]);
    }
  }

  const top = [...counts.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, maxNodes)
    .map(([id, count]) => ({ id, count }));

  const idSet = new Set(top.map((n) => n.id));
  const links = [];
  for (const [key, w] of pairCounts) {
    const [a, b] = key.split('\0');
    if (!idSet.has(a) || !idSet.has(b) || w <= 0) continue;
    links.push({ source: a, target: b, weight: w });
  }

  return { nodes: top, links };
}
