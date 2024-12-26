//
// https://github.com/vasturiano/3d-force-graph/blob/master/example/auto-colored/index.html
//
import { ForceGraph3D } from 'react-force-graph';
import React, { useState, useEffect } from 'react';

const Words = () => {
  const [data, setData] = useState({ nodes: [{ id: 0 }], links: [] });

  useEffect(() => {
    setInterval(() => {
      setData(({ nodes, links }) => {
        const id = nodes.length;
        return {
          nodes: [...nodes, { id }],
          links: [...links, { source: id, target: Math.round(Math.random() * (id-1)) }]
        };
      });
    }, 1000);
  }, []);

  return (<div><h1>Hello Words</h1>
    <ForceGraph3D
      graphData={data}
      backgroundColor="#000000"
      nodeColor="#FFFFFF"      
      linkWidth={1} 
    />
  </div>);
};

export default Words;