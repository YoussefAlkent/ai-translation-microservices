FROM node:18-alpine

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install --production

# Copy source code
COPY src/ ./src/

EXPOSE 3001

# Start the application
CMD ["npm", "start"]
