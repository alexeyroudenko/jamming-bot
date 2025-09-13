import 'aframe';
import React, { useState, useEffect } from "react";
import './App.css';
import Navbar from "./Navbar";
import { useNavigate, useLocation } from 'react-router-dom';

import {
  BrowserRouter as Router,
  Routes,
  Route,
} from "react-router-dom";

// import Contacts from "./pages/contacts";
import Logs from "./pages/logs";
import Graph from "./pages/graph";
import Cloud from "./pages/cloud";
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
        <AutoSwitcher />
        <Routes className="Nav">
          <Route path="/" element={<Logs/>} />
          <Route path="/steps" element={<Graph/>} />
          <Route exact path="/cloud" element={<Cloud/>} />
        </Routes>
      </Router>

    </div>
  );
}

function AutoSwitcher() {
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    const paths = ["/", "/steps", "/cloud"];
    let currentIndex = paths.indexOf(location.pathname);
    if (currentIndex === -1) currentIndex = 0;
    const interval = setInterval(() => {
      currentIndex = (currentIndex + 1) % paths.length;
      navigate(paths[currentIndex]);
    }, 1000*300);
    return () => clearInterval(interval);
  }, [location.pathname, navigate]);

  return null;
}

export default App;