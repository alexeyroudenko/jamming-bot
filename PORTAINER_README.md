# Portainer Template for Jamming Bot

This directory contains Portainer templates for deploying the Jamming Bot application stack.

## Templates Included

### 1. Jamming Bot (Production)
- **File**: Uses `docker-compose-prod.yml`
- **Description**: Complete production deployment with all services
- **Services Included**:
  - Bot service (port 7001)
  - Flask API (port 5000) 
  - Redis cache (port 6379)
  - PostgreSQL database
  - Worker processes (RQ workers)
  - Nginx reverse proxy (ports 80, 443, 5001)
  - Multiple microservices (tags, keywords, semantic, IP services)
  - SpaCy API for NLP processing
  - RQ Dashboard for monitoring workers

### 2. Jamming Bot (Development)
- **File**: Uses `docker-compose.yml`
- **Description**: Simplified development deployment
- **Services Included**: Core services for development and testing

## How to Use

### Option 1: Direct Import in Portainer
1. Go to your Portainer instance
2. Navigate to **App Templates** → **Settings**
3. Add the template URL: `https://raw.githubusercontent.com/alexeyroudenko/jamming-bot/main/portainer-template.json`
4. Save the settings

### Option 2: Manual Upload
1. Download the `portainer-template.json` file
2. In Portainer, go to **App Templates** → **Custom Templates**
3. Upload the JSON file

### Option 3: Using the Stack Creation
1. Go to **Stacks** → **Add Stack**
2. Choose **Repository** option
3. Enter repository URL: `https://github.com/alexeyroudenko/jamming-bot`
4. Select the appropriate compose file:
   - `docker-compose-prod.yml` for production
   - `docker-compose.yml` for development

## Required Environment Variables

Before deploying, make sure to configure these environment variables:

### Essential Variables
- `BOT_TOKEN`: Your bot authentication token
- `SECRET_KEY`: Flask application secret key
- `DATABASE_URI`: PostgreSQL connection string (optional, uses default if not set)

### Optional Variables
- `FLASK_ENV`: Environment setting (production/development)
- `REDIS_URL`: Redis connection URL (uses default if not set)

## Network and Ports

The stack creates an internal bridge network `app_network` with the following exposed ports:

- **80, 443**: Nginx (HTTP/HTTPS)
- **5000**: Flask API
- **5001**: Nginx additional port
- **6379**: Redis
- **7001**: Bot service
- **8003**: Tags service
- **8004**: IP service  
- **8005**: Semantic service
- **7771**: Keywords service
- **9181**: RQ Dashboard

## Volumes

The stack creates and uses several volumes:
- `postgres_data_tags`: PostgreSQL data persistence
- `data`: Application data (external volume)
- Bind mounts for application code and configuration

## SSL/TLS Certificates

The production template includes Certbot for automatic SSL certificate management for domains:
- `jamming-bot.arthew0.online`
- `n8n.arthew0.online`

Update the certbot configuration in the compose file to use your own domains.

## Resource Limits

The production template includes resource limits:
- Bot service: 0.5 CPU cores
- Flask service: 0.5 CPU cores  
- Workers: 0.25 CPU cores each

## Monitoring

The stack includes:
- **RQ Dashboard** (port 9181): Monitor worker queues and jobs
- **Redis**: For caching and job queuing

## Troubleshooting

1. **Services not starting**: Check the logs in Portainer for specific error messages
2. **Database connection issues**: Verify the `DATABASE_URI` environment variable
3. **Bot not responding**: Ensure `BOT_TOKEN` is correctly set
4. **SSL issues**: Check certbot logs and domain configuration

## Development vs Production

**Development template**:
- Uses `docker-compose.yml`
- Simplified service configuration
- Suitable for testing and development

**Production template**:
- Uses `docker-compose-prod.yml`
- Full service stack with monitoring
- SSL certificate management
- Resource limits and optimization
- Nginx reverse proxy with load balancing