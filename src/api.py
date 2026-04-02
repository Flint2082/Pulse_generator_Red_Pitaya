from fastapi import FastAPI
from packages.pulse_gen_interface import PulseGenInterface


# --- init hardware ---
controller = PulseGenInterface()
app = FastAPI()

# --- API endpoints ---

@app.post("/start")
def start():
    controller.start()
    return {"status": "started"}

@app.post("/stop")
def stop():
    controller.stop()
    return {"status": "stopped"}

@app.get("/status")
def status():
    return controller.get_status()