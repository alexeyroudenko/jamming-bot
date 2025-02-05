//
//
//
//

let MAX_NODES = 256

function getDomain(url, subdomain) {
    subdomain = subdomain || false;
    url = url.replace(/(https?:\/\/)?(www.)?/i, '');
    if (!subdomain) {
        url = url.split('.');
        url = url.slice(url.length - 2).join('.');
    }
    if (url.indexOf('/') !== -1) {
        return url.split('/')[0];
    }
    return url;
}


function myGraph() {

    var nodes = []
    var links = []
    
    this.getNodes = function() {
        return nodes
    }
    // Add and remove elements on the graph object
    this.addNode = function (id, step, r=6) {
        //console.log(r)
        nodes.push({"id": id, "step": step, "r": r});
        update();
        return id
    };

    this.removeNode = function(id) {
        var i = 0;
        var n = findNode(id);            
        while (i < links.length) {
            if ((links[i].source.id == id) || (links[i].source.id == id)) {
                links.splice(i, 1);
            }
            else i++;
        }
        nodes.splice(this.findNodeIndex(id), 1);
        update();
    };

    this.removeLink = function (source, target) {
        for (var i = 0; i < links.length; i++) {
            if (links[i].source.id == source && links[i].target.id == target) {
                links.splice(i, 1);
                break;
            }
        }
        update();
    };

    this.removeallLinks = function () {
        links.splice(0, links.length);
        update();
    };

    this.removeAllNodes = function () {
        nodes.splice(0, nodes.length);
        update();
    };

    this.addLink = function (source, target, value) {
        links.push({"source": findNode(source), "target": findNode(target), "value": value});
        update();
    };

    this.findNode = function (id) {
        for (var i in nodes) {
            if (nodes[i]["id"] === id) return nodes[i];
        };
    };

    this.removeLinksForNode = function (node_id) {
        i = 0;
        while (i < links.length) {
            if (links[i].source.id == node_id || links[i].target.id == node_id) {
                links.splice(i, 1);
            } else {
                i+=1;
            }
        }
        update();
    }; 

    var findNode = function (id) {

        for (var i in nodes) {
            if (nodes[i]["id"] === id) return nodes[i];
        };
    };

    this.findNodeIndex = function (id) {
        for (var i = 0; i < nodes.length; i++) {
            if (nodes[i].id == id) {
                return i;
            }
        };
    };

    // set up the D3 visualisation in the specified element
    var w = window.innerWidth,
    h = window.innerHeight;
    var aspect = w / h;

    // const container = d3.select(graph.node().parentNode)
    function isMobile() {
        const regex = /Mobi|Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i;
        return regex.test(navigator.userAgent);
    }

    var color = d3.scale.category10();
    var scale = 1;
    
    if (isMobile()) {
        scale = 1.5;
    }
    scale = 1.0;
    var vis = d3.select("body")
        .append("svg:svg")
        .attr("width", Math.floor(w*scale))
        .attr("height", Math.floor(h*scale))
        .attr("id", "svg")
        .attr("pointer-events", "all")
        .attr("viewBox", "0 0 " + Math.floor(w*scale) + " " + Math.floor(h*scale))
        .attr("perserveAspectRatio", "xMinYMid")
        // .on("mouseover", handleMouseOver)
        // .on("mouseout", handleMouseOut); 
        //.append('svg:g');

    function handleMouseOver(d, i) {
        console.log("over", d, i)
    }

    function handleMouseOut(d, i) {
        console.log("out", d, i)
    }
    
    function resize() {
        var w = window.innerWidth;
        var h = window.innerHeight;
        //const targetWidth = window.innerWidth;
        //graph.attr('width', w);
        //graph.attr('height', Math.round(w / aspect));        
        vis.attr("width", w).attr("height", h)
    }

    window.addEventListener('resize', function (event) {
        //console.log('Произошло событие', event.type)
        resize();
    })

    resize()
    console.log(w, h)

    var force = d3.layout.force();


    nodes = force.nodes();
    links = force.links();

    this.get_all = function() {
        var force = d3.layout.force();
        nodes = force.nodes();
        return nodes
    }

    var update = function () {

        //console.log("update")
        
        links = force.links();

        // console.log("----------line selectAll")
        var link = vis.selectAll("line")
            .data(links, function (d) {
                // if (d.source && d.target)
                // console.log(d.source.id + "-" + d.target.id) 
                // console.log(d.source + "-" + d.target)                    
                return d.source.id + "-" + d.target.id;
            });

        link.enter().append("line")
            .attr("id", function (d) {
                if (d.source && d.target)
                return d.source.id + "-" + d.target.id;
            })
            .attr("stroke-width", function (d) {
                return d.value / 1;
            })
            .attr("class", "link");

        link.append("title")
               .text(function (d) {
                   return d.value;
               });

        link.exit().remove();

        var node = vis.selectAll("g.node")
            .data(nodes, function (d) {
                //console.log("selectAll", d)
                return d.id;
            });

        var nodeEnter = node.enter().append("g")
            .attr("class", "node")
            .call(force.drag);

        nodeEnter.append("svg:circle")
            .attr("r", function (d) {return d.r*1.0;})
            .attr("id", function (d) {return "Node;" + d.id;})
            .attr("class", "nodeStrokeClass")
            //.attr("fill", function(d) { return color(d.id); });

        nodeEnter.append("svg:text")
            .attr("class", "textClass")
            .attr("x", 28)
            .attr("y", ".31em")
            //.text(function (d) {return d.step  + ": " + d.id;
            .text(function (d) {
                return d.id;
            });

        node.exit().remove();

        force.on("tick", function () {
            node.attr("transform", function (d) {
                return "translate(" + d.x + "," + d.y + ")";
            });
            link.attr("x1", function (d) {
                return d.source.x;
            })
            .attr("y1", function (d) {
                return d.source.y;
            })
            .attr("x2", function (d) {
                return d.target.x;
            })
            .attr("y2", function (d) {
                return d.target.y;
            });
        });

        // Restart the force layout.
        // force.gravity(.001)
        // .nodes(nodes)
        // .links(links)
        // .charge(-100000)
        // .chargeDistance(100)
        // .friction(0.4)
        // .theta(1.8)
        // .alpha(1.1)
        // .linkStrength(0.2)
        // .linkDistance( function(d) { return d.value * 10 } )
        // .size([w, h])
        // .start();


        force.gravity(.005)
        .nodes(nodes)
        .links(links)
        .charge(-1000)
        .chargeDistance(100)
        .linkStrength(0.1)
        .linkDistance( function(d) { return d.value * 10 } )
        .friction(0.5)
        .theta(.3)
        .alpha(.3)
        .size([w, h])
        .start();

    };


    // Make it all go
    update();
    this.upd = function() {
        update()
    }
};






var graph = new myGraph("#svgdiv");
//function drawGraph() {}
//drawGraph();

// because of the way the network is created, nodes are created first, and links second,
// so the lines were on top of the nodes, this just reorders the DOM to put the svg:g on top
function keepNodesOnTop() {
    $(".nodeStrokeClass").each(function( index ) {
        var gnode = this.parentNode;
        gnode.parentNode.appendChild(gnode);
    });
};


function clear_graph() {
    console.log("clear_graph")

    // graph.removeAllNodes()
    // graph.removeallLinks()
    while (graph.getNodes().length > 0) {
        graph.removeNode(graph.getNodes()[0].id)
        graph.upd()
    }

    // console.log(graph)
    // console.log(graph.nodes)
    // console.log(graph.links)
    // console.log(graph.getNodes())
    // console.log(graph.upd())
    // console.log(graph.get_all())

    window.location.reload();
}








if (false) {
    graph.addNode("URL0", 0, 0);
    graph.addNode("URL1", 0, 10);
    graph.addNode("URL2", 0, 20);
    graph.addNode("URL3", 0, 30);
    graph.addLink("URL0", "URL1", '10');
    graph.addLink("URL0", "URL2", '10');
    graph.addLink("URL1", "URL2", '10');
    graph.addLink("URL1", "URL3", '10');
    graph.removeNode("URL0")
    graph.removeLinksForNode("URL0")

    node = graph.findNode("URL1");
    node.r = 20;
    node.value = 5

    node = graph.findNode("URL2");
    node.r = 30;
    console.log(node);
    graph.upd();

} else {
    // graph.addNode("http://arthew0.online", 0);
}








/*
    message to create node
    url, src, step, size
*/
let last_added = "";
socket.on('node', function(node_data) {
    console.log("node_data", node_data)
    url = node_data['url'];
    src = node_data['src'];    
    node_id = graph.addNode(url, node_data['step'], node_data['size']);
    node_src = graph.findNode(src)

    if (!node_src) {
        graph.addNode(src, 0);
        graph.addLink(src, url,  getLinkLength(url, src));
    }  

    if (graph.findNodeIndex(src)) {
        graph.addLink(src, url, '15');            
    }

    if (last_added) {
        graph.addLink(last_added, url, getLinkLength(url, last_added));
    }

    last_added = url
    keepNodesOnTop();

    //
    // Limit Nodes
    //

    if (graph.getNodes().length > MAX_NODES) {
        graph.removeNode(graph.getNodes()[0].id)
    }
});





window.setInterval(function () {
    simulate()
}, 200);