import subprocess
import threading
import time
from flask import Flask, render_template
import requests

app = Flask(__name__)

# Function to check if Streamlit is running
def check_streamlit():
    try:
        response = requests.get("http://localhost:8501")
        return response.status_code == 200
    except requests.ConnectionError:
        return False

# Function to run Streamlit in a separate thread
def run_streamlit():
    subprocess.run(["streamlit", "run", "streamlit_app.py"])

# Start Streamlit in the background and ensure it starts before rendering Flask page
@app.before_first_request
def before_first_request():
    # Start Streamlit in a separate thread
    threading.Thread(target=run_streamlit).start()

    # Wait for Streamlit to be available
    while not check_streamlit():
        time.sleep(1)  # Check every second

@app.route('/')
def index():
    # Ensure Streamlit is available before loading the page
    return render_template('streamlit_embed.html')

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)  # `use_reloader=False` to avoid restarting Flask server when Streamlit starts
