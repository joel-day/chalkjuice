import json
import pandas as pd
import joblib
import numpy as np
from helpers import joel_boto
jb = joel_boto(api_gateway_endpoint="https://7aqddsnx56.execute-api.us-east-2.amazonaws.com/prod/")


# AWS Credentials & Region
#messege = f'Barry reserves the first 34 games of a teams history to use for modeling. The first superbowl era game {team} played was on {teams_first_game}, make the selections for {team} equal to or more recent than Week {oldest_week_for_modeling}, {season}.'
table_name = "nfl_matchups_model_stats"


# Global model and scaler
s3_bucket = "chalkjuice-backend"
model_key = "nfl_matchups_model/lr_model.joblib"
model_key2 = "nfl_matchups_model/lr_model_2.joblib"
scaler_key = "nfl_matchups_model/chalk_22_scaler.pkl"
scaler_key2 = "nfl_matchups_model/chalk_22_scaler_2.pkl"
model_1995 = None
scaler_for_model_1995 = None
model_1994 = None
scaler_for_model_1994 = None


def load_model():
    global model_1995, scaler_for_model_1995, model_1994, scaler_for_model_1994
    if model_1995 is None or scaler_for_model_1995 is None or model_1994 is None or scaler_for_model_1994 is None:

        model_path = "/tmp/lr_model.joblib"
        scaler_path = "/tmp/chalk_22_scaler.pkl"
        model_path2 = "/tmp/lr_model_2.joblib"
        scaler_path2 = "/tmp/chalk_22_scaler_2.pkl"

        # Download once per cold start
        jb.s3.download_file(s3_bucket, model_key, model_path)
        jb.s3.download_file(s3_bucket, scaler_key, scaler_path)
        jb.s3.download_file(s3_bucket, model_key2, model_path2)
        jb.s3.download_file(s3_bucket, scaler_key2, scaler_path2)

        
        model_1995 = joblib.load(model_path)
        model_1994 = joblib.load(model_path2)
        scaler_for_model_1995 = joblib.load(scaler_path)
        scaler_for_model_1994 = joblib.load(scaler_path2)

load_model()  # Load once when Lambda is cold

def model_output(team, opponent, points_team1, points_team2):    
    sd = 8
    limit = 100
    n = 0
    team1_wins = 0
    team2_wins = 0

    # Create an empty DataFrame to store results
    df = pd.DataFrame(columns=[f"{team} Points", f"{opponent} Points", "Winner"])
    while n < limit:
        # Add some variance to the scores

        team1_score = max(0, round(np.random.normal(loc=points_team1.item(), scale=sd), 0))
        team2_score = max(0, round(np.random.normal(loc=points_team2.item(), scale=sd), 0))

        if team1_score > team2_score:
            winner = team
        else:
            winner = opponent

        # Append the scores to the DataFrame
        df.loc[len(df)] = [team1_score, team2_score, winner]

        if team1_score > team2_score:
            team1_wins += 1
        else:
            team2_wins += 1

        n += 1

    team1_win_pct = team1_wins / limit

    df['Simulated Game #'] = df.index + 1
    df = df[['Simulated Game #'] + [col for col in df.columns if col != 'Simulated Game #']]
    y = df.columns[1]
    df[y] = df[y].astype(int)
    x = df.columns[2]
    df[x] = df[x].astype(int)

    return team1_win_pct, df

def get_model_predictions(team, opp, team_year, opp_year, table_name, model, model_1995_true):

    team_year1 = team + str(team_year)
    team_year2 = opp + str(opp_year)

    # Grab Team stats
    key = {"team_year": {"S": team_year1}}  # ← correctly builds the key

    response = jb.dynamodb.get_item(
        TableName=table_name,
        Key=key
    )

    item = response.get("Item", {})

    passing_yds = float(item["passing_yds"]["N"])
    passing_int = float(item["passing_int"]["N"])
    passing_times_sacked = float(item["passing_times_sacked"]["N"])
    rushing_yds = float(item["rushing_yds"]["N"])
    fmb = float(item["fmb"]["N"])
    if model_1995_true:
        time_of_possession = float(item["time_of_possession"]["N"])
    punts_yds = float(item["punts_yds"]["N"])
    penalty_yds = float(item["penalty_yds"]["N"])
    pass_play_percentage = float(item["pass_play_percentage"]["N"])
    drives = float(item["drives"]["N"])
    tds_per_yard = float(item["tds_per_yard"]["N"])
    if model_1995_true:
        clutch_conversion_percentage = float(item["clutch_conversion_percentage"]["N"])
    fg_percentage = float(item["fg_percentage"]["N"])
    home_game = float(item["home_game"]["N"])

    key2 = {"team_year": {"S": team_year2}}  # ← correctly builds the key


    # Grab Opp stats
    response2 = jb.dynamodb.get_item(
        TableName=table_name,
        Key=key2
    )

    item = response2.get("Item", {})

    def_passing_yds = float(item["def_passing_yds"]["N"])
    def_passing_int = float(item["def_passing_int"]["N"])
    def_passing_times_sacked = float(item["def_passing_times_sacked"]["N"])
    def_rushing_yds = float(item["def_rushing_yds"]["N"])
    def_fmb = float(item["def_fmb"]["N"])
    if model_1995_true:
        def_time_of_possession = float(item["def_time_of_possession"]["N"])
    def_pass_play_percentage = float(item["def_pass_play_percentage"]["N"])
    def_drives = float(item["def_drives"]["N"])
    def_tds_per_yard = float(item["def_tds_per_yard"]["N"])
    if model_1995_true:
        def_clutch_conversion_percentage = float(item["def_clutch_conversion_percentage"]["N"])

    if model_1995_true:
        # recreate original scaler array
        model_input_1995 = np.array([
            passing_yds,
            passing_int,
            passing_times_sacked,
            rushing_yds,
            fmb,
            time_of_possession,
            punts_yds,
            penalty_yds,
            def_passing_yds,
            def_passing_int,
            def_passing_times_sacked,
            def_rushing_yds,
            def_fmb,
            def_time_of_possession,
            pass_play_percentage,
            def_pass_play_percentage,
            drives,
            def_drives,
            tds_per_yard,
            def_tds_per_yard,
            clutch_conversion_percentage,
            def_clutch_conversion_percentage,
            fg_percentage,
            home_game
        ], dtype=float)

        model_input = np.array(model_input_1995.reshape(1, -1))
        predictions = model.predict(model_input)

    else:

        # recreate original scaler array
        model_input_1994 = np.array([
            passing_yds,
            passing_int,
            passing_times_sacked,
            rushing_yds,
            fmb,
            punts_yds,
            penalty_yds,
            def_passing_yds,
            def_passing_int,
            def_passing_times_sacked,
            def_rushing_yds,
            def_fmb,
            pass_play_percentage,
            def_pass_play_percentage,
            drives,
            def_drives,
            tds_per_yard,
            def_tds_per_yard,
            fg_percentage,
            home_game
        ], dtype=float)

        model_input = np.array(model_input_1994.reshape(1, -1))
        predictions = model.predict(model_input)


    return predictions

def send_chunk(connection_id, message):
    """Send JSON chunk via WebSocket"""
    jb.api_client.post_to_connection(ConnectionId=connection_id, Data=json.dumps(message).encode("utf-8"))

def lambda_handler(event, context):
    print("Received event:", json.dumps(event, indent=2))
    connection_id = event["requestContext"]["connectionId"] 
    body = json.loads(event["body"])

    team = body.get('team')
    opp = body.get('opponent')
    team_season = body.get('season1')
    opp_season = body.get('season2')

    team_season = int(team_season)
    opp_season = int(opp_season)

    # For seasons after 1994 i am missing the TimeOfPossession and Cluth features for both off/def
    if team_season <= 1994 or opp_season <= 1994:
        model_1995_true = False
        model_choice = model_1994
    else:
        model_1995_true = True
        model_choice = model_1995

    points_team1 = get_model_predictions(team, opp, team_season, opp_season, table_name, model_choice, model_1995_true)
    points_team2 = get_model_predictions(opp, team, opp_season, team_season, table_name, model_choice, model_1995_true)

    team1_win_pct, df = model_output(team, opp, points_team1, points_team2) 
    team1_win_pct

    send_chunk(connection_id, {"label": "model_results_team1_win_pct", "data": team1_win_pct})

    labels = ["model_results_headers", "model_results_rows", "model_results_rows_last"]
    jb.send_df_to_frontend_in_chunks(df, connection_id, 50, labels)
    
    return {"statusCode": 200, "body": "Streaming Complete"}