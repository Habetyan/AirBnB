# wsgi.py
from app.app import app as flask_app
import app.pages.home
import app.pages.geo_visualizations
import app.pages.technical

app = flask_app  # Set the app variable at the root level
server = app  # For gunicorn

if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0', port=10000)