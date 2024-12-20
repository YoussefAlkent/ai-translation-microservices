# Use a newer Node.js version compatible with Next.js 15
FROM node:20-alpine

# Set the working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy the rest of the application code
COPY . .

# Build the application
RUN npm run build

# Expose the port
EXPOSE 4200

# Set the port environment variable
ENV PORT=4200

# Start the application
CMD ["npm", "run", "start"]