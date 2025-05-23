import json
import boto3

dynamodb = boto3.client("dynamodb")
table_name = "ws_active"

def lambda_handler(event, context):
    print("Received event:", json.dumps(event, indent=2))  # Logs the entire event for debugging
    connection_id = event["requestContext"]["connectionId"]
    print(connection_id)

    try:
        # Store connection ID in DynamoDB
        dynamodb.put_item(
            TableName=table_name,
            Item={"connection_id": {"S": connection_id}}
        )

        return {'statusCode': 200, 'body': "Connection stored successfully"}

    except Exception as e:
        print(f"Error: {str(e)}")
        return {'statusCode': 500, 'body': f"Failed due to: {str(e)}"}


