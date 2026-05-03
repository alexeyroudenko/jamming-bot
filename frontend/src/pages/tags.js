import React from "react";
import cloud from "d3-cloud";
import { Url } from '../constants'
import { CloudUrl } from '../constants'
import io from "socket.io-client"
import '../App.css';

const PLACEHOLDER_TAGS = [
  { value: 'loading', count: 38 },
  { value: 'tags', count: 30 },
  { value: 'cloud', count: 28 },
]

/** Укладка как в [d3-cloud](https://github.com/jasondavies/d3-cloud): спираль Archimedean, плотно к центру; цвета — нейтральные (см. CSS). */
const D3_CLOUD_FONT = '"Segoe UI", "Helvetica Neue", Helvetica, Arial, sans-serif'
const D3_CLOUD_TAG_LIMIT = 220
const D3_CLOUD_FONT_MIN = 12
const D3_CLOUD_FONT_MAX = 56

function d3CloudRotateDeg(text) {
  const s = String(text)
  let h = 0
  for (let i = 0; i < s.length; i++) {
    h = (h + s.charCodeAt(i) * (i + 1)) % 997
  }
  return h % 10 < 3 ? 90 : 0
}

function limitTagsForD3Cloud(tags) {
  if (!tags || !tags.length) return []
  if (tags.length <= D3_CLOUD_TAG_LIMIT) return tags
  return [...tags].sort((a, b) => b.count - a.count).slice(0, D3_CLOUD_TAG_LIMIT)
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
    this._cloudInnerRef = React.createRef();
    this._ovalRo = null
    this._ovalObservedEl = null
    this._cloudLayout = null
    this._cloudLayoutGeneration = 0
    this._cloudLayoutDebounce = null
    this.state = {
      loaded: false,
      error: false,
      cloudSize: { w: 0, h: 0 },
      cloudWords: [],
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
        // API returns { data: [...], page, limit, total_jobs }; legacy may be a bare array.
        const logs = Array.isArray(data) ? data : (data && data.data) || []
        this.setState({
          loaded: true,
          logs,
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
        if (el) el.scrollLeft = el.scrollWidth
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

  componentDidUpdate(prevProps, prevState) {
    this._ensureOvalResizeObserver()
    const { cloudSize, tags, loaded } = this.state
    const sizeOk = cloudSize.w > 0 && cloudSize.h > 0
    const prevSize = prevState.cloudSize
    const sizeChanged =
      prevSize.w !== cloudSize.w || prevSize.h !== cloudSize.h
    const tagsChanged = prevState.tags !== tags
    if (loaded && sizeOk && (tagsChanged || sizeChanged)) {
      this._scheduleD3CloudLayout()
    }
  }

  _scheduleD3CloudLayout() {
    if (this._cloudLayoutDebounce) window.clearTimeout(this._cloudLayoutDebounce)
    this._cloudLayoutDebounce = window.setTimeout(() => {
      this._cloudLayoutDebounce = null
      this._runD3CloudLayout()
    }, 90)
  }

  _runD3CloudLayout() {
    const { tags, cloudSize } = this.state
    const w = cloudSize.w
    const h = cloudSize.h
    const limited = limitTagsForD3Cloud(tags)
    if (!w || !h || !limited.length) {
      this.setState({ cloudWords: [] })
      return
    }
    if (this._cloudLayout) {
      this._cloudLayout.stop()
      this._cloudLayout = null
    }
    this._cloudLayoutGeneration += 1
    const gen = this._cloudLayoutGeneration
    const counts = limited.map((t) => t.count)
    const minC = Math.min(...counts)
    const maxC = Math.max(...counts)
    const words = limited.map((t) => ({
      text: String(t.value),
      count: t.count,
    }))

    const layout = cloud()
      .size([w, h])
      .words(words)
      .text((d) => d.text)
      .timeInterval(10)
      .padding(1)
      .spiral('archimedean')
      .rotate((d) => d3CloudRotateDeg(d.text))
      .font(D3_CLOUD_FONT)
      .fontWeight(700)
      .fontSize((d) => {
        if (minC === maxC) return (D3_CLOUD_FONT_MIN + D3_CLOUD_FONT_MAX) / 2
        return (
          D3_CLOUD_FONT_MIN +
          ((d.count - minC) / (maxC - minC)) * (D3_CLOUD_FONT_MAX - D3_CLOUD_FONT_MIN)
        )
      })
      .on('end', (out) => {
        if (gen !== this._cloudLayoutGeneration) return
        this.setState({ cloudWords: out || [] })
      })
    this._cloudLayout = layout
    layout.start()
  }

  _ensureOvalResizeObserver() {
    const el = this._cloudInnerRef.current
    if (!el || el === this._ovalObservedEl) return
    if (this._ovalRo) {
      this._ovalRo.disconnect()
    }
    this._ovalObservedEl = el
    this._ovalRo = new ResizeObserver((entries) => {
      const cr = entries[0]?.contentRect
      if (!cr) return
      const w = Math.round(cr.width)
      const h = Math.round(cr.height)
      this.setState((prev) => {
        if (prev.cloudSize.w === w && prev.cloudSize.h === h) return null
        return { cloudSize: { w, h } }
      })
    })
    this._ovalRo.observe(el)
    const w0 = Math.round(el.clientWidth)
    const h0 = Math.round(el.clientHeight)
    if (w0 > 0 && h0 > 0) {
      this.setState((prev) => {
        if (prev.cloudSize.w === w0 && prev.cloudSize.h === h0) return null
        return { cloudSize: { w: w0, h: h0 } }
      })
    }
  }

  componentWillUnmount() {
    if (this._cloudLayoutDebounce) {
      window.clearTimeout(this._cloudLayoutDebounce)
      this._cloudLayoutDebounce = null
    }
    if (this._cloudLayout) {
      this._cloudLayout.stop()
      this._cloudLayout = null
    }
    if (this._ovalRo) {
      this._ovalRo.disconnect()
      this._ovalRo = null
    }
    this._ovalObservedEl = null
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
    const phraseHighlight = new Set(this.state.phraseHighlightValues)
    const { cloudWords, cloudSize } = this.state

    return (
      <div className="tags-page-root">
        <details className="tags-page-details">
          <summary className="tags-page-details__summary">
            Логи шагов, события, текущий шаг
          </summary>
          <div className="tags-page-details__body">
            <section className="tags-console-section" aria-label="Step logs">
              <h3 className="tags-console-section__title">Шаги</h3>
              {!this.state.logs ? null : this.state.logs.slice().reverse().map((step, index) => (
                <div key={index} className="tags-log-line">
                  <code>{step['step']}</code>{' '}
                  <code className={step['status_string']}>{step['status_code']}</code>{' '}
                  <code><a href={step['url']} target="_blank" rel="noopener noreferrer">{step['url']}</a></code>
                </div>
              ))}
            </section>
            <section className="tags-console-section" aria-label="Events">
              <h3 className="tags-console-section__title">События</h3>
              {!this.state.events ? null : this.state.events.slice().reverse().map((step, index) => (
                <div key={index} className="tags-event-line">
                  <code className={step['status_string']}>{step['event']}</code>
                </div>
              ))}
            </section>
            <section className="tags-console-section" aria-label="Current step and semantics">
              <h3 className="tags-console-section__title">Текущий шаг</h3>
              <div className="tags-meta-block tags-meta-block--step">
                <p className="tags-meta-heading">Step {this.state.step?.['step']}</p>
                <div className="tags-meta-url">
                  <code><a href={this.state.step?.['url']}>{this.state.step?.['url']}</a></code>
                </div>
                <ul className="tags-meta-list">
                  <li><code>from <a href={this.state.step?.['src_url']}>{this.state.step?.['src_url']}</a></code></li>
                  <li><code className={this.state.step?.['status_string']}>status: {this.state.step?.['status_code']}</code></li>
                  <li><code>ip: {this.state.step?.['ip']}</code></li>
                  <li><code>{this.state.step?.['struct_text']}</code></li>
                </ul>
              </div>
              <div className="tags-meta-block tags-meta-block--semantics">
                <ul className="tags-semantic-log-list">
                  {!this.state.semantics_log ? null : [].concat(this.state.semantics_log.slice().reverse()).slice(0, 32).map((step, index) => (
                    <li key={index}><code>{step}</code></li>
                  ))}
                </ul>
              </div>
            </section>
          </div>
        </details>

        <section className="tags-page-cloud" aria-label="Tag cloud">
          <div className="tags-page-cloud__clip">
            <div
              className="tags-d3-cloud"
              ref={this._cloudInnerRef}
              role="list"
            >
              {cloudWords.map((d, i) => {
                const highlighted = phraseHighlight.has(d.text)
                const w = cloudSize.w
                const h = cloudSize.h
                return (
                  <span
                    role="listitem"
                    key={`${d.text}-${i}`}
                    className={
                      'tags-d3-cloud__word' +
                      (highlighted ? ' tags-d3-cloud__word--highlight' : '')
                    }
                    style={{
                      position: 'absolute',
                      left: `${w / 2 + d.x}px`,
                      top: `${h / 2 + d.y}px`,
                      transform: `translate(-50%, -50%) rotate(${d.rotate}deg)`,
                      fontSize: `${d.size}px`,
                      fontFamily: d.font || D3_CLOUD_FONT,
                      fontWeight: d.weight != null ? d.weight : 700,
                      lineHeight: 1.05,
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {d.text}
                  </span>
                )
              })}
            </div>
          </div>
        </section>

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
