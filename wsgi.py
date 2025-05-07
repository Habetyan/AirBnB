import os
from app.app import app
import app.pages.home
import app.pages.geo_visualizations
import app.pages.technical

server = app.server

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(debug=False, host='0.0.0.0', port=port)
