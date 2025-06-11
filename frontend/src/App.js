import 'aframe';
import React, { useState, useEffect } from "react";
import './App.css';
import Navbar from "./Navbar";

import {
  BrowserRouter as Router,
  Routes,
  Route,
} from "react-router-dom";

// import Contacts from "./pages/contacts";
import Logs from "./pages/logs";
import Blank from "./pages/graph";
import Home from "./pages/home";
import Words from "./pages/words";
import Steps from './components/Steps';

function App() {
  const [bg, setBg] = useState([]);
  useEffect(() => {
  }, []);

  return (
    <div className="App">
      
      <Router
          future={{
            v7_startTransition: true,
            v7_relativeSplatPath: true,
          }}
          
      >
        <Navbar/>
        <Routes className="Nav">
          <Route exact path="/" element={<Logs/>} />
          <Route path="/steps" element={<Steps/>} />
          <Route path="/words" element={<Words/>} />
          <Route path="/graph" element={<Blank/>} />
          {/* <Route path="/contact" element={<Сontact />} /> */}
        </Routes>
      </Router>

    </div>
  );
}

export default App;