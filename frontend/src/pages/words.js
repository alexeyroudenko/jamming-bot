import React, { Component } from "react";
import { Graph } from "react-d3-graph";

class Words extends Component {
    constructor() {
      super();
      let data = {
        nodes: [{ id: "Harry" }, { id: "Sally" }, { id: "Alice" }],
        links: [
          { source: "Harry", target: "Sally" },
          { source: "Harry", target: "Alice" }
        ]
      };
      this.state = {
        data: data
      };
    }
  
    render() {
      // the graph configuration, you only need to pass down properties
      // that you want to override, otherwise default ones will be used
      const myConfig = {
        nodeHighlightBehavior: true,
        node: {
          color: "lightgreen",
          size: 120,
          highlightStrokeColor: "blue"
        },
        link: {
          highlightColor: "lightblue"
        }
      };
      const reactRef = this;
      const onDoubleClickNode = function(nodeId) {
        let modData = { ...reactRef.state.data };
        let selectNode = modData.nodes.filter(item => {
          return item.id === nodeId;
        });
        selectNode.forEach(item => {
          if (item.color && item.color === "red") item.color = "blue";
          else item.color = "red";
        });
        reactRef.setState({ data: modData });
      };
  
      return (
        <div className="App">
          <h1>Hello CodeSandbox</h1>
          <Graph
            id="graph-id" // id is mandatory, if no id is defined rd3g will throw an error
            data={this.state.data}
            config={myConfig}
            onDoubleClickNode={onDoubleClickNode}
          />
        </div>
      );
    }
  }
  export default Words;

  

// const Words = ({ bg, setBg }) => {

//     // Graph data
//     const data = {
//         nodes: [{ id: "Harry" }, { id: "Sally" }, { id: "Alice" }],
//         links: [
//             { source: "Harry", target: "Sally" },
//             { source: "Harry", target: "Alice" },
//         ],
//     };
    
//     // Graph configuration
//     const myConfig = {
//         nodeHighlightBehavior: true,
//         node: {
//         color: "lightgreen",
//         size: 120,
//             highlightStrokeColor: "blue",
//         },
//         link: {
//             highlightColor: "lightblue",
//         },
//     };
    
//     // Node click handler
//     const onClickNode = (nodeId) => {
//         alert(`Clicked node ${nodeId}`);
//     };
    
//     // Link click handler
//     const onClickLink = (source, target) => {
//         alert(`Clicked link between ${source} and ${target}`);
//     };

//     const onClickGraph = (x, y) => {
//         alert(`Clicked canvas ${x}:${y}`);
//     };

//     return (
//         <div>
//             <h1>
//                 words
//                 <Graph
//                     id="graph-id" // id is mandatory
//                     data={data}
//                     config={myConfig}
//                     onClickGraph={onClickGraph}
//                     onClickNode={onClickNode}
//                     onClickLink={onClickLink}
//                 />
//             </h1>
//         </div>
//     );
// };

// export default Words;
