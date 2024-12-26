//
// https://github.com/vasturiano/3d-force-graph/blob/master/example/auto-colored/index.html
//
import { ForceGraph3D } from 'react-force-graph';
import * as THREE from 'three';
import React, { useState, useEffect } from 'react';

import io from "socket.io-client"
import { Url } from '../constants'
import '../App.css';

export const socket = io(Url, { transports: ["websocket", "polling"] })


const Words = () => {
  const [data, setData] = useState({ nodes: [{ id: 0 }], links: [] });
    
  useEffect(() => {

    // setInterval(() => {
    //   setData(({ nodes, links }) => {
    //     const id = nodes.length;
    //     return {
    //       nodes: [...nodes, { id }],
    //       links: [...links, { source: id, target: Math.round(Math.random() * (id - 1)) }]
    //     };
    //   });
    // }, 1000);

    let counter = 0
    let start_time = 0    
    let latency = 0
    let startStep = 0
    let started = 0

    socket.on("connect", () => {
        socket.emit('consumer')
        console.log("connected to socket", socket.id)
        window.setInterval(function () {
          start_time = (new Date).getTime();          
          socket.emit('my_ping');
        }, 250);

    });

    socket.on("connect_error", (err) => { console.log(err) });
    socket.on("disconnect", () => {console.log("Disconnected from socket. v1.0")});
    socket.on("my_pong", (msg) => {
      latency = (new Date).getTime() - start_time; 
      counter = counter + 1            
    });
    socket.on("step", (msg) => {       
      const data = msg

      let step = parseInt(data['step'])
      if (started === 0) {
          startStep = step;
          started = 1;
      }
            
      let url = data['url'];
      let from_url = data['src_url'];    
      let struct_text = data['struct_text']
      let text = data['text']
      let words = data['words']
      
      
      setData(({ nodes, links }) => {
        const id = nodes.length;
        return {
          nodes: [...nodes, { id, name: `Node ${url}` }],
          links: [...links, { source: id, target: Math.round(Math.random() * (id - 1)) }]
        };
      });

      
      //console.log('step: ', step, url);
    });

  }, []);

  const createNodeLabel = (node) => {
    const group = new THREE.Group();
    const circleGeometry = new THREE.SphereGeometry(3, 16, 16);
    const circleMaterial = new THREE.MeshBasicMaterial({ color: 'white' });
    const circle = new THREE.Mesh(circleGeometry, circleMaterial);
    group.add(circle);

    const sprite = new THREE.Sprite(
      new THREE.SpriteMaterial({
        map: new THREE.CanvasTexture(generateTextCanvas(node.name || node.id)),
        depthTest: false
      })
    );
    sprite.scale.set(256/4, 64/4, 1); // Размер текстового поля
    sprite.position.set(0, 6, 0); // Расположение текста над кружочком
    group.add(sprite);

    return group;
  };

  const generateTextCanvas = (text) => {
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d');
    const fontSize = 14;

    canvas.width = 256;
    canvas.height = 64;

    context.font = `${fontSize}px Verdana`;
    context.fillStyle = 'white';
    context.textAlign = 'center';
    context.textBaseline = 'middle';
    context.fillText(text, canvas.width / 2, canvas.height / 2);

    return canvas;
  };  

  return (
    <div className="Graph3d">
      <ForceGraph3D
        graphData={data}
        backgroundColor="#000000"
        nodeColor={() => 'white'} // Устанавливаем цвет узлов в белый
        linkColor="#FFFFFF"
        linkWidth={1}
        nodeThreeObject={createNodeLabel}
      />
    </div>
  );
};

export default Words;
