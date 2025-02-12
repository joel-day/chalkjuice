/*---------------------------------------------------------------------
    File Name: chalk_custom.js
---------------------------------------------------------------------*/
  // Storage for incoming data
let tableHeadersa = [];
let tableDataa = [];

document.addEventListener("DOMContentLoaded", async () => {
  const socket = new WebSocket("wss://0t9yhsvorj.execute-api.us-east-2.amazonaws.com/production/");

  // When WebSocket connection is established
  socket.onopen = function (event) {
      console.log("✅ WebSocket is connected!");
      
    
  };
  // WebSocket event handlers
  socket.onmessage = function (event) {
    console.log("📩 Message received from WebSocket:", event.data);

    try {
      const jsonData = JSON.parse(event.data);
      console.log("🔍 Parsed JSON:", jsonData);

      if (jsonData.label === "headers") {
        updateTableHeaders(jsonData.data);
      } else if (jsonData.label === "chunk") {
        appendRowsToTable(jsonData.data);
      }
    } catch (error) {
      console.error("❌ Failed to parse JSON:", error);
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
function updateTableHeaders(headers) {
  const table = document.getElementById("data-table5");
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
function appendRowsToTable(rows) {
  const table = document.getElementById("data-table5");
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
  

// Reusable function to populate a table
async function populateTable_noapi(tableId) {
  const table = document.getElementById(tableId);
  const tableHeader = table.querySelector("thead");
  const tableBody = table.querySelector("tbody");

  try {
      
      // Waits for the response body to be read and converted to a JSON object.
      const data = await response.json();

      // Populate headers
      const headers = Object.keys(data[0]);
      headers.forEach(header => {
          const th = document.createElement("th");
          th.textContent = header;
          tableHeader.appendChild(th);
      });

      // Populate rows
      data.forEach(row => {
          const tr = document.createElement("tr");
          headers.forEach(header => {
              const td = document.createElement("td");
              td.textContent = row[header];
              tr.appendChild(td);
          });
          tableBody.appendChild(tr);
      });
  } catch (error) {
      console.error("Error loading table data:", error);
  }
}




























// Reusable function to populate a table
async function populateTable(tableId, apiurl) {
  const table = document.getElementById(tableId);
  const tableHeader = table.querySelector("thead");
  const tableBody = table.querySelector("tbody");

  try {
      // Fetches data from your AWS API and waits until the network request completes.
      const response = await fetch(apiurl);
      if (!response.ok) {
          throw new Error(`Error: ${response.statusText}`);
      }
      
      // Waits for the response body to be read and converted to a JSON object.
      const data = await response.json();

      // Populate headers
      const headers = Object.keys(data[0]);
      headers.forEach(header => {
          const th = document.createElement("th");
          th.textContent = header;
          tableHeader.appendChild(th);
      });

      // Populate rows
      data.forEach(row => {
          const tr = document.createElement("tr");
          headers.forEach(header => {
              const td = document.createElement("td");
              td.textContent = row[header];
              tr.appendChild(td);
          });
          tableBody.appendChild(tr);
      });
  } catch (error) {
      console.error("Error loading table data:", error);
  }
}


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


// Fetch data and populate the first table
document.addEventListener("DOMContentLoaded", async () => {
  const apiurl = "https://04hc2ltc67.execute-api.us-east-2.amazonaws.com/dosbowl";
  const tableIds = [
    // "data-table", "data-table2", "data-table3", "data-table4", "data-table6",
    "data-table"
  ];

  // Populate all tables
  for (const tableId of tableIds) {
    await populateTable(tableId, apiurl);
  }
  


  // Hide the loader and enable scrolling after a delay of 2 seconds
  setTimeout(function () {
    document.querySelector('.loader_bg').style.display = 'none'; // Hides the loader
    document.querySelector('html').classList.remove('no-scroll'); // Re-enable scrolling
  }, 2000); // Delay for 2 seconds (2000 milliseconds)


});


