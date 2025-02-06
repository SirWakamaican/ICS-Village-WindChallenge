/***************************************************************
 * 1) LAYOUT SETUP AND ZONE TRACKING
 ***************************************************************/
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
  
  // We have 16 zones. 1 = Normal, 0 = Down
  let zones = Array(16).fill(1);
  
  // We'll store the polygons for each zone, and their text coordinates
  // shapes[i] = array of points [[x1,y1], [x2,y1], [x2,y2], [x1,y2], [x1,y1]]
  // textLocation[i] = [centerX, centerY]
  let shapes = [];
  let textLocation = [];
  
  /**
   * Dynamically create a 4x4 grid of squares over the canvas.
   * Each zone is a rectangle. shapes[0] -> zone1, shapes[1] -> zone2, etc.
   */
  function initShapesAndTextLocations() {
    const rows = 4;
    const cols = 4;
    const cellWidth = canvas.width / cols;
    const cellHeight = canvas.height / rows;
  
    for (let i = 0; i < 16; i++) {
      const row = Math.floor(i / cols);
      const col = i % cols;
  
      const x1 = col * cellWidth;
      const y1 = row * cellHeight;
      const x2 = x1 + cellWidth;
      const y2 = y1 + cellHeight;
  
      // A simple rectangle: top-left -> top-right -> bottom-right -> bottom-left -> back to top-left
      shapes[i] = [
        [x1, y1],
        [x2, y1],
        [x2, y2],
        [x1, y2],
        [x1, y1]
      ];
  
      // Center of the cell for the zone label
      textLocation[i] = [
        (x1 + x2) / 2,
        (y1 + y2) / 2
      ];
    }
  }
  
  /***************************************************************
   * 2) DRAWING AND UPDATING ON CANVAS
   ***************************************************************/
  
  /**
   * Draw a single zone on the canvas
   * @param {CanvasRenderingContext2D} ctx
   * @param {boolean} isNormal - true=Normal, false=Down
   * @param {number} zoneNumber - 1..16
   */
  function drawZone(ctx, isNormal, zoneNumber) {
    const zoneIndex = zoneNumber - 1;
    ctx.beginPath();
  
    // Color: Normal=red, Down=green
    ctx.fillStyle = isNormal ? "red" : "green";
    ctx.globalAlpha = 0.4;
  
    // Draw the polygon
    // shapes[zoneIndex] is the array of points for this zone
    ctx.moveTo(shapes[zoneIndex][0][0], shapes[zoneIndex][0][1]);
    shapes[zoneIndex].forEach((pt) => {
      ctx.lineTo(pt[0], pt[1]);
    });
    ctx.fill();
  
    // Label the zone number in the center
    ctx.globalAlpha = 0.6;
    ctx.textAlign = "center";
    ctx.font = "40px Arial"; // Adjust font size to fit squares
    ctx.fillText(
      zoneNumber.toString(),
      textLocation[zoneIndex][0],
      textLocation[zoneIndex][1]
    );
    ctx.globalAlpha = 1;
  }
  
  /**
   * Update the side panel text/color for each zone
   */
  function updateBoard() {
    zones.forEach((val, index) => {
      const zoneNum = index + 1;
      const textElem = document.getElementById(`zone${zoneNum}Text`);
      const divElem = document.getElementById(`zone${zoneNum}Div`);
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
  
  /**
   * Called whenever a single zone’s status changes
   * @param {number} zoneNumber - from 1..16
   * @param {boolean} isNormal
   */
  function updateZone(zoneNumber, isNormal) {
    // Check zone bounds
    if (zoneNumber < 1 || zoneNumber > 16) return;
  
    // 1=Normal, 0=Down
    zones[zoneNumber - 1] = isNormal ? 1 : 0;
    updateBoard();
  
    // Redraw entire map
    ctx.drawImage(image, 0, 0);
    for (let i = 1; i <= 16; i++) {
      drawZone(ctx, zones[i - 1] === 1, i);
    }
  }
  
  /***************************************************************
   * 3) INITIAL SETUP AND EVENT HANDLERS
   ***************************************************************/
  
  resize();            // Size the side panel
  initShapesAndTextLocations(); // Build shapes + text coords for 16 squares
  
  // Draw once image is loaded
  image.addEventListener("load", () => {
    ctx.drawImage(image, 0, 0);
    for (let i = 1; i <= 16; i++) {
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
    ctx.drawImage(image, 0, 0);
    for (let i = 1; i <= 16; i++) {
      drawZone(ctx, zones[i - 1] === 1, i);
    }
  });
  
  // Listen for MQTT messages forwarded by the server
  socket.on('mqttMessage', (data) => {
    console.log("mqttMessage:", data);
  
    const prefix = "zone";
    
    // Extract everything after "zone"
    const zoneStr = data.topic.slice(prefix.length); // e.g. "10"
    const zoneNum = parseInt(zoneStr, 10); 
    if (isNaN(zoneNum)) return;
  
    // -- Possibly parse data.message as JSON --
    let value = data.message;
    if (typeof value === 'string') {
      try {
        const parsed = JSON.parse(value);
        value = parsed;
      } catch (err) {
        // leave as string if parse fails
      }
    }
  
    // If it's an array, pick subValue = value[zoneNum % 4], else process value directly
    if (Array.isArray(value)) {
      const subValue = value[zoneNum % 4];
      processValue(zoneNum, subValue);
    } else {
      processValue(zoneNum, value);
    }
  });
  
  /**
   * Convert subValue to a boolean, then updateZone(zoneNum, thatBoolean)
   */
  function processValue(zoneNum, val) {
    if (typeof val === 'boolean') {
      updateZone(zoneNum, val);
    } else if (typeof val === 'string') {
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
      if (val === 0) {
        updateZone(zoneNum, false);
      } else if (val === 1) {
        updateZone(zoneNum, true);
      } else {
        console.log('Number not recognized (only 0/1) -> boolean:', val);
      }
    } else {
      console.log('Unsupported type for data.message:', val);
    }
  }
  
  socket.on('disconnect', () => {
    console.log('Socket.IO disconnected');
  });
  