# Run:
#    $env:GEMINI_API_KEY="YOUR_API_KEY"
#    python server.py


import os
import sys
import subprocess
from fastapi import FastAPI
from fastapi.responses import FileResponse
import uvicorn

app = FastAPI()
call_process = None


@app.get("/")
def read_index():
    return FileResponse("index.html")


@app.post("/api/start_call")
def start_call():
    global call_process
    if call_process is None or call_process.poll() is not None:
        env = os.environ.copy()
        python_exe = r"C:\Users\Giridharan\AppData\Local\Python\pythoncore-3.14-64\python.exe"
        call_process = subprocess.Popen([python_exe, "speech_to_speech.py"], env=env)
        return {"status": "started"}
    return {"status": "already_running"}


@app.post("/api/stop_call")
def stop_call():
    global call_process
    if call_process and call_process.poll() is None:
        call_process.terminate()
        call_process = None
        return {"status": "stopped"}
    return {"status": "not_running"}


if __name__ == "__main__":
    print("\n==========================================")
    print("🌐 GIRISHA WEB UI SERVER RUNNING")
    print("==========================================")
    print("Open http://localhost:8000 in your web browser!\n")
    uvicorn.run(app, host="127.0.0.1", port=8000)
