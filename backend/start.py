import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from __init__ import create_app

app = create_app()

HOST = os.environ.get('BACKEND_HOST', '0.0.0.0')
PORT = int(os.environ.get('BACKEND_PORT', 5000))

if __name__ == '__main__':
    print(f"Database initialized, starting server on http://localhost:{PORT}")
    app.run(debug=True, host=HOST, port=PORT)
