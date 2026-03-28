import React from "react";
import { Url } from '../constants'
import { CloudUrl } from '../constants'
import io from "socket.io-client"
import '../App.css';



import { TagCloud } from 'react-tagcloud'

const PLACEHOLDER_TAGS = [
  { value: 'loading', count: 38 },
  { value: 'tags', count: 30 },
  { value: 'cloud', count: 28 },
]

/** react-tagcloud v2: chip style (dark blue tile + white text), like the legacy UI. */
function logsTagRenderer(tag, size, _color) {
  const { className, style, ...rest } = tag.props || {}
  const key = tag.key || tag.value
  const tagStyle = {
    display: 'inline-block',
    margin: '5px 4px',
    verticalAlign: 'middle',
    backgroundColor: '#003399',
    color: '#f5f5f5',
    fontSize: `${size}px`,
    fontFamily: 'Verdana',
    fontWeight: 500,
    padding: '11px 12px',
    lineHeight: 1.25,
    borderRadius: '3px',
    border: '0px solid #243552',
    boxSizing: 'border-box',
    ...style,
  }
  let tagClassName = 'tag-cloud-tag logs-tag-chip'
  if (className) tagClassName += ` ${className}`
  return (
    <span className={tagClassName} style={tagStyle} key={key} {...rest}>
      {tag.value}
    </span>
  )
}

async function fetchJson(url) {
  const res = await fetch(url, { method: 'GET' })
  const ct = res.headers.get('content-type') || ''
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`)
  }
  if (!ct.includes('application/json')) {
    throw new Error('Expected JSON, got non-JSON response')
  }
  return res.json()
}

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
      tags: PLACEHOLDER_TAGS,
      step: {},
      struct_text: "..."
    }
    this.socket = io(Url, { transports: ["websocket", "polling"] })
  }

  fetchAPI() {
    console.log("fetchAPI")
    const API_URL = Url+"/api/steps/"
    fetchJson(API_URL)
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


      this._tagsPollId = setInterval(() => {
        const url = CloudUrl
        console.log("first tags request", url)
        fetchJson(url)
          .then((result) => {
            const tags = result.map((tag) => ({
              value: tag.name,
              count: tag.count,
            }))
            this.setState({ tags })
          })
          .catch((err) => console.warn("tags poll:", err.message))
      }, 2000)

    }
  }

  componentDidUpdate() {
  }

  componentWillUnmount() {
    if (this._tagsPollId) {
      clearInterval(this._tagsPollId)
    }
    this.socket.disconnect()
  }




  render() {

    if (!this.state.loaded)
    {
      return <p className="logs-page-muted">Loading...</p>
    } else if (this.state.error) {
      console.log("error")
      return <p className="logs-page-muted">Error loading logs</p>
    }
    else return (
      <div className="Graph3d">
        <h1 className="logs-page-title">logs</h1>
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

        <div className="semantic_cloud">
        <TagCloud
          className="logs-tag-cloud"
          minSize={6}
          maxSize={128}
          tags={this.state.tags}
          renderer={logsTagRenderer}
          disableRandomColor={true}
          onClick={tag => alert(`'${tag.value}' was selected!`)}
        />
        </div>
    
      </div>
    )
  }
}