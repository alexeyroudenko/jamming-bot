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





import React, { useState, useEffect, useRef, useCallback } from "react";
import './App.css';


import Navbar from "./Navbar";

import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
  useNavigate,
  useLocation,
} from "react-router-dom";


import Tags from "./pages/tags";
import Blank from "./pages/graph";
import Semantic from "./pages/semantic";
import Steps from './components/Steps';
import AtlasPage from './pages/atlas';
import TagEmbedPage from './pages/tagEmbed';

/** Tag embed routes cycled when autoswitch is on (key "a"). */
const TAG_EMBED_AUTOSWITCH_ROUTES = [
  '/tags',
  '/tags3d',
  '/sentiment-vortex',
  '/vectorfield-3d',
]
const TAG_EMBED_AUTOSWITCH_MS = 2 * 60 * 1000

const TAG_EMBED_AUTOSWITCH_STORAGE_KEY = 'jamming-bot:tag-embed-autoswitch'

function readTagEmbedAutoswitchFromStorage() {
  try {
    if (typeof window === 'undefined') return false
    return window.localStorage.getItem(TAG_EMBED_AUTOSWITCH_STORAGE_KEY) === '1'
  } catch {
    return false
  }
}

function writeTagEmbedAutoswitchToStorage(enabled) {
  try {
    if (typeof window === 'undefined') return
    window.localStorage.setItem(TAG_EMBED_AUTOSWITCH_STORAGE_KEY, enabled ? '1' : '0')
  } catch {
    /* quota / private mode */
  }
}

const SCENES_PWA_TITLE = 'Jamming Bot Scenes'

/** PWA manifest + document title for `/static-app/tags` only (restore on unmount). */
function PwaScenesManifest({ children }) {
  useEffect(() => {
    const link = document.querySelector('link[rel="manifest"]')
    if (!link) return undefined

    const prevHref = link.getAttribute('href')
    const base = (process.env.PUBLIC_URL || '').replace(/\/$/, '')
    link.setAttribute('href', `${base}/manifest-scenes.json`)

    const prevTitle = document.title
    document.title = SCENES_PWA_TITLE

    return () => {
      if (prevHref != null) link.setAttribute('href', prevHref)
      document.title = prevTitle
    }
  }, [])

  return children
}

/** Routes + nav; wrapped by `Router` in `App` (and by `MemoryRouter` in tests). */
export function AppContent() {
  const navigate = useNavigate()
  const location = useLocation()
  const [tagEmbedAutoswitch, setTagEmbedAutoswitch] = useState(readTagEmbedAutoswitchFromStorage)
  const intervalRef = useRef(null)
  const pathnameRef = useRef(location.pathname)

  pathnameRef.current = location.pathname

  const clearAutoswitchInterval = useCallback(() => {
    if (intervalRef.current != null) {
      window.clearInterval(intervalRef.current)
      intervalRef.current = null
    }
  }, [])

  useEffect(() => {
    const onKeyDown = (e) => {
      if (e.defaultPrevented) return
      const el = e.target
      if (
        el &&
        (el.tagName === 'INPUT' ||
          el.tagName === 'TEXTAREA' ||
          el.tagName === 'SELECT' ||
          (typeof el.isContentEditable === 'boolean' && el.isContentEditable))
      ) {
        return
      }
      if (e.ctrlKey || e.metaKey || e.altKey) return
      if (e.key !== 'a' && e.key !== 'A') return
      e.preventDefault()
      setTagEmbedAutoswitch((v) => !v)
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])

  useEffect(() => {
    writeTagEmbedAutoswitchToStorage(tagEmbedAutoswitch)
    // eslint-disable-next-line no-console
    console.log('[tag-embed-autoswitch]', tagEmbedAutoswitch ? 'on' : 'off')
  }, [tagEmbedAutoswitch])

  useEffect(() => {
    if (!tagEmbedAutoswitch) {
      clearAutoswitchInterval()
      return
    }
    const tick = () => {
      const path = pathnameRef.current
      const i = TAG_EMBED_AUTOSWITCH_ROUTES.indexOf(path)
      const nextIdx = i === -1 ? 0 : (i + 1) % TAG_EMBED_AUTOSWITCH_ROUTES.length
      navigate(TAG_EMBED_AUTOSWITCH_ROUTES[nextIdx])
    }
    intervalRef.current = window.setInterval(tick, TAG_EMBED_AUTOSWITCH_MS)
    return clearAutoswitchInterval
  }, [tagEmbedAutoswitch, navigate, clearAutoswitchInterval])

  return (
    <>
      <Navbar />
      <Routes className="Nav">
        <Route
          path="/"
          element={
            <PwaScenesManifest>
              <TagEmbedPage title="Tags" path="/tags/" />
            </PwaScenesManifest>
          }
        />
        <Route path="/semantic" element={<Semantic />} />
        <Route path="/steps" element={<Steps />} />
        <Route path="/atlas" element={<AtlasPage />} />
        <Route path="/words" element={<Navigate to="/semantic" replace />} />
        <Route path="/graph" element={<Blank />} />
        <Route
          path="/tags"
          element={
            <PwaScenesManifest>
              <TagEmbedPage title="Tags" path="/tags/" />
            </PwaScenesManifest>
          }
        />
        <Route
          path="/tags3d"
          element={<TagEmbedPage title="Tags 3D" path="/tags/3d/" />}
        />
        <Route
          path="/sentiment-vortex"
          element={
            <TagEmbedPage title="Sentiment vortex" path="/tags/sentiment-vortex/" />
          }
        />
        <Route
          path="/vectorfield-3d"
          element={
            <TagEmbedPage title="Vectorfield 3D" path="/tags/vectorfield-3d/" />
          }
        />
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