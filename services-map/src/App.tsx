import { useCallback, useMemo, useState } from 'react'
import { VisGraph } from '@unovis/react'
import { GraphLayoutType } from '@unovis/ts'
import { edgesForNode, useGraphData } from './graph/useGraphData'
import type { GraphGroup, GraphNodeDatum } from './graph/types'

const GROUP_ORDER: GraphGroup[] = [
  'edge',
  'core',
  'workers',
  'services',
  'infra',
  'ops',
  'external',
]

const GROUP_COLORS: Record<GraphGroup, string> = {
  edge: '#22d3ee',
  core: '#a78bfa',
  workers: '#fbbf24',
  services: '#4ade80',
  infra: '#38bdf8',
  ops: '#71717a',
  external: '#f87171',
}

function groupIndex(group: GraphGroup): number {
  const i = GROUP_ORDER.indexOf(group)
  return i >= 0 ? i : GROUP_ORDER.length - 1
}

export default function App() {
  const [hideOps, setHideOps] = useState(true)
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const { generatedAt, deploymentFile, nodes, links, groupLabels } =
    useGraphData(hideOps)

  const selectedNode = useMemo(
    () => nodes.find((n) => n.id === selectedId) ?? null,
    [nodes, selectedId],
  )

  const selectionEdges = useMemo(
    () => (selectedId ? edgesForNode(selectedId, links) : null),
    [selectedId, links],
  )

  const layoutNodeGroup = useCallback(
    (d: GraphNodeDatum) => String(groupIndex(d.group)),
    [],
  )

  const layoutParallelNodeSubGroup = useCallback(
    (d: GraphNodeDatum) => d.subGroup ?? 'service',
    [],
  )

  const nodeFill = useCallback((d: GraphNodeDatum) => GROUP_COLORS[d.group], [])
  const nodeLabel = useCallback((d: GraphNodeDatum) => d.label, [])

  return (
    <div className="app">
      <header className="app-header">
        <div>
          <h1>Jamming Bot — Service Map</h1>
          <p className="meta">
            from {deploymentFile} · {nodes.length} nodes · {links.length} edges
          </p>
        </div>
        <p className="meta">
          generated {new Date(generatedAt).toLocaleString()}
        </p>
      </header>

      <aside className="sidebar">
        <div className="sidebar-controls">
          <label>
            <input
              type="checkbox"
              checked={hideOps}
              onChange={(e) => setHideOps(e.target.checked)}
            />
            Hide ops / metrics services
          </label>
        </div>
        <ul className="service-list" role="listbox" aria-label="Services">
          {nodes.map((n) => (
            <li key={n.id}>
              <button
                type="button"
                className={selectedId === n.id ? 'selected' : ''}
                onClick={() => setSelectedId(n.id)}
                role="option"
                aria-selected={selectedId === n.id}
              >
                {n.label}
                <span className="group-tag">{n.group}</span>
              </button>
            </li>
          ))}
        </ul>
      </aside>

      <main className="graph-panel">
        <div className="graph-container">
          <VisGraph
            data={{ nodes, links }}
            layoutType={GraphLayoutType.Parallel}
            layoutNodeGroup={layoutNodeGroup}
            layoutParallelNodeSubGroup={layoutParallelNodeSubGroup}
            layoutParallelNodesPerColumn={8}
            nodeFill={nodeFill}
            nodeStroke={() => 'rgba(255,255,255,0.35)'}
            nodeLabel={nodeLabel}
            nodeSize={28}
            linkFlow={true}
            linkBandWidth={1.5}
          />
        </div>

        {selectedNode && selectionEdges && (
          <aside className="detail-panel" aria-live="polite">
            <h2>{selectedNode.label}</h2>
            <p>
              group: <strong>{selectedNode.group}</strong>
              {selectedNode.port != null && (
                <>
                  {' '}
                  · port {selectedNode.port}
                </>
              )}
              {selectedNode.kind === 'virtual' && <> · virtual node</>}
            </p>
            <h3>Incoming ({selectionEdges.incoming.length})</h3>
            <ul>
              {selectionEdges.incoming.length === 0 && <li>—</li>}
              {selectionEdges.incoming.map((e, i) => (
                <li key={`in-${i}`}>
                  {e.source} — {e.label || e.origin}
                </li>
              ))}
            </ul>
            <h3>Outgoing ({selectionEdges.outgoing.length})</h3>
            <ul>
              {selectionEdges.outgoing.length === 0 && <li>—</li>}
              {selectionEdges.outgoing.map((e, i) => (
                <li key={`out-${i}`}>
                  → {e.target} — {e.label || e.origin}
                </li>
              ))}
            </ul>
          </aside>
        )}
      </main>

      <div className="legend">
        {GROUP_ORDER.filter((g) => !hideOps || g !== 'ops').map((g) => (
          <span key={g}>
            <span className="dot" style={{ background: GROUP_COLORS[g] }} />
            {groupLabels[g]}
          </span>
        ))}
      </div>

      <footer className="app-footer">
        Declared topology from Kubernetes env +{' '}
        <code>services-map/topology.json</code> — not live traffic.{' '}
        <a
          href="https://coroot.jamming-bot.arthew0.online/"
          target="_blank"
          rel="noreferrer"
        >
          Coroot
        </a>{' '}
        for runtime service map.
      </footer>
    </div>
  )
}
