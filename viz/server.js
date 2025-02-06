const fs = require('fs');
const path = require('path');
const express = require('express');
const helmet = require('helmet');
const https = require('https');
const { Server } = require('socket.io');
const mqtt = require('mqtt');

// ---------------------------------------------------------------------
// SSL certificates for HTTPS (Node.js server-side TLS).
// ---------------------------------------------------------------------
const serverKey = fs.readFileSync(path.join(__dirname, 'mqtt-certs', 'server.key'));
const serverCert = fs.readFileSync(path.join(__dirname, 'mqtt-certs', 'server.pem'));
const caPath = path.join(__dirname, 'mqtt-certs', 'ca.pem'); 

// Create an Express app
const app = express();

// Use Helmet for default security headers, including basic CSP
app.use(
  helmet({
    contentSecurityPolicy: {
      directives: {
        defaultSrc: ["'self'"],
        scriptSrc: ["'self'"] // Scripts must come from same origin
      }
    },
  })
);

// Serve static files (index.html, main.js, images, etc.) from the "public" folder
app.use(express.static(path.join(__dirname, 'public')));

// Create an HTTPS server
const server = https.createServer(
  {
    key: serverKey,
    cert: serverCert,
    // If using self-signed, you may need: ca: fs.readFileSync(caPath)
  },
  app
);

// Attach Socket.IO to the HTTPS server
const io = new Server(server);

// ---------------------------------------------------------------------
// MQTT Client Setup - connect to broker at 'mqtt' for TLS on port 1883
// ---------------------------------------------------------------------
const mqttClient = mqtt.connect({
  host: 'mqtt',
  port: 1883,         // If Mosquitto is configured for TLS on 1883
  protocol: 'mqtts',  // 'mqtts' indicates secure MQTT
  ca: fs.readFileSync(caPath),
  // If self-signed, you might do rejectUnauthorized: false
});

mqttClient.on('connect', () => {
  console.log('Node.js -> MQTT broker connected');
  
  // Subscribe to zones 1..16
  for (let i = 1; i <= 16; i++) {
    const topic = `zone${i}`;
    mqttClient.subscribe(topic, (err) => {
      if (err) {
        console.error(`Error subscribing to ${topic}:`, err.message);
      } else {
        console.log(`Subscribed to ${topic}`);
      }
    });
  }
});

mqttClient.on('message', (topic, message) => {
  console.log(`MQTT message on ${topic}: ${message.toString()}`);
  // Forward MQTT data to all Socket.IO clients
  io.emit('mqttMessage', { topic, message: message.toString() });
});

mqttClient.on('error', (err) => {
  console.error('MQTT Error:', err.message);
});

// ---------------------------------------------------------------------
// Socket.IO: Handle client connections
// ---------------------------------------------------------------------
io.on('connection', (socket) => {
  console.log('New Socket.IO client:', socket.id);

  // Example custom event
  socket.on('my event', (data) => {
    console.log('Client says:', data);
    socket.emit('my response', { msg: 'Hello from the server!' });
  });
});

// Start the server on port 3000
server.listen(3000, () => {
  console.log('HTTPS server running on https://localhost:3000');
});
