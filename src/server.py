import asyncio
import random
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

app = FastAPI()

# Shared state
clients = set()
streaming = False

# Simulated data source (replace with RP acquisition)
async def data_generator():
    while True:
        if streaming:
            data = {
                "value": random.random(),
                "timestamp": asyncio.get_event_loop().time()
            }

            # Broadcast to all clients
            disconnected = set()
            for ws in clients:
                try:
                    await ws.send_json(data)
                except:
                    disconnected.add(ws)

            clients.difference_update(disconnected)

        await asyncio.sleep(0.05)  # 20 Hz

# Start background task
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(data_generator())


# ----------------------
# REST API
# ----------------------

@app.post("/start")
async def start():
    global streaming
    streaming = True
    return JSONResponse({"status": "started"})


@app.post("/stop")
async def stop():
    global streaming
    streaming = False
    return JSONResponse({"status": "stopped"})


@app.get("/status")
async def status():
    return {"streaming": streaming, "clients": len(clients)}


# ----------------------
# WebSocket
# ----------------------

@app.websocket("/stream")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.add(websocket)

    try:
        while True:
            # Keep connection alive / receive commands if needed
            await websocket.receive_text()
    except WebSocketDisconnect:
        clients.remove(websocket)