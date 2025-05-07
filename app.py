# app.py in the root directory
from app.app import app
import app.pages.home
import app.pages.geo_visualizations
import app.pages.technical

server = app.server  # This is important for gunicorn to find the server

if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0', port=10000)