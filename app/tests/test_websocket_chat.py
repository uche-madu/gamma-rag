import asyncio
import websockets
import json

# 🔑 INSTRUCTIONS TO GET JWT TOKEN FROM SWAGGER UI:
# 1. Open your FastAPI Swagger UI: http://localhost:8000/docs
# 2. Register a new user using the `/register` endpoint.
# 3. Log in using the `/login` endpoint.
# 4. After a successful login, click on any secured route.
# 5. Look at the **"Authorize"** button (a lock icon) in the top-right corner.
# 6. Click it, copy the **Bearer Token**, and replace JWT_TOKEN below.

# JWT_TOKEN = "REPLACE_WITH_YOUR_JWT_TOKEN"

# Example JWT Token:
JWT_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI1NzY3N2Q4Yy0wOWM4LTQ3MjItYWIzNy0wMTE2ZDA3N2EzYWYiLCJhdWQiOlsiZmFzdGFwaS11c2VyczphdXRoIl19.6m9mC-escj2eWbdgrwB-_D0rCiHvoeHm1bqSB_0_gvE"

async def test_websocket():
    # Connect to the local WebSocket server
    uri = f"ws://localhost:8000/chat/ws?token={JWT_TOKEN}"

    # Connect to the deployed WebSocket server
    # uri = f"wss://gamma-rag-financial-advisor.onrender.com/chat/ws?token={JWT_TOKEN}"
    
    async with websockets.connect(uri) as websocket:
        print("Connected to WebSocket server.")

        # List of test queries to simulate user interactions
        test_queries = [
            {"query": "Hi! my name is John."},
            {"query": ""},
            {"query": "Is this a good time to buy upwork stocks?"},
            {"query": "What are the top news articles about Tesla?"},
            {"query": "What is the current market trend?"},
            {"query": "Can you provide an analysis of Apple's stock?"},
            {"query": "What is my name?"},
            {"query": "Is this a good time to buy Tesla stock?"},
            {"query": "What was my previous query?"}
        ]

        for test_message in test_queries:
            try:
                # Send a test message
                await websocket.send(json.dumps(test_message))
                print(f"Sent: {test_message}")

                # Receive and print the response
                response = await websocket.recv()
                print(f"Received: {response}")

            except websockets.exceptions.ConnectionClosed:
                print("Connection closed by the server.")
                break

            # Wait for a short period before sending the next query
            await asyncio.sleep(1)

# Run the test
asyncio.run(test_websocket())