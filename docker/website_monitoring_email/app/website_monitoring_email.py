from helpers import joel_boto
jb = joel_boto()

website_name_com = 'chalkjuice.com'
website_name = website_name_com[:-4]
s3_log_bucket_name = website_name_com + '-logs'
ATHENA_DATABASE = website_name + "_website"
ATHENA_TABLE = "cloudfront_logs"
ATHENA_OUTPUT_BUCKET = f"s3://{s3_log_bucket_name}/{website_name}_website_athena_parquet/" 

def get_website_vistor_counts(ATHENA_DATABASE, ATHENA_TABLE, ATHENA_OUTPUT_BUCKET):
    base_filter = """
        WHERE sc_status IN (200, 304)
          AND x_edge_result_type IN ('Hit', 'Miss')
    """

    queries = {
        "total_unique_visitors": f"""
            SELECT COUNT(DISTINCT c_ip) AS unique_visitors
            FROM {ATHENA_DATABASE}.{ATHENA_TABLE}
            {base_filter}
        """,

        "total_requests": f"""
            SELECT COUNT(*) AS successful_requests
            FROM {ATHENA_DATABASE}.{ATHENA_TABLE}
            {base_filter}
        """,

        "unique_visitors_24h": f"""
            SELECT COUNT(DISTINCT c_ip) AS unique_visitors_24h
            FROM {ATHENA_DATABASE}.{ATHENA_TABLE}
            {base_filter}
            AND from_iso8601_timestamp(concat_ws('', cast(date as varchar), 'T', time, 'Z')) >= current_timestamp - INTERVAL '1' DAY
        """,

        "unique_visitors_7d": f"""
            SELECT COUNT(DISTINCT c_ip) AS unique_visitors
            FROM {ATHENA_DATABASE}.{ATHENA_TABLE}
            {base_filter}
            AND from_iso8601_timestamp(concat_ws('', cast(date as varchar), 'T', time, 'Z')) >= current_timestamp - INTERVAL '7' DAY
        """,

        "unique_visitors_30d": f"""
            SELECT COUNT(DISTINCT c_ip) AS unique_visitors
            FROM {ATHENA_DATABASE}.{ATHENA_TABLE}
            {base_filter}
            AND from_iso8601_timestamp(concat_ws('', cast(date as varchar), 'T', time, 'Z')) >= current_timestamp - INTERVAL '30' DAY
        """
    }

    results = {}
    for key, query in queries.items():
        x = jb.query_athena(query, ATHENA_DATABASE, ATHENA_OUTPUT_BUCKET)
        df = jb.create_df_from_athena_query(x)
        results[key] = df.iloc[0, 0]

    return results


def lambda_handler(event, context):

    results = get_website_vistor_counts(ATHENA_DATABASE, ATHENA_TABLE, ATHENA_OUTPUT_BUCKET)

    # Define the sender email and display name
    sender_email = "dosbowl@chalkjuice.com"
    sender_name = "Chalkjuice.com Info"  # Change this to your desired display name
    recipient_email = 'joelday.business@gmail.com'
    subject = '📈 Website Visitor Summary 📉'
    body_text = (
        f"𓀅 Total Unique Visitors 𓀛: {results['total_unique_visitors']}\n\n"
        f"Last 24 Hours: {results['unique_visitors_24h']}\n"
        f"Last 7 Days: {results['unique_visitors_7d']}\n"
        f"Last 30 Days: {results['unique_visitors_30d']}\n\n"
        f"Total Requests: {results['total_requests']}"
    )


    jb.send_email(sender_email, sender_name, recipient_email, subject, body_text)


    return {"statusCode": 200, "body": "Streaming Complete"}