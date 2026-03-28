//
// https://github.com/vasturiano/3d-force-graph/blob/master/example/auto-colored/index.html
//
import { ForceGraph3D } from 'react-force-graph';
import * as THREE from 'three';
import React, { useState, useEffect, useRef } from 'react';

import io from "socket.io-client"
import { Url } from '../constants'
import '../App.css';

export const socket = io(Url, { transports: ["websocket", "polling"] });

let rotationSpeed = .6; // Скорость вращения камеры
let count = 0;
let angle = 0;

const Words = () => {

  const [data, setData] = useState({ nodes: [{ id: 0 }], links: [] });
  const graphRef = useRef();
  const baseRotation = 0.001;


  // useEffect(() => {
  //   console.log("begin");
  //   setInterval(() => {
  //     setData(({ tags }) => {
  //       const id = 1
  //       fetch(Url + "/api/v1/tags/tags/group/")
  //           .then((res) => res.json())
  //           // .then((result) => {
  //           // //     console.log("firstRequest result:");                
  //           // //     const id = tags.length;
  //           // //     count = count + 1;
  //           // //     if (count % 7 === 6) {
  //           // //       rotationSpeed += 1.0
  //           // //     }
  //           //     };
  //       return () => {
  //         tags: [...tags, { source: id, name: Math.round(Math.random() * (id - 1)),  count: 25}]
  //             };
  //       });
  //       }, 10000);
  // }, []);


  useEffect(() => {
    const handleResize = () => {
      if (graphRef.current) {
        const graph = graphRef.current;
        graph.renderer().setSize(window.innerWidth, window.innerHeight);
        graph.camera().aspect = window.innerWidth / window.innerHeight;
        graph.camera().updateProjectionMatrix();
      }
    };
    window.addEventListener('resize', handleResize);
    handleResize();
    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, []);

  useEffect(() => {
    let animationFrameId;
    const animateCamera = () => {      
      if (graphRef.current) {
        rotationSpeed = rotationSpeed * 0.94; // / count;         
        const distance = 300; // Радиус вращения камеры
        angle = angle + rotationSpeed * 0.1 + baseRotation;
        const camera = graphRef.current.camera();
        camera.position.x = Math.sin(angle) * distance;
        camera.position.z = Math.cos(angle) * distance;
        camera.lookAt(0, 0, 0); // Фокусируем камеру на центре графа
        camera.updateProjectionMatrix();
      }

      animationFrameId = requestAnimationFrame(animateCamera);
    };
    animateCamera();
    return () => cancelAnimationFrame(animationFrameId); // Очищаем анимацию при размонтировании
  }, []);





  useEffect(() => {

    // setInterval(() => {
    //   setData(({ nodes, links }) => {
    //     const id = nodes.length;
    //     count = count + 1;
    //     if (count % 7 === 6) {
    //       rotationSpeed += 1.0
    //     }
    //     return {
    //       nodes: [...nodes, { id }],
    //       links: [...links, { source: id, target: Math.round(Math.random() * (id - 1)) }]
    //     };
    //   });
    // }, 2000);

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


      let semantic_words = data['semantic_words']      
      console.log("semantic_words", semantic_words)      
      if (msg['semantic_words']) {
        count = count + 1;
        if (count % 7 === 6) {
          rotationSpeed += .3
        }
        msg['semantic_words'].slice(0, 5).forEach (
          (element) => { 
            console.log(element);
            let text = element;
            setData(({ nodes, links }) => {
              const id = nodes.length;
              return {
                nodes: [...nodes, { id, name: `${text}` }],
                links: [...links, { source: id, target: Math.round(Math.random() * (id - 1)) }]
              };
            });            
          }
        );
      }




      // setData(({ nodes, links }) => {
      //   const id = nodes.length;
      //   return {
      //     nodes: [...nodes, { id, name: `${step} ${url}` }],
      //     links: [...links, { source: id, target: Math.round(Math.random() * (id - 1)) }]
      //   };
      // });
      console.log('step: ', step, url);
    });

  }, []);

  const createLineMaterial = () => {
    return new THREE.ShaderMaterial({
      uniforms: {
        resolution: { value: new THREE.Vector2(window.innerWidth, window.innerHeight) },
        color: { value: new THREE.Color(0x999999) }
      },
      vertexShader: `
        uniform vec2 resolution;
        void main() {
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
      `,
      fragmentShader: `
        uniform vec3 color;
        void main() {
          gl_FragColor = vec4(color, 1.0);
        }
      `,
      linewidth: 1 // Это игнорируется в WebGL (для информации)
    });
  };

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
  
  // const [tagData, setTagData] = useState({ tags: [{ name: 0, count: 0 }] });
  
  // useEffect(() => {
  //   setInterval(() => {
  //     const url = "http://localhost:8080/api/v1/tags/tags/group/"
  //     console.log("first request", url)
  //     fetch(url)        
  //     .then((res) => res.json())
  //       .then((result) => {            
  //           var tags = []                
  //           result.forEach((tag) => {
  //             let new_tag = {"name": tag.name, "count": tag.count}
  //             tags.push(new_tag)
  //             console.log("------------------------ ", new_tag)                      
  //           })
  //           this.setTagData(tags);          
  //         })
  //     }, 10000);
  // });

  return (
    <div className="Graph3d" style={{ width: '100%', height: '100%' }}>
      <ForceGraph3D
        ref={graphRef}
        graphData={data}
        backgroundColor="#000000"
        nodeColor={() => 'white'} // Устанавливаем цвет узлов в белый
        nodeThreeObject={createNodeLabel}
        linkThreeObjectExtend={true} // Используем кастомный объект
        linkThreeObject={() => {
          const geometry = new THREE.BufferGeometry();
          const material = createLineMaterial();
          return new THREE.Line(geometry, material);
        }}
      />

    </div>

  );
};

export default Words;
