from fastapi import FastAPI
from packages.pulse_gen_interface import PulseGenInterface

import casperfpga

# --- init hardware ---
fpga = casperfpga.CasperFpga("localhost")  # or 127.0.0.1
controller = PulseGenInterface(fpga)


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

