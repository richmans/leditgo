from flask import Flask
app = Flask(__name__)

@app.route("/api/")
def hello():
    return "LED Api"

@app.route("/api/screen", methods=['POST'])
def screen():
  return "Done."
if __name__ == "__main__":
    app.run(host='0.0.0.0')