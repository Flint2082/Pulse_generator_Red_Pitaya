import asyncio
import random
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from packages.pulse_gen_interface import PulseGeneratorInterface

app = FastAPI()

pulser = PulseGeneratorInterface()

# Shared state
clients = set()

# # Start background task
# @app.on_event("startup")
# async def startup_event():
#     asyncio.create_task(data_generator())


# ----------------------
# REST API
# ----------------------

@app.post("/start")
async def start():
    pulser.start()
    return JSONResponse({"status": "started"})


@app.post("/stop")
async def stop():
    pulser.stop()
    return JSONResponse({"status": "stopped"})


@app.get("/status")
async def status():
    status = pulser.get_status()
    return {"status": status, "clients": len(clients)}

@app.post("/clear")
async def clear():
    pulser.clear_all_outputs()
    return JSONResponse({"status": "outputs cleared"})

@app.post("/set_period")
async def set_period(params: dict):
    pulser.set_period(params["period_length_ticks"])
    return JSONResponse({"status": "period updated", "received": params})

@app.post("/set_pulse")
async def set_pulse(params: dict):
    pulser.set_pulse(params["output_idx"], params["pulse_idx"], params["start"], params["stop"])
    return JSONResponse({"status": "pulse config updated", "received": params})