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
        <div className="semantic_cloud">
        <TagCloud
          minSize={16}
          maxSize={96}
          font={"impact"}
          padding={0}
          colorOptions={options}
          fontSizeMapper={fontSizeMapper} 
          tags={data}
          rotate={rotate}
          disableRandomColor={true}
          onClick={tag => alert(`'${tag.value}' was selected!`)}
        />
        </div>
    
      </div>
    )
  }
}