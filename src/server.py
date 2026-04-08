import asyncio
from contextlib import asynccontextmanager
import random
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from packages.pulse_gen_interface import PulseGenInterface 


# Shared state
clients = set()

# ----------------------
# Datastructures
# ----------------------

class periodConfig(BaseModel):
    period_length_ticks: int

class PulseConfig(BaseModel):
    output_idx: int
    pulse_idx: int
    start: int
    stop: int
    
    
# ----------------------
# Lifecycle events
# ----------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup code
    app.state.pulser = PulseGenInterface()
    print("Server started, pulse generator initialized")
    
    yield  # Control is transferred to the request handlers while the server is running
    
    # Shutdown code
    app.state.pulser.cleanup()
    print("Server shutting down, pulse generator cleaned up")

app = FastAPI(lifespan=lifespan)

# ----------------------
# REST API
# ----------------------

@app.post("/start")
async def start():
    app.state.pulser.start()
    return JSONResponse({"status": "started"})


@app.post("/stop")
async def stop():
    app.state.pulser.stop()
    return JSONResponse({"status": "stopped"})


@app.get("/status")
async def status():
    status = app.state.pulser.get_status()
    return {"status": status, "clients": len(clients)}

@app.post("/clear")
async def clear():
    app.state.pulser.clear_all_outputs()
    return JSONResponse({"status": "outputs cleared"})

@app.post("/set_period")
async def set_period(config: periodConfig):
    try:
        app.state.pulser.set_period(config.period_length_ticks)
        return JSONResponse({"status": "period updated", "received": config.model_dump()})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/set_pulse")
async def set_pulse(config: PulseConfig):
    try:
        app.state.pulser.set_pulse(config.output_idx, config.pulse_idx, config.start, config.stop)
        return JSONResponse({"status": "pulse config updated", "received": config.model_dump()})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))