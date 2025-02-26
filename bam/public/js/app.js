/*---------------------------------------------------------------------
    File Name: chalk_custom.js
---------------------------------------------------------------------*/
// 1) HTML begins loading.
// 2) HTML finishes loading and DOM is built → DOMContentLoaded fires.
// 3) CSS, JavaScript, and images continue loading.
// 4) Everything is fully loaded → load fires.

//general--------------------------------------------------------------------------------------------------------------
// Initially disable scrolling to prvent scroll bar from showing on loading screen 
document.querySelector('html').classList.add('no-scroll');

// Storage for incoming data
let tableHeadersa = [];
let tableDataa = [];
//declares an undefined variable
let heartbeatInterval;

  //calling connectWebSocket() craetes a brand-new WebSocket object each time. Must reload the handlers. 
  // i use the heartbeat functions to keep it open to avoid having to reopen
const socket = new WebSocket("wss://0t9yhsvorj.execute-api.us-east-2.amazonaws.com/production/");



//definitions---------------------------------------------------------------------------------------------------------------
// create life
function startHeartbeat() {
  if (heartbeatInterval) clearInterval(heartbeatInterval);  // Clear existing interval
  heartbeatInterval = setInterval(() => {
    if (socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ action: "heartbeat" }));
      console.log("thump-thump");
    }
  }, 300000); // 2 minutes 
}

// end a life
function stopHeartbeat() {
  if (heartbeatInterval) {
    clearInterval(heartbeatInterval);
    heartbeatInterval = null;
  }
}

// Function to clear a table element
function clearTable(table_df) {
  const table = document.getElementById(table_df);
  if (!table) return;
  
  //clear headers
  const tableHeader = table.querySelector("thead");
  tableHeader.innerHTML = "";

  //clear body
  const tableBody = table.querySelector("tbody");
  if (tableBody) {
      tableBody.innerHTML = ""; // Clears only the data rows
  }
}

// Function to send a query with the selected year and team
function refresh_hisotrical_matchups_table(selectedYear, selectedTeam) {
  clearTable("data-table5"); // Clear the table before sending the new request

  let query = `SELECT * FROM chalkjuice_data WHERE season = ${selectedYear}`;
  
  // If a specific team is selected, add the team filter to the query
  if (selectedTeam !== "ALL") {
    query += ` AND team = '${selectedTeam}'`;
  }

  // Retrieves data to update the Historical Matchups table upon dropdown selections
  if (socket.readyState === WebSocket.OPEN) {
    const message = {
      action: "fetch_gold",  // WebSocket route name (same as the action upon page load to fill the table)
      query: query
    };

    socket.send(JSON.stringify(message));
    console.log(`📤 Sent query: ${query}`);
  } else {
    console.warn(" WebSocket is not open. Cannot send message.");
  }
}

// Function to retrieve model results (df with 100 matchups, win percentage)
function barry_model_results(team, opp, week1, week2, season1, season2) {
  
  if (socket.readyState === WebSocket.OPEN) {
    const message2 = {
      action: "fetch_model",  // WebSocket route name
      team: team,
      opponent: opp,
      week1: week1,
      week2: week2,
      season1: season1,
      season2: season2
    };

  socket.send(JSON.stringify(message2));
  console.log(`This data is on a new path now. less chosen. ${team}, ${opp}, ${week1}, ${week2}, ${season1}, ${season2}`);
  } else {
    console.warn("websocket closed gotta refresh page");
  }
}

// ** Function to update table headers **
function updateTableHeaders(headers, table_df) {
  const table = document.getElementById(table_df);
  if (!table) return;

  const tableHeader = table.querySelector("thead");
  tableHeader.innerHTML = "";

  const headerRow = document.createElement("tr");
  headers.forEach(header => {
    const th = document.createElement("th");
    th.textContent = header;
    headerRow.appendChild(th);
  });
  tableHeader.appendChild(headerRow);
}

// ** Function to append rows to table without storing in memory **
function appendRowsToTable(rows, table_df) {
  const table = document.getElementById(table_df);
  if (!table) return;

  const tableBody = table.querySelector("tbody");

  rows.forEach(row => {
    const tr = document.createElement("tr");
    row.forEach(cell => {
      const td = document.createElement("td");
      td.textContent = cell;
      tr.appendChild(td);
    });
    tableBody.appendChild(tr);
  });

  console.log(`✅ ${rows.length} rows added to the table.`);
}
  
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

  console.log("model result received:", data);

  // Find the results block in your HTML
  const resultsBlock = document.getElementById("results-block");


  // Create a new paragraph element to hold the message
  const messageElement = document.createElement("p");
  messageElement.classList.add("model-message"); // Add a class for styling
  messageElement.textContent = `Team 1 win percentage: ${Math.round(data.data * 100)}%`; // Set the text content

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

  socket.onopen = function (event) {
    // the lambda integration attached to this $connect route saves the gateway connectionID in a DynamoDB table
    console.log("websocket is alive");
    
    // Retrieves data to fill the Historical Matchups table upon page load
    const message = {
      action: "fetch_gold",  // WebSocket route name needs custom integration request
      query: "SELECT * FROM chalkjuice_data WHERE season = 2023;"
    };
    socket.send(JSON.stringify(message));

    // Heartbeat sends a messge to gateway every 2 minutes to keep the connection alive
    startHeartbeat();
  };

  socket.onmessage = function (event) {
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

      } else if (jsonData.label == "model_error") {

        const headerContainer3 = document.querySelector(".header-container3");
        if (headerContainer3) {
            headerContainer3.style.display = "none";
        }

        const loadingImage = document.getElementById("loading-image");
        loadingImage.remove();

        const button = document.getElementById("model_button");
        button.disabled = false; // Re-enable button on error
        append_data_to_results_block_error(jsonData);

      } else if (jsonData.label == "model_results_team1_win_pct") {

        const headerContainer3 = document.querySelector(".header-container3");
        if (headerContainer3) {
            headerContainer3.style.display = "none";
        }

        const loadingImage = document.getElementById("loading-image");
        loadingImage.remove();

        const button = document.getElementById("model_button");
        button.disabled = false; // Re-enable button on error

        append_data_to_results_block(jsonData);

      } else if (jsonData.label == "model_results_headers") {
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
  };

  socket.onclose = function (event) {
    console.log("websocket kaput:", event);
    stopHeartbeat();
  };

  socket.onerror = function (error) {
    console.error("🚨 WebSocket error:", error);
  };

  //event listeners------------------------------------------------------------------------------------------------------------------------

  document.getElementById("year-select").addEventListener("change", function () {

    const tableWrapperHidden = document.querySelector(".table-wrapper_hidden2");
    if (tableWrapperHidden) {
        tableWrapperHidden.style.display = "none";
    }

    const matchupsBlock = document.getElementById("matchups-block");

    // Create the loading image element
    const loadingImage2 = document.createElement("img");

    loadingImage2.src = "images/loading.gif"; 
    loadingImage2.style.width = "50px";  
    loadingImage2.style.height = "50px";  
    loadingImage2.id = "loading-image2";
    loadingImage2.alt = "Loading...";
    loadingImage2.style.display = "block"; 

    matchupsBlock.appendChild(loadingImage2);

    const resultsContainer2 = document.querySelector(".results-container2");
    
    if (resultsContainer2) {
        resultsContainer2.style.justifyContent = "center"; // Align content to the top
    }

    refresh_hisotrical_matchups_table(this.value, document.getElementById("team-select").value);
  });

  document.getElementById("team-select").addEventListener("change", function () {

    const tableWrapperHidden = document.querySelector(".table-wrapper_hidden2");
    if (tableWrapperHidden) {
        tableWrapperHidden.style.display = "none";
    }

    const matchupsBlock = document.getElementById("matchups-block");

    // Create the loading image element
    const loadingImage2 = document.createElement("img");

    loadingImage2.src = "images/loading.gif"; 
    loadingImage2.style.width = "50px";  
    loadingImage2.style.height = "50px";  
    loadingImage2.id = "loading-image2";
    loadingImage2.alt = "Loading...";
    loadingImage2.style.display = "block"; 

    matchupsBlock.appendChild(loadingImage2);

    const resultsContainer2 = document.querySelector(".results-container2");
    
    if (resultsContainer2) {
        resultsContainer2.style.justifyContent = "center"; // Align content to the top
    }
    refresh_hisotrical_matchups_table(document.getElementById("year-select").value, this.value);
  });

  document.getElementById("barryLink").addEventListener("click", function(event) {
    event.preventDefault(); // Prevent default anchor behavior
    window.location.href = "index.html"; // Navigate to the desired page
  })
  
  document.getElementById("barryLink2").addEventListener("click", function(event) {
      event.preventDefault(); // Prevent default anchor behavior
      window.location.href = "index_barry.html"; // Navigate to the desired page
    })

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

    // Determine which loading image to use
    const loadingImageSrc = (modelTeam === "KAN" || modelOpponent === "KAN") 
        ? "images/loading_taylor.gif" 
        : "images/loading.gif";
    

    // Create the loading image element
    const loadingImage = document.createElement("img");

    // Check conditions and update both the image source and size
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
      document.getElementById("model_week1").value,
      document.getElementById("model_week2").value,
      document.getElementById("model_season1").value,
      document.getElementById("model_season2").value
    );

    

    clearTable("data-table6");
  });
});

























