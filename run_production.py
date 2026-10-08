from app import app, seed_db, socketio
import os

if __name__ == '__main__':
    # Initialize database
    print("Initializing Fashion World Pro Database...")
    seed_db()
    
    # Run the production server with SocketIO support
    print("\n-------------------------------------------")
    print("FASHION WORLD PRO - REAL-TIME POWERED SERVER")
    print("-------------------------------------------")
    print("Serving on http://localhost:8080")
    print("WebSockets: ENABLED")
    print("Press Ctrl+C to stop.\n")
    
    socketio.run(app, host='0.0.0.0', port=8080)
