from flask import Flask, send_from_directory, request, jsonify
import screenclient
import traceback
import sys    
app = Flask(__name__, static_url_path='', static_folder='www/build')
defaultText = [a.rstrip('\n') for a in open("default.txt").readlines()]
lastText = defaultText

if len(sys.argv) > 1:
  host = sys.argv[1]
else:
  host = "localhost"
print("Using led screen at " + host)
  
@app.route('/')
def root():
  return app.send_static_file('index.html')

@app.route("/api/")
def hello():
  return "LED Api"

@app.route("/api/screen", methods=['POST'])
def screen():
  global lastText
  data = request.get_json()
  lastText = data
  print(data)
  try: 
    client = screenclient.ScreenClient(host)
    client.doUpdate(data)
  except Exception as e:
    print e.message
    traceback.print_exc()
    return e.message, 500
  else: 
    return "Done."

@app.route("/api/last", methods=['GET'])
def last():
  global lastText
  return jsonify(results=lastText)
  
@app.route("/api/default", methods=['GET'])
def getDefault():
  global defaultText
  return jsonify(results=defaultText)

if __name__ == "__main__":
  app.run(host='0.0.0.0')