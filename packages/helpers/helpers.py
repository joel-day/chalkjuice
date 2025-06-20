from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError
import botocore.exceptions
import os
import pandas as pd
import time
import hashlib
import io
import base64
import subprocess
import docker
import zlib
import json  
import csv
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.base import MIMEBase
from email import encoders

class joel_boto:
    def __init__(self, api_gateway_endpoint=None):
        if os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
            print("running in lambda joel")

            aws_region = 'us-east-2'

            self.session = boto3.Session(region_name=aws_region)

        else:
            # local dev — ok to load .env
            print("running local credentials")
            load_dotenv()
            aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
            aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
            aws_region = os.getenv("AWS_DEFAULT_REGION", "us-east-2")

            self.session = boto3.Session(
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key,
                region_name=aws_region
            )

        self.region = aws_region

        sts_client = self.session.client('sts')
        identity = sts_client.get_caller_identity()
        self.account_id = identity['Account']

        self.s3 = self.session.client("s3")
        self.s3_resource = self.session.resource("s3")

        self.athena = self.session.client("athena")

        self.dynamodb = self.session.client("dynamodb")
        self.dynamodb_resource = self.session.resource("dynamodb")

        self.ecr = boto3.client("ecr")
        self.ecr_login()

        self.lambda_client = boto3.client("lambda")

        self.ses = boto3.client('ses')

        self.apigw = boto3.client('apigatewayv2')

        self.iam = boto3.client("iam")

        print("✅ Connected to all clients successfully.")

        # Optionally initialize API Gateway client
        self.api_client = None
        if api_gateway_endpoint:
            self.api_client = self.session.client(
                "apigatewaymanagementapi",
                endpoint_url=api_gateway_endpoint
            )
            print("✅ Logged in to api_gateway successfully.")

# API Gateway ###########################     
    def send_df_to_frontend_in_chunks(self, df, connection_id, chunk_size, labels):
        """
        Send a pandas DataFrame to the frontend over WebSocket in chunks.
        Each message is labeled for proper handling on the client side.
        """
        label1 = labels[0]
        label2 = labels[1]
        label3 = labels[2]
        # Convert DataFrame to CSV in memory
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)  # Save without index
        csv_buffer.seek(0)
        csv_reader = csv.reader(csv_buffer)

        # Send headers
        headers = next(csv_reader)  # Extract headers from the first row
        self.api_client.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps({"label": label1, "data": headers}).encode("utf-8")
        )

        # Send rows in chunks
        chunk = []
        for row in csv_reader:
            chunk.append(row)
            if len(chunk) >= chunk_size:
                self.api_client.post_to_connection(
                    ConnectionId=connection_id,
                    Data=json.dumps({"label": label2, "data": chunk}).encode("utf-8")
                )
                chunk = []

        # Send any remaining rows
        if chunk:
            self.api_client.post_to_connection(
                ConnectionId=connection_id,
                Data=json.dumps({"label": label3, "data": chunk}).encode("utf-8")
            )

    def create_routes_and_integrations(self, lambda_routes, api_id):
        # STEP 2: Create routes and integrations
        for route_key, lambda_arn in lambda_routes.items():
            # Create integration
            integration = self.apigw.create_integration(
                ApiId=api_id,
                IntegrationType='AWS_PROXY',
                IntegrationUri=f'arn:aws:apigateway:{self.region}:lambda:path/2015-03-31/functions/{lambda_arn}/invocations'
            )

            integration_id = integration['IntegrationId']
            
            # Create route
            self.apigw.create_route(
                ApiId=api_id,
                RouteKey=route_key,
                Target=f'integrations/{integration_id}'
            )
            print(f"Connected route '{route_key}' to Lambda")

# Lambda ####################################
    def create_lambda_function(self, lamdba_fxn_name, role_arn, repo_image_uri, timeout=300, memorysize=512):
        try:
            response = self.lambda_client.create_function(
                FunctionName=lamdba_fxn_name,
                Role=role_arn,
                Code={
                    'ImageUri': repo_image_uri
                },
                PackageType='Image',
                Timeout=timeout,
                MemorySize=memorysize,
                Publish=True,
            )
            print("✅ Lambda Created:", response["LastModified"])
        except self.lambda_client.exceptions.ResourceConflictException:
            print(f"⚠️ Lambda function '{lamdba_fxn_name}' already exists. Exiting.")

    def update_lambda_function(self, lamdba_fxn_name, repo_image_uri):    
        response = self.lambda_client.update_function_code(
            FunctionName=lamdba_fxn_name,
            ImageUri=repo_image_uri,  # or a specific tag/sha
            Publish=True  # Optional: set to True to create a new version
        )

        print("✅ Lambda updated:", response["LastModified"])

    def list_active_lambdas(self):
        
        paginator = self.lambda_client.get_paginator('list_functions')

        print("Listing Lambda functions and ARNs:")

        for page in paginator.paginate():
            for function in page['Functions']:
                print(f"Name: {function['FunctionName']}, ARN: {function['FunctionArn']}")

    def create_lambda_permissions(self, lambda_routes, api_id, api_name):
        # Step 5: Add Lambda permissions for API Gateway to invoke the Lambdas
        for lambda_arn in lambda_routes.values():
            fn_name = lambda_arn.split(':')[-1]
            statement_id = f'{api_name}-{fn_name}-invoke'
            try:
                self.lambda_client.add_permission(
                    FunctionName=fn_name,
                    StatementId=statement_id,
                    Action='lambda:InvokeFunction',
                    Principal='apigateway.amazonaws.com',
                    SourceArn=f'arn:aws:execute-api:{self.region}:{self.account_id}:{api_id}/*'
                )
                print(f"Added permission for Lambda function {fn_name} to be invoked by API Gateway.")
            except self.lambda_client.exceptions.ResourceConflictException:
                print(f"Permission {statement_id} already exists, skipping.")

# S3 ####################################
    def s3_bucket_exists(self, bucket_name: str) -> bool:
        try:
            self.s3.head_bucket(Bucket=bucket_name)
            return True
        except ClientError as e:
            error_code = int(e.response["Error"]["Code"])
            if error_code == 404:
                return False  # Bucket does not exist
            elif error_code == 403:
                return True   # Bucket exists but is not accessible (you don't own it)
            else:
                return False  # Other error (e.g., network)
            
    def create_s3_bucket(self, bucket_name):
        try:
            self.s3.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={'LocationConstraint': self.region}
            )
            print(f"✅ Created bucket: {bucket_name}")
            
        except ClientError as e:
            if e.response["Error"]["Code"] == "BucketAlreadyOwnedByYou":
                print(f"✅ Bucket already exists and owned by you: {bucket_name}")
            else:
                raise

    def upload_file_to_s3(self, local_csv_file_path, bucket_name, file_name):
        try:
            self.s3.upload_file(local_csv_file_path, bucket_name, file_name)
            print(f"✅ Uploaded {local_csv_file_path} to s3://{bucket_name}/{file_name}")
        except ClientError as e:
            print(f"❌ Upload failed: {e}")
            raise

    def s3_csv_to_df(self, s3_bucket, file_name): 
        # Read CSV from S3 int pandas
        obj = self.s3.get_object(Bucket=s3_bucket, Key=file_name)
        df = pd.read_csv(obj["Body"])

        return df
    
# SES #################################
    def send_email(self, sender_email, sender_name, recipient_email, subject, body_text, png = None):
        
        try:
            msg = MIMEMultipart('related')
            msg['Subject'] = subject
            msg['From'] = f'{sender_name} <{sender_email}>'
            msg['To'] = recipient_email
        
            # Create the HTML body with line breaks
            body_html = """<html>
                <head></head>
                <body>
                <p><strong>{}</strong></p>
                </body>
                </html>""".format(body_text.replace('\n', '<br>'))

            # Attach the body in HTML format
            msg.attach(MIMEText(body_html, 'html'))
            
            if png:
                # Download the most recent image
                attachment = MIMEBase('application', 'octet-stream')
                attachment.set_payload(png)
                encoders.encode_base64(attachment)
                attachment.add_header('Content-Disposition', f'attachment; filename="{os.path.basename(latest_image_key)}"')
                msg.attach(attachment)


            # Send the email
            response = self.ses.send_raw_email(
                Source=sender_email,
                Destinations=[recipient_email],
                RawMessage={'Data': msg.as_string()}
            )
        
            print("Email sent! Message ID:", response['MessageId'])

        except Exception as e:
            print('Error sending email:', str(e))
            
        return ('email sent')

# Athena #################################
    def query_athena(self, query, athena_database, athena_output_location):
        response = self.athena.start_query_execution(
            QueryString=query,
            QueryExecutionContext={'Database': athena_database},
            ResultConfiguration={'OutputLocation': athena_output_location}
        )

        # Wait for the query to finish
        query_execution_id = response['QueryExecutionId']
        while True:
            status = self.athena.get_query_execution(QueryExecutionId=query_execution_id)['QueryExecution']['Status']['State']
            if status in ['SUCCEEDED', 'FAILED', 'CANCELLED']:
                #print(f"Query finished with status: {status}")
                break
            time.sleep(1)

        if status != 'SUCCEEDED':
            raise Exception("Failed to query database.")
        
        return query_execution_id

    def create_df_from_athena_query(self, query_execution_id):
        # Get Query Results
        results = self.athena.get_query_results(QueryExecutionId=query_execution_id)

        columns = [col["Label"] for col in results["ResultSet"]["ResultSetMetadata"]["ColumnInfo"]]

        # Extract Rows
        rows = []
        for row in results["ResultSet"]["Rows"][1:]:  # Skip header row
            extracted_row = [col.get("VarCharValue", None) for col in row["Data"]]  # Extract actual values
            rows.append(extracted_row)

        # Convert to Pandas DataFrame
        df = pd.DataFrame(rows, columns=columns)
        df = df.fillna("NA")
        #df.columns = df.columns.str.replace('_', ' ').str.title()

        return df

# DynamoDB ################################
    def check_dynamo_table_exists(self, table_name):
        try:
            self.dynamodb.describe_table(TableName=table_name)
            print(f"✅ Table '{table_name}' already exists.")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                print(f"❌ Table '{table_name}' does not exist.")
                return False
            else:
                raise  # Re-raise unexpected exceptions

    def create_dynamodb_table(self, table_name, partition_key, attribute_type):
        # Required at creation: You define only the partition key
        self.dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': partition_key,
                    'KeyType': 'HASH'  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': partition_key,
                    'AttributeType': attribute_type
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
    
    def add_data_to_dynamo_table(self, table, dict_items):
        """
        dict_items={
            "query_hash": {"S": query_hash},
            "compressed_json": {"B": compressed_json}, # Compressed JSON stored as binary
            "hits": {"N": "0"},
            "team": {"S": team},
            "year": {"S": year}
        }
        """
        
        self.dynamodb.put_item(
            TableName=table,
            Item=dict_items
        )
    
    def check_dynamo_item_exists_by_partition_key(self, table, partition_key, query_hash):
        key = {partition_key: {"S": query_hash}}  # ← correctly builds the key

        response = self.dynamodb.get_item(
            TableName=table,
            Key=key
        )

        if "Item" in response:
            return True
        else:
            return False
        
    def delete_dynamo_item_by_partition_key(self, table, partition_key, key_value):
        self.dynamodb.delete_item(
            TableName=table,
            Key={partition_key: {"S": key_value}}
        )
        print("✔️ Deleted item:", key_value)

# ECR ################################
    def ecr_login(self):
        auth_data = self.ecr.get_authorization_token(registryIds=[self.account_id])['authorizationData'][0]
        token = auth_data['authorizationToken']
        proxy_endpoint = auth_data['proxyEndpoint']
        username, password = base64.b64decode(token).decode('utf-8').split(':')

        # Log in to Docker using the token
        login_command = ["docker", "login","--username", username,"--password", password,proxy_endpoint]
        result = subprocess.run(login_command, capture_output=True, text=True)

        if result.returncode == 0:
            print("✅ Logged in to ECR successfully.")
        else:
            print("❌ Failed to log in to ECR.")
            print(result.stderr)
        
    def create_ecr_repository(self, repo_name):
        try:
            response = self.ecr.create_repository(
                repositoryName=repo_name,
                imageScanningConfiguration={'scanOnPush': True},
                tags=[
                    {'Key': 'CreatedBy', 'Value': 'Boto3'}
                ]
            )
            print("Repository created successfully:")
            print(response['repository']['repositoryUri'])

        except self.ecr.exceptions.RepositoryAlreadyExistsException:
            print(f"Repository '{repo_name}' already exists.")
        except Exception as e:
            print("Error creating repository:", str(e))

    def get_ecr_repo_uri(self, repo_name):
        try:
            response = self.ecr.describe_repositories(
                repositoryNames=[repo_name]
            )
            repo_uri = response['repositories'][0]['repositoryUri']
            return repo_uri

        except self.ecr.exceptions.RepositoryNotFoundException:
            print(f"Repository '{repo_name}' not found.")
        except Exception as e:
            print("Error describing repository:", str(e))

    def build_and_push_to_ECR(self, path_docker, repo_uri):

        client = docker.from_env()

        # Build image with the same tag name as the ECR URI
        client.images.build(
            path=path_docker, 
            tag=f"{repo_uri}:latest"
        )

        # Push to ECR (you must be logged in first via `aws ecr get-login-password`)
        client.images.push(
            repo_uri,
            tag="latest"
        )

# I AM ################################
    def create_lambda_iam_role(self, role_name, managed_policies):
        lambda_trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "lambda.amazonaws.com"
                    },
                    "Action": "sts:AssumeRole"
                }
            ]
        }
        # Create IAM role
        try:
            response = self.iam.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(lambda_trust_policy),
                Description="IAM role for Lambda with full access to API Gateway, Athena, DynamoDB, ECR, S3, CloudWatch",
            )
            print(f"✅ Created IAM Role: {response['Role']['Arn']}")
        except self.iam.exceptions.EntityAlreadyExistsException:
            print(f"⚠️ IAM Role '{role_name}' already exists.")
            return

        # Attach policies
        for policy_arn in managed_policies:
            self.iam.attach_role_policy(
                RoleName=role_name,
                PolicyArn=policy_arn
            )
            print(f"🔗 Attached policy: {policy_arn}")


class chalkjuice_helpers():
    def hash_query(query):
        """Generate a SHA256 hash for the given query."""
        return hashlib.sha256(query.encode()).hexdigest()

    def compress_df_to_json(df):
        # Convert DataFrame to JSON format
        json_str = df.to_json(orient="records")
        
        # Compress the JSON string
        compressed_data = zlib.compress(json_str.encode())

        return compressed_data

    def decompress_json(compressed_data):
        """Decompress JSON data from zlib."""
        return json.loads(zlib.decompress(compressed_data).decode())
    
