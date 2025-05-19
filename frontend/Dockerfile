# Use Node.js LTS
FROM node:20-slim

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install
RUN npm install --save-dev @types/js-cookie

# Copy the rest of the application
COPY . .

# Build the Next.js application
RUN npm run build

# Prepare the production build
# Next.js output directory structure has changed, we need to make sure the standalone server can access static files
RUN cp -R .next/static .next/standalone/.next/static
RUN cp -R public .next/standalone/public

# Expose the port the app runs on
EXPOSE 3000

# Set the working directory to the standalone directory
WORKDIR /app/.next/standalone

# Command to run the application - use standalone server.js
CMD ["node", "server.js"]
