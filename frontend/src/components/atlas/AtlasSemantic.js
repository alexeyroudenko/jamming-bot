import React, { useEffect, useMemo, useRef, useState } from 'react';
import * as d3 from 'd3';
import { buildWordCooccurrence } from '../../lib/atlas/buildWordGraph';
import { atlasColors } from './atlasTheme';

/**
 * @param {{ steps: object[] }} props
 */
export default function AtlasSemantic({ steps }) {
  const svgRef = useRef(null);
  const [tick, setTick] = useState(0);
  const graph = useMemo(() => buildWordCooccurrence(steps || [], { maxNodes: 64, maxSteps: 350 }), [steps]);

  const tickerText = useMemo(() => {
    const lines = [];
    const slice = (steps || []).slice(-12).reverse();
    for (const row of slice) {
      const h =
        (row.hrases && row.hrases[0]) ||
        (row.phrases && row.phrases[0]) ||
        (row.text && row.text.slice(0, 120));
      if (h) lines.push(String(h).replace(/\s+/g, ' ').trim());
    }
    if (!lines.length) return [];
    const off = tick % lines.length;
    return [...lines.slice(off), ...lines.slice(0, off)].slice(0, 5);
  }, [steps, tick]);

  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), 4200);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    const el = svgRef.current;
    if (!el) return;
    const width = el.clientWidth || 720;
    const height = 320;

    const { nodes, links } = graph;
    if (!nodes.length) {
      d3.select(el).selectAll('*').remove();
      const s = d3.select(el).append('svg').attr('width', width).attr('height', height);
      s.append('text')
        .attr('x', width / 2)
        .attr('y', height / 2)
        .attr('text-anchor', 'middle')
        .attr('fill', atlasColors.muted)
        .attr('font-size', 13)
        .text('No tokens in recent steps');
      return;
    }

    let simulation;
    try {
    const idSet = new Set(nodes.map((n) => n.id));
    const simNodes = nodes.map((n) => ({ ...n }));
    const simLinks = links
      .map((l) => {
        if (!idSet.has(l.source) || !idSet.has(l.target)) return null;
        return { source: l.source, target: l.target, weight: l.weight };
      })
      .filter(Boolean);

    simulation = d3
      .forceSimulation(simNodes)
      .force(
        'link',
        d3
          .forceLink(simLinks)
          .id((d) => d.id)
          .strength((d) => 0.12 + 0.02 * Math.min(d.weight, 20))
      )
      .force('charge', d3.forceManyBody().strength(-120))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius((d) => 8 + Math.sqrt(d.count || 1) * 2));

    const svg = d3.select(el).selectAll('svg').data([null]).join('svg').attr('width', width).attr('height', height);

    const g = svg.selectAll('g.main').data([null]).join('g').attr('class', 'main');

    const link = g
      .selectAll('line')
      .data(simLinks)
      .join('line')
      .attr('stroke', atlasColors.border)
      .attr('stroke-opacity', 0.55)
      .attr('stroke-width', (d) => 0.5 + Math.min(d.weight, 12) * 0.15);

    const node = g
      .selectAll('circle')
      .data(simNodes)
      .join('circle')
      .attr('r', (d) => 4 + Math.sqrt(d.count || 1) * 1.8)
      .attr('fill', atlasColors.accent)
      .attr('fill-opacity', 0.75)
      .call(
        d3
          .drag()
          .on('start', (ev, d) => {
            if (!ev.active) simulation.alphaTarget(0.35).restart();
            d.fx = d.x;
            d.fy = d.y;
          })
          .on('drag', (ev, d) => {
            d.fx = ev.x;
            d.fy = ev.y;
          })
          .on('end', (ev, d) => {
            if (!ev.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
          })
      );

    const label = g
      .selectAll('text.lbl')
      .data(simNodes)
      .join('text')
      .attr('class', 'lbl')
      .text((d) => {
        const id = String(d.id ?? '');
        return id.length > 18 ? `${id.slice(0, 16)}…` : id;
      })
      .attr('font-size', 9)
      .attr('fill', atlasColors.muted)
      .attr('pointer-events', 'none');

    simulation.on('tick', () => {
      link
        .attr('x1', (d) => (d.source && d.source.x != null ? d.source.x : 0))
        .attr('y1', (d) => (d.source && d.source.y != null ? d.source.y : 0))
        .attr('x2', (d) => (d.target && d.target.x != null ? d.target.x : 0))
        .attr('y2', (d) => (d.target && d.target.y != null ? d.target.y : 0));
      node.attr('cx', (d) => d.x ?? 0).attr('cy', (d) => d.y ?? 0);
      label.attr('x', (d) => (d.x ?? 0) + 6).attr('y', (d) => (d.y ?? 0) + 3);
    });
    } catch (err) {
      console.error('AtlasSemantic chart error', err);
      d3.select(el).selectAll('*').remove();
      d3.select(el)
        .append('svg')
        .attr('width', width)
        .attr('height', height)
        .append('text')
        .attr('x', width / 2)
        .attr('y', height / 2)
        .attr('text-anchor', 'middle')
        .attr('fill', atlasColors.destructive)
        .attr('font-size', 12)
        .text('Chart error (see console)');
    }

    return () => {
      if (simulation) simulation.stop();
    };
  }, [graph]);

  return (
    <div className="atlas-semantic-split">
      <div ref={svgRef} className="atlas-viz-host atlas-semantic-force" />
      <div className="atlas-ticker" aria-live="polite">
        {tickerText.map((line, i) => (
          <p key={`${i}-${String(line).slice(0, 24)}`} className="atlas-ticker-line">
            {line}
          </p>
        ))}
      </div>
    </div>
  );
}
