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
    var width = this.props.width * 14 + 26;
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
    this.updateScreen();
    this.setLines("last")
  }
  
  setLines(variant) {
    fetch("/api/" + variant).then(function(response){
      response.json().then(function(result) {
        var rules = this.state.rules;
        var lines = result.results
        console.log(lines);
        for(var i=0; i< this.props.ledHeight;i++) {
          rules[i].text = lines[i]
        }
        this.updateScreen();
      }.bind(this))
    }.bind(this))
  }
  updateScreen() {
    var rules = [];
    for(var i=0; i< this.props.ledHeight;i++) {
      var line = this.state.rules[i].text;
      var diff = this.props.ledWidth - line.length
      if (diff > 0) {
        line += " ".repeat(diff);
      } else if (diff < 0) {
        line = line.substr(0, this.props.ledWidth)
      }
      rules.push(line)
    }
    this.props.onUpdate(rules)
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
      }), function() {
        this.updateScreen();
      }.bind(this))
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
        <Button bsStyle='link' onClick={this.setLines.bind(this,"default")}>Default</Button>
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
    this.onLedUpdate = this.onLedUpdate.bind(this);
  }
  componentWillMount() {
    this.state={status: "ready", rules: []}
  }
  
  onLedUpdate(rules) {
    this.setState({rules: rules});
  }
  
  onUpdate() {
    this.setState({status: "updating"})
    var body =  JSON.stringify(this.state.rules);
    fetch("/api/screen", {method: "POST", body: body, headers: new Headers({
		'Content-Type': 'application/json'
	})}).then(function(response){
      response.text().then(function(responseText) {
        console.log(responseText, response.ok);
        if(response.ok) {
          this.setState({status: "ready", error: ""});
        }else{
          console.log({status: "error", error: responseText})
          this.setState({status: "error", error: responseText});
        }
      }.bind(this))
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
          <Navbar.Text>
           {this.state.error}
          </Navbar.Text>
          <Navbar.Form pullRight>
            <Button bsStyle='primary' className={(this.state.status === "ready") ? "": "disabled"} onClick={this.onUpdate}>Update screen</Button>
          </Navbar.Form>
        </Navbar>
        <div className="App-editor">
          <LedScreen onUpdate={this.onLedUpdate} ledHeight='8' ledWidth='20'/>
        </div>
          
      </div>
    );
  }
}

export default App;
