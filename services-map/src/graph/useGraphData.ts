import { useMemo } from 'react'
import raw from '../generated/graph-data.json'
import type { GraphDataJson, GraphGroup, GraphLinkDatum, GraphNodeDatum } from './types'

const GROUP_ORDER: GraphGroup[] = [
  'edge',
  'core',
  'workers',
  'services',
  'infra',
  'ops',
  'external',
]

const GROUP_LABELS: Record<GraphGroup, string> = {
  edge: 'Ingress / edge',
  core: 'Core',
  workers: 'Workers',
  services: 'Microservices',
  infra: 'Infrastructure',
  ops: 'Ops / metrics',
  external: 'External',
}

export function useGraphData(hideOps: boolean) {
  const data = raw as GraphDataJson

  return useMemo(() => {
    const visibleIds = new Set(
      data.nodes
        .filter((n) => !(hideOps && n.group === 'ops'))
        .map((n) => n.id),
    )

    const nodes: GraphNodeDatum[] = data.nodes
      .filter((n) => visibleIds.has(n.id))
      .map((n) => ({
        ...n,
        subGroup: n.kind === 'virtual' ? 'virtual' : 'service',
      }))

    const links: GraphLinkDatum[] = data.links.filter(
      (l) => visibleIds.has(l.source) && visibleIds.has(l.target),
    )

    return {
      generatedAt: data.generatedAt,
      deploymentFile: data.deploymentFile,
      nodes,
      links,
      groupOrder: GROUP_ORDER,
      groupLabels: GROUP_LABELS,
    }
  }, [data, hideOps])
}

export function edgesForNode(
  nodeId: string,
  links: GraphLinkDatum[],
): { incoming: GraphLinkDatum[]; outgoing: GraphLinkDatum[] } {
  return {
    incoming: links.filter((l) => l.target === nodeId),
    outgoing: links.filter((l) => l.source === nodeId),
  }
}
