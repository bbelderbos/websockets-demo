import asyncio

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.templating import Jinja2Templates

app = FastAPI()
templates = Jinja2Templates(directory="templates")

countdown_state = {"countdown": 0, "running": False}
countdown_lock = asyncio.Lock()
listeners = set()


async def _countdown(from_number: int = 10, sleep_time: int = 1):
    """Runs a shared countdown and notifies all WebSocket clients."""
    async with countdown_lock:
        if countdown_state["running"]:
            return
        countdown_state["running"] = True
        countdown_state["countdown"] = from_number

    for i in range(from_number, 0, -1):
        async with countdown_lock:
            countdown_state["countdown"] = i

        for ws in list(listeners):
            try:
                await ws.send_text(str(i))
            except WebSocketDisconnect:
                listeners.discard(ws)

        await asyncio.sleep(sleep_time)

    for ws in list(listeners):
        try:
            await ws.send_text("Time's up!")
        except WebSocketDisconnect:
            listeners.discard(ws)

    async with countdown_lock:
        countdown_state["countdown"] = 0
        countdown_state["running"] = False


@app.websocket("/ws/timer")
async def websocket_timer(websocket: WebSocket):
    """WebSocket connection that syncs with the shared in-memory state."""
    await websocket.accept()
    listeners.add(websocket)

    try:
        async with countdown_lock:
            current_value = countdown_state["countdown"]
            await websocket.send_text(str(current_value))
            if not countdown_state["running"]:
                asyncio.create_task(_countdown())

        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        print("WebSocket client disconnected.")
    finally:
        listeners.discard(websocket)


@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
