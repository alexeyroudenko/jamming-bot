import React, { useEffect, useMemo, useRef, useState } from 'react';
import * as d3 from 'd3';
import { buildUrlHierarchyRoot } from '../../lib/atlas/buildSunburstTree';
import { atlasColors } from './atlasTheme';

const RADIUS = 168;

/**
 * @param {{ steps: object[] }} props
 */
export default function AtlasSunburst({ steps }) {
  const ref = useRef(null);
  const [focusData, setFocusData] = useState(null);
  const treeData = useMemo(() => buildUrlHierarchyRoot(steps || []), [steps]);

  useEffect(() => {
    setFocusData(null);
  }, [treeData]);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const width = el.clientWidth || 520;
    const height = Math.min(420, RADIUS * 2 + 48);

    d3.select(el).selectAll('*').remove();

    try {
      const fullRoot = d3
        .hierarchy(treeData)
        .sum((d) => d.value || 0)
        .sort((a, b) => (b.value || 0) - (a.value || 0));

      if (!fullRoot.children || fullRoot.children.length === 0) {
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
          .text('No URL paths');
        return;
      }

      const activeRoot = focusData
        ? d3
            .hierarchy(focusData)
            .sum((d) => d.value || 0)
            .sort((a, b) => (b.value || 0) - (a.value || 0))
        : fullRoot;

      const partition = d3.partition().size([2 * Math.PI, activeRoot.height + 1]);
      partition(activeRoot);

      const arc = d3
        .arc()
        .startAngle((d) => d.x0)
        .endAngle((d) => d.x1)
        .padAngle((d) => Math.min((d.x1 - d.x0) / 2, 0.02))
        .innerRadius((d) => d.y0 * RADIUS)
        .outerRadius((d) => Math.max(d.y0 * RADIUS, d.y1 * RADIUS - 1));

      const color = d3.scaleOrdinal(d3.schemeTableau10);

      const svg = d3
        .select(el)
        .append('svg')
        .attr('width', width)
        .attr('height', height)
        .attr('viewBox', [-width / 2, -height / 2, width, height].join(' '));

      const g = svg.append('g');

      const nodes = activeRoot.descendants().filter((d) => d.depth && (d.y0 * RADIUS) < RADIUS - 2);

      const path = g
        .selectAll('path')
        .data(nodes)
        .join('path')
        .attr('fill', (d) => color(String(d.data.name ?? '')))
        .attr('fill-opacity', (d) => (d.children ? 0.5 : 0.88))
        .attr('stroke', atlasColors.border)
        .attr('d', arc)
        .style('cursor', (d) => (d.children ? 'pointer' : 'default'))
        .on('click', (ev, d) => {
          ev.stopPropagation();
          if (d.children) setFocusData(d.data);
        });

      path
        .append('title')
        .text((d) => `${String(d.data.name ?? '')}\n${d.value ?? ''}`);
    } catch (err) {
      console.error('AtlasSunburst chart error', err);
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
        .text('Sunburst error (see console)');
    }

    return () => {
      d3.select(el).selectAll('*').remove();
    };
  }, [treeData, focusData]);

  return (
    <div className="atlas-sunburst-wrap">
      <div className="atlas-sunburst-toolbar">
        {focusData ? (
          <button type="button" className="atlas-btn-ghost" onClick={() => setFocusData(null)}>
            Reset view
          </button>
        ) : (
          <span className="atlas-sunburst-hint">Click a ring segment with children to zoom.</span>
        )}
      </div>
      <div ref={ref} className="atlas-viz-host atlas-sunburst-host" />
    </div>
  );
}
