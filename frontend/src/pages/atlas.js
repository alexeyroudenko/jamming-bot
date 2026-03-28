import React from 'react';
import { useStepsDataset } from '../lib/atlas/useStepsDataset';
import AtlasErrorBoundary from '../components/atlas/AtlasErrorBoundary';
import AtlasTimeRhythm from '../components/atlas/AtlasTimeRhythm';
import AtlasSemantic from '../components/atlas/AtlasSemantic';
import AtlasSankey from '../components/atlas/AtlasSankey';
import AtlasSunburst from '../components/atlas/AtlasSunburst';
import AtlasStatusGrid from '../components/atlas/AtlasStatusGrid';
import AtlasAggregates from '../components/atlas/AtlasAggregates';
import './atlas.css';

export default function AtlasPage() {
  const { loading, error, source, notice, steps } = useStepsDataset();

  return (
    <div className="atlas-page">
      <h1>Data Atlas</h1>
      <p className="atlas-lead">
        Live views of crawl steps: rhythm, language tokens, navigation structure, HTTP health, and
        quick aggregates.
      </p>

      {loading && <div className="atlas-banner">Loading step history…</div>}
      {error && <div className="atlas-banner atlas-banner--err">Could not load data: {error}</div>}
      {notice && !loading && <div className="atlas-banner atlas-banner--warn">{notice}</div>}

      <section className="atlas-section">
        <h2>Time and rhythm</h2>
        <p className="atlas-desc">Bar height = text length; color = HTTP status. X = time when timestamps exist, else step index.</p>
        <AtlasErrorBoundary key={`t-${source}-${steps.length}`} label="Time and rhythm">
          <AtlasTimeRhythm steps={steps} />
        </AtlasErrorBoundary>
      </section>

      <section className="atlas-section">
        <h2>Text and semantics</h2>
        <p className="atlas-desc">2D co-occurrence of tokens from recent steps; ticker shows latest phrases or text snippets.</p>
        <AtlasErrorBoundary key={`s-${source}-${steps.length}`} label="Semantics">
          <AtlasSemantic steps={steps} />
        </AtlasErrorBoundary>
      </section>

      <section className="atlas-section">
        <h2>Graph and navigation</h2>
        <p className="atlas-desc">Sankey: host-to-host transitions. Sunburst: hostname → path segments (visit counts).</p>
        <h3 className="atlas-card-title" style={{ marginTop: '0.5rem' }}>
          Host flow
        </h3>
        <AtlasErrorBoundary key={`k-${source}-${steps.length}`} label="Sankey (host flow)">
          <AtlasSankey steps={steps} />
        </AtlasErrorBoundary>
        <h3 className="atlas-card-title" style={{ marginTop: '1.25rem' }}>
          URL paths
        </h3>
        <AtlasErrorBoundary key={`u-${source}-${steps.length}`} label="Sunburst (URL paths)">
          <AtlasSunburst steps={steps} />
        </AtlasErrorBoundary>
      </section>

      <section className="atlas-section">
        <h2>Statuses and failures</h2>
        <p className="atlas-desc">One column per step (recent window); outline marks non-empty error field.</p>
        <AtlasErrorBoundary key={`g-${source}-${steps.length}`} label="Status grid">
          <AtlasStatusGrid steps={steps} />
        </AtlasErrorBoundary>
      </section>

      <section className="atlas-section">
        <h2>Aggregates</h2>
        <p className="atlas-desc">Histogram of text length, top tokens, status code counts (debounced).</p>
        <AtlasErrorBoundary key={`a-${source}-${steps.length}`} label="Aggregates">
          <AtlasAggregates steps={steps} />
        </AtlasErrorBoundary>
      </section>

      <p className="atlas-meta">
        Source: <code>{source}</code> · steps in view: {steps.length}
      </p>
    </div>
  );
}
