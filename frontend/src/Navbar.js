// Filename - "./components/Navbar.js

import React from "react";
import { Nav, NavLink, NavMenu } from "./Navbar2";

const Navbar = () => {
    return (
            <Nav className="Nav">
                <NavMenu>
                    <NavLink to="/">
                    logs
                    </NavLink>

                    {/* <NavLink to="/words">
                    semantic
                    </NavLink> */}

                    <NavLink to="/steps">
                    steps
                    </NavLink>

                    <NavLink to="/cloud">
                    cloud
                    </NavLink>
                </NavMenu>
            </Nav>
    );
};

export default Navbar;
