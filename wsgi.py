from main import app

# Import the app from main.py to be served by gunicorn
# The app is already configured and ready to use

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)