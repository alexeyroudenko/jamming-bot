# Quick Deployment Guide for Portainer

## Method 1: Using App Templates (Recommended)

### Automatic Setup
Run the setup script to automatically configure the template in your Portainer:

```bash
./setup-portainer-template.sh https://your-portainer-url.com admin your-password
```

### Manual Setup
1. In Portainer, go to **Settings** → **App Templates**
2. Add this URL: `https://raw.githubusercontent.com/alexeyroudenko/jamming-bot/main/portainer-template.json`
3. Save settings
4. Go to **App Templates** and find "Jamming Bot" templates

## Method 2: Direct Stack Creation

1. Go to **Stacks** → **Add Stack**
2. Choose **Repository**
3. Enter:
   - **Repository URL**: `https://github.com/alexeyroudenko/jamming-bot`
   - **Compose file**: `docker-compose-prod.yml` (production) or `docker-compose.yml` (development)
   - **Stack name**: `jamming-bot`

## Required Configuration

### Essential Environment Variables
Before deploying, set these in the **Environment** section:

```
BOT_TOKEN=your_actual_bot_token
SECRET_KEY=your_secure_secret_key
```

### Optional Variables
```
FLASK_ENV=production
POSTGRES_USER=tags_db_username
POSTGRES_PASSWORD=secure_password_here
POSTGRES_DB=tags_db_dev
DOMAIN_NAME=your-domain.com
EMAIL=your-email@domain.com
```

## Template Options

### 🚀 Production Template
- **File**: `docker-compose-prod.yml`
- **Services**: All services with monitoring, SSL, resource limits
- **Best for**: Production deployments

### 🔧 Development Template  
- **File**: `docker-compose.yml`
- **Services**: Core services only
- **Best for**: Development and testing

### ⚡ Minimal Template
- **Services**: Bot + Flask + Redis only
- **Best for**: Quick testing

## Post-Deployment

### Check Service Status
1. Go to **Stacks** → Select your stack
2. Verify all services are running (green status)

### Access Services
- **Flask API**: `http://your-server:5000`
- **Bot Service**: `http://your-server:7001`
- **RQ Dashboard**: `http://your-server:9181` (production only)
- **Nginx**: `http://your-server` (production only)

### Common Issues

**Services won't start?**
- Check logs in Portainer for each service
- Verify BOT_TOKEN is set correctly
- Ensure required ports are available

**Database connection errors?**
- Wait for PostgreSQL to fully initialize (30-60 seconds)
- Check DATABASE_URI environment variable

**Bot not responding?**
- Verify BOT_TOKEN is valid
- Check bot service logs

## Updating the Stack

1. Go to **Stacks** → Select your stack
2. Click **Editor** tab
3. Click **Update the stack**
4. Choose **Pull and redeploy**

## Backup Important Data

The following should be backed up regularly:
- PostgreSQL data: `/var/lib/docker/volumes/jamming-bot_postgres_data_tags`
- Application data: `./data` directory
- Redis data: `./data/redis`

## Support

For issues:
1. Check service logs in Portainer
2. Review the main README.md
3. Check the GitHub repository issues