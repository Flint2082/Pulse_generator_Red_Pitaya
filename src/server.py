import asyncio
from contextlib import asynccontextmanager
import random
from pathlib import Path
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect 
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

from packages.pulse_gen_interface import PulseGenInterface 


WEB_DIR = Path(__file__).parent.parent / "web"

# ----------------------
# Datastructures
# ----------------------

class PeriodConfig(BaseModel):
    period_length_ticks: int

class PulseConfig(BaseModel):
    output_idx: int
    pulse_idx: int
    start: int
    stop: int

class PulseTrainConfig(BaseModel):
    output_idx: int
    pulse_train: list[tuple[int, int]]
    
    
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
    app.state.pulser.stop()
    print("Server shutting down, pulse generator cleaned up")

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or put your frontend's URL instead of "*"
    allow_methods=["*"],  # allow GET, POST, OPTIONS, etc.
    allow_headers=["*"],  # allow any headers
)



# ----------------------
# REST API
# ----------------------

# GET endpoints

@app.get("/api/get_status")
async def status():
    status = app.state.pulser.get_status()
    return {"status": status}

@app.get("/api/get_system_info")
async def system_info():
    return {
        "fpg_file": app.state.pulser.fpg_file.split("/")[-1],
        "fpga_clock_freq": app.state.pulser.fpga_clock_freq_Hz,
        "num_outputs": app.state.pulser.NUM_OUTPUTS,
        "max_pulses_per_output": app.state.pulser.MAX_PULSES_PER_OUTPUT
    }

@app.get("/api/get_pulse_config")
async def get_pulse_config():
    pulse_data = app.state.pulser.get_pulse_data()
    return {"pulse_data": pulse_data}

@app.get("/api/get_cycle_count")
async def get_cycle_count():
    cycle_count = app.state.pulser.get_cycle_count()
    return {"cycle_count": cycle_count}

# POST endpoints

@app.post("/api/start")
async def start():
    app.state.pulser.start()
    return JSONResponse({"status": "started"})


@app.post("/api/stop")
async def stop():
    app.state.pulser.stop()
    return JSONResponse({"status": "stopped"})


@app.post("/api/reset")
async def reset():
    app.state.pulser.reset()
    return JSONResponse({"status": "pulse generator counters reset"})


@app.post("/api/clear_outputs")
async def clear_outputs():
    app.state.pulser.clear_all_outputs()
    return JSONResponse({"status": "all outputs cleared"})

@app.post("/api/set_period")
async def set_period(config: PeriodConfig):
    try:
        app.state.pulser.set_period(config.period_length_ticks)
        return JSONResponse({"status": "period updated", "received": config.model_dump()})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/set_pulse")
async def set_pulse(config: PulseConfig):
    try:
        app.state.pulser.set_pulse(config.output_idx, config.pulse_idx, config.start, config.stop)
        return JSONResponse({"status": "pulse config updated", "received": config.model_dump()})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/set_pulse_train")
async def set_pulse_train(config: PulseTrainConfig):
    try:
        app.state.pulser.set_pulse_train(config.output_idx, config.pulse_train)
        return JSONResponse({"status": "pulse train config updated", "received": config.model_dump()})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    
app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")