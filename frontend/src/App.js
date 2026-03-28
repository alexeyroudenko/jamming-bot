// import React, { Component } from "react";
// import { Graph } from "react-d3-graph";
// import "./App.css";

// class App extends Component {
//   constructor() {
//     super();
//     let data = {
//       nodes: [{ id: "Harry" }, { id: "Sally" }, { id: "Alice" }],
//       links: [
//         { source: "Harry", target: "Sally" },
//         { source: "Harry", target: "Alice" }
//       ]
//     };
//     this.state = {
//       data: data
//     };
//   }

//   render() {
//     // the graph configuration, you only need to pass down properties
//     // that you want to override, otherwise default ones will be used
//     const myConfig = {
//       nodeHighlightBehavior: true,
//       node: {
//         color: "lightgreen",
//         size: 120,
//         highlightStrokeColor: "blue"
//       },
//       link: {
//         highlightColor: "lightblue"
//       }
//     };
//     const reactRef = this;
//     const onDoubleClickNode = function(nodeId) {
//       let modData = { ...reactRef.state.data };
//       let selectNode = modData.nodes.filter(item => {
//         return item.id === nodeId;
//       });
//       selectNode.forEach(item => {
//         if (item.color && item.color === "red") item.color = "blue";
//         else item.color = "red";
//       });
//       reactRef.setState({ data: modData });
//     };

//     return (
//       <div className="App">
//         <h1>Hello CodeSandbox</h1>
//         <Graph
//           id="graph-id" // id is mandatory, if no id is defined rd3g will throw an error
//           data={this.state.data}
//           config={myConfig}
//           onDoubleClickNode={onDoubleClickNode}
//         />
//       </div>
//     );
//   }
// }
// export default App;





import React, { useState, useEffect } from "react";
import './App.css';


import Navbar from "./Navbar";

import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";


import Tags from "./pages/tags";
import Blank from "./pages/graph";
import Semantic from "./pages/semantic";
import Steps from './components/Steps';
import AtlasPage from './pages/atlas';

/** Routes + nav; wrapped by `Router` in `App` (and by `MemoryRouter` in tests). */
export function AppContent() {
  return (
    <>
      <Navbar />
      <Routes className="Nav">
        <Route path="/" element={<Tags />} />
        <Route path="/semantic" element={<Semantic />} />
        <Route path="/steps" element={<Steps />} />
        <Route path="/atlas" element={<AtlasPage />} />
        <Route path="/words" element={<Navigate to="/semantic" replace />} />
        <Route path="/graph" element={<Blank />} />
      </Routes>
    </>
  );
}

function App() {
  const [bg, setBg] = useState([]);
  useEffect(() => {
  }, []);


  return (
    <div className="App">
      
      <Router
          basename="/static-app"
          future={{
            v7_startTransition: true,
            v7_relativeSplatPath: true,
          }}
      >
        <AppContent />
      </Router>

    </div>
  );
}


// import { Url } from './constants'
// import CommunityDetection from './components/CommunityDetection';
// import PageRank from './components/PageRank';

// function App() {
//   const [algorithm, setAlgorithm] = useState("CommunityDetection")

//   const handleClick = (algorithm) => {
//     setAlgorithm(algorithm)
//   }

//   if (algorithm === "PageRank") {
//     return (
//       <div className="App">
//         <button onClick={() => handleClick("CommunityDetection")}>Check out Community Detection</button>
//         <PageRank />
//       </div >
//     );
//   }
//   else {
//     return (
//       <div className="App">
//         <button onClick={() => handleClick("PageRank")}>Check out PageRank</button>
//         <CommunityDetection />
//       </div >
//     );
//   }
// }

export default App;