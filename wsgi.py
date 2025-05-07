# wsgi.py
from app.app import app as flask_app  
import app.pages.home
import app.pages.geo_visualizations
import app.pages.technical

server = flask_app.server 

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(debug=False, host='0.0.0.0', port=port)
