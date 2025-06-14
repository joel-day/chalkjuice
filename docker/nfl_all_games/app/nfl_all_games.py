import json
import pandas as pd
from helpers import joel_boto
from helpers import chalkjuice_helpers as ch
import re

jb = joel_boto(api_gateway_endpoint="wss://7aqddsnx56.execute-api.us-east-2.amazonaws.com/prod/")

dynamodb_table = "nfl_games_all"
partition_key = "query_hash"
athena_database = "nfl"
athena_ouput_location = "s3://chalkjuice-backend/nfl_games_all_athena_parquet/"

def pull_df_from_dynamo_then_tally(query_hash, partition_key, dynamodb_table):

    # Decompress the query results paried with the matching guery hash row
    response = jb.dynamodb.get_item(
        TableName=dynamodb_table,
        Key={partition_key: {"S": query_hash}}
    )
    compressed_json = response["Item"]["compressed_json"]["B"]  # Get binary data
    data = ch.decompress_json(compressed_json)


    # Add 1 to the hits column
    jb.dynamodb_resource.Table(dynamodb_table).update_item(
        Key={partition_key: query_hash},  # No need for {"S": query_hash} when using resource
        UpdateExpression="SET hits = hits + :inc",
        ExpressionAttributeValues={":inc": 1}
    )
    print("item was cached, added 1 to hits")

    return pd.DataFrame(data)

def pull_df_from_athena_then_cache(query, query_hash, partition_key, dynamodb_table, athena_database, athena_ouput_location):   

        # Grab data from athena
        query_execution_id = jb.query_athena(query, athena_database, athena_ouput_location)
        # Create a pandas df using the query results in s3
        result_df = jb.create_df_from_athena_query(query_execution_id)

        # Extract year
        year_match = re.search(r'season\s*=\s*(\d+)', query)
        selected_year = year_match.group(1) if year_match else None

        # Extract team
        team_match = re.search(r"team\s*=\s*'([^']+)'", query)
        team = team_match.group(1) if team_match else 'ALL'

        # Cahce the query results in dynamo for next time
        compressed_json = ch.compress_df_to_json(result_df)
        dict_items = {
            partition_key: {"S": query_hash},
            "compressed_json": {"B": compressed_json}, # Compressed JSON stored as binary
            "hits": {"N": "0"},
            "team": {"S": team},
            "year": {"S": selected_year}

        }

        jb.add_data_to_dynamo_table(dynamodb_table, dict_items)
        print("item wasnt cached, is now")

        return result_df

def lambda_handler(event, context):
    print("🔍 EVENT:", json.dumps(event))

    # Collect connection variables
    connection_id = event["requestContext"]["connectionId"]
    body = json.loads(event["body"])
    query = body.get('query')

    # Hash the query for storage in dynamoDB.
    query_hash = ch.hash_query(query)


    # Checks if the results of the query are already chached
    if jb.check_dynamo_item_exists_by_partition_key(dynamodb_table, partition_key, query_hash):
        print('existed')
        # Pull the compressed cached data from dynamo to populate the table, then tally
        df = pull_df_from_dynamo_then_tally(query_hash, partition_key, dynamodb_table)
    else:
        print('didnt exist')
        # Query Athena to populate the table, then cahche
        df = pull_df_from_athena_then_cache(query, query_hash, partition_key, dynamodb_table, athena_database, athena_ouput_location)


    # Send data in chunks to frontend
    jb.send_df_to_frontend_in_chunks(df, connection_id, 50)


    # Exit
    return {"statusCode": 200, "body": "Streaming Complete"}

