from flask import Flask, jsonify, request
from flask_cors import CORS
from dataStore import S1Fetcher

#app instance
app = Flask(__name__)
CORS(app)

@app.route("/api/home", methods=['GET'])
def return_home():
    return jsonify({
        'message':"Hello World!",
        'people': ['jack', 'barry', 'harry']
    })

@app.route("/api/ipos", methods=['GET'])
def fetch_ipos():
    start = request.args.get('start','2025-07-02')
    end   = request.args.get('end','2025-07-11')
    fetcher = S1Fetcher()
    ipo_data = fetcher.fetch(start, end)
    return jsonify(ipo_data)



if __name__ == "__main__":
    app.run(debug=True, port=8080)



