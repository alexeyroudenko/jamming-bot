// Filename - pages/blank.js
import { Url } from '../constants'
import React from "react";

const Blank = () => {
    return (
        <div style={{width: "100%", height: "100%"}}>
            <h1>
                blank (steps) page
            </h1>
            <iframe
                style={{width: "100%", height: "100%"}}
                src={Url}
                loading="lazy"
            ></iframe>
        </div>
    );
};

export default Blank;