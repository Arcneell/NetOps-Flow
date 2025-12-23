# =============================================================================
# NetOps-Flow Frontend Dockerfile - Multi-stage optimized build
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Dependencies - Install npm packages
# -----------------------------------------------------------------------------
FROM node:20-alpine AS deps

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production

# -----------------------------------------------------------------------------
# Stage 2: Builder - Build the application
# -----------------------------------------------------------------------------
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files and install all dependencies (including dev)
COPY package*.json ./
RUN npm ci

# Copy source code
COPY . .

# Build the application
RUN npm run build

# -----------------------------------------------------------------------------
# Stage 3: Production - Serve with nginx
# -----------------------------------------------------------------------------
FROM nginx:alpine AS production

# Labels
LABEL maintainer="NetOps-Flow Team"
LABEL description="NetOps-Flow Frontend"
LABEL version="2.0.0"

# Copy nginx configuration
COPY <<EOF /etc/nginx/conf.d/default.conf
server {
    listen 80;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;
    gzip_min_length 1000;

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # SPA routing - serve index.html for all routes
    location / {
        try_files \$uri \$uri/ /index.html;
    }

    # API proxy (optional - can be configured)
    # location /api {
    #     proxy_pass http://backend:8000;
    #     proxy_http_version 1.1;
    #     proxy_set_header Upgrade \$http_upgrade;
    #     proxy_set_header Connection 'upgrade';
    #     proxy_set_header Host \$host;
    #     proxy_cache_bypass \$http_upgrade;
    # }

    # Health check endpoint
    location /health {
        access_log off;
        return 200 'OK';
        add_header Content-Type text/plain;
    }
}
EOF

# Copy built assets from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost/health || exit 1

# Expose port
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]

# -----------------------------------------------------------------------------
# Stage 4: Development - With hot reload
# -----------------------------------------------------------------------------
FROM node:20-alpine AS development

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install all dependencies
RUN npm install

# Copy source (will be overridden by volume mount in dev)
COPY . .

# Expose Vite dev server port
EXPOSE 3000

# Start development server
CMD ["npm", "run", "dev", "--", "--host"]
