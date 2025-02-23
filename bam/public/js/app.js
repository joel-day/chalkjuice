/*---------------------------------------------------------------------
    File Name: chalk_custom.js
---------------------------------------------------------------------*/
// 1) HTML begins loading.
// 2) HTML finishes loading and DOM is built → DOMContentLoaded fires.
// 3) CSS, JavaScript, and images continue loading.
// 4) Everything is fully loaded → load fires.


//----------------------- DOM -------------------------------------//
// DOMContentLoaded is a JS event that fires when the initial HTML document has been fully loaded 
// and parsed by the browser. The DOM is fully loaded, and I can manipulate elements now! DOMContentLoaded: E
// Ensures the table element exists in the DOM before you attempt to populate it.
// Async allows you to use await within the callback 
// This is an example of a callback
// addEventListener takes two arguments:The name of the event ("DOMContentLoaded").
// A callback function (async () => { ... }) that will be executed when the event occurs

// Initially disable scrolling to prvent scroll bar from showing on loading screen 
document.querySelector('html').classList.add('no-scroll');


// Storage for incoming data
let tableHeadersa = [];
let tableDataa = [];

const socket = new WebSocket("wss://0t9yhsvorj.execute-api.us-east-2.amazonaws.com/production/");

document.addEventListener("DOMContentLoaded", async () => {
  const socket = new WebSocket("wss://0t9yhsvorj.execute-api.us-east-2.amazonaws.com/production/");

  // When WebSocket connection is established
  socket.onopen = function (event) {
      console.log("✅ WebSocket is connected!");
      
            // Send a query request to the WebSocket API
      const message = {
        action: "fetch_gold",  // WebSocket route name
        query: "SELECT * FROM chalkjuice_data WHERE season = 2023;"
      };

      socket.send(JSON.stringify(message));
    
  };

  // Function to clear only the table body (keeps headers intact)
  function clearTable(table_df) {
    const table = document.getElementById(table_df);
    if (!table) return;

    const tableBody = table.querySelector("tbody");
    if (tableBody) {
        tableBody.innerHTML = ""; // Clears only the data rows
    }
  }
  // Function to send a query with the selected year and team
  function sendQuery(selectedYear, selectedTeam) {
    clearTable("data-table5"); // Clear the table before sending the new request

    let query = `SELECT * FROM chalkjuice_data WHERE season = ${selectedYear}`;
    
    // If a specific team is selected, add the team filter to the query
    if (selectedTeam !== "ALL") {
      query += ` AND team = '${selectedTeam}'`;
    }

    if (socket.readyState === WebSocket.OPEN) {
      const message = {
        action: "fetch_gold",  // WebSocket route name
        query: query
      };

      socket.send(JSON.stringify(message));
      console.log(`📤 Sent query: ${query}`);
    } else {
      console.warn("⚠️ WebSocket is not open. Cannot send message.");
    }
  }
  // Event listeners for dropdown changes
  document.getElementById("year-select").addEventListener("change", function () {
    sendQuery(this.value, document.getElementById("team-select").value);
  });
  document.getElementById("team-select").addEventListener("change", function () {
    sendQuery(document.getElementById("year-select").value, this.value);
  });


// Function to send a query with the selected year and team
function send_model_data(team, opp, week1, week2, season1, season2) {

  // change to clear the contents of theblock that displays the reuslts //  clearTable(); // Clear the table before sending the new request
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
  console.log(`📤 Sent Model Inputs: ${team}, ${opp}, ${week1}, ${week2}, ${season1}, ${season2}`);
  } else {
    console.warn("⚠️ WebSocket is not open. Cannot send message.");
  }
}
document.getElementById("model_button").addEventListener("click", function () {
  send_model_data(
    document.getElementById("model_team").value,
    document.getElementById("model_opponent").value,
    document.getElementById("model_week1").value,
    document.getElementById("model_week2").value,
    document.getElementById("model_season1").value,
    document.getElementById("model_season2").value
  );
});

  // WebSocket event handlers /////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
  socket.onmessage = function (event) {
    console.log("📩 Message received from WebSocket:", event.data);

    try {
      const jsonData = JSON.parse(event.data);
      console.log("🔍 Parsed JSON:", jsonData);

      if (jsonData.label === "headers") {
        updateTableHeaders(jsonData.data, "data-table5");
      } else if (jsonData.label === "chunk") {
        appendRowsToTable(jsonData.data, "data-table5");
      } else if (jsonData.label === "last_chunk") {
        appendRowsToTable(jsonData.data, "data-table5");

        // Hide the loader **after** the last chunk has been processed
        setTimeout(() => {
          document.querySelector('.loader_bg').style.display = 'none';
          document.querySelector('html').classList.remove('no-scroll');
          console.log("🚀 Last chunk loaded. Loader hidden.");
        }, 1);

      } else if (jsonData.label == "model_error") {
        append_data_to_results_block(jsonData);
      } else if (jsonData.label == "model_results_team1_win_pct") {
        append_data_to_results_block(jsonData);


      } else if (jsonData.label == "model_results_headers") {
        updateTableHeaders(jsonData.data, "data-table6");
      } else if (jsonData.label === "model_results_rows") {
        appendRowsToTable(jsonData.data, "data-table6");
      } else if (jsonData.label === "model_results_rows_last") {
        appendRowsToTable(jsonData.data, "data-table6");

  
      }
    } catch (error) {
      console.log("⚠️ Received non-JSON message:", event.data);
  }
  };

  socket.onclose = function (event) {
    console.log("❌ WebSocket closed:", event);
  };

  socket.onerror = function (error) {
    console.error("🚨 WebSocket error:", error);
  };
});
  
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
  

function append_data_to_results_block(data) {

  
}























