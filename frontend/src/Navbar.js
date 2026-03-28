// Filename - "./components/Navbar.js

import React from "react";
import { Nav, NavLink, NavMenu } from "./Navbar2";

const Navbar = () => {
    return (
            <Nav className="Nav">
                <NavMenu>
                    <NavLink to="/">
                    Semantic cloud
                    </NavLink>

                    <NavLink to="/semantic">
                    Semantic
                    </NavLink>

                    <NavLink to="/steps">
                    Steps
                    </NavLink>
                    <NavLink to="/atlas">
                    Data Atlas
                    </NavLink>
                    <NavLink to="/graph">
                    Graph
                    </NavLink>
                </NavMenu>
            </Nav>
    );
};

export default Navbar;
