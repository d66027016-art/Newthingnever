import asyncio
import json
import os
import sys

# Add root directory to sys.path to resolve local imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

# Import the request handler from the existing api.py
from netlify.functions.api import handle_request

if __name__ == "__main__":
    try:
        # Read the event JSON passed from Javascript's stdin
        stdin_content = sys.stdin.read()
        if stdin_content:
            event = json.loads(stdin_content)
        else:
            event = {}
        
        # Execute the handler and print the result
        response = asyncio.run(handle_request(event))
        print(json.dumps(response))
    except Exception as e:
        # Return fallback error format if execution fails
        fallback_res = {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type, X-API-Key",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS"
            },
            "body": json.dumps({"error": str(e)})
        }
        print(json.dumps(fallback_res))
