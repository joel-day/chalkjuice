import json
import boto3
import pandas as pd
from io import StringIO


s3 = boto3.client('s3')



def lambda_handler(event, context):
    region = boto3.Session().region_name
    bucket = 'chalkjuice'



    file_key = 'gold_all_49.csv'



    # Get the content of the latest CSV file
    csv_obj = s3.get_object(Bucket=bucket, Key=file_key)
    csv_data = csv_obj['Body'].read().decode('utf-8')



    # Convert the CSV data to a pandas DataFrame
    df = pd.read_csv(StringIO(csv_data))





    # Convert the DataFrame to JSON
    json_data = df.to_json(orient='records')
    print(json_data)



    # Return the JSON data for use in the HTTP API
    return {
        'statusCode': 200,
        'body': json_data,
        'headers': {
            'Content-Type': 'application/json',
            #'Access-Control-Allow-Origin': '*',  # Allow all origins
            #'Access-Control-Allow-Headers': '*',  # Allow specific headers
            #'Access-Control-Allow-Methods': 'OPTIONS, GET, POST',  # Allowed methods
        }
    }