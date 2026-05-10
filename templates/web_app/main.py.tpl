$all_imports

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

APP_NAME = "$app_name"
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

$python_logic

@app.route("/")
def index():
    return send_file(os.path.join(os.path.dirname(__file__), "templates", "index.html"))

$extra_routes

if __name__ == "__main__":
    port = int(os.environ.get("KROWORK_PORT", 5000))
    print(APP_NAME + " running at http://127.0.0.1:" + str(port))
    app.run(host="127.0.0.1", port=port, debug=False)
