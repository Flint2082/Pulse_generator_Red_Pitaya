import asyncio
import http.client as http_client
import websockets
import json


RP_IP = "rp-f0f587.local"  # Update with your RP's IP address
PORT = 8000

# Simple script to test the server
if __name__ == "__main__":
    
    try:
        conn = http_client.HTTPConnection(RP_IP, PORT)
    except Exception as e:
        print(f"Error connecting to server: {e}")
        exit(1)

    # Start streaming
    conn.request("POST", "/start")
    response = conn.getresponse()
    print(f"Start response: {response.status} {response.reason}")