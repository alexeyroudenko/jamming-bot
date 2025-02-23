
var text = "."
var url = "/"





var server = window.location.protocol + "//" + window.location.host;
console.log("server", server)

var socket = io();

height = 600

var counter = 0
var tag = 0
var imgs = 0

var start_time = (new Date).getTime()   
socket.on('connect', function() {  
    console.log("on connect")
    window.setInterval(function () {
        counter += 1
        start_time = (new Date).getTime();
        //console.log("semd my_ping")
        socket.emit('my_ping');
    }, 250);
});


function getLinkLength(url1, url2) {
length = "30"
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





        // Send midi notes
        //
        navigator.requestMIDIAccess().then(midiAccess => {
            const outputs = Array.from(midiAccess.outputs.values());
            if (outputs.length === 0) {
                console.error("No midi devices");
                return;
            }
            const output = outputs[1]; 
            const noteOn = [0x90, words_count*3, 127]; // Note On (канал 1, нота C4, velocity 127)
            output.send(noteOn);
            setTimeout(() => {
                output.send([0x80, words_count*3, 0]); // Note Off (канал 1, нота C4, velocity 0)
            }, 100);
        });
    
        




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
            if (text)
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

        //document.getElementById("log_phrases").innerHTML = "<code><h3>noun_phrases</h3>" + data['noun_phrases'].join('<br>') + "</code>";
        //words_all = data['words_str'] + words_all
        //words = data['words']
        //node = graph.findNode(data.url);
        //node.data = data;
        //node.r = data.sentences;
        //console.log(node, node.data); 
        //document.getElementById("log_words").innerHTML = "<code>" + words_all + "</code>";        
    }



    socket.on('set_values', function(data) {
        // console.log('set_values', data);
        graph.setValues(data)        
        $('#value').html(data['v1']);
    });


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