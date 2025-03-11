import asyncio

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.templating import Jinja2Templates
import redis.asyncio as redis

app = FastAPI()
templates = Jinja2Templates(directory="templates")
redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)


async def _countdown(from_number: int = 10, sleep_time: int = 1):
    """Runs a shared countdown and notifies all WebSocket clients."""
    await redis_client.set("countdown_running", "1")
    await redis_client.set("countdown", from_number)

    for i in range(from_number, 0, -1):
        await redis_client.set("countdown", i)
        await redis_client.publish("timer_channel", str(i))
        await asyncio.sleep(sleep_time)

    await redis_client.publish("timer_channel", "Time's up!")
    await redis_client.set("countdown", 0)
    await redis_client.set("countdown_running", "0")


@app.websocket("/ws/timer")
async def websocket_timer(websocket: WebSocket):
    """WebSocket connection that syncs with Redis pub/sub."""
    await websocket.accept()

    pubsub = redis_client.pubsub()
    await pubsub.subscribe("timer_channel")

    try:
        current_value = await redis_client.get("countdown")
        if current_value:
            await websocket.send_text(current_value)

        countdown_running = await redis_client.get("countdown_running")
        if countdown_running != "1":
            asyncio.create_task(_countdown())

        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    await websocket.send_text(message["data"])
                except WebSocketDisconnect:
                    print("Client disconnected.")
                    break

    except WebSocketDisconnect:
        print("WebSocket client disconnected.")

    finally:
        # Ensure the client unsubscribes from Redis when they disconnect
        await pubsub.unsubscribe("timer_channel")


@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
