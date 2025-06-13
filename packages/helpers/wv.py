from packages.helpers.helpers import joel_boto

jb = joel_boto()

website_name_com = 'chalkjuice.com'
website_name = website_name_com[:-4]
s3_log_bucket_name = website_name_com + '-logs'
ATHENA_DATABASE = website_name + "_website"
ATHENA_TABLE = "cloudfront_logs"
ATHENA_OUTPUT_BUCKET = f"s3://{s3_log_bucket_name}/{website_name}_website_athena_parquet/" 

def get_website_vistor_counts():
    create_and_fill_table_query = f"""
        SELECT COUNT(DISTINCT c_ip) AS unique_visitors
        FROM {ATHENA_DATABASE}.{ATHENA_TABLE}
        WHERE sc_status IN (200, 304)
        AND x_edge_result_type IN ('Hit', 'Miss');
    """
    x = jb.query_athena(create_and_fill_table_query, ATHENA_DATABASE, ATHENA_OUTPUT_BUCKET)
    x = jb.create_df_from_athena_query(x)
    total_unique_visitors = x["Unique Visitors"][0]

    create_and_fill_table_query = f"""
        SELECT COUNT(*) AS successful_requests
        FROM {ATHENA_DATABASE}.{ATHENA_TABLE}
        WHERE sc_status IN (200, 304)
        AND x_edge_result_type IN ('Hit', 'Miss');
    """
    x = jb.query_athena(create_and_fill_table_query, ATHENA_DATABASE, ATHENA_OUTPUT_BUCKET)
    x = jb.create_df_from_athena_query(x)
    total_requests = x["Successful Requests"][0]

    return print("total_unique_visitors: ", total_unique_visitors, "total_requests: ", total_requests)