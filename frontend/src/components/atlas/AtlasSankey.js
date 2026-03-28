import React, { useEffect, useMemo, useRef } from 'react';
import * as d3 from 'd3';
import { sankey, sankeyLinkHorizontal } from 'd3-sankey';
import { aggregateHostFlows } from '../../lib/atlas/aggregateSankey';
import { atlasColors } from './atlasTheme';

const M = { top: 8, right: 12, bottom: 8, left: 12 };

/**
 * @param {{ steps: object[] }} props
 */
export default function AtlasSankey({ steps }) {
  const ref = useRef(null);
  const graph = useMemo(() => aggregateHostFlows(steps || [], { maxNodes: 34 }), [steps]);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const width = el.clientWidth || 800;
    const height = 280;
    d3.select(el).selectAll('*').remove();

    if (!graph.links.length) {
      d3.select(el)
        .append('svg')
        .attr('width', width)
        .attr('height', height)
        .append('text')
        .attr('x', width / 2)
        .attr('y', height / 2)
        .attr('text-anchor', 'middle')
        .attr('fill', atlasColors.muted)
        .attr('font-size', 13)
        .text('No host transitions');
      return;
    }

    try {
      const sk = sankey()
        .nodeWidth(10)
        .nodePadding(10)
        .extent([
          [M.left, M.top],
          [width - M.right, height - M.bottom],
        ]);

      let workingLinks = graph.links.map((d) => ({ ...d }));
      let nodes;
      let links;
      const maxStrip = graph.links.length + 8;
      for (let guard = 0; guard < maxStrip; guard++) {
        if (!workingLinks.length) {
          d3.select(el)
            .append('svg')
            .attr('width', width)
            .attr('height', height)
            .append('text')
            .attr('x', width / 2)
            .attr('y', height / 2)
            .attr('text-anchor', 'middle')
            .attr('fill', atlasColors.muted)
            .attr('font-size', 13)
            .text('No acyclic host flow (cycles removed)');
          return;
        }
        try {
          const laid = sk({
            nodes: graph.nodes.map((d) => ({ ...d })),
            links: workingLinks.map((d) => ({ ...d })),
          });
          nodes = laid.nodes;
          links = laid.links;
          break;
        } catch (e) {
          const msg = e && e.message ? String(e.message) : '';
          if (!/circular/i.test(msg)) throw e;
          let mi = 0;
          for (let i = 1; i < workingLinks.length; i++) {
            if (workingLinks[i].value < workingLinks[mi].value) mi = i;
          }
          workingLinks.splice(mi, 1);
        }
      }
      if (!nodes || !links) {
        throw new Error('Sankey layout failed after cycle stripping');
      }

      const svg = d3.select(el).append('svg').attr('width', width).attr('height', height);

      svg
        .append('g')
        .attr('fill', 'none')
        .selectAll('path')
        .data(links)
        .join('path')
        .attr('d', sankeyLinkHorizontal())
        .attr('stroke', atlasColors.accent)
        .attr('stroke-opacity', 0.35)
        .attr('stroke-width', (d) => Math.max(1, d.width))
        .attr('stroke-linecap', 'round');

      const node = svg
        .append('g')
        .selectAll('g')
        .data(nodes)
        .join('g')
        .attr('transform', (d) => `translate(${d.x0},${d.y0})`);

      node
        .append('rect')
        .attr('height', (d) => d.y1 - d.y0)
        .attr('width', (d) => d.x1 - d.x0)
        .attr('fill', atlasColors.surface)
        .attr('stroke', atlasColors.border)
        .attr('rx', 2);

      node
        .append('text')
        .attr('x', (d) => (d.x0 < width * 0.5 ? 6 + (d.x1 - d.x0) : -6))
        .attr('y', (d) => (d.y1 - d.y0) / 2)
        .attr('dy', '0.35em')
        .attr('text-anchor', (d) => (d.x0 < width * 0.5 ? 'start' : 'end'))
        .attr('fill', atlasColors.muted)
        .attr('font-size', 10)
        .attr('font-family', 'ui-monospace, monospace')
        .text((d) => {
          const n = String(d.name ?? '');
          return n.length > 22 ? `${n.slice(0, 20)}…` : n;
        });
    } catch (err) {
      console.error('AtlasSankey chart error', err);
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
        .text('Sankey layout error (see console)');
    }

    return () => {
      d3.select(el).selectAll('*').remove();
    };
  }, [graph]);

  return <div ref={ref} className="atlas-viz-host" />;
}
