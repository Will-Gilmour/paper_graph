# Use a small Node image
FROM node:18-alpine

# Create app directory
WORKDIR /app

# Install dependencies based on package.json/lockfile
COPY package.json package-lock.json* ./
RUN npm ci

# Copy the rest of your source code
COPY . .

# Expose Vite’s default port
EXPOSE 3000

# Dev server: watch all files under /app
CMD ["npm", "run", "dev"]
