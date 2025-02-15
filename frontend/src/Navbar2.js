// Filename - ./components/Navbar.js

import { FaBars } from "react-icons/fa";
import { NavLink as Link } from "react-router-dom";
import styled from "styled-components";

export const Nav = styled.nav`
    // background: #fff;
    height: 85px;
    display: flex;
    justify-content: space-between;
    // padding: 0.2rem calc((100vw - 1000px) / 2);
    z-index: 12;
`;

export const NavLink = styled(Link)`
    color: #808080;
    display: flex;
    align-items: center;
    text-decoration: none;
    padding: 0 1rem;
    height: 100%;
    cursor: pointer;
    &.active {
        color: #bbb;
    }
    text-shadow: 1px 1px #777777;
`;

export const Bars = styled(FaBars)`
    display: none;
    color: #808080;
    @media screen and (max-width: 768px) {
        display: block;
        position: absolute;
        top: 0;
        right: 0;
        /*transform: translate(-100%, 75%);*/
        font-size: 1.2rem;
        cursor: pointer;
    }
`;

export const NavMenu = styled.div`
    // background: #fff;
    display: flex;
    align-items: center;
    padding-left: 45%;
    /* Second Nav */
    /* margin-right: 24px; */
    /* Third Nav */
    /* width: 100vw;
white-space: nowrap; */
    @media screen and (max-width: 768px) {
        display: none;
    }
`;
