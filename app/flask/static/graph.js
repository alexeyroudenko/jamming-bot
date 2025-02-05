
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


var graph;

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
        nodes.splice(0, links.length);
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

    var nodes = force.nodes(),
    links = force.links();


    var update = function () {

        //console.log("update")
        
        links = force.links();

        var link = vis.selectAll("line")
            .data(links, function (d) {                    
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
            .text(function (d) {return d.id;
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
        force.gravity(.01)
          .charge(-1000)
          .friction(0.1)
          .linkDistance( function(d) { return d.value * 10 } )
          .size([w, h])
          .start();
    };


    // Make it all go
    update();
    this.upd = function() {
        update()
    }
};

graph = new myGraph("#svgdiv");
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




var text = "."
var url = "/"

var server = window.location.protocol + "//" + window.location.host;
// console.log("server", server)

var socket = io();

height = 600

var counter = 0
var tag = 0
var imgs = 0

var start_time = (new Date).getTime()   
socket.on('connect', function() {  
    console.log("on connect " + server)
    window.setInterval(function () {
        counter += 1
        start_time = (new Date).getTime();
        //console.log("semd my_ping")
        socket.emit('my_ping');
    }, 250);
});


function getLinkLength(url1, url2) {
length = "50" //30
if (getDomain(url1,2)==getDomain(url2,2)) {
    length = "10"
}
return length
}





//
// EVENT
//
//
//
//
let log_page = ""
let last_event_time = -1;
let last_event = "";
var event_time = (new Date).getTime()
socket.on('event', function(data) {                
    if (data['event'] == "retrieve_next_url") {
        log_page = ""
        event_time = (new Date).getTime()
    }                
    const deltaTime = (new Date).getTime() - event_time;
    log_line = data['event'] + " - " + deltaTime
    log_page = log_page + "\n" + log_line
    $('#log_events').html("<code>" + log_page + "</code>");
    $('#log_text').html(counter);
    event_time = (new Date).getTime()
})



//
// SUBLINKS
//
//
//
//
let log_sub_page = ""
let last_sub_event_time = -1;
let last_sub_event = "";
var event_sub_time = (new Date).getTime()
socket.on('sublink', function(data) {        
    log_sub_line = data['url']
    log_sub_page = log_sub_line  + "\n" + log_sub_page 
    log_sub_page.substring(0, 1024);
    $('#log_sub').html("<code>" + log_sub_page + "</code>");
    //$('#log_text').html(counter);
    event_sub_time = (new Date).getTime()
})



socket.on('clear', function(data){
    console.log("clear")
    url = ""
    text = ""    
    graph.removeAllNodes()
    graph.removeallLinks()
})

//
// STEP
//
//
//
//
//
//
let timeoutId = -1;
let last_added = "";
socket.on('step', function(data) {
    clearTimeout(timeoutId);
    console.log(data)
    step = data['step']
    url = data['url'];
    from_url = data['src_url'];    
    struct_text = data['struct_text']
    text = data['text']
    words = data['words']


    if (data.analyzed) {
        words_count = data.analyzed.words_count;
        words_count = Math.min(words_count/10+5, 20);
    } else {
        words_count = Math.random() * 700.0;
        words_count = Math.min(words_count/10+5, 20);
    }
    
    headers = data['headers']        
    node_id = graph.addNode(url, step, words_count);
    node_src = graph.findNode(from_url)
    if (!node_src) {
        graph.addNode(from_url, 0);
        graph.addLink(from_url, url,  getLinkLength(url, from_url));
    }    

    if (graph.findNodeIndex(from_url)) {
        graph.addLink(from_url, url, '15');            
    }

    if (last_added) {
        graph.addLink(last_added, url, getLinkLength(url, last_added));
    }

    last_added = url

    keepNodesOnTop();

    var log_view = document.getElementById('log_url');
    log_view.innerHTML = "<code><nobr>" + step + " : " + url + "</nobr></code>";

    function updateData(selectedNode)  {
        diff.removed.forEach((node) => nodes.splice(nodes.indexOf(node), 1))
    }



    //
    //
    // Limit Nodes
    //
    let MAX_NODES = 15
    if (graph.getNodes().length > MAX_NODES) {
        graph.removeNode(graph.getNodes()[0].id)
    }

    let textLength = 2048;
    if (textLength < 2048) {
        textLength = text.length
    }
    let delay = 1
    let index = 0;
    function animateText() {            
        const element = document.getElementById( "log_text")
        if (index < text.length) {              
            element.innerHTML = "<code>"+text.slice(0, index)+"</code>";
            var rng = document.createRange();
            rng.setStartBefore( document.getElementById('s1') );
            rng.setEndAfter( document.getElementById('s2') );
            //document.getSelection().addRange(rng);    
            index+=10;
            timeoutId = setTimeout(animateText, delay);
        } else {
            clearTimeout(timeoutId);
        }
    }    
    animateText();
        
    //typeString(text, "log_text", 2); //log_img(text)    
    if (data.analyzed) {
        document.getElementById("log_words").innerHTML = "<code>" + data.analyzed.words.join(', ') + "</code>";
    }
    if (struct_text) {
        document.getElementById("log_phrases").innerHTML = "<code>" + struct_text + "</code>";
    }
    document.getElementById("log_headers").innerHTML = "<code>" + headers + "</code>";
    //typeString(url, "log_url", 1); //log_msg(info)


    // console.log("semantic_words", data['semantic_words'])
    set_semantic_woords_from_array(step, data['semantic_words'])


}); // socket on step




//
//
//
function set_semantic_woords_from_array(step_number, semantic_words_array) {
    let words = semantic_words_array
    let sindex = 0;
    let stimeoutId = 0
    words_all = "END" 

    function sanimateText() {            
        if (sindex < words.length) {     
            swords = words.slice(sindex, sindex+1)[0];            
            if (swords != "") {
                words_all = swords + ", " + words_all;
            }
            sindex += 1;
            document.getElementById("log_words").innerHTML = "<code><h3>Step " + step_number + " semantic</h3>" + words_all + "</code>";
            stimeoutId = setTimeout(sanimateText, 150);
        } else {
            clearTimeout(stimeoutId);
        }
    }    
    sanimateText();

    // document.getElementById("log_phrases").innerHTML = "<code><h3>noun_phrases</h3>" + data['noun_phrases'].join('<br>') + "</code>";

    //words_all = data['words_str'] + words_all
    //words = data['words']
    //node = graph.findNode(data.url);
    //node.data = data;
    //node.r = data.sentences;
    //console.log(node, node.data); 
    //document.getElementById("log_words").innerHTML = "<code>" + words_all + "</code>";        
}






//
// ANALYZED
//
//
//
//
//
//
words_all = ""
socket.on('analyzed', function(data) {
    
    let words = data['words_str'].split(" ")
    let sindex = 0;
    let stimeoutId = 0
    function sanimateText() 
    {            
        if (sindex < words.length) {     
            swords = words.slice(sindex, sindex+1)[0];            
            if (swords != "") {
                words_all = swords + ", " + words_all;
            }
            sindex += 1;
            document.getElementById("log_words").innerHTML = "<code><h3>semantic</h3>" + words_all + "</code>";
            stimeoutId = setTimeout(sanimateText, 150);
        } else {
            clearTimeout(stimeoutId);
        }
    }    
    sanimateText();

    document.getElementById("log_phrases").innerHTML = "<code><h3>noun_phrases</h3>" + data['noun_phrases'].join('<br>') + "</code>";

    //words_all = data['words_str'] + words_all
    //words = data['words']
    //node = graph.findNode(data.url);
    //node.data = data;
    //node.r = data.sentences;
    //console.log(node, node.data); 
    //document.getElementById("log_words").innerHTML = "<code>" + words_all + "</code>";
})



socket.on('my_pong', function () {
    const latency = (new Date).getTime() - start_time;
    $('#latency').html(latency);
    $('#counter').html(counter);
});

socket.on('disconnect', function() {
    console.log('Disconnected from server');
});




function reset() {
    console.log("reset")
    //d3.select("svg").remove();
    //drawGraph();
    socket.emit('reset');
}

function stop() {
    console.log("stop")
    url = ""
    text = ""    
    graph.removeAllNodes()
    graph.removeallLinks()
    socket.emit('stop');
}

function start() {
    console.log("start")
    socket.emit('start');
}

function restart() {
    console.log("restart")
    // url = ""
    // text = ""    
    // graph.removeAllNodes()
    // graph.removeallLinks()
    socket.emit('restart');
}

function do_step() {
    console.log("step")
    socket.emit('step');
}

function do_add() {
    new_id = "URL" + Math.random() * 1000
    console.log("add", new_id)
    // socket.emit('add');
    graph.addNode(new_id);
    graph.addLink(new_id, "URL1", '10');
}


console.log("loaded js")