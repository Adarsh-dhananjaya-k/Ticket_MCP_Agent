import subprocess
import time
import sys
import os

def run_system():
    print("🚀 Starting Ticket MCP Agent System...")
    
    # Paths to the scripts
    # Using 'python' or 'venv/Scripts/python.exe' depending on environment
    python_exe = sys.executable if "venv" in sys.prefix else "python"
    
    # 1. Start MCP Server
    print("📦 Starting MCP Server...")
    mcp_server = subprocess.Popen([python_exe, "-m", "mcp_server.server"])
    time.sleep(3) # Give it a moment to bind to the port
    
    # 2. Start Teams Bot Server (App)
    print("🤖 Starting Teams Bot Server...")
    app_server = subprocess.Popen([python_exe, "-m", "agent.app"])
    time.sleep(2)
    
    # 3. Start Worker Agent
    print("👷 Starting Worker Agent...")
    worker_agent = subprocess.Popen([python_exe, "-m", "agent.worker_agent"])
    
    print("\n✅ All systems online! Press Ctrl+C to shut down.\n")
    
    try:
        # Keep the main process alive until interrupted
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down systems...")
        worker_agent.terminate()
        app_server.terminate()
        mcp_server.terminate()
        print("Bye!")

if __name__ == "__main__":
    run_system()
