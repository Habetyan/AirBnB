from app.app import server 

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 10000))
    server.run(debug=False, host='0.0.0.0', port=port)
