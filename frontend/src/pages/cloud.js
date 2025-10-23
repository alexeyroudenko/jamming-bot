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
export default class Cloud extends React.Component {

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
  selectedTags: [],
      step: {},
      struct_text: "..."
    }
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
      })
      .catch((error) => {
        console.log(error)
        this.setState({
          loaded: true, 
          error: true
        })
      });
  }

  componentDidMount() {
    console.log("cloud componentDidMount")
    if (this.state.loaded === false) {
      this.fetchAPI();

      this.updateTimer = setInterval(() => {
        const url = CloudUrl
        console.log("cloud tags request", url)
        let dt = []
        fetch(url) 
        .then((res) => res.json())
          .then((result) => {
              var tags = []
              result.forEach((tag) => {
                let new_tag = {value: tag.name, count: tag.count}
                tags.push(new_tag)
                dt.push(new_tag)
              })
        this.setState({tags: tags})
        data = dt
            })
        }, 5000);
    }
  }

  stopUpdateTimer() {
    if (this.updateTimer) {
      clearInterval(this.updateTimer);
      this.updateTimer = null;
    }
  }

  componentDidUpdate() {
    console.log("cloud componentDidUpdate")
  }

  componentWillUnmount() {
    console.log("cloud componentWillUnmount")
    this.stopUpdateTimer()
  }  


  handleTagClick = (tag) => {
    this.setState((prevState) => {
      const isSelected = prevState.selectedTags.includes(tag.value);
      return {
        selectedTags: isSelected
          ? prevState.selectedTags.filter((t) => t !== tag.value)
          : [...prevState.selectedTags, tag.value],
      };
    });
  };

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
      <div className="Graph3d" style={{ width: '100vw', height: '100vh', overflow: 'hidden' }}>
        <div className="semantic_cloud" style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <TagCloud
          minSize={12}
          maxSize={120}
          font={"impact"}
          padding={5}
          colorOptions={options}
          fontSizeMapper={fontSizeMapper}
          tags={data}
          rotate={rotate}
          disableRandomColor={true}
          renderer={(tag, size, color) => {
            const isSelected = this.state.selectedTags.includes(tag.value);
            // Generate unique animation delay and duration based on tag
            const animationDelay = (tag.value.charCodeAt(0) % 10) * 0.1;
            const animationDuration = 3 + (tag.value.length % 5);
            
            return (
              <span
                key={tag.value}
                style={{
                  display: 'inline-block',
                  margin: '3px',
                  fontSize: size,
                  color: color,
                  fontWeight: isSelected ? 'bold' : 'normal',
                  textDecoration: isSelected ? 'underline' : 'none',
                  cursor: 'pointer',
                  background: isSelected ? '#ffeb3b' : color,
                  color: isSelected ? '#222' : color,
                  boxShadow: isSelected ? '0 0 0 2px #ffeb3b, 0 2px 8px rgba(0,0,0,0.15)' : 'none',
                  borderRadius: '4px',
                  padding: '2px 6px',
                  animation: `tagFloat ${animationDuration}s ease-in-out ${animationDelay}s infinite`,
                  position: 'relative',
                }}
                onClick={() => this.handleTagClick(tag)}
              >
                {tag.value}
              </span>
            );
          }}
        />
        </div>
      </div>
    )
  }
}