from app import app
import webbrowser
import threading

def open_browser():
    webbrowser.open_new("http://127.0.0.1:5050")

if __name__ == "__main__":
    threading.Timer(1.0, open_browser).start()
    app.run(port=5050)
