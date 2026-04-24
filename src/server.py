from contextlib import asynccontextmanager
from pathlib import Path
import logging
import subprocess

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from packages.pulse_gen_interface import PulseGenInterface


# =========================================================
# CONFIG
# =========================================================

WEB_DIR = Path(__file__).parent.parent / "web"

logger = logging.getLogger(__name__)


# =========================================================
# DATA MODELS
# =========================================================

class PeriodConfig(BaseModel):
    period_length_ticks: int


class MaxCyclesConfig(BaseModel):
    enabled: bool
    max_cycles: int


class PulseConfig(BaseModel):
    output_idx: int
    pulse_idx: int
    start: int
    stop: int


class PulseTrainConfig(BaseModel):
    output_idx: int
    pulse_train: list[tuple[int, int]]


# =========================================================
# HELPERS
# =========================================================

def handle_error(message: str, exc: Exception) -> None:
    logger.exception(message)
    raise HTTPException(status_code=500, detail=str(exc))


def success(status: str, **extra):
    return JSONResponse({
        "status": status,
        **extra
    })


def pulser():
    return app.state.pulser


# =========================================================
# APP LIFECYCLE
# =========================================================

@asynccontextmanager
async def lifespan(app: FastAPI):

    app.state.pulser = PulseGenInterface()

    logger.info("Pulse generator initialized")

    yield

    app.state.pulser.stop()

    logger.info("Pulse generator stopped")


app = FastAPI(lifespan=lifespan)


# =========================================================
# MIDDLEWARE
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# GET ENDPOINTS
# =========================================================

@app.get("/api/get_logs")
async def get_logs():
    try:
        result = subprocess.check_output(
            ["journalctl", "-n", "50", "--no-pager"],
            text=True
        )

        return {
            "logs": result.splitlines()
        }

    except Exception as exc:
        handle_error("Failed to read logs", exc)


@app.get("/api/get_status")
async def get_status():
    try:
        return {
            "status": pulser().get_status()
        }

    except Exception as exc:
        handle_error("Failed to read status", exc)


@app.get("/api/get_system_info")
async def get_system_info():
    try:
        return {
            "fpg_file": Path(pulser().fpg_file).name,
            "fpga_clock_freq": pulser().fpga_clock_freq_Hz,
            "num_outputs": pulser().NUM_OUTPUTS,
            "max_pulses_per_output": pulser().MAX_PULSES_PER_OUTPUT,
        }

    except Exception as exc:
        handle_error("Failed to read system info", exc)


@app.get("/api/get_pulse_config")
async def get_pulse_config():
    try:
        return {
            "pulse_data": pulser().get_pulse_data()
        }

    except Exception as exc:
        handle_error("Failed to read pulse config", exc)


@app.get("/api/get_cycle_config")
async def get_cycle_config():
    try:
        cycle_config = pulser().get_cycle_config()
        return {
            "enabled": cycle_config["enabled"],
            "max_cycles": cycle_config["max_cycles"]
        }

    except Exception as exc:
        handle_error("Failed to read cycle config", exc)


@app.get("/api/get_cycle_count")
async def get_cycle_count():
    try:
        return {
            "cycle_count": pulser().get_cycle_count()
        }

    except Exception as exc:
        handle_error("Failed to read cycle count", exc)


# =========================================================
# CONTROL ENDPOINTS
# =========================================================

@app.post("/api/load_bitstream")
async def load_bitstream():
    try:
        pulser().load_bitstream()

        return success("bitstream loaded")

    except Exception as exc:
        handle_error("Failed to load bitstream", exc)


@app.post("/api/start")
async def start():
    try:
        pulser().start()

        return success("started")

    except Exception as exc:
        handle_error("Failed to start pulse generator", exc)


@app.post("/api/stop")
async def stop():
    try:
        pulser().stop()

        return success("stopped")

    except Exception as exc:
        handle_error("Failed to stop pulse generator", exc)


@app.post("/api/reset")
async def reset():
    try:
        pulser().reset()

        return success("pulse generator counters reset")

    except Exception as exc:
        handle_error("Failed to reset pulse generator", exc)


@app.post("/api/clear_outputs")
async def clear_outputs():
    try:
        pulser().clear_all_outputs()

        return success("all outputs cleared")

    except Exception as exc:
        handle_error("Failed to clear outputs", exc)


# =========================================================
# CONFIGURATION ENDPOINTS
# =========================================================

@app.post("/api/set_period")
async def set_period(config: PeriodConfig):
    try:
        pulser().set_period(config.period_length_ticks)

        return success(
            "period updated",
            received=config.model_dump()
        )

    except Exception as exc:
        handle_error("Failed to set period", exc)


@app.post("/api/set_cycle_limit")
async def set_cycle_limit(config: MaxCyclesConfig):
    try:
        pulser().set_cycle_limit_enable(config.enabled)
        pulser().set_max_cycles(config.max_cycles)

        return success(
            "cycle limit updated",
            received=config.model_dump()
        )

    except Exception as exc:
        handle_error("Failed to set cycle limit", exc)


@app.post("/api/set_pulse")
async def set_pulse(config: PulseConfig):
    try:
        pulser().set_pulse(
            config.output_idx,
            config.pulse_idx,
            config.start,
            config.stop
        )

        return success(
            "pulse updated",
            received=config.model_dump()
        )

    except Exception as exc:
        handle_error("Failed to set pulse", exc)


@app.post("/api/set_pulse_train")
async def set_pulse_train(config: PulseTrainConfig):
    try:
        pulser().set_pulse_train(
            config.output_idx,
            config.pulse_train
        )

        return success(
            "pulse train updated",
            received=config.model_dump()
        )

    except Exception as exc:
        handle_error("Failed to set pulse train", exc)


# =========================================================
# STATIC WEB UI
# =========================================================

app.mount(
    "/",
    StaticFiles(directory=WEB_DIR, html=True),
    name="web"
)