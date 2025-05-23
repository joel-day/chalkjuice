// Storage for incoming data
let heartbeatInterval;

// Keeps the connection from being marked idle. 
// Well within the 10-minute timeout window (5 minutes is a good safety margin).
export function startHeartbeat(socket) {
    stopHeartbeat(); // Clear previous if any
    heartbeatInterval = setInterval(() => {
        if (socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({ action: "heartbeat" }));
            console.log("Heartbeat sent to keep connection alive");
        }
    }, 300000); // 5 minutes
};

export function stopHeartbeat() {
  if (heartbeatInterval) {
    clearInterval(heartbeatInterval);
    heartbeatInterval = null;
  }
};

export function sendMessage(message, socket) {
  if (socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify(message));
    console.info("📤 Sent message:", message);
  } else {
    console.warn("WebSocket is not open. Cannot send message:", message);
  }
};

// ** Function to update table headers **
export function updateTableHeaders(headers, table_df) {
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
export function appendRowsToTable(rows, table_df) {
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

// Function to clear a table element
export function clearTable(table_df) {
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
};