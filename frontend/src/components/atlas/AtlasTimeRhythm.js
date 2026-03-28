import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';
import { atlasColors, statusColor } from './atlasTheme';

const M = { top: 24, right: 16, bottom: 32, left: 48 };

/**
 * @param {{ steps: Array<{ _n?: number, _ts?: number, text_length?: number, status_num?: number }> }} props
 */
export default function AtlasTimeRhythm({ steps }) {
  const ref = useRef(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const width = el.clientWidth || 800;
    const height = 220;
    const innerW = width - M.left - M.right;
    const innerH = height - M.top - M.bottom;

    const data = (steps || []).filter((d) => Number.isFinite(d._n));
    const withTs = data.filter((d) => Number.isFinite(d._ts));
    const useTime = withTs.length > data.length * 0.35;
    const series = useTime ? withTs : data;

    if (!series.length) {
      d3.select(el).selectAll('*').remove();
      d3.select(el)
        .append('svg')
        .attr('width', width)
        .attr('height', height)
        .append('text')
        .attr('x', width / 2)
        .attr('y', height / 2)
        .attr('text-anchor', 'middle')
        .attr('fill', atlasColors.muted)
        .attr('font-family', 'system-ui, sans-serif')
        .attr('font-size', 13)
        .text('No steps yet');
      return;
    }

    const x = useTime
      ? d3
          .scaleTime()
          .domain(d3.extent(series, (d) => new Date(d._ts)))
          .range([0, innerW])
      : d3
          .scaleLinear()
          .domain(d3.extent(series, (d) => d._n))
          .range([0, innerW]);

    const maxLen = d3.max(series, (d) => d.text_length) || 1;
    const y = d3
      .scaleLinear()
      .domain([0, maxLen])
      .nice()
      .range([innerH, 0]);

    const svg = d3
      .select(el)
      .selectAll('svg')
      .data([null])
      .join('svg')
      .attr('width', width)
      .attr('height', height);

    const g = svg
      .selectAll('g.root')
      .data([null])
      .join('g')
      .attr('class', 'root')
      .attr('transform', `translate(${M.left},${M.top})`);

    g.selectAll('rect.bar')
      .data(series, (d) => d._n)
      .join('rect')
      .attr('class', 'bar')
      .attr('x', (d) => {
        const v = useTime ? new Date(d._ts) : d._n;
        const px = x(v);
        const wBand = innerW / Math.max(series.length, 1);
        return px - wBand * 0.2;
      })
      .attr('width', () => Math.max(1, innerW / Math.max(series.length, 1) * 0.35))
      .attr('y', (d) => y(d.text_length))
      .attr('height', (d) => innerH - y(d.text_length))
      .attr('rx', 1)
      .attr('fill', (d) => statusColor(d.status_num))
      .attr('opacity', 0.85);

    const xAxis = g.selectAll('g.x-axis').data([null]).join('g').attr('class', 'x-axis').attr('transform', `translate(0,${innerH})`);

    if (useTime) {
      xAxis.call(d3.axisBottom(x).ticks(Math.min(8, series.length)).tickFormat(d3.timeFormat('%H:%M')));
    } else {
      xAxis.call(d3.axisBottom(x).ticks(6).tickFormat(d3.format('d')));
    }
    xAxis.selectAll('text').attr('fill', atlasColors.muted).attr('font-size', 11);
    xAxis.selectAll('path,line').attr('stroke', atlasColors.border);

    const yAxis = g.selectAll('g.y-axis').data([null]).join('g').attr('class', 'y-axis');
    yAxis.call(d3.axisLeft(y).ticks(4));
    yAxis.selectAll('text').attr('fill', atlasColors.muted).attr('font-size', 11);
    yAxis.selectAll('path,line').attr('stroke', atlasColors.border);

    g.selectAll('text ylab')
      .data([null])
      .join('text')
      .attr('class', 'ylab')
      .attr('transform', 'rotate(-90)')
      .attr('x', -innerH / 2)
      .attr('y', -38)
      .attr('text-anchor', 'middle')
      .attr('fill', atlasColors.muted)
      .attr('font-size', 11)
      .attr('font-family', 'system-ui, sans-serif')
      .text('text length');

    g.selectAll('text xlab')
      .data([null])
      .join('text')
      .attr('class', 'xlab')
      .attr('x', innerW / 2)
      .attr('y', innerH + 42)
      .attr('text-anchor', 'middle')
      .attr('fill', atlasColors.muted)
      .attr('font-size', 11)
      .attr('font-family', 'system-ui, sans-serif')
      .text(useTime ? 'time' : 'step #');
  }, [steps]);

  return <div ref={ref} className="atlas-viz-host" />;
}
