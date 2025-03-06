# import pytest
# from httpx import AsyncClient
# from starlette.testclient import TestClient
# from websockets import connect
# import asyncio

# from main import app  # Import your FastAPI app

# @pytest.fixture
# async def test_client():
#     async with AsyncClient(app=app, base_url="http://test") as ac:
#         yield ac

# @pytest.mark.asyncio
# async def test_websocket_chat():
#     uri = "ws://localhost:8000/chat/ws"
    
#     async with connect(uri) as websocket:
#         await websocket.send('{"query": "Tell me about stock trends"}')
#         response = await websocket.recv()
        
#         assert response is not None
#         assert isinstance(response, str)  # Ensure it's a valid string response



import asyncio
import websockets
import json

import urllib.parse


JWT_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI1NzY3N2Q4Yy0wOWM4LTQ3MjItYWIzNy0wMTE2ZDA3N2EzYWYiLCJhdWQiOlsiZmFzdGFwaS11c2VyczphdXRoIl19.6m9mC-escj2eWbdgrwB-_D0rCiHvoeHm1bqSB_0_gvE"

encoded_token = urllib.parse.quote(JWT_TOKEN)

async def test_websocket():
    uri = f"ws://localhost:8000/chat/ws?token={JWT_TOKEN}"
    
    async with websockets.connect(uri) as websocket:
        print("Connected to WebSocket server.")

        # Send a test message
        test_message = {"query": "Tell me about stock trends"}
        await websocket.send(json.dumps(test_message))
        print(f"Sent: {test_message}")

        # Receive response
        while True:
            try:
                response = await websocket.recv()
                print(f"Received: {response}")
            except websockets.exceptions.ConnectionClosed:
                print("Connection closed by the server.")
                break

# Run the test
asyncio.run(test_websocket())
