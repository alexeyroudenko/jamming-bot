import React from "react";
import { Url } from '../constants'
import { CloudUrl } from '../constants'
import io from "socket.io-client"
import '../App.css';



import { TagCloud } from 'react-tagcloud'

const fontSizeMapper = word => Math.log2(word.value) * 5;
const rotate = word => { 
  const positions = [270, 0];
  return randomFromArray(positions);
};


let data = [
  { value: 'loading', count: 38 },
  { value: 'tags', count: 30 },
  { value: 'cloud', count: 28 },
]

const randomFromArray = (myArray) =>
  myArray[Math.floor(Math.random() * myArray.length)];
const generateRandomData = () => {
  const weight = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 10000];
  const words = data(100);
  let data = [];
  for (var i = 0; i < 100; i++) {
    data.push({
      text: words[i].initCap(),
      value: randomFromArray(weight),
    });
  }
  return data;
};

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
      tags: [],
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
    // console.log("initSockets")
    this.socket.on("connect", () => {
        this.socket.emit('consumer')
        // console.log("connected to socket v1.0", this.socket.id)
    });

    this.socket.on("connect_error", (err) => { console.log(err) });
    this.socket.on("disconnect", () => {console.log("Disconnected from socket. v1.0")});

    this.socket.on("step", (msg) => {
      // let data = this.state.logs
      // data2.push(msg)      
      // let new_semantics = this.state.semantics_log;
      // if (msg['semantic']) {
      //   msg['semantic'].forEach(
      //     (element) => new_semantics.push(element['type'] + " : " + element['text'])
      //   );
      // }
      // console.log("new_semantics", new_semantics)      
      let step_data = msg;
      this.setState({
        // loaded: true, 
        // logs: data,
        step: step_data,
        // semantics_log:new_semantics,
        // struct_text: msg['struct_text']
      })
    
    })  

    this.socket.on("event", (msg) => {
      console.log("event", msg)
      if (msg['event'] === "say_finish") {
        this.setState({events: []})
      } else {
        let data2 = this.state.events
        data2.push(msg)
        this.setState({events: data2})
      }
    })  





    
  }

  componentDidMount() {




    // console.log("componentDidMount")
    if (this.state.loaded === false) {
      this.fetchAPI();


      setInterval(() => {
        const url = CloudUrl
        console.log("first tags request", url)

        let dt = []

        fetch(url)        
        .then((res) => res.json())
          .then((result) => {            
              var tags = []                
              result.forEach((tag) => {
                let new_tag = {value: tag.name, count: tag.count}
                tags.push(new_tag)
                dt.push(new_tag)
                // console.log("------------------------ ", new_tag)                      
              })
              this.setState({tags: tags})
              data = dt
            })
        }, 2000);

    }
  }

  componentDidUpdate() {
  }

  componentWillUnmount() {
    this.socket.disconnect();
  }  




  render() {

    // custom random color options
    // see randomColor package: https://github.com/davidmerfield/randomColor
    const options = {
      luminosity: 'light',
      hue: 'blue',
    }

    // console.log("render", this.state)
    if (!this.state.loaded)
    {
      return <p>Loading...</p>;
    } else if (this.state.error) {
      console.log("error")
      return <p>Error</p>;
    }
    else return (
      <div className="Graph3d">
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
    
      </div>
    )
  }
}