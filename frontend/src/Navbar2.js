// Filename - ./components/Navbar.js

import { FaBars } from "react-icons/fa";
import { NavLink as Link } from "react-router-dom";
import styled from "styled-components";

export const Nav = styled.nav`
    height: auto;
    min-height: var(--app-nav-offset, 2.5rem);
    display: flex;
    justify-content: flex-end;
    align-items: center;
    width: 100%;
    box-sizing: border-box;
    padding: 0.12rem 0.4rem;
    z-index: 12;
`;

export const NavLink = styled(Link)`
    color: #808080;
    display: flex;
    align-items: center;
    text-decoration: none;
    padding: 0 0.35rem;
    height: auto;
    font-size: inherit;
    line-height: 1.2;
    cursor: pointer;
    white-space: nowrap;
    &.active {
        color: #bbb;
    }
    text-shadow: 0.5px 0.5px #333;
`;

export const Bars = styled(FaBars)`
    display: none;
    color: #808080;
    @media screen and (max-width: 1024px) {
        display: block;
        position: absolute;
        top: 0;
        right: 0;
        transform: translate(-100%, 75%);
        font-size: .2em;
        cursor: pointer;
    }
`;

export const NavMenu = styled.div`
    display: flex;
    flex-direction: row;
    flex-wrap: wrap;
    align-items: center;
    justify-content: flex-end;
    gap: 0.02rem 0;
    margin-left: auto;
    width: auto;
    max-width: 100%;
    @media screen and (max-width: 768px) {
        display: none;
    }
`;
