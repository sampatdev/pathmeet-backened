import asyncio
import websockets
import json

TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIyNDI2MzU5Ny1mMDIwLTQwNTUtODNkZi02NjZiMzEyMzYwNzciLCJleHAiOjE3ODM3NzI2MTUsImp0aSI6IjQyOWQzNmVmLTU3MmYtNGIyNC04ZjgyLWNhODAwMjk5ZjJhNyJ9.rLhJmo2grVrO7Y9Y2HqRQVzOySupWT7u7wUkp-lWepU"
SESSION_ID = "744cf9ba-2217-4f18-979d-17ec74f50a57"

async def test():
    url = f"ws://localhost:8000/ws/meetup/{SESSION_ID}?token={TOKEN}"
    async with websockets.connect(url) as ws:
        await ws.send(json.dumps({"lat": 12.9716, "lng": 77.5946}))
        print("Sent location, waiting for others...")
        try:
            response = await asyncio.wait_for(ws.recv(), timeout=5)
            print("Received:", response)
        except asyncio.TimeoutError:
            print("No message received (expected if you're the only one connected)")

asyncio.run(test())



## eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIyNDI2MzU5Ny1mMDIwLTQwNTUtODNkZi02NjZiMzEyMzYwNzciLCJleHAiOjE3ODM3NzI2MTUsImp0aSI6IjQyOWQzNmVmLTU3MmYtNGIyNC04ZjgyLWNhODAwMjk5ZjJhNyJ9.rLhJmo2grVrO7Y9Y2HqRQVzOySupWT7u7wUkp-lWepU

# eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI0MTNhNGIzNC00YWU0LTQ1ZjAtYTU5YS04NTdmYzNjMzcwZDYiLCJleHAiOjE3ODM3NzI2NzIsImp0aSI6IjE0ZTcwNWIxLTM5OGUtNDNiYy1iMzc4LTMzODc5NGY1NzBiNCJ9.gVW7QopoIeqa9YCn0f2wESs1Rxg9makNwhBMchslXh8