// Filename - "./components/Navbar.js

import React from "react";
import { Nav, NavLink, NavMenu } from "./Navbar2";

const Navbar = () => {
    return (
            <Nav className="Nav">
                <NavMenu>
                    <NavLink to="/tags">
                    Tags
                    </NavLink>
                    <NavLink to="/tags3d">
                    Tags 3D
                    </NavLink>
                    <NavLink to="/sentiment-vortex">
                    Sentiment vortex
                    </NavLink>
                    <NavLink to="/vectorfield-3d">
                    Vectorfield 3D
                    </NavLink>
                </NavMenu>
            </Nav>
    );
};

export default Navbar;
