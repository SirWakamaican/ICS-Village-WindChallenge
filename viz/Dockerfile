# Example Dockerfile for HTTPS container
FROM node:18-alpine

# Create app directory
WORKDIR /usr/src/app

# Copy package.json and package-lock.json (if present)
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy the rest of the code (server.js, public folder, etc.)
COPY . .

# Expose the port that your Node.js server listens on
EXPOSE 3000

# Run the server
CMD ["npm", "start"]
