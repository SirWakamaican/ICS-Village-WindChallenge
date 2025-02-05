const fs = require('fs');
const path = require('path');
const express = require('express');
const helmet = require('helmet');
const https = require('https');
const { Server } = require('socket.io');
const mqtt = require('mqtt');

// ---------------------------------------------------------------------
// SSL certificates for HTTPS (Node.js server-side TLS).
// Adjust paths to your actual cert files if you want HTTPS in Node.
// If you prefer plain HTTP, skip these lines and use `http.createServer()`.
//
// * This is separate from the MQTT certs used by Mosquitto, though
//   you might reuse the same files in some setups.
// ---------------------------------------------------------------------
const serverKey = fs.readFileSync(path.join(__dirname, 'mqtt-certs', 'server.key'));
const serverCert = fs.readFileSync(path.join(__dirname, 'mqtt-certs', 'server.pem'));
const caPath = path.join(__dirname, 'mqtt-certs', 'ca.pem'); 

// Create an Express app
const app = express();

// Use Helmet for some default security headers, including a basic CSP
app.use(
  helmet({
    contentSecurityPolicy: {
      directives: {
        defaultSrc: ["'self'"],
        // 'self' means scripts, images, etc. must come from the same origin
        scriptSrc: ["'self'"]
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
    // If using self-signed, you may need: ca: fs.readFileSync('ca-cert.pem')
  },
  app
);

// Attach Socket.IO to the HTTPS server
const io = new Server(server);

// ---------------------------------------------------------------------
// (Optional) MQTT Client Setup - if your Node.js app also needs to
// connect to the broker internally at hostname "mqtt" from Compose.
// ---------------------------------------------------------------------
const mqttClient = mqtt.connect({
  host: 'mqtt',
  port: 1883,       // or 8443 if using TLS on the broker
  protocol: 'mqtts', // or 'mqtts' if using TLS
  ca: fs.readFileSync(caPath),
  // For self-signed certs or local dev, you might set rejectUnauthorized: false
});

mqttClient.on('connect', () => {
  console.log('Node.js -> MQTT broker connected');
  // Example: subscribe to some topics
  mqttClient.subscribe('zone1');
  mqttClient.subscribe('zone2');
  mqttClient.subscribe('zone3');
  mqttClient.subscribe('zone4');
  mqttClient.subscribe('zone5');
  mqttClient.subscribe('zone6');
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
  // For example, handle a custom event
  socket.on('my event', (data) => {
    console.log('Client says:', data);
    socket.emit('my response', { msg: 'Hello from the server!' });
  });
});

// Start the server on port 3000
server.listen(3000, () => {
  console.log('HTTPS server running on https://localhost:3000');
});
