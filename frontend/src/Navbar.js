// Filename - "./components/Navbar.js

import React from "react";
import { Nav, NavLink, NavMenu } from "./Navbar2";

const Navbar = () => {
    return (
            <Nav className="Nav">
                <NavMenu>
                    <NavLink to="/semantic">
                    Semantic
                    </NavLink>
                    <NavLink to="/semantic3d">
                    Semantic 3D
                    </NavLink>
                    <NavLink to="/tags">
                    Tags
                    </NavLink>
                    <NavLink to="/tags/3d">
                    Tags 3D
                    </NavLink>
                    <NavLink to="/tags/sentiment-vortex">
                    Sentiment vortex
                    </NavLink>
                    <NavLink to="/tags/vectorfield-3d">
                    Vectorfield 3D
                    </NavLink>
                </NavMenu>
            </Nav>
    );
};

export default Navbar;
