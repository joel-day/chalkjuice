# ChalkJuice

# Barry - NFL Game Prediction Model 

Barry uses Machine Learning and a dataset of all previous NFL matchups to predict the amount of times a team will win against the provided opponent. 

When a team wins in an actual NFL matchup, the winning team isnt neccesarily the better team, it was just the better team that day. This model simulates a matchup 100 times, providing a better understaning of which team is better. 

You can compare teams from different years, the same team over different years, and even the same team over different weeks in the same season!

It does so by first generating what the team is expected to score - considering the strength of their offense and the strength of the opponent's defense. Then a score is randomly generated around that mean based on how much scores typically vary across real historical matchups. 

If you select a week that didnt exist for the given season, (ex. week 18 in 2020) Barry will automatically try previous weeks until the week was present for that year. (ex. it will try week 18, then 17, then 16 ect.).

NOTE: Barry reserves the first 34 games of a teams existance for model training, so those initial games are not suitbale for use in the model. 

email chalkjuice@protonmail.com with any questions, issues, or fun ideas!

## Ideas

IDEA: implement dynamoDB caching for the model to increase speead and save money 

IDEA: Redesign logo with three circles idea. black and white on the I. Loading screen with logo moving. maybe just an image that pulsates in size. 

IDEA: when you click a row show an ask barry popup box. add messege that says click on a row to ask barry to simlate the game 

IDEA: fake simulated league of every nfl team of all time in pools like soccer. monthly, then once annualy wuith the 12 winner for the main winner. 

IDEA: All time rankings

IDEA: under the table post weekly data analysis. Tableau. add two arrows that can loop between previous posts. show the date posted. 

IDEA: Future game schdule table. click to run through model (current stats) and priovde current API odds for the game. Use the match up templatre i created (visual)

IDEA: Add summary pane underneith table with relevnt infor based on selected team(s)/ year. Add a best team worst team

IDEA: recomended bet (paid) emailed to users

IDEA: biggest upsets all time. Win despite lowest win % chance

IDEA: and messge if the team didnt exist that year. make the text smaller.  move date column to end combine point columns

IDEA: click the column headers to sort by that column. click again for reverse sort. dont requery - use the table saved in javascript. 



