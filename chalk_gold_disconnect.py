import json
import boto3

dynamodb = boto3.client("dynamodb")
table_name = "ws_active"

def lambda_handler(event, context):
    print("Received event:", json.dumps(event, indent=2))  # Logs the entire event for debugging
    connection_id = event["requestContext"]["connectionId"]
    print(f"Removing connection_id: {connection_id} from {table_name}")

    try:
        # Remove the connection_id from DynamoDB
        dynamodb.delete_item(
            TableName=table_name,
            Key={"connection_id": {"S": connection_id}}  # Specify the key to delete
        )
        return {"statusCode": 200, "body": "Disconnected"}
    except Exception as e:
        print(f"Error removing connection_id: {e}")
        return {"statusCode": 500, "body": "Error removing connection"}

