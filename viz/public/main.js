function resize() {
    const body = document.getElementById("body");
    const canvas = document.getElementById("canvas");
    const side = document.getElementById("side");
    side.style.width = (body.clientWidth - canvas.clientWidth) - 1 + "px";
  }
  
  window.onresize = resize;
  
  const canvas = document.getElementById("canvas");
  const ctx = canvas.getContext("2d");
  const image = document.getElementById("map");
  
  // Zone elements
  const zone1Text = document.getElementById('zone1Text');
  const zone1Div = document.getElementById('zone1Div');
  const zone2Text = document.getElementById('zone2Text');
  const zone2Div = document.getElementById('zone2Div');
  const zone3Text = document.getElementById('zone3Text');
  const zone3Div = document.getElementById('zone3Div');
  const zone4Text = document.getElementById('zone4Text');
  const zone4Div = document.getElementById('zone4Div');
  const zone5Text = document.getElementById('zone5Text');
  const zone5Div = document.getElementById('zone5Div');
  
  // Tracks which zones are "good"/"normal" vs "down"
  let zones = [1, 1, 1, 1, 1]; // 1 = Normal, 0 = Down
  
  // Coordinates for drawing shapes
  const textLocation = [[335,430],[1052,302],[1894,834],[490,1250],[1190,937],[1386,1419]];
  const shapes = [
    [ [0,0], [502,0], [1019,699], [1093,713], [1072,799], [0,799], [0,0] ],
    [ [502,0], [1019,699], [1093,713], [1942,0], [502,0] ],
    [ [1942,0], [1093,713], [1245,780], [2077,1684], [2232,1684], [2232,0], [1942,0] ],
    [ [0,799], [1072,799], [995,915], [995,1684], [0,1684], [0,799] ],
    [ [995,1066], [995,915], [1072,799], [1093,713], [1245,780], [1519,1066], [2077,1684], [995,1684], [995,1066] ],
    [ [995,1684], [995,1066], [1519,1066], [2077,1684], [995,1684] ],
  ];
  
  function drawZone(ctx, isNormal, z) {
    const zoneIndex = z - 1;
    ctx.beginPath();
    
    // Color: normal=red, down=green (per your existing code)
    ctx.fillStyle = isNormal ? "red" : "green";
    ctx.globalAlpha = 0.4;
  
    // Draw polygon
    ctx.moveTo(shapes[zoneIndex][0][0], shapes[zoneIndex][0][1]);
    shapes[zoneIndex].forEach((pix) => {
      ctx.lineTo(pix[0], pix[1]);
    });
    ctx.fill();
  
    // Label the zone number
    ctx.globalAlpha = 0.6;
    ctx.textAlign = "center";
    ctx.font = "120px Arial";
    ctx.fillText(z.toString(), textLocation[zoneIndex][0], textLocation[zoneIndex][1]);
    ctx.globalAlpha = 1;
  }
  
  function updateBoard() {
    // For each zone, update the text and background color
    zones.forEach((val, index) => {
      const zoneNum = index + 1;
      const textElem = document.getElementById('zone' + zoneNum + 'Text');
      const divElem = document.getElementById('zone' + zoneNum + 'Div');
      if (!textElem || !divElem) return;
  
      if (val === 1) {
        textElem.innerText = "Normal";
        divElem.style.backgroundColor = "red";
      } else {
        textElem.innerText = "Down";
        divElem.style.backgroundColor = "green";
      }
    });
  }
  
  // Update one zone by number
  function updateZone(zoneNumber, isNormal) {
    // Just to be safe, zoneNumber should be 1..5 in your example
    if (zoneNumber < 1 || zoneNumber > 6) return;
  
    zones[zoneNumber - 1] = isNormal ? 1 : 0;
    updateBoard();
  
    // Redraw the map
    ctx.drawImage(image, 0, 0);
    for (let i = 1; i <= 5; i++) {
      drawZone(ctx, zones[i - 1] === 1, i);
    }
  }
  
  resize();
  
  // Wait for the map image to load, then draw it once
  image.addEventListener("load", () => {
    ctx.drawImage(image, 0, 0);
    for (let i = 1; i <= 5; i++) {
      drawZone(ctx, zones[i - 1] === 1, i);
    }
  });
  
  // ---------------------------------------------------------------
  // SOCKET.IO: connect to the server, handle events
  // ---------------------------------------------------------------
  const socket = io();
  
  // Example: send an event
  socket.emit('my event', { msg: 'Hello from the client!' });
  
  // Handle server response
  socket.on('my response', (data) => {
    console.log('Server responded:', data);
    // Draw the map if not already drawn
    ctx.drawImage(image, 0, 0);
    for (let i = 1; i <= 5; i++) {
      drawZone(ctx, zones[i - 1] === 1, i);
    }
  });
  
  // Listen for MQTT messages forwarded by the server
  socket.on('mqttMessage', (data) => {
    console.log("mqttMessage:", data);
  
    // Suppose the topic ends with the zone number, e.g. "zone1" => 1
    const lastChar = data.topic.charAt(data.topic.length - 1);
    const zoneNum = parseInt(lastChar, 10);
    if (isNaN(zoneNum)) return;
  
    // Convert the message to a boolean
    // e.g. if message = "1" => isNormal=true, if "0" => isNormal=false
    // Step 1: If it's an array, pick subValue = data.message[zoneNum % 4]
// Step 2: Check subValue's type (boolean/string/number) and call updateZone(zoneNum, boolean)

// 1) Possibly parse data.message as JSON if it's a string
let value = data.message;
if (typeof value === 'string') {
  try {
    const parsed = JSON.parse(value);  // Try to parse JSON
    value = parsed;                    // If successful, replace value
  } catch (err) {
    // If parse fails, we leave 'value' as the original string
    // We'll still do the string logic below.
  }
}

// 2) Now handle arrays, booleans, strings, numbers, etc.
if (Array.isArray(value)) {
  // If it's an array, pick the element based on zoneNum % 4
  const subValue = value[zoneNum % 4];

  // We'll process subValue as if it were "data.message" using a helper function
  processValue(zoneNum, subValue);

} else {
  // It's not an array, so directly process 'value'
  processValue(zoneNum, value);
}

// --------------------------------------------------
// Helper function to parse subValue into a boolean, if possible
// --------------------------------------------------
function processValue(zoneNum, val) {
  if (typeof val === 'boolean') {
    // Already boolean
    updateZone(zoneNum, val);

  } else if (typeof val === 'string') {
    // Check for "true", "false", "0", "1"
    const lower = val.toLowerCase();
    if (lower === 'true') {
      updateZone(zoneNum, true);
    } else if (lower === 'false') {
      updateZone(zoneNum, false);
    } else if (lower === '0') {
      updateZone(zoneNum, false);
    } else if (lower === '1') {
      updateZone(zoneNum, true);
    } else {
      console.log('String not recognized as boolean/0/1:', val);
    }

  } else if (typeof val === 'number') {
    // 0 => false, 1 => true
    if (val === 0) {
      updateZone(zoneNum, false);
    } else if (val === 1) {
      updateZone(zoneNum, true);
    } else {
      console.log('Number not recognized as boolean (only 0/1 allowed):', val);
    }

  } else {
    // Any other type is unsupported
    console.log('Unsupported type for data.message:', val);
  }
}

  
      
      
    
  
    
  });
  
  socket.on('disconnect', () => {
    console.log('Socket.IO disconnected');
  });
  