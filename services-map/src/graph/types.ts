export type GraphGroup =
  | 'edge'
  | 'core'
  | 'workers'
  | 'services'
  | 'infra'
  | 'ops'
  | 'external'

export interface GraphNodeJson {
  id: string
  label: string
  group: GraphGroup
  port?: number
  kind: 'service' | 'virtual'
}

export interface GraphLinkJson {
  source: string
  target: string
  label: string
  origin: 'env' | 'topology'
}

export interface GraphDataJson {
  generatedAt: string
  deploymentFile: string
  nodes: GraphNodeJson[]
  links: GraphLinkJson[]
  groups: GraphGroup[]
}

export interface GraphNodeDatum extends GraphNodeJson {
  subGroup?: string
}

export interface GraphLinkDatum {
  source: string
  target: string
  label: string
  origin: string
}
