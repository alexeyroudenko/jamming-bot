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

/** react-tagcloud v2: chip style; optional highlightSet marks auto-selected phrase words in red. */
function tagsTagRenderer(tag, size, _color, highlightSet) {
  const { className, style, ...rest } = tag.props || {}
  const key = tag.key || tag.value
  const highlighted = highlightSet && highlightSet.has(tag.value)
  const tagStyle = {
    display: 'inline-block',
    margin: '5px 4px',
    verticalAlign: 'middle',
    backgroundColor: highlighted ? '#c41e1e' : '#003399',
    color: '#f5f5f5',
    fontSize: `${size}px`,
    fontFamily: 'Verdana',
    fontWeight: 500,
    padding: '11px 12px',
    lineHeight: 1.25,
    borderRadius: '3px',
    border: highlighted ? '2px solid #ff6b6b' : '0px solid #243552',
    boxSizing: 'border-box',
    ...style,
  }
  let tagClassName = 'tag-cloud-tag tags-tag-chip'
  if (className) tagClassName += ` ${className}`
  if (highlighted) tagClassName += ' tags-tag-chip--highlight'
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
 * Home route: step logs + tag cloud
 */
export default class Tags extends React.Component {

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
      struct_text: "...",
      phraseHighlightValues: [],
      phraseHistory: [],
    }
    this.socket = io(Url, { transports: ["websocket", "polling"] })
    this._phraseLoopActive = false
    this._phraseTimeoutId = null
    this._phraseFeedRef = React.createRef()
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
        this._startPhraseHighlightLoop()
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

  _startPhraseHighlightLoop() {
    if (this._phraseLoopActive) return
    this._phraseLoopActive = true
    this._schedulePhraseTick()
  }

  _schedulePhraseTick() {
    if (!this._phraseLoopActive) return
    const delayMs = 3000 + Math.random() * 2000
    this._phraseTimeoutId = window.setTimeout(() => this._runPhraseTick(), delayMs)
  }

  _runPhraseTick() {
    if (!this._phraseLoopActive) return
    this.setState(
      (prev) => {
        const tags = prev.tags
        if (!tags || tags.length < 2) {
          return { phraseHighlightValues: [] }
        }
        const phraseLen = 2 + Math.floor(Math.random() * 2)
        const len = Math.min(phraseLen, tags.length)
        const maxStart = tags.length - len
        const start = Math.floor(Math.random() * (maxStart + 1))
        const slice = tags.slice(start, start + len)
        const phrase = slice.map((t) => t.value).join(' ')
        const phraseHighlightValues = slice.map((t) => t.value)
        const phraseHistory = [...prev.phraseHistory, phrase].slice(-3)
        return { phraseHighlightValues, phraseHistory }
      },
      () => {
        const el = this._phraseFeedRef.current
        if (el) el.scrollTop = el.scrollHeight
        this._schedulePhraseTick()
      }
    )
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
    this._phraseLoopActive = false
    if (this._phraseTimeoutId) {
      window.clearTimeout(this._phraseTimeoutId)
    }
    if (this._tagsPollId) {
      clearInterval(this._tagsPollId)
    }
    this.socket.disconnect()
  }




  render() {

    if (!this.state.loaded)
    {
      return <p className="tags-page-muted">Loading...</p>
    } else if (this.state.error) {
      console.log("error")
      return <p className="tags-page-muted">Error loading logs</p>
    }
    else return (
      <div className="Graph3d tags-page-root">
        <h1 className="tags-page-title">logs</h1>
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
          className="tags-tag-cloud"
          minSize={6}
          maxSize={128}
          tags={this.state.tags}
          renderer={(tag, size, color) =>
            tagsTagRenderer(
              tag,
              size,
              color,
              new Set(this.state.phraseHighlightValues)
            )
          }
          disableRandomColor={true}
        />
        </div>

        <div
          className="tags-phrase-feed"
          ref={this._phraseFeedRef}
          role="log"
          aria-live="polite"
          aria-label="Auto-captured word phrases from tag cloud"
        >
          {this.state.phraseHistory.map((line, i) => (
            <div key={i} className="tags-phrase-feed__line">
              {line}
            </div>
          ))}
        </div>
    
      </div>
    )
  }
}
