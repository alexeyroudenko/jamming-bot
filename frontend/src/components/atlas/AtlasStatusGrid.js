import React, { useEffect, useRef } from 'react';
import { atlasColors, statusColor } from './atlasTheme';

const MAX_COLS = 720;
const ROW_H = 6;

/**
 * @param {{ steps: Array<{ status_num?: number, error?: string }> }} props
 */
export default function AtlasStatusGrid({ steps }) {
  const ref = useRef(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const data = (steps || []).filter((d) => Number.isFinite(d._n));
    const n = data.length;
    if (!n) {
      canvas.width = 400;
      canvas.height = 80;
      ctx.fillStyle = atlasColors.surface;
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = atlasColors.muted;
      ctx.font = '13px system-ui, sans-serif';
      ctx.fillText('No steps', 16, 44);
      return;
    }

    const cols = Math.min(n, MAX_COLS);
    const rows = Math.ceil(n / cols);
    const w = Math.max(320, cols);
    const h = Math.max(ROW_H * rows, ROW_H);

    canvas.width = w;
    canvas.height = h;
    ctx.fillStyle = atlasColors.bg;
    ctx.fillRect(0, 0, w, h);

    for (let i = 0; i < n; i++) {
      const col = i % cols;
      const row = Math.floor(i / cols);
      const d = data[i];
      const x = col;
      const y = row * ROW_H;
      ctx.fillStyle = statusColor(d.status_num);
      ctx.fillRect(x, y, 1, ROW_H - 1);
      if (d.error && String(d.error).trim()) {
        ctx.strokeStyle = atlasColors.destructive;
        ctx.lineWidth = 1;
        ctx.strokeRect(x + 0.25, y + 0.25, 0.5, ROW_H - 1.5);
      }
    }
  }, [steps]);

  return (
    <div className="atlas-status-grid-wrap">
      <canvas ref={ref} className="atlas-status-canvas" />
      <p className="atlas-legend">
        <span className="atlas-legend-swatch" style={{ background: atlasColors.accent }} /> 200
        <span className="atlas-legend-swatch" style={{ background: '#f97316', marginLeft: 12 }} /> 4xx
        <span className="atlas-legend-swatch" style={{ background: atlasColors.destructive, marginLeft: 12 }} /> 5xx
        <span className="atlas-legend-note"> · red outline: error field</span>
      </p>
    </div>
  );
}
