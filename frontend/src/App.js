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
    const interval = setInterval(() => {
      if (location.pathname === "/") {
        navigate("/logs");
      } else {
        navigate("/");
      }
    }, 180000*60); // 10 Minutes
    return () => clearInterval(interval);
  }, [location.pathname, navigate]);

  return null;
}

export default App;