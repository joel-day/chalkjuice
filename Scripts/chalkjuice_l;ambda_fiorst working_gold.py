import json
import boto3
import csv
import pandas as pd
import os
import itertools




s3 = boto3.client("s3")

# Construct the API Gateway Management API URL
api_gateway_endpoint = "https://0t9yhsvorj.execute-api.us-east-2.amazonaws.com/production"
api_client = boto3.client("apigatewaymanagementapi", endpoint_url=api_gateway_endpoint)


BUCKET_NAME = "chalkjuice"
CSV_FILE_NAME = "gold_all_49.csv"
CHUNK_SIZE = 50  # Number of rows per JSON chunk

def lambda_handler(event, context):
    print("Event received:", json.dumps(event))  # Debugging
    connection_id = event.get("connection_id")
    if not connection_id:
        print("No connection ID found")
        return {"statusCode": 400, "body": "Missing connection ID"}
    print(f"Connection ID: {connection_id}")




    # Read CSV file from S3
    obj = s3.get_object(Bucket=BUCKET_NAME, Key=CSV_FILE_NAME)
    csv_data = obj["Body"].read().decode("utf-8").splitlines()

    # Parse CSV
    csv_reader = csv.reader(csv_data)
    headers = next(csv_reader)  # Extract headers from the first row

    # Send headers separately
    send_chunk(connection_id, {"label": "headers", "data": headers})

    filtered_rows = list(itertools.islice(csv_reader, 1000))

    chunk = []
    count = 0

    for row in filtered_rows:
        chunk.append(row)  # Keep rows as lists (not dicts)
        count += 1

        # Send data in chunks
        if count >= CHUNK_SIZE:
            send_chunk(connection_id, {"label": "chunk", "data": chunk})
            chunk = [] 
            count = 0

    send_chunk(connection_id, {"label": "chunk", "data": chunk})

    return {"statusCode": 200, "body": "Streaming started"}

def send_chunk(connection_id, message):
    """Send JSON chunk via WebSocket"""
    api_client.post_to_connection(ConnectionId=connection_id, Data=json.dumps(message).encode("utf-8"))




    
    




                            