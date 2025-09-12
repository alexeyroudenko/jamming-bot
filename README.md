# Jamming Bot

*A samurai has no goal, only a path*

A complete bot application with Flask backend, Redis, PostgreSQL, and multiple microservices for advanced functionality.

## Quick Start with Portainer

### One-Click Deployment
Use our Portainer templates for instant deployment:

1. **Automatic Setup**: Run the setup script
   ```bash
   ./setup-portainer-template.sh https://your-portainer-url.com
   ```

2. **Manual Setup**: Add template URL in Portainer
   ```
   https://raw.githubusercontent.com/alexeyroudenko/jamming-bot/main/portainer-template.json
   ```

3. **Direct Stack Creation**: Use repository URL
   ```
   Repository: https://github.com/alexeyroudenko/jamming-bot
   Compose file: docker-compose-prod.yml
   ```

📖 **Detailed deployment guide**: [PORTAINER_DEPLOYMENT.md](PORTAINER_DEPLOYMENT.md)

## Architecture

### Services
- **Bot Service** (port 7001): Core bot functionality
- **Flask API** (port 5000): Web API and interface
- **Redis** (port 6379): Caching and job queuing
- **PostgreSQL**: Data persistence
- **Worker Processes**: Background job processing
- **Nginx** (ports 80, 443): Reverse proxy with SSL
- **Microservices**:
  - Tags Service (port 8003)
  - Keywords Service (port 7771)
  - Semantic Service (port 8005)
  - IP Service (port 8004)

### Features
- 🤖 Advanced bot capabilities
- 🌐 Web API with real-time updates
- 📊 Background job processing
- 🔍 Semantic analysis and NLP
- 🏷️ Tag and keyword management
- 🌍 IP geolocation services
- 📈 Monitoring and dashboards

## Environment Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Required variables:
- `BOT_TOKEN`: Your bot authentication token
- `SECRET_KEY`: Flask application secret key

## Manual Deployment

### Development
```bash
docker-compose up -d
```

### Production
```bash
docker-compose -f docker-compose-prod.yml up -d
```

## Monitoring

- **RQ Dashboard**: `http://localhost:9181` (production)
- **Application**: `http://localhost:5000`
- **Bot Status**: `http://localhost:7001`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

[Your License Here]