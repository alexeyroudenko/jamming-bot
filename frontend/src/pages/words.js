//
// https://github.com/vasturiano/3d-force-graph/blob/master/example/auto-colored/index.html
//
import { ForceGraph3D } from 'react-force-graph';
import React, { useState, useEffect } from 'react';
import '../App.css';

const Words = () => {
  const [data, setData] = useState({ nodes: [{ id: 0 }], links: [] });

  useEffect(() => {
    setInterval(() => {
      setData(({ nodes, links }) => {
        const id = nodes.length;
        return {
          nodes: [...nodes, { id }],
          links: [...links, { source: id, target: Math.round(Math.random() * (id - 1)) }]
        };
      });
    }, 200);
  }, []);

  return (
    <div className="Graph3d">
      <ForceGraph3D
        graphData={data}
        backgroundColor="#000000"
        nodeColor={() => 'white'} // Устанавливаем цвет узлов в белый
        linkColor="#FFFFFF"
        linkWidth={1}
      />
    </div>
  );
};

export default Words;
