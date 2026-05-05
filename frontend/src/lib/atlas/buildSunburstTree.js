/**
 * Build a nested tree from URL paths for d3.partition / sunburst.
 * Leaf nodes carry visit counts; interior counts come from d3.hierarchy .sum.
 */
export function buildUrlHierarchyRoot(steps) {
  const root = { name: 'root', children: [] };

  function findChild(node, name) {
    if (!node.children) node.children = [];
    let ch = node.children.find((c) => c.name === name);
    if (!ch) {
      ch = { name, children: [] };
      node.children.push(ch);
    }
    return ch;
  }

  for (const row of steps || []) {
    const raw = row.url || row.current_url || '';
    if (!raw) continue;
    let pathname = '/';
    try {
      const u = new URL(raw.startsWith('http') ? raw : `https://${raw}`);
      pathname = u.pathname || '/';
    } catch {
      continue;
    }

    const segments = pathname.split('/').filter(Boolean);
    if (!segments.length) {
      root.value = (root.value || 0) + 1;
      continue;
    }

    let node = root;
    for (let i = 0; i < segments.length; i += 1) {
      node = findChild(node, segments[i]);
      if (i === segments.length - 1) {
        node.value = (node.value || 0) + 1;
      }
    }
  }

  return root;
}
