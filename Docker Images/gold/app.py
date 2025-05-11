import json
import boto3
import csv

s3 = boto3.client("s3")
apigateway = boto3.client("apigatewaymanagementapi", endpoint_url="wss://peugig81gd.execute-api.us-east-2.amazonaws.com/test_1/")

BUCKET_NAME = "chalkjuice"
CSV_FILE_NAME = "gold_all_49.csv"
CHUNK_SIZE = 50  # Now sending 10 rows per chunk

def lambda_handler(event, context):
    print("Event:", json.dumps(event, indent=2))
    connection_id = event["requestContext"]["connectionId"]

    # Read CSV from S3
    obj = s3.get_object(Bucket=BUCKET_NAME, Key=CSV_FILE_NAME)
    csv_data = obj["Body"].read().decode("utf-8").splitlines()

    csv_reader = csv.reader(csv_data)
    headers = next(csv_reader)  # Extract headers

    # Send headers first
    send_chunk(connection_id, {"headers": headers})

    chunk = []
    count = 0

    for row in csv_reader:
        chunk.append(row)
        count += 1

        if count >= CHUNK_SIZE:
            send_chunk(connection_id, {"data": chunk})
            chunk = []
            count = 0

    if chunk:
        send_chunk(connection_id, {"data": chunk})  # Send any remaining data

    return {"statusCode": 200, "body": "Streaming started"}

def send_chunk(connection_id, message):
    """Send JSON chunk via WebSocket"""
    apigateway.post_to_connection(ConnectionId=connection_id, Data=json.dumps(message).encode("utf-8"))
