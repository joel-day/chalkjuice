import json

def lambda_handler(event, context):
    print("Received event:", json.dumps(event, indent=2))  # Logs the entire event for debugging
    return {"statusCode": 200, "body": "Disconnected"}


