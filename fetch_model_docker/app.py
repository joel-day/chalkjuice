import boto3
import sys
import zipfile
import json
import hashlib
import zlib
import pandas as pd
import csv
import io
import itertools
import joblib
import pickle
import os
from datetime import datetime
import time
import joblib
from sklearn.preprocessing import StandardScaler
import numpy as np


# AWS Credentials & Region
AWS_REGION = "us-east-2"  # Change to your region
DATABASE = "chalk"
TABLE = "chalkjuice_data"
S3_OUTPUT = "s3://chalkjuice/golden_athena/"  # Replace with your actual S3 bucket

# Initialize Athena Client
athena_client = boto3.client("athena", region_name=AWS_REGION)

weights = [5,7,9,13,.3,.25,.25,.2]
games_back = weights[0] + weights[1] + weights[2] + weights[3] + 1


# AWS Credentials & Region
AWS_REGION = "us-east-2"  # Change to your region
DATABASE = "chalk"
TABLE = "chalkjuice_data"
S3_OUTPUT = "s3://chalkjuice/golden_athena/"  # Replace with your actual S3 bucket

# Initialize Athena Client
athena_client = boto3.client("athena", region_name=AWS_REGION)

# Global model and scaler
s3_bucket = "chalkjuice"
model_key = "lr_model.joblib"
model_key2 = "lr_model_2.joblib"
scaler_key = "chalk_22_scaler.pkl"
scaler_key2 = "chalk_22_scaler_2.pkl"
model1 = None
scaler1 = None
model2 = None
scaler2 = None


def load_model():
    global model1, scaler1, model2, scaler2
    if model1 is None or scaler1 is None or model2 is None or scaler2 is None:
        s3 = boto3.client("s3")
        model_path = "/tmp/lr_model.joblib"
        scaler_path = "/tmp/chalk_22_scaler.pkl"
        model_path2 = "/tmp/lr_model_2.joblib"
        scaler_path2 = "/tmp/chalk_22_scaler_2.pkl"

        # Download once per cold start
        s3.download_file(s3_bucket, model_key, model_path)
        s3.download_file(s3_bucket, scaler_key, scaler_path)
        s3.download_file(s3_bucket, model_key2, model_path2)
        s3.download_file(s3_bucket, scaler_key2, scaler_path2)

        
        model1 = joblib.load(model_path)
        model2 = joblib.load(model_path2)
        scaler1 = joblib.load(scaler_path)
        scaler2 = joblib.load(scaler_path2)

        print(f"scaler1 type: {type(scaler1)}")
        print(f"scaler2 type: {type(scaler2)}")

load_model()  # Load once when Lambda is cold

def weighted_avg(df, col, gb1, gb2, gb3, gb4, weight1, weight2, weight3, weight4, inte = None):

    # gb stands for games back 
    gb2 = gb1 + gb2
    gb3 = gb2 + gb3
    gb4 = gb3 + gb4

    average_gb1 = df[col].iloc[:gb1].mean()
    weighted_gb1 = average_gb1 * weight1

    average_gb2 = df[col].iloc[gb1:gb2].mean()
    weighted_gb2 = average_gb2 * weight2


    average_gb3 = df[col].iloc[gb2:gb3].mean()
    weighted_gb3 = average_gb3 * weight3

    average_gb4 = df[col].iloc[gb3:gb4].mean()
    weighted_gb4 = average_gb4 * weight4


    weighted_avg = round(((weighted_gb1 + weighted_gb2 + weighted_gb3 + weighted_gb4) / sum([weight1, weight2, weight3, weight4])), 3)

    
    if inte == 1:
        weighted_avg = int(weighted_avg)

    return weighted_avg

def query_athena_df(query):
    # Start Query Execution
    response = athena_client.start_query_execution(
        QueryString=query,
        QueryExecutionContext={"Database": DATABASE},
        ResultConfiguration={"OutputLocation": S3_OUTPUT},
    )

    # Get Query Execution ID
    query_execution_id = response["QueryExecutionId"]

    # Wait for Query to Complete
    while True:
        status = athena_client.get_query_execution(QueryExecutionId=query_execution_id)
        state = status["QueryExecution"]["Status"]["State"]
        
        if state in ["SUCCEEDED", "FAILED", "CANCELLED"]:
            break
        
        time.sleep(.1)  # Check every .1 seconds

    if state != "SUCCEEDED":
        failure_reason = status["QueryExecution"]["Status"].get("StateChangeReason", "Unknown Error")
        raise Exception(f"Athena query failed with state: {state}, Reason: {failure_reason}")


    # Get Query Results
    results = athena_client.get_query_results(QueryExecutionId=query_execution_id)

    columns = [col["Label"] for col in results["ResultSet"]["ResultSetMetadata"]["ColumnInfo"]]

    # Extract Rows
    rows = []
    for row in results["ResultSet"]["Rows"][1:]:  # Skip header row
        extracted_row = [col.get("VarCharValue", None) for col in row["Data"]]  # Extract actual values
        rows.append(extracted_row)

    # Convert to Pandas DataFrame
    df = pd.DataFrame(rows, columns=columns)
    df = df.fillna("NA")

    return df

def collect_df_for_each_matchup(team, opponent, date1, date2, model):
    
    # create data frames with the 35 most recent games =< the proivided date for both team offense and opponent defense
    query_offense = f'''
        SELECT date, team, opponent, points, home_game,
            passing_yds, passing_tds, passing_int, 
            passing_times_sacked, rushing_yds, 
            rush_tds, fmb, "3d_att", "3d_conversions", "4d_att", "4d_conversions", time_of_possession, 
            fga, punts_yds, punts_total, "2pm", "2pa",
            penalty_yds, fgm, passing_att, rushing_att
        FROM "{DATABASE}"."{TABLE}"
        WHERE team = '{team}'
            AND TRY_CAST(DATE_PARSE(date, '%m/%d/%Y') AS DATE) <= DATE '{date1}'
        ORDER BY TRY_CAST(DATE_PARSE(date, '%m/%d/%Y') AS DATE) DESC
        LIMIT {games_back+1};
    '''
    off_df = query_athena_df(query_offense)

    query_defense = f'''
        SELECT 
            date, team, opponent, passing_yds AS def_passing_yds, 
            passing_tds AS def_passing_tds, passing_int AS def_passing_int, 
            passing_times_sacked AS def_passing_times_sacked, rushing_yds AS def_rushing_yds, 
            rush_tds AS def_rush_tds, fmb AS def_fmb, 
            "3d_att" AS def_3d_att, "3d_conversions" AS def_3d_conversions, 
            "4d_att" AS def_4d_att, "4d_conversions" AS def_4d_conversions, 
            time_of_possession AS def_time_of_possession, fga AS def_fga, 
            punts_total AS def_punts_total, "2pm" AS def_2pm, 
            "2pa" AS def_2pa, passing_att AS def_passing_att, rushing_att AS def_rushing_att
        FROM "{DATABASE}"."{TABLE}"
        WHERE opponent = '{opponent}'
            AND TRY_CAST(DATE_PARSE(date, '%m/%d/%Y') AS DATE) <= DATE '{date2}' 
        ORDER BY TRY_CAST(DATE_PARSE(date, '%m/%d/%Y') AS DATE) DESC
        LIMIT {games_back+1};
    '''
    def_df = query_athena_df(query_defense)


    # join the two dfs on the index column because teams may play on different days on the same week. 
    merged_df = off_df.merge(def_df, left_index=True, right_index=True, how='inner')
    merged_df = merged_df[merged_df['date_x'] != '1/2/2023']
    merged_df = merged_df[merged_df['date_y'] != '1/2/2023']

    # first take out any information from the row date in question
    home_game = int(merged_df['home_game'][0])

    # remove the top row because you dont want to train the model on data from the same week we are uses for points
    merged_df_2 = merged_df.drop(merged_df.index[0])
    merged_df_2 = merged_df_2.drop(columns=['date_x', 'team_x', 'opponent_x', 'date_y', 'team_y', 'opponent_y', 'home_game', 'points'])

    if model == 2:
        # drop these for the smaller model
        merged_df_2 = merged_df_2.drop(columns=['time_of_possession', 'def_time_of_possession', '2pm', '2pa', 'def_2pm', 'def_2pa',
            '3d_att', 'def_3d_att', '3d_conversions', 'def_3d_conversions', '4d_att', 'def_4d_att', '4d_conversions', 
            'def_4d_conversions'])

    # convert to integers. this is the part that despises N/A values 
    merged_df_2 = merged_df_2.astype(int)


    
    return(merged_df_2, home_game)

def create_features(df, model):  

    merged_df_2 = df
    ##### pass_play_percentage
    merged_df_2['pass_play_percentage'] = 100*(merged_df_2['passing_att'] / (merged_df_2['passing_att'] + merged_df_2['rushing_att']))
    merged_df_2['def_pass_play_percentage'] = 100*(merged_df_2['def_passing_att'] / (merged_df_2['def_passing_att'] + merged_df_2['def_rushing_att']))

    merged_df_2 = merged_df_2.drop(columns=['passing_att', 'rushing_att', 'def_passing_att', 'def_rushing_att'])

    ##### drives
    # Offensive drives
    merged_df_2['drives'] = merged_df_2['passing_tds'] + merged_df_2['rush_tds'] + merged_df_2['fga'] + merged_df_2['punts_total']

    # Defensive drives
    merged_df_2['def_drives'] = merged_df_2['def_passing_tds'] + merged_df_2['def_rush_tds'] + merged_df_2['def_fga'] + merged_df_2['def_punts_total']

    # drop
    merged_df_2 = merged_df_2.drop(columns=['punts_total', 'def_punts_total', 'def_fga'])

    ##### tds per 10000 yards
    # Offensive touchdowns per yard
    merged_df_2['tds_per_yard'] = 10000 * ((merged_df_2['passing_tds'] + merged_df_2['rush_tds']) / \
                                (merged_df_2['passing_yds'] + merged_df_2['rushing_yds']))

    # Defensive touchdowns per yard
    merged_df_2['def_tds_per_yard'] = 10000 * ((merged_df_2['def_passing_tds'] + merged_df_2['def_rush_tds']) / \
                                    (merged_df_2['def_passing_yds'] + merged_df_2['def_rushing_yds']))

    merged_df_2 = merged_df_2.drop(columns=['passing_tds', 'rush_tds', 'def_passing_tds', 'def_rush_tds'])


    ##### fg_percentage
    merged_df_2['fg_percentage'] = 100*(np.where(merged_df_2['fga'] == 0, 0, merged_df_2['fgm'] / merged_df_2['fga']))

    # Now drop 'fgm' and 'fga'
    merged_df_2 = merged_df_2.drop(columns=['fgm', 'fga'])

    merged_df_2 = merged_df_2.astype(int)


    if model == 1:
        ##### cluth metric
        # Offensive clutch conversion percentage
        merged_df_2['clutch_conversion_percentage'] = 100*((merged_df_2['3d_conversions'] + merged_df_2['4d_conversions'] + merged_df_2['2pm']) / \
                                                    (merged_df_2['3d_att'] + merged_df_2['4d_att'] + merged_df_2['2pa']))

        # Defensive clutch conversion percentage
        merged_df_2['def_clutch_conversion_percentage'] = 100*(1 - ((merged_df_2['def_3d_conversions'] + merged_df_2['def_4d_conversions'] + merged_df_2['def_2pm']) / \
                                                        (merged_df_2['def_3d_att'] + merged_df_2['def_4d_att'] + merged_df_2['def_2pa'])))

        # Drop the original columns
        merged_df_2 = merged_df_2.drop(columns=[
            '3d_att', '4d_att', '2pa', '3d_conversions', '4d_conversions', '2pm',
            'def_3d_att', 'def_4d_att', 'def_2pa', 'def_3d_conversions', 'def_4d_conversions', 'def_2pm'
        ])

    return merged_df_2

def weighted(merged_df_2, model):    
    # Dictionary to store weighted averages
    weighted_averages = {}
    # List of columns to calculate weighted averages for
    if model == 2:
        columns = [
            'passing_yds', 'passing_int', 'passing_times_sacked', 'rushing_yds', 'fmb',
            'punts_yds', 'penalty_yds', 'def_passing_yds',
            'def_passing_int', 'def_passing_times_sacked',
            'def_rushing_yds', 'def_fmb', 'def_passing_times_sacked',
            'pass_play_percentage', 'def_pass_play_percentage', 'drives',
            'def_drives', 'tds_per_yard', 'def_tds_per_yard',
            'fg_percentage'
        ]

    else:
        columns = [
            'passing_yds', 'passing_int', 'passing_times_sacked', 'rushing_yds', 'fmb', 'time_of_possession',
            'punts_yds', 'penalty_yds', 'def_passing_yds',
            'def_passing_int', 'def_passing_times_sacked',
            'def_rushing_yds', 'def_fmb', 'def_time_of_possession', 'def_passing_times_sacked',
            'pass_play_percentage', 'def_pass_play_percentage', 'drives',
            'def_drives', 'tds_per_yard', 'def_tds_per_yard',
            'clutch_conversion_percentage', 'def_clutch_conversion_percentage',
            'fg_percentage'
            ]

    # Calculate weighted averages and store in the dictionary
    for col in columns:
        weighted_averages[col] = weighted_avg(merged_df_2, col, *weights)

    # Convert dictionary to a DataFrame (single-row)
    weighted_avg_df = pd.DataFrame([weighted_averages])

    return weighted_avg_df

def get_predictions_2(team, opponent, date1, date2):  

    team = team
    opponent = opponent
    date1 = date1
    date2 = date2


    if datetime.strptime(date1, '%Y-%m-%d').year < 1994 or datetime.strptime(date2, '%Y-%m-%d').year < 1994:
        model_used = 2
  
    else:
        model_used = 1
        
    print(model_used)

    # create a 34 most recent game df fro each matchup
    merged_df_2, home_game = collect_df_for_each_matchup(team, opponent, date1, date2, model_used)

    # create features
    merged_df_2 = create_features(merged_df_2, model_used)

    # get the aggregated weighted averages of each feature
    weighted_avg_df = weighted(merged_df_2, model_used)
    weighted_avg_df.columns

    # add home_game the only varible that doesnt need to be weighted
    weighted_avg_df['home_game'] = home_game


    if model_used == 2 :
        # scale the featurs using the scaler form the model
        scaled_inputs = scaler2.transform(weighted_avg_df)
        predictions = model2.predict(scaled_inputs)

    else:
        # scale the featurs using the scaler form the model
        scaled_inputs = scaler1.transform(weighted_avg_df)
        predictions = model1.predict(scaled_inputs)

    return predictions, model_used

def model_output(team, opponent, points_team1, points_team2):    
    sd = 8
    limit = 100
    n = 0
    team1_wins = 0
    team2_wins = 0

    # Create an empty DataFrame to store results
    df = pd.DataFrame(columns=[team, opponent])

    while n < limit:
        # Add some variance to the scores
        team1_score =  round(np.random.normal(loc=points_team1.item(), scale=sd), 1)
        team2_score =  round(np.random.normal(loc=points_team2.item(), scale=sd), 1)

        # Append the scores to the DataFrame
        df.loc[len(df)] = [team1_score, team2_score]

        if team1_score > team2_score:
            team1_wins += 1
        else:
            team2_wins += 1

        n += 1

    team1_win_pct = team1_wins / limit

    return team1_win_pct, df

def oldest_usable_game(team, games_back):
    query = f"""
        WITH ordered_games AS (
            SELECT date,
                ROW_NUMBER() OVER (PARTITION BY team ORDER BY date ASC) AS row_num
            FROM "{DATABASE}"."{TABLE}"
            WHERE team = '{team}' 
        )
        SELECT date
        FROM ordered_games
    """
    df = query_athena_df(query)
    df.columns = df.columns.str.replace('_', ' ').str.title()  # Format column names
    df['Date'] = pd.to_datetime(df['Date'])  # Ensure 'Date' is in datetime format
    df = df.sort_values(by='Date', ascending=True)  # Sort from oldest to newest

    teams_first_game = str(df['Date'].iloc[(0)])[:10]
    oldest_game_for_modeling = str(df['Date'].iloc[(games_back)])[:10]
    
    messege = f'Barry reserves the first 34 games of a teams history to use for modeling. The first superbowl era game {team} played was on {teams_first_game}, chose a date equal to or more recent than {oldest_game_for_modeling}.'
    # the model used depends on the date due to missing data. 


    return team, teams_first_game, oldest_game_for_modeling, messege

def week_to_date(team, season, week):
    week = int(week)
    original_week = week
    direction = -1  # Start by decrementing
    
    while 1 <= week <= 18:  # Ensure week stays within valid range
        query_date_from_week = f'''
            SELECT date
            FROM "{DATABASE}"."{TABLE}"
            WHERE team = '{team}' AND season = {season} AND week = {week}
        '''
        date_from_week = query_athena_df(query_date_from_week)
        
        if not date_from_week.empty:  # If the query returns a result, return it

            date_from_week["date"] = pd.to_datetime(date_from_week["date"]).dt.strftime("%Y-%m-%d")

            return date_from_week["date"].iloc[0]  # Returns '2002-10-06'

        
        week += direction  # Move in the current direction
        
        if week == 0:  # If we hit week 0, switch direction to increment
            week = original_week + 1
            direction = 1  # Start incrementing instead
        
    return None  # Return None if no valid date is found within week 1-18

def send_chunk(connection_id, message):
    # Initialize API Gateway Client
    api_gateway_endpoint = "https://0t9yhsvorj.execute-api.us-east-2.amazonaws.com/production"
    api_client = boto3.client("apigatewaymanagementapi", endpoint_url=api_gateway_endpoint)

    """Send JSON chunk via WebSocket"""
    api_client.post_to_connection(ConnectionId=connection_id, Data=json.dumps(message).encode("utf-8"))


CHUNK_SIZE = 50  # Number of rows per JSON chunk

def lambda_handler(event, context):
    print("Received event:", json.dumps(event, indent=2))

    connection_id = event["requestContext"]["connectionId"] 
    print(connection_id)

    body = json.loads(event["body"])
    team = body.get('team')
    opponent = body.get('opponent')
    week1 = body.get('week1')
    week2 = body.get('week2')
    season1 = body.get('season1')
    season2 = body.get('season2')

    print(team, opponent, week1, week2, season1, season2)

    date1 = week_to_date(team, season1, week1)
    date2 = week_to_date(opponent, season2, week2)


    team, teams_first_game, oldest_game_for_modeling, messege = oldest_usable_game(team, 34)
    opponent, teams_first_game_2, oldest_game_for_modeling_2, messege_2 = oldest_usable_game(opponent, 34)

    if date1 == None:
        send_chunk(connection_id, {"label": "model_error", "data": messege})

        return {"statusCode": 200, "body": "Streaming Complete"}

    elif date2 == None:
        send_chunk(connection_id, {"label": "model_error", "data": messege_2})

        return {"statusCode": 200, "body": "Streaming Complete"}

    else:
    
        # Convert input dates and oldest usable game dates to datetime objects
        date1_dt = datetime.strptime(date1, '%Y-%m-%d')
        date2_dt = datetime.strptime(date2, '%Y-%m-%d')
        oldest_game_for_modeling_dt = datetime.strptime(oldest_game_for_modeling, '%Y-%m-%d')
        oldest_game_for_modeling_2_dt = datetime.strptime(oldest_game_for_modeling_2, '%Y-%m-%d')


        # Check if either date is before the oldest usable game for that team
        date1_too_early = date1_dt < oldest_game_for_modeling_dt
        date2_too_early = date2_dt < oldest_game_for_modeling_2_dt

        if date1_too_early:
            send_chunk(connection_id, {"label": "model_error", "data": messege})

            return {"statusCode": 200, "body": "Streaming Complete"}

        if date2_too_early:
            send_chunk(connection_id, {"label": "model_error", "data": messege_2})

            return {"statusCode": 200, "body": "Streaming Complete"}

        # Only run predictions if BOTH dates are valid
        if not date1_too_early and not date2_too_early:
            points_team1, model_used1 = get_predictions_2(team, opponent, date1, date2)
            points_team2, model_used2 = get_predictions_2(opponent, team, date2, date1)
            team1_win_pct, df = model_output(team, opponent, points_team1, points_team2)  

            send_chunk(connection_id, {"label": "model_results_team1_win_pct", "data": team1_win_pct})

            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False)  # Save without index
            csv_buffer.seek(0)
            csv_reader = csv.reader(csv_buffer)
            print(csv_reader)

            headers = next(csv_reader)  # Extract headers from the first row

            # Send headers separately
            send_chunk(connection_id, {"label": "model_results_headers", "data": headers})

            filtered_rows = list(itertools.islice(csv_reader, None))

            chunk = []
            count = 0

            for row in filtered_rows:
                chunk.append(row)  # Keep rows as lists (not dicts)
                count += 1

                # Send data in chunks
                if count >= CHUNK_SIZE:
                    send_chunk(connection_id, {"label": "model_results_rows", "data":chunk})
                    chunk = [] 
                    count = 0

            send_chunk(connection_id, {"label": "model_results_rows_last", "data": chunk})
            


        
        return {"statusCode": 200, "body": "Streaming Complete"}