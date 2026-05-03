import React from 'react'
import { tagsEmbedUrl } from '../constants'
import '../App.css'

/**
 * Same layout as pages/graph.js: legacy shell + full-size iframe to tag UI.
 * @param {{ title: string, path: string }} props
 */
export default function TagEmbedPage({ title, path }) {
  const src = tagsEmbedUrl(path)
  return (
    <div className="legacy" style={{ width: '100%', height: '100%' }}>
      <h1>{title}</h1>
      <iframe
        style={{ width: '100%', height: '100%', border: '0' }}
        src={src}
        title={title}
        loading="lazy"
      />
    </div>
  )
}
