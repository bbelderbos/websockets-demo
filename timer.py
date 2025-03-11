import asyncio

from fastapi import FastAPI, WebSocket, Request
from fastapi.templating import Jinja2Templates

app = FastAPI()
templates = Jinja2Templates(directory="templates")


async def _countdown(from_number: int = 10, sleep_time: int = 1):
    for i in range(from_number, 0, -1):
        yield i
        await asyncio.sleep(sleep_time)


@app.websocket("/ws/timer")
async def websocket_timer(websocket: WebSocket):
    await websocket.accept()

    async for i in _countdown():
        await websocket.send_text(str(i))

    await websocket.send_text("Time's up!")
    await websocket.close()


@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
