import React, { useEffect, useMemo, useRef, useState } from 'react';
import * as d3 from 'd3';
import { atlasColors } from './atlasTheme';

const DEBOUNCE_MS = 260;

/**
 * @param {{ steps: object[] }} props
 */
export default function AtlasAggregates({ steps }) {
  const histRef = useRef(null);
  const wordsRef = useRef(null);
  const statusRef = useRef(null);
  const prevLenRef = useRef(0);
  const [debounced, setDebounced] = useState(steps || []);

  useEffect(() => {
    const next = steps || [];
    const firstFill = prevLenRef.current === 0 && next.length > 0;
    prevLenRef.current = next.length;
    if (firstFill) {
      setDebounced(next);
      return;
    }
    if (next.length === 0) {
      prevLenRef.current = 0;
      setDebounced([]);
      return;
    }
    const t = setTimeout(() => setDebounced(next), DEBOUNCE_MS);
    return () => clearTimeout(t);
  }, [steps]);

  const wordCounts = useMemo(() => {
    const m = new Map();
    for (const row of debounced) {
      const bag = [...(row.words || []), ...(row.tags || []), ...(row.semantic_words || [])];
      for (const w of bag) {
        const k = String(w).trim().toLowerCase();
        if (k.length < 2 || k.length > 40) continue;
        m.set(k, (m.get(k) || 0) + 1);
      }
    }
    return [...m.entries()].sort((a, b) => b[1] - a[1]).slice(0, 14);
  }, [debounced]);

  const statusCounts = useMemo(() => {
    const m = new Map();
    for (const row of debounced) {
      const c = row.status_num || 0;
      const k = c || '—';
      m.set(k, (m.get(k) || 0) + 1);
    }
    return [...m.entries()].sort((a, b) => b[1] - a[1]);
  }, [debounced]);

  useEffect(() => {
    const el = histRef.current;
    if (!el) return;
    const W = el.clientWidth || 320;
    const H = 140;
    const m = { t: 8, r: 8, b: 28, l: 36 };
    const iw = W - m.l - m.r;
    const ih = H - m.t - m.b;

    const lengths = debounced.map((d) => d.text_length || 0).filter((x) => x >= 0);
    d3.select(el).selectAll('*').remove();
    if (!lengths.length) {
      d3.select(el).append('svg').attr('width', W).attr('height', H);
      return;
    }

    const ext = d3.extent(lengths);
    const lo = ext[0] ?? 0;
    const hi = ext[1] ?? 0;
    const domain = lo === hi ? [lo - 1, hi + 1] : [lo, hi];
    const bins = d3.bin().domain(domain).thresholds(12)(lengths);
    const x = d3
      .scaleLinear()
      .domain([bins[0].x0, bins[bins.length - 1].x1])
      .range([0, iw]);
    const y = d3
      .scaleLinear()
      .domain([0, d3.max(bins, (b) => b.length) || 1])
      .nice()
      .range([ih, 0]);

    const svg = d3.select(el).append('svg').attr('width', W).attr('height', H);
    const g = svg.append('g').attr('transform', `translate(${m.l},${m.t})`);

    g.selectAll('rect')
      .data(bins)
      .join('rect')
      .attr('x', (d) => x(d.x0) + 1)
      .attr('width', (d) => Math.max(0, x(d.x1) - x(d.x0) - 2))
      .attr('y', (d) => y(d.length))
      .attr('height', (d) => ih - y(d.length))
      .attr('fill', atlasColors.accent)
      .attr('opacity', 0.65);

    g.append('g')
      .attr('transform', `translate(0,${ih})`)
      .call(d3.axisBottom(x).ticks(4))
      .selectAll('text')
      .attr('fill', atlasColors.muted)
      .attr('font-size', 9);
    g.selectAll('.domain,.tick line').attr('stroke', atlasColors.border);
  }, [debounced]);

  useEffect(() => {
    const el = wordsRef.current;
    if (!el) return;
    const W = el.clientWidth || 320;
    const H = 160;
    const m = { t: 8, r: 16, b: 8, l: 96 };
    const iw = W - m.l - m.r;
    const ih = H - m.t - m.b;

    d3.select(el).selectAll('*').remove();
    if (!wordCounts.length) {
      d3.select(el).append('svg').attr('width', W).attr('height', H);
      return;
    }

    const x = d3
      .scaleLinear()
      .domain([0, d3.max(wordCounts, (d) => d[1]) || 1])
      .nice()
      .range([0, iw]);
    const y = d3
      .scaleBand()
      .domain(wordCounts.map((d) => d[0]))
      .range([0, ih])
      .padding(0.15);

    const svg = d3.select(el).append('svg').attr('width', W).attr('height', H);
    const g = svg.append('g').attr('transform', `translate(${m.l},${m.t})`);

    g.selectAll('rect')
      .data(wordCounts)
      .join('rect')
      .attr('x', 0)
      .attr('y', (d) => y(d[0]))
      .attr('width', (d) => x(d[1]))
      .attr('height', y.bandwidth())
      .attr('fill', atlasColors.accentDim)
      .attr('opacity', 0.8);

    g.selectAll('text.lbl')
      .data(wordCounts)
      .join('text')
      .attr('class', 'lbl')
      .attr('x', -6)
      .attr('y', (d) => (y(d[0]) || 0) + y.bandwidth() / 2)
      .attr('dy', '0.35em')
      .attr('text-anchor', 'end')
      .attr('fill', atlasColors.muted)
      .attr('font-size', 9)
      .text((d) => (d[0].length > 18 ? `${d[0].slice(0, 16)}…` : d[0]));
  }, [wordCounts]);

  useEffect(() => {
    const el = statusRef.current;
    if (!el) return;
    const W = el.clientWidth || 280;
    const H = 140;
    const m = { t: 8, r: 8, b: 28, l: 32 };
    const iw = W - m.l - m.r;
    const ih = H - m.t - m.b;

    d3.select(el).selectAll('*').remove();
    if (!statusCounts.length) {
      d3.select(el).append('svg').attr('width', W).attr('height', H);
      return;
    }

    const x = d3
      .scaleBand()
      .domain(statusCounts.map((d) => String(d[0])))
      .range([0, iw])
      .padding(0.2);
    const y = d3
      .scaleLinear()
      .domain([0, d3.max(statusCounts, (d) => d[1]) || 1])
      .nice()
      .range([ih, 0]);

    const svg = d3.select(el).append('svg').attr('width', W).attr('height', H);
    const g = svg.append('g').attr('transform', `translate(${m.l},${m.t})`);

    g.selectAll('rect')
      .data(statusCounts)
      .join('rect')
      .attr('x', (d) => x(String(d[0])))
      .attr('y', (d) => y(d[1]))
      .attr('width', x.bandwidth())
      .attr('height', (d) => ih - y(d[1]))
      .attr('fill', atlasColors.muted)
      .attr('opacity', 0.75);

    g.append('g')
      .attr('transform', `translate(0,${ih})`)
      .call(d3.axisBottom(x))
      .selectAll('text')
      .attr('fill', atlasColors.muted)
      .attr('font-size', 9);
    g.selectAll('.domain,.tick line').attr('stroke', atlasColors.border);
  }, [statusCounts]);

  return (
    <div className="atlas-aggregates-grid">
      <div className="atlas-aggregate-card">
        <h3 className="atlas-card-title">Text length</h3>
        <div ref={histRef} className="atlas-mini-chart" />
      </div>
      <div className="atlas-aggregate-card">
        <h3 className="atlas-card-title">Top tokens</h3>
        <div ref={wordsRef} className="atlas-mini-chart atlas-mini-chart--tall" />
      </div>
      <div className="atlas-aggregate-card">
        <h3 className="atlas-card-title">Status codes</h3>
        <div ref={statusRef} className="atlas-mini-chart" />
      </div>
    </div>
  );
}
