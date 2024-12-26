import React from "react";
import { Url } from '../constants'
import io from "socket.io-client"
import '../App.css';



/**
 * Component that show logs
 */
export default class Logs extends React.Component {

  constructor(props) {
    super(props);
    this.myReference = React.createRef();
    this.state = {
      loaded: false,
      error: false,
      events: [],
      logs: [],
      semantics: [],
      semantics_log: [],
      step: {},
      struct_text: "..."
    }
    this.socket = io(Url, { transports: ["websocket", "polling"] })
  }

  fetchAPI() {
    console.log("fetchAPI")
    const API_URL = Url+"/api/steps/"
    fetch(API_URL, {method: "GET"})
      .then(res => res.json())
      .then(data => {
        // console.log("data", data)
        this.setState({
          loaded: true,
          logs: data
        })
        this.initSockets()
      })
      .catch((error) => {
        console.log(error)
        this.setState({
          loaded: true, 
          error: true
        })
      });
  }

  initSockets() {
    console.log("initSockets")
    this.socket.on("connect", () => {
        this.socket.emit('consumer')
        console.log("connected to socket v1.0", this.socket.id)
    });

    this.socket.on("connect_error", (err) => { console.log(err) });
    this.socket.on("disconnect", () => {console.log("Disconnected from socket. v1.0")});

    this.socket.on("step", (msg) => {
      let data = this.state.logs
      data.push(msg)      
      
      let new_semantics = this.state.semantics_log;
      if (msg['semantic']) {
        msg['semantic'].forEach(
          (element) => new_semantics.push(element['type'] + " : " + element['text'])
        );
      }
      console.log("new_semantics", new_semantics)
      
      this.setState({
        loaded: true, 
        logs: data,
        step: msg,
        semantics_log:new_semantics,
        struct_text: msg['struct_text']
      })
    
    })  

    this.socket.on("event", (msg) => {
      console.log("event", msg)
      if (msg['event'] === "say_finish") {
        this.setState({events: []})
      } else {
        let data = this.state.events
        
        data.push(msg)
        this.setState({events: data})
      }
    })  

  }

  componentDidMount() {
    console.log("componentDidMount")
    if (this.state.loaded === false) {
      this.fetchAPI();
    }
  }

  componentDidUpdate() {
  }

  componentWillUnmount() {
    this.socket.disconnect();
  }  

  render() {
    // console.log("render", this.state)
    if (!this.state.loaded)
    {
      return <p>Loading...</p>;
    } else if (this.state.error) {
      console.log("error")
      return <p>Error: {this.error.message}</p>;
    }
    else return (
      <div>
        <h1>logs</h1>
        <div className="logs">
          {!this.state.logs ? null : this.state.logs.slice().reverse().map((step, index) => (
            <div key={index} className="item">
              <code>{step['step']}</code>&nbsp;
              <code className={step['status_string']}>{step['status_code']}</code>&nbsp;
              <code><a href={step['url']} target="blank">{step['url']}</a></code>
            </div>
          ))}
        </div>
        
        <div className="events">
          {!this.state.events ? null : this.state.events.slice().reverse().map((step, index) => (
            <div key={index} className="item">
              <code className={step['status_string']}>{step['event']}</code>
            </div>
          ))}
        </div>

        <div className="struct_text">
          <h2>Step {this.state.step['step']}</h2>
          <h3><code><a href={this.state.step['url']}>{this.state.step['url']}</a></code></h3>
          <ul>
            <li><code>from <a href={this.state.step['src_url']}>{this.state.step['src_url']}</a></code></li>
            <li><code className={this.state.step['status_string']}>status: {this.state.step['status_code']}</code></li><br/>
            <li><code>ip: {this.state.step['ip']}</code></li>                                                
            <li><code>{this.state.step['struct_text']}</code></li>
          </ul>
        </div>

        <div className="semantic_log">
        <ul>
          {!this.state.semantics_log ? null : [].concat(this.state.semantics_log.slice().reverse()).slice(0, 32).map((step, index) => (
              <li><code>{step}</code></li>
          ))}
        </ul>
        </div>


        {/* <div className="semantic">
            {!this.state.step['semantic'] ? null : this.state.step['semantic'].slice().reverse().map((step, index) => (
            <div key={index} className="item">
              <code className={step['type']}>{step['type']} ::: {step['text']}</code>
            </div>
          ))}
        </div> */}


      </div>
    )
  }
}