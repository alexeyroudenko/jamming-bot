#!/usr/bin/env node
/**
 * Build graph-data.json from deployment.yaml + services-map/topology.json.
 * Usage: node scripts/generate-services-graph.mjs [deployment.yaml] [topology.json] [out.json]
 */
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { createRequire } from 'node:module'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const repoRoot = path.resolve(__dirname, '..')
const require = createRequire(path.join(repoRoot, 'services-map/package.json'))
const yaml = require('yaml')

const deploymentPath = path.resolve(repoRoot, process.argv[2] ?? 'deployment.yaml')
const topologyPath = path.resolve(repoRoot, process.argv[3] ?? 'services-map/topology.json')
const outPath = path.resolve(
  repoRoot,
  process.argv[4] ?? 'services-map/src/generated/graph-data.json',
)

const topology = JSON.parse(fs.readFileSync(topologyPath, 'utf8'))
const nodeGroups = topology.nodeGroups ?? {}
const virtualNodes = topology.virtualNodes ?? []
const manualEdges = topology.edges ?? []
const sourceAliases = topology.sourceAliases ?? {}
const skipEnvNames = new Set(topology.skipEnvNames ?? [])

const INFRA_IDS = new Set(['redis', 'tags-db', 'jaeger', 'otel-collector'])
const OPS_SUFFIX = /-(metrics|lb|nodeport)$/

function defaultGroup(id) {
  if (nodeGroups[id]) return nodeGroups[id]
  if (INFRA_IDS.has(id)) return 'infra'
  if (OPS_SUFFIX.test(id)) return 'ops'
  return 'services'
}

function resolveSource(deploymentName) {
  return sourceAliases[deploymentName] ?? deploymentName
}

/** @param {string} envName @param {string} raw */
function extractTargets(envName, raw) {
  if (!raw || typeof raw !== 'string') return []
  const targets = []
  const trimmed = raw.trim()

  if (envName === 'S3_HOST' && trimmed && !trimmed.includes(' ')) {
    return ['external-s3']
  }

  const urlMatch = trimmed.match(/^https?:\/\/([^/:]+)(?::\d+)?/i)
  if (urlMatch) targets.push(urlMatch[1])

  const redisUrl = trimmed.match(/^redis:\/\/([^/:]+)/i)
  if (redisUrl) targets.push(redisUrl[1])

  if (
    envName.endsWith('_HOST') ||
    envName === 'REDIS_HOST' ||
    envName === 'RQ_REDIS_HOST' ||
    envName === 'FLASK_HOST'
  ) {
    if (!trimmed.includes('/') && !trimmed.includes(' ')) {
      targets.push(trimmed)
    }
  }

  return [...new Set(targets)]
}

function envValue(entry) {
  if (entry?.value != null) return String(entry.value)
  return null
}

const docs = yaml.parseAllDocuments(fs.readFileSync(deploymentPath, 'utf8')).map((d) => d.toJS())

const serviceIds = new Set()
const servicePorts = new Map()

for (const doc of docs) {
  if (doc?.kind !== 'Service') continue
  const ns = doc.metadata?.namespace
  if (ns && ns !== 'jamming-bot') continue
  const name = doc.metadata?.name
  if (!name) continue
  serviceIds.add(name)
  const port = doc.spec?.ports?.[0]?.port
  if (port != null) servicePorts.set(name, port)
}

const nodes = [...serviceIds]
  .sort()
  .map((id) => ({
    id,
    label: id,
    group: defaultGroup(id),
    port: servicePorts.get(id),
    kind: 'service',
  }))

const nodeIdSet = new Set(nodes.map((n) => n.id))

for (const vn of virtualNodes) {
  if (!vn.id) continue
  if (!nodeIdSet.has(vn.id)) {
    nodes.push({
      id: vn.id,
      label: vn.label ?? vn.id,
      group: vn.group ?? defaultGroup(vn.id),
      kind: 'virtual',
    })
    nodeIdSet.add(vn.id)
  }
}

const edgeKey = (s, t, label) => `${s}\0${t}\0${label ?? ''}`
const edgesMap = new Map()

function ensureSourceNode(id) {
  if (nodeIdSet.has(id)) return
  const known = virtualNodes.find((v) => v.id === id)
  nodes.push({
    id,
    label: known?.label ?? id,
    group: known?.group ?? 'workers',
    kind: 'virtual',
  })
  nodeIdSet.add(id)
}

function addEdge(source, target, label, origin) {
  const src = resolveSource(source)
  if (!nodeIdSet.has(target)) return
  if (!nodeIdSet.has(src)) ensureSourceNode(src)
  if (src === target) return
  const key = edgeKey(src, target, label)
  if (!edgesMap.has(key)) {
    edgesMap.set(key, { source: src, target, label: label ?? '', origin })
  }
}

for (const doc of docs) {
  if (doc?.kind !== 'Deployment' && doc?.kind !== 'Job') continue
  const ns = doc.metadata?.namespace
  if (ns && ns !== 'jamming-bot') continue
  const deploymentName = doc.metadata?.name
  if (!deploymentName) continue

  const containers = doc.spec?.template?.spec?.containers ?? []
  for (const container of containers) {
    for (const entry of container.env ?? []) {
      const name = entry?.name
      if (!name || skipEnvNames.has(name)) continue
      const raw = envValue(entry)
      if (raw == null) continue

      const shouldParse =
        name.endsWith('_SERVICE_URL') ||
        name.endsWith('_HOST') ||
        name === 'REDIS_URL' ||
        name === 'OTEL_EXPORTER_OTLP_ENDPOINT' ||
        name === 'APP_SERVICE_URL'

      if (!shouldParse) continue

      for (const target of extractTargets(name, raw)) {
        addEdge(deploymentName, target, `${deploymentName}: ${name}`, 'env')
      }
    }
  }
}

for (const e of manualEdges) {
  if (!e.source || !e.target) continue
  if (!nodeIdSet.has(e.target)) continue
  if (!nodeIdSet.has(e.source)) {
    nodes.push({
      id: e.source,
      label: e.source,
      group: 'edge',
      kind: 'virtual',
    })
    nodeIdSet.add(e.source)
  }
  addEdge(e.source, e.target, e.label ?? '', 'topology')
}

const links = [...edgesMap.values()].map((e) => ({
  source: e.source,
  target: e.target,
  label: e.label,
  origin: e.origin,
}))

const payload = {
  generatedAt: new Date().toISOString(),
  deploymentFile: path.basename(deploymentPath),
  nodes,
  links,
  groups: ['edge', 'core', 'workers', 'services', 'infra', 'ops', 'external'],
}

fs.mkdirSync(path.dirname(outPath), { recursive: true })
fs.writeFileSync(outPath, JSON.stringify(payload, null, 2) + '\n')
console.log(`Wrote ${nodes.length} nodes, ${links.length} links → ${outPath}`)
