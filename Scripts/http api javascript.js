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