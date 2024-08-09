const fs = require('fs');

const express = require('express');
const https = require('https');
const mqtt = require('mqtt');
const { Server } = require('socket.io');
const path = require('path');


const certPath = path.join(__dirname,'mqtt-certs', 'client-cert.pem');
const keyPath = path.join(__dirname,'mqtt-certs', 'client-key.pem');
const caPath = path.join(__dirname,'mqtt-certs', 'ca-cert.pem');

const mqttOptions = {
  host: 'mqtt',
  port: 1883,
  protocol: 'mqtts',
  cert: fs.readFileSync(certPath),
  key: fs.readFileSync(keyPath),
  ca: fs.readFileSync(caPath),
  rejectUnauthorized: false // Set to false if using self-signed certs and you don't want to verify them
};
const topics = ["zone1","zone2","zone3","zone4","zone5","zone6"]
var socketOver = null;
const mqttClient = mqtt.connect(mqttOptions);

mqttClient.on('connect', () => {
  console.log(`Connected to MQTT broker at ${mqttOptions.host}`);
  topics.forEach(mqttTopic => {
    mqttClient.subscribe(mqttTopic, (err) => {
      if (err) {
          console.error(`Failed to subscribe to topic ${mqttTopic}`, err);
      } else {
          console.log(`Subscribed to topic ${mqttTopic}`);
      }
  });
    
  });
  
});

mqttClient.on('message', (topic, message) => {
  console.log(`Received message on topic ${topic}: ${message.toString()}`);
  if (socketOver){
    socketOver.emit('mqttMessage', {topic:topic,message:message.toString()});
    console.log(`emmited ${topic}: ${message.toString()}`);
  }
  //socket.emit('mqttMessage', message.toString());
  //console.log(`emmited ${topic}: ${message.toString()}`);
});

mqttClient.on('error', (err) => {
  console.error('MQTT client encountered an error:', err.message);
});

// Handle other possible events like close and reconnect
mqttClient.on('close', () => {
  console.log('MQTT client disconnected');
});

mqttClient.on('reconnect', () => {
  console.log('MQTT client reconnecting...');
});


const app = express();

// Load SSL certificate and key
const servercertPath = path.join(__dirname,'mqtt-certs', 'server-cert.pem');
const serverpkeyPath = path.join(__dirname,'mqtt-certs', 'server-key.pem');

const options = {
    key: fs.readFileSync(serverpkeyPath),
    cert: fs.readFileSync(servercertPath)
};

// Create an HTTPS server
const server = https.createServer(options, app);

// Create a Socket.IO instance attached to the HTTPS server
const io = new Server(server);

// Serve static files from the 'public' directory


app.get("/", (req, res) => {
  res.sendFile(__dirname + "/index.html");
});
app.get("/map.png", (req, res) => {
  res.sendFile(__dirname + "/map.png");
});
app.get("/nrel-logo-web.svg", (req, res) => {
  res.sendFile(__dirname + "/nrel-logo-web.svg");
});



// Handle Socket.IO connections
io.on('connection', (socket) => {
    console.log('A user connected:', socket.id);

    // Handle a custom event
    socket.on('my event', (data) => {
        console.log('Received data:', data);
        // Send a response back to the client
        socket.emit('my response', { msg: 'Hello from the server!' });
    });
    socketOver = socket;

    // Handle disconnection
    socket.on('disconnect', () => {
        console.log('A user disconnected:', socket.id);
    });
});

// Start the server
const PORT = 3000;
server.listen(PORT, () => {
    console.log(`HTTPS server running on https://localhost:${PORT}`);
});