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
                    <NavLink to="/steps">
                    steps
                    </NavLink>                     
                    <NavLink to="/words">
                    words
                    </NavLink>
                    <NavLink to="/blank">
                    blank
                    </NavLink>
                </NavMenu>
            </Nav>
    );
};

export default Navbar;
