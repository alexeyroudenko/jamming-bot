/** Style guide: dark zinc + cyan accent */
export const atlasColors = {
  bg: '#09090b',
  surface: '#18181b',
  border: '#27272a',
  text: '#fafafa',
  muted: '#a1a1aa',
  accent: '#22d3ee',
  accentDim: '#0891b2',
  success: '#10b981',
  destructive: '#ef4444',
};

/** @param {number} code */
export function statusColor(code) {
  if (!code || code === 200) return atlasColors.accent;
  if (code >= 500) return atlasColors.destructive;
  if (code >= 400) return '#f97316';
  if (code >= 300) return '#eab308';
  return atlasColors.muted;
}
