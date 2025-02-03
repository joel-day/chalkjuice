import express from 'express';
// const fetch = require('node-fetch');
import fetch from 'node-fetch';

// Define a route
const app = express();

const data2 = {
    headers: ["Name", "Wins", "Points", "Rank"]
};


// everything inside here is served stically 
app.use(express.static('public'));

const apiUrl_dosbowl = 'https://04hc2ltc67.execute-api.us-east-2.amazonaws.com/dosbowl'; 

// Define a route
app.get('/data', async (req, res) => {
    try {
      const response = await fetch(apiUrl_dosbowl);
      const data = await response.json();
      res.json(data);
    } catch (error) {
      console.error('Error fetching data:', error);
      res.status(500).send('Error fetching data');
    }
  });


  // Define a route
app.get('/data2', async (req, res) => {
  try {
    const response = await fetch(apiUrl_dosbowl);
    const data = await response.json();
    res.json({
      headers: data2.headers,
      data: data,
      lastUpdates: new Date().toISOString()});
  } catch (error) {
    console.error('Error fetching data:', error);
    res.status(500).send('Error fetching data');
  }
});

// Start the server
const port = 3004;
app.listen(port, () => {console.log(`Server is running at http://localhost:${port}`);});
