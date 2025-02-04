// https://blog.bitsrc.io/real-time-visualization-with-react-and-d3-js-6ee29e36acb6
import React from 'react';
import * as d3 from "d3";
import io from "socket.io-client"
import { Url } from '../constants'

var node;
var link;
var simulation;
var width = window.innerWidth;
var height = 800;
var tooltip;
var clusterColors = {};

/**
 * Component that draws nodes and edges as a part of different communities in real-time.
 */
export default class CommunityDetection extends React.Component {

    constructor(props) {
        super(props);
        this.lastAdded = ""
        this.myReference = React.createRef();
        this.state = {
            nodes: [],
            links: [],
            url: ""
        }
        this.socket = io(Url, { transports: ["websocket", "polling"] })

        this.handleClick = () => {
            alert("Hello!")
        };  
    }


    findNode(id, updatedNodes) {        
        updatedNodes.forEach((node) => {
            if (node.id === id)
                return node
        })
        //console.log("findNode", node)
        //return id
        return id
    }

    findNodeByURL(id, updatedNodes) {
        let n = false
        updatedNodes.forEach((nn) => {
            // console.log("check", nn.id, id, nn.id === id)            
            if (nn.id === id) {
                // console.log("finded", id, nn.id, nn.id === id)
                n = nn
            }
        })
        return n
    }

    firstRequest() {
        console.log("firstRequest")
        fetch(Url + "/api/steps/")
            .then((res) => res.json())
            .then((result) => {
                console.log("firstRequest result:");                
                var edges = []
                var nodes = []
                var new_nodes = []                
                result.forEach((node) => {
                    // console.log("------------------------ ", node)
                    
                    let url = node.url;
                    let src_url = node.src_url;
                    let step = node.step;
                    node.id = node.current_url;  
                    
                    // console.log("begin find type1--------------", src_url, nodes)   
                    let type1 = typeof(this.findNodeByURL(src_url, nodes))
                    
                    // console.log("end find type1--------------", type1)   
                    // console.log("type1", type1)
                    
                    if (type1 === "boolean") {
                        
                        let new_node = {
                            "id":url,
                            "step":step,
                            "url":url,
                            "src_url":src_url
                        }

                        let type2 = this.findNodeByURL(src_url, new_nodes)
                        // console.log("end find type2 ", type2, src_url, new_nodes)
                        if (type2 === false) {
                            // console.log(new_nodes.length)
                            new_nodes.push(new_node)                            
                            nodes.push(new_node)
                            console.log("new_node", new_node)

                            // var edge = {
                            //     id: src_url + "-" + node.url,
                            //     source: src_url,
                            //     target: node.url,
                            //     r: 10
                            // }
                            
                            // console.log("new_edge?", edge)
                            
                            if (node.url) {
                                // edges.push(edge)
                            }

                        } else {
                            // console.log("----------- skip new_node")
                        }

                    }
                    nodes.push(node)
                    // if (node.current_url === node.src_url)
                    // return node
                })  

                // console.log("nodes", nodes)
                // console.log("new_nodes", new_nodes)

                this.setState({ nodes: nodes, links: edges })
            })
    }

    transformData(data) {
        // console.log("transformData", data, data.vertices)
        var nodes = data.vertices.map((vertex) => {            
            return {
                id: vertex.id,
                type: "url",
                username: vertex.id,
                rank: 5,
                cluster: 2,
                data: vertex,
                step: vertex.step
            };
        });
        var links = data.edges.map((edge) => {
            return {
                id: edge.id,
                source: edge.source,
                target: edge.target,
                r: 10
                // type: edge.type,
            };
        });
        this.lastAdded = data.vertices[0].id

        return { nodes, links };
    }

    componentDidMount() 
    {
        this.initializeGraph(this.state.nodes, this.state.links)
        // this.firstRequest();

        this.socket.on("connect", () => {
            this.socket.emit('consumer')
            console.log("Connected to socket v1.0", this.socket.id)
        });

        this.socket.on("connect_error", (err) => { console.log(err) });
        this.socket.on("disconnect", () => {console.log("Disconnected from socket. v1.0")});

        // this.socket.on("step", (data) => {
        //     //console.log('Received a message from the WebSocket service: ', data);
        //     let dataa = {}
        //     dataa.vertices = [{"id":1}, {"id":2}, {"id":3}]
        //     dataa.edges = []
        //     console.log(dataa.vertices)
        //     this.transformData(dataa) 
        // });

        this.socket.on("step", (msg) => { 
            console.log('step: ', msg, msg.data);            
            // msg.id = msg.current_url;
            var data = {};
            data.vertices = [msg]
            data.edges = [{}]
            
            // data.edges = [{
            //     id: this.lastAdded + "-" + msg.current_url,
            //     source: msg.current_url,
            //     target: this.lastAdded,
            //     r: 10
            // }]

            var currentNodes = this.state.nodes
            var newNodes = this.transformData(data).nodes
            var updatedNodes = currentNodes.concat(newNodes)

            // var currentLinks = this.state.links
            // var newLinks = this.transformData(data).links
            // console.log("updatedNodes", updatedNodes)
            // filter new edges to have only the ones that have source and target node
            // var filteredLinks = newLinks.filter((link) => {
            //     return (
            //         updatedNodes.find((node) => node.id === link.source) &&
            //         updatedNodes.find((node) => node.id === link.target)
            //     );
            // })

            // get all edges (old + new)
            // var updatedLinks = currentLinks.concat(filteredLinks)
            // set source and target to appropriate node -> they exists since we filtered the edges
            // updatedLinks.forEach((link) => {
                // link.source = this.findNode(link.source, updatedNodes)
                // link.target = this.findNode(link.target, updatedNodes)
            // })
            // update state with new nodes and edges
            // this.setState({ nodes: updatedNodes, links: updatedLinks, url: msg.current_url})
            this.setState({ nodes: updatedNodes })
        });

    }

    componentDidUpdate() {
        this.updateGraph(this.state.nodes, this.state.links)
    }

    componentWillUnmount() {
        // this.socket.emit('disconnect');
        this.socket.disconnect();
    }

    drag()  {
        function dragstarted(event) {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            tooltip.style("visibility", "hidden")
            event.subject.fx = event.subject.x;
            event.subject.fy = event.subject.y;
        }

        function dragged(event) {
            tooltip.style("visibility", "hidden")
            event.subject.fx = event.x;
            event.subject.fy = event.y;
        }

        function dragended(event) {
            tooltip.style("visibility", "hidden")
            if (!event.active) simulation.alphaTarget(0);
            event.subject.fx = null;
            event.subject.fy = null;
        }

        return d3
            .drag()
            .on("start", dragstarted)
            .on("drag", dragged)
            .on("end", dragended);
    }

    handleZoom(e) {
        d3.selectAll("svg g")
            .attr("transform", e.transform)
    }

    initZoom(zoom) {
        d3.select('svg')
            .call(zoom);
    }

    createTooltip() {
        return (d3.select("body")
            .append("div")
            .style("position", "absolute")
            .style("z-index", "10")
            .style('background-color', '#ff0000')
            .style("color", "#ffffff")
            .style("visibility", "hidden"));
    }

    /**
     * Method that initializes everything that will be drawn.
     */
    initializeGraph(nodes, links) {
        var svg = d3.select(this.myReference.current);
        // erase everything
        svg.selectAll("*").remove();

        // initialize zoom
        var zoom = d3.zoom() 

        //.translateTo([0,0]) 
        //.extent([-width/2,-width/2], [width/2,width/2])          
        //.extent([[0, 0], [width, height]])
            // .call(zoom.translateTo, 0.5 * width, 0.5 * height)
            // .on("zoom", this.handleZoom)
        
        this.initZoom(zoom)        
        d3.select("svg").call(zoom)

        // initialize tooltip
        tooltip = this.createTooltip()

        var weightScale = d3.scaleLinear()
        .domain(d3.extent(links, function (d) { return d.weight }))
        .range([.1, 4])

        // set up simulation, link and node
        simulation = d3
            .forceSimulation(nodes)
            .force("x", d3.forceX().strength(0.01))
            .force("y", d3.forceY().strength(0.01))            
            .force("charge", d3.forceManyBody().strength(1.1))
            // .force("charge", d3.forceManyBody().strength(-5))
            // .force("collide", d3.forceCollide().radius(40.2)) 
            .force("center", d3.forceCenter(width / 2, height / 2))
            // .force('link', d3.forceLink(links).id(function (n) { return n.id; }).strength(function (d) {return weightScale(d.weight)}).distance(20))
            // .force("radial", d3.forceRadial(340, 0/2, 0/2));

        // var ff = d3.force();
        // console.log(d3)

        link = svg.append("g")
            .attr('stroke', 'white')
            .attr('stroke-opacity', 0.3)
            .selectAll('line')
            .data(links)
            .join('line')
            .attr('id', (d) => d.source.id + '-' + d.target.id)
            .attr('stroke-width', .5);

        node = svg.append("g")
            .selectAll("circle")
            .data(this.state.nodes)
            .join("circle")
            .attr("r", function (d) {return 40;})
            .attr("class", "node")
            // .attr('fill', function (d) {
            //     if (!clusterColors.hasOwnProperty(d.cluster)) {
            //         clusterColors[d.cluster] = "#" + Math.floor(Math.random() * 16777215).toString(16)
            //     }
            //     return clusterColors[d.cluster]
            // })
            .on("mouseover", function (d) {
                tooltip.text(d.srcElement["__data__"]["username"])
                tooltip.style("visibility", "visible")
            })
            .on("mousemove", function (event, d) { return tooltip.style("top", (event.y - 10) + "px").style("left", (event.x + 10) + "px"); })
            .on("mouseout", function (event, d) { return tooltip.style("visibility", "hidden"); })
            .call(this.drag(simulation));


        simulation.on("tick", () => {
            // console.log("tick", node)
            node.attr("cx", (d) => d.x).attr("cy", (d) => d.y);
            link
                .attr('x1', (d) => d.source.x)
                .attr('y1', (d) => d.source.y)
                .attr('x2', (d) => d.target.x)
                .attr('y2', (d) => d.target.y);
        });
    }

    /**
     * Method that is called on every new node/edge and draws updated graph.
     */
    updateGraph(nodes, links) {

        console.log("updateGraph")

        // Update existing nodes
        // node.selectAll('circle').style('fill', function (d) {
        //     if (!clusterColors.hasOwnProperty(d.cluster)) {
        //         clusterColors[d.cluster] = Math.floor(Math.random() * 16777215).toString(16);
        //     }
        //     return clusterColors[d.cluster];
        // });

        // Remove old nodes
        node.exit().remove();

        // Add new nodes
        node = node.data(nodes, (d) => d.id);
        node = node
            .enter()
            .append('circle')
            .attr("r", function (d) {return 27;})
            .attr('fill', function (d) {
                if (!clusterColors.hasOwnProperty(d.cluster)) {
                    // clusterColors[d.cluster] = "#" + Math.floor(Math.random() * 16777215).toString(16)
                    clusterColors[d.cluster] = "#ffffff"
                }
                return clusterColors[d.cluster]
            })
            .on("mouseover", function (d) {
                tooltip.text(d.srcElement["__data__"]["username"])
                tooltip.style("visibility", "visible")
            })
            .on("mousemove", function (event, d) { return tooltip.style("top", (event.y - 10) + "px").style("left", (event.x + 10) + "px"); })
            .on("mouseout", function (event, d) { return tooltip.style("visibility", "hidden"); })
            .call(this.drag())
            .merge(node);

        link = link.data(links, (d) => {
            return d.source.id + '-' + d.target.id;
        });

        // Remove old links
        link.exit().remove();

        link = link
            .enter()
            .append('line')
            .attr('id', (d) => d.source.id + '-' + d.target.id)
            .attr('stroke', 'white')
            .attr('stroke-opacity', 0.8)
            .attr('stroke-width', .5)
            .merge(link);

        // Set up simulation on new nodes and edges
        try {
            simulation
                .nodes(nodes)
                .force('link', d3.forceLink(links).id(function (n) { return n.id; }).distance(50))
                .force('charge', d3.forceManyBody())
                .force('center', d3.forceCenter(width / 2, height / 2));
        } catch (err) {
            console.log('err', err);
        }

        simulation.on('tick', () => {
            node.attr('cx', (d) => d.x).attr('cy', (d) => d.y);
            link
                .attr('x1', (d) => d.source.x)
                .attr('y1', (d) => d.source.y)
                .attr('x2', (d) => d.target.x)
                .attr('y2', (d) => d.target.y);
        });
        // simulation.alphaTarget(0.1).restart();
    }

    

    render() {
        return (<div>
            <h1><code>{this.state.url}</code></h1>
            <p><code>nodes:{this.state.nodes.length}</code></p>
            <svg
                className="svg" 
                ref={this.myReference}
                onMouseUp={this.handleClick}
                style={{
                    height: "800",
                    width: "100%",
                    marginRight: "0px",
                    marginLeft: "0px",
                    background: "black"
                }}></svg></div>
        );
    }
}