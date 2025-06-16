from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError
import os
import pandas as pd
import time
import io
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
