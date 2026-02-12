import multiprocessing
import time
import os
import sys

# Import the entry points for both parts of your app
# Note: You might need to adjust imports based on your exact folder names
from backend.fix_engine import start_fix_engine
from frontend.app import run_dash_server

def run_backend():
    """Wrapper to start the FIX engine"""
    print(f"[Backend] Starting FIX Engine on PID {os.getpid()}...")
    try:
        # This function should contain your initiator.start() and the loop
        start_fix_engine() 
    except Exception as e:
        print(f"[Backend] Error: {e}")

def run_frontend():
    """Wrapper to start the Dash server"""
    print(f"[Frontend] Starting Dash Server on PID {os.getpid()}...")
    try:
        # This starts the Flask/Dash server
        # debug=False is important here! debug=True causes a reloader 
        # that can mess up multiprocessing on some systems.
        run_dash_server(debug=False, port=8050)
    except Exception as e:
        print(f"[Frontend] Error: {e}")

if __name__ == "__main__":
    # 1. Create the processes
    backend_process = multiprocessing.Process(target=run_backend)
    frontend_process = multiprocessing.Process(target=run_frontend)

    # 2. Start them
    backend_process.start()
    frontend_process.start()

    print("---------------------------------------------------")
    print(f"   App Running. Open browser at http://127.0.0.1:8050")
    print(f"   Press Ctrl+C to stop both processes.")
    print("---------------------------------------------------")

    # 3. Monitor and Cleanup
    try:
        while True:
            time.sleep(1)
            # Optional: Check if processes are still alive
            if not backend_process.is_alive():
                print("[Monitor] Backend died. Shutting down...")
                break
            if not frontend_process.is_alive():
                print("[Monitor] Frontend died. Shutting down...")
                break
    except KeyboardInterrupt:
        print("\n[Monitor] Stopping...")

    # 4. Graceful Shutdown
    backend_process.terminate()
    frontend_process.terminate()
    backend_process.join()
    frontend_process.join()
    print("[Monitor] Shutdown Complete.")