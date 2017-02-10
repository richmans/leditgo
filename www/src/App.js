import React, { Component } from 'react';
import 'bootstrap/dist/css/bootstrap.css';
import { Button, Navbar } from 'react-bootstrap';
import './App.css';
import update from 'immutability-helper';

class LedRule extends Component {
  constructor(props) {
    super(props);
    this.onChange = this.onChange.bind(this);
  }
  
  onChange(event) {
    var newValue = event.target.value;
    if (newValue.length <= this.props.width) {
      this.props.onUpdate(this.props.idx, newValue);
    }
  }
  
  render() {
    var width = this.props.width * 16;
    var style = {width: width};
    return (
      <input onChange={this.onChange} value={this.props.text} style={style} className='led-rule form-control'/>
    );
  }
}

class LedScreen extends Component {
  constructor(props) {
    super(props);
    this.onUpdateRule = this.onUpdateRule.bind(this);
  }
  
  componentWillMount() {
    var rules = [];
    for(var i=0; i< this.props.ledHeight;i++) {
      rules.push({
        "key": i,
        "text": "",
        "width": this.props.ledWidth
      });
    }
    this.state = {
      "rules": rules
    }
  }
  
  onUpdateRule(key, text) {
     if (key < this.props.ledHeight) {
      this.setState(update(this.state, {
        "rules": {
          [key]: {
            "text": {
              $set: text
            }
          }
        }
      }))
    }
  }
  
  render() {
    var rules = this.state.rules.map(function(rule) {return(
      <LedRule 
      key={rule.key}
      idx={rule.key}
      width={rule.width}
      text={rule.text}
      onUpdate={this.onUpdateRule}
       />)
    }.bind(this));
    return (
      <div className="led-screen">
        {rules}
      </div>
    )
  }
}

class StatusIndicator extends Component {
  render() {
    var text = 'Ready';
    if(this.props.indicator === "updating") text = "Sending update...";
    if(this.props.indicator === "error") text = "Failed to send update.";
    return (
      <span className={"status-" + this.props.indicator}>{text}</span>
    )
  }
}
class App extends Component {
  constructor(props) {
    super(props);
    this.onUpdate = this.onUpdate.bind(this);
  }
  componentWillMount() {
    this.state={status: "ready"}
  }
  
  onUpdate() {
    this.setState({status: "updating"})
    fetch("/api/screen", {method: "POST"}).then(function(response){
      if(response.ok) {
        return response.text();
      } else {
        throw new Error('Network response was not ok.');
      }
    }).then(function(response) {
      this.setState({status: "ready"});
    }.bind(this)).catch(function(error) {
      this.setState({status: "error"});
    }.bind(this))
  }
  
  render() {
    return (
      <div className="App">
        <Navbar>
          <Navbar.Header>
             <Navbar.Brand>
               <a href='#' >Led it go</a>
             </Navbar.Brand>
             
          </Navbar.Header>
          <Navbar.Text>
            <StatusIndicator indicator={this.state.status}/>
          </Navbar.Text>
          <Navbar.Form pullRight>
            <Button bsStyle='primary' onClick={this.onUpdate}>Update screen</Button>
          </Navbar.Form>
        </Navbar>
        <div className="App-editor">
          <LedScreen ledHeight='8' ledWidth='20'/>
        </div>
          
      </div>
    );
  }
}

export default App;
