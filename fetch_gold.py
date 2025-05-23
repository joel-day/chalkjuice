import json
import boto3
import hashlib
import time
import zlib
import pandas as pd
import csv
import io
import time
import itertools
import os

# Initialize Athena Client
AWS_REGION = "us-east-2"  # Change to your region
athena = boto3.client("athena", region_name=AWS_REGION)
ATHENA_DATABASE = "chalk"
ATHENA_TABLE = "chalkjuice_data"
ATHENA_OUTPUT_BUCKET = "s3://chalkjuice/golden_athena/"  # Replace with your actual S3 bucket

# Initialize Dynamo Client
dynamodb = boto3.client("dynamodb")
dynamodb_resource = boto3.resource("dynamodb")
DYNAMODB_TABLE = "gold_hash"
table = dynamodb_resource.Table(DYNAMODB_TABLE)

# Initialize API Gateway Client
api_gateway_endpoint = "https://0t9yhsvorj.execute-api.us-east-2.amazonaws.com/production"
api_client = boto3.client("apigatewaymanagementapi", endpoint_url=api_gateway_endpoint)

def run_athena_query(query):
    """Execute an Athena query and fetch results."""
    query_execution = athena.start_query_execution(
        QueryString=query,
        QueryExecutionContext={"Database": ATHENA_DATABASE},
        ResultConfiguration={"OutputLocation": ATHENA_OUTPUT_BUCKET}
    )
    query_execution_id = query_execution["QueryExecutionId"]


        # Wait for Query to Complete
    while True:
        status = athena.get_query_execution(QueryExecutionId=query_execution_id)
        state = status["QueryExecution"]["Status"]["State"]
        print(state)
        
        if state in ["SUCCEEDED", "FAILED", "CANCELLED"]:
            break
        
        time.sleep(.1)  # Check every .1 seconds

    if state != "SUCCEEDED":
        raise Exception(f"Athena query failed with state: {state}")
    
    # Get Query Results
    results = athena.get_query_results(QueryExecutionId=query_execution_id)

    columns = [col["Label"] for col in results["ResultSet"]["ResultSetMetadata"]["ColumnInfo"]]

    # Extract Rows
    rows = []
    for row in results["ResultSet"]["Rows"][1:]:  # Skip header row
        extracted_row = [col.get("VarCharValue", None) for col in row["Data"]]  # Extract actual values
        rows.append(extracted_row)

    df = pd.DataFrame(rows, columns=columns)
    df = df.fillna("NA")
    df.columns = df.columns.str.replace('_', ' ').str.title()
    
    
    df['Date'] = pd.to_datetime(df['Date'])  # Convert date column to datetime

    df = df.sort_values(by=['Season', 'Date'], ascending=[False, True])

    df['Date'] = df['Date'].astype(str)  # Convert the Date column to string

    
    return df

def hash_query(query):
    """Generate a SHA256 hash for the given query."""
    return hashlib.sha256(query.encode()).hexdigest()

def compress_json(df):
    # Convert DataFrame to JSON format
    json_str = df.to_json(orient="records")
    
    # Compress the JSON string
    compressed_data = zlib.compress(json_str.encode())

    return compressed_data

def decompress_json(compressed_data):
    """Decompress JSON data from zlib."""
    return json.loads(zlib.decompress(compressed_data).decode())

def store_in_cache(query_hash, compressed_json):
    """Store the compressed query result in DynamoDB."""
    dynamodb.put_item(
        TableName=DYNAMODB_TABLE,
        Item={
            "query_hash": {"S": query_hash},
            "compressed_json": {"B": compressed_json}, # Compressed JSON stored as binary
            "hits": {"N": "0"}
        }
    )

def get_df_try_hash(query):
    """
    Check if the query hash exists in DynamoDB.
    If it exists, retrieve and decompress the JSON data, then return as a Pandas DataFrame.
    """
    # Create hash from the query
    query_hash = hash_query(query)


    # Check if the hash exists in DynamoDB
    response = dynamodb.get_item(
        TableName=DYNAMODB_TABLE,
        Key={"query_hash": {"S": query_hash}}
    )

    # If hash exists, retrieve and decompress the data
    if "Item" in response:

        
        table.update_item(
            Key={"query_hash": query_hash},  # No need for {"S": query_hash} when using resource
            UpdateExpression="SET hits = hits + :inc",
            ExpressionAttributeValues={":inc": 1}
        )

        print("item was cached")
        compressed_json = response["Item"]["compressed_json"]["B"]  # Get binary data

        # Decompress and convert back to JSON
        json_str = zlib.decompress(compressed_json).decode()
        data = json.loads(json_str)

        # Convert JSON to Pandas DataFrame
        return pd.DataFrame(data)
    
    else:

        result_df = run_athena_query(query)

        compressed_json = compress_json(result_df)

        store_in_cache(query_hash, compressed_json)

        
        return result_df

def send_chunk(connection_id, message):
    """Send JSON chunk via WebSocket"""
    api_client.post_to_connection(ConnectionId=connection_id, Data=json.dumps(message).encode("utf-8"))

CHUNK_SIZE = 50  # Number of rows per JSON chunk

def lambda_handler(event, context):
    print("Received event:", json.dumps(event, indent=2))

    connection_id = event["requestContext"]["connectionId"]
    print(connection_id)

    body = json.loads(event["body"])
    query = body.get('query')
    print(f"SQL Query: {query}")

    df = get_df_try_hash(query)

    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)  # Save without index
    csv_buffer.seek(0)
    csv_reader = csv.reader(csv_buffer)
    print(csv_reader)

    headers = next(csv_reader)  # Extract headers from the first row

    # Send headers separately
    send_chunk(connection_id, {"label": "headers", "data": headers})

    filtered_rows = list(itertools.islice(csv_reader, None))

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

    send_chunk(connection_id, {"label": "last_chunk", "data": chunk})

    return {"statusCode": 200, "body": "Streaming Complete"}

