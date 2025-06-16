//const { startHeartbeat, stopHeartbeat } = require('./helpers');
import { startHeartbeat, stopHeartbeat, sendMessage, updateTableHeaders, appendRowsToTable, clearTable } from './helpers.js';

// Initially disable scrolling to prvent scroll bar from showing on loading screen 
document.querySelector('html').classList.add('no-scroll');

// brand-new WebSocket object each time. Must reload the handlers. 
// i use the heartbeat functions to keep it open to avoid having to reopen
const socket = new WebSocket("wss://7aqddsnx56.execute-api.us-east-2.amazonaws.com/prod/");


const oldest_year = {
  'ARI': '1970',
  'ATL': '1970',
  'BAL': '1970',
  'BUF': '1970',
  'CAR': '1998',
  'CHI': '1970',
  'CIN': '1971',
  'CLE': '2002',
  'DAL': '1970',
  'DEN': '1970',
  'DET': '1970',
  'GNB': '1970',
  'HOU': '2005',
  'IND': '1970',
  'JAX': '1998',
  'KAN': '1970',
  'LAC': '1970',
  'LAR': '1970',
  'LVR': '1970',
  'MIA': '1970',
  'MIN': '1970',
  'NOR': '1970',
  'NWE': '1970',
  'NYG': '1970',
  'NYJ': '1970',
  'PHI': '1970',
  'PIT': '1970',
  'SEA': '1979',
  'SFO': '1970',
  'TAM': '1979',
  'TEN': '1970',
  'WAS': '1970'
};



//definitions---------------------------------------------------------------------------------------------------------------

// this adds an error messege when the team data isnt availble
function append_data_to_results_block_error(data) {

    console.log("🛑 Error result received:", data);

    // Find the results block in your HTML
    const resultsBlock = document.getElementById("results-block");

    // Create a new paragraph element to hold the message
    const messageElement = document.createElement("p");
    messageElement.classList.add("error-message"); // Add a class for styling
    messageElement.textContent = data.data; // Set the text content

    // Append to the results block
    resultsBlock.appendChild(messageElement);
}

// add the win percentage as text to a blook
function append_data_to_results_block(data) {

  const team  = document.getElementById("model_team").value

  console.log("model result received:", data);

  // Find the results block in your HTML
  const resultsBlock = document.getElementById("results-block");


  // Create a new paragraph element to hold the message
  const messageElement = document.createElement("p");
  messageElement.classList.add("model-message"); // Add a class for styling
  messageElement.textContent = `${team} win percentage: ${Math.round(data.data * 100)}%`; // Set the text content

  // Create a new meter element
  const meterElement = document.createElement("meter");
  meterElement.id = "usage_meter";  // Give it an ID
  meterElement.classList.add("custom-meter"); // Add a class for styling
  meterElement.value = Math.round(data.data * 100);  // Convert to percentage
  meterElement.max = 100;  // Max value is now 100%
  meterElement.textContent = `${meterElement.value}%`;  // Fallback text if unsupported



  // Append to the results block
  resultsBlock.appendChild(messageElement);
  resultsBlock.appendChild(meterElement);

}


//dom----------------------------------------------------------------------------------------------------------------
// DOMContentLoaded is a JS event that fires when the initial HTML document has been fully loaded and parsed by 
// the browser. It ensures the table element exists in the DOM before you attempt to populate it.
document.addEventListener("DOMContentLoaded", async () => {

  socket.addEventListener("open", (event) => {
    // the lambda integration attached to this $connect route saves the gateway connectionID in a DynamoDB table
    console.log("websocket is alive");
    
    // Retrieves data to fill the Historical Matchups table upon page load
    const message = {
      action: "nfl_all_games",  // WebSocket route name needs custom integration request
      query: 'SELECT * FROM "nfl"."nfl_games_all" WHERE season = 2023;'
    };
    socket.send(JSON.stringify(message));

    // Heartbeat sends a messge to gateway every 2 minutes to keep the connection alive
    startHeartbeat(socket);
  });

  socket.addEventListener("message", (event) => {
    console.log("line has been hit up:", event.data);
    try {
      const jsonData = JSON.parse(event.data);
      console.log('Parsed JSON:', jsonData);

      if (jsonData.label === "headers") {

        const loadingImage2 = document.getElementById("loading-image2");
        if (loadingImage2) {
            loadingImage2.remove();
        }

        const resultsContainer2 = document.querySelector(".results-container2");
    
        if (resultsContainer2) {
            resultsContainer2.style.justifyContent = "flex-start"; // Align content to the top
        }

        document.querySelector(".table-wrapper_hidden2").style.display = "flex";

        updateTableHeaders(jsonData.data, "data-table5");

      } else if (jsonData.label === "chunk") {
        appendRowsToTable(jsonData.data, "data-table5");

      } else if (jsonData.label === "last_chunk") {
        appendRowsToTable(jsonData.data, "data-table5");
        // Hide the loader **after** the last chunk has been processed
        setTimeout(() => {
          document.querySelector('.loader_bg').style.display = 'none';
          document.querySelector('html').classList.remove('no-scroll');
          console.log("Last chunk loaded. Loader hidden.");
        }, 1);

      } else if (jsonData.label === "model_error") {

        const headerContainer3 = document.querySelector(".header-container3");
        if (headerContainer3) {
            headerContainer3.style.display = "none";
        }

        const loadingImage = document.getElementById("loading-image");
        loadingImage.remove();

        const button = document.getElementById("model_button");
        button.disabled = false; // Re-enable button on error
        append_data_to_results_block_error(jsonData);

      } else if (jsonData.label === "model_results_team1_win_pct") {

        const headerContainer3 = document.querySelector(".header-container3");
        if (headerContainer3) {
            headerContainer3.style.display = "none";
        }

        const loadingImage = document.getElementById("loading-image");
        loadingImage.remove();

        const button = document.getElementById("model_button");
        button.disabled = false; // Re-enable button on error

        append_data_to_results_block(jsonData);

      } else if (jsonData.label === "model_results_headers") {
        document.querySelector(".header-container2").style.display = "flex";
        document.querySelector(".table-wrapper_hidden").style.display = "flex";
        updateTableHeaders(jsonData.data, "data-table6");

      } else if (jsonData.label === "model_results_rows") {
        appendRowsToTable(jsonData.data, "data-table6");

      } else if (jsonData.label === "model_results_rows_last") {
        appendRowsToTable(jsonData.data, "data-table6");

      }
    } catch (error) {
      console.log("yo this isnt json, might not be a problem, just so ya know:", event.data);
  }
  });

  socket.addEventListener("close", (event) => {
    console.log("websocket kaput:", event);
    stopHeartbeat();
  });

  socket.addEventListener("error", (error) => {
    console.error("🚨 WebSocket error:", error);
  });

  //event listeners------------------------------------------------------------------------------------------------------------------------

    // loading image
  function historical_mathchups_loading_image() {
        // hides the table wrapper while the data loads
        const tableWrapperHidden = document.querySelector(".table-wrapper_hidden2");
        if (tableWrapperHidden) {
            tableWrapperHidden.style.display = "none";
        }
    
        // inserts the loading image while the data loads
        const matchupsBlock = document.getElementById("matchups-block");
        const loadingImage2 = document.createElement("img");
        loadingImage2.src = "images/loading.gif"; 
        loadingImage2.style.width = "50px";  
        loadingImage2.style.height = "50px";  
        loadingImage2.id = "loading-image2";
        loadingImage2.alt = "Loading...";
        loadingImage2.style.display = "block"; 
        matchupsBlock.appendChild(loadingImage2);
    
        // changes the css so the loading image is centered within the block
        const resultsContainer2 = document.querySelector(".results-container2");
        if (resultsContainer2) {
            resultsContainer2.style.justifyContent = "center"; // Align content to the top
        }
  }

    // Function to send a query with the selected year and team
  function refresh_historical_matchups_table(selectedYear, selectedTeam) {
    clearTable("data-table5"); // Clear the table before sending the new request

    let query = `SELECT * FROM "nfl"."nfl_games_all" WHERE season = ${selectedYear}`;
    
    // If a specific team is selected, add the team filter to the query
    if (selectedTeam !== "ALL") {
      query += ` AND team = '${selectedTeam}';`;
    }
    else {
      query += `;`;
    }


    const message = {
      action: "nfl_all_games",  // WebSocket route name (same as the action upon page load to fill the table)
      query: query
    };

    sendMessage(message, socket);
  }

  document.getElementById("year-select").addEventListener("change", function () {

    // generates laoding image, hides the table wrapper and header while laoding data
    historical_mathchups_loading_image()

    // refresh the table
    refresh_historical_matchups_table(this.value, document.getElementById("team-select").value);
  });

  document.getElementById("team-select").addEventListener("change", function () {

    // generates laoding image, hides the table wrapper and header while laoding data
    historical_mathchups_loading_image()

    // refresh the table
    refresh_historical_matchups_table(document.getElementById("year-select").value, this.value);
  });

  // Function to retrieve model results (df with 100 matchups, win percentage)
  function barry_model_results(team, opp, season1, season2) {
    
    const message = {
      action: "nfl_matchups_model",  // WebSocket route name
      team: team,
      opponent: opp,
      season1: season1,
      season2: season2
    };

    sendMessage(message, socket);
  }

  document.getElementById("model_button").addEventListener("click", function () {

    const button = document.getElementById("model_button");
    button.disabled = true; // Disable button on click

    // Find the results block in your HTML
    const resultsBlock = document.getElementById("results-block");
    // Clear existing content before adding new data
    resultsBlock.innerHTML = "";

    const headerContainer3 = document.querySelector(".header-container3");
    if (headerContainer3) {
        headerContainer3.style.display = "flex";
    }

    const headerContainer = document.querySelector(".header-container2");
    if (headerContainer) {
        headerContainer.style.display = "none";
    }
    
    const tableWrapperHidden = document.querySelector(".table-wrapper_hidden");
    if (tableWrapperHidden) {
        tableWrapperHidden.style.display = "none";
    }

    // Get input values
    const modelTeam = document.getElementById("model_team").value;
    const modelOpponent = document.getElementById("model_opponent").value;

    // Create the loading image element
    const loadingImage = document.createElement("img");
    if (modelTeam === "KAN" || modelOpponent === "KAN") {
        loadingImage.src = "images/loading_taylor.gif"; 
        loadingImage.style.width = "120px";  
        loadingImage.style.height = "80px";  
        loadingImage.style.borderRadius = "10px"; // Rounds the corners
    } else {
        loadingImage.src = "images/loading.gif"; 
        loadingImage.style.width = "50px";  
        loadingImage.style.height = "50px";  
    }

    loadingImage.id = "loading-image";
    loadingImage.alt = "Loading...";
    loadingImage.style.display = "block"; 

    resultsBlock.appendChild(loadingImage);

    barry_model_results(
      document.getElementById("model_team").value,
      document.getElementById("model_opponent").value,
      document.getElementById("model_season1").value,
      document.getElementById("model_season2").value
    );

  
    clearTable("data-table6");
  });


  const modelTeam = document.getElementById("model_team");
  const modelSeason1 = document.getElementById("model_season1");
  const modelOpponent = document.getElementById("model_opponent");
  const modelSeason2 = document.getElementById("model_season2");

  function updateYearOptions(teamCode, dropdown) {

      const oldest = parseInt(oldest_year[teamCode]);

      dropdown.innerHTML = ''; // Clear current options

      for (let year = 2023; year >= oldest; year--) {
          const option = document.createElement("option");
          option.value = year;
          option.textContent = year;
          dropdown.appendChild(option);
      }
  }

  // Initial load
  updateYearOptions(modelTeam.value, modelSeason1);

  // Update on team change
  modelTeam.addEventListener("change", () => {
      updateYearOptions(modelTeam.value, modelSeason1);
  });

    // Initial load
  updateYearOptions(modelOpponent.value, modelSeason2);

  // Update on team change
  modelOpponent.addEventListener("change", () => {
      updateYearOptions(modelOpponent.value, modelSeason2);
  });




  document.getElementById("popup-link").addEventListener("click", function(event) {
    event.preventDefault();
    document.getElementById("popup-window").style.display = "block";
    // document.getElementById("overlay").style.display = "block";
  });

  document.getElementById("close-popup").addEventListener("click", function() {
    document.getElementById("popup-window").style.display = "none";
  });
});

























