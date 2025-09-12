#!/bin/bash

# Jamming Bot Portainer Template Setup Script
# This script helps you configure the Portainer template for easy deployment

echo "🤖 Jamming Bot Portainer Template Setup"
echo "======================================="
echo ""

# Check if Portainer URL is provided
if [ -z "$1" ]; then
    echo "Please provide your Portainer URL as the first argument."
    echo "Usage: $0 <portainer-url> [admin-username] [admin-password]"
    echo "Example: $0 https://portainer.yourdomain.com admin mypassword"
    echo ""
    echo "If username and password are not provided, you'll be prompted for them."
    exit 1
fi

PORTAINER_URL="$1"
USERNAME="$2"
PASSWORD="$3"

# Remove trailing slash from URL
PORTAINER_URL=${PORTAINER_URL%/}

echo "Portainer URL: $PORTAINER_URL"
echo ""

# Prompt for credentials if not provided
if [ -z "$USERNAME" ]; then
    read -p "Portainer username: " USERNAME
fi

if [ -z "$PASSWORD" ]; then
    read -s -p "Portainer password: " PASSWORD
    echo ""
fi

echo ""
echo "🔐 Authenticating with Portainer..."

# Authenticate and get JWT token
AUTH_RESPONSE=$(curl -s -X POST \
  "$PORTAINER_URL/api/auth" \
  -H "Content-Type: application/json" \
  -d "{\"Username\":\"$USERNAME\",\"Password\":\"$PASSWORD\"}")

# Extract JWT token
JWT=$(echo $AUTH_RESPONSE | grep -o '"jwt":"[^"]*' | cut -d'"' -f4)

if [ -z "$JWT" ]; then
    echo "❌ Authentication failed. Please check your credentials and Portainer URL."
    echo "Response: $AUTH_RESPONSE"
    exit 1
fi

echo "✅ Authentication successful!"
echo ""

# Get template URL
TEMPLATE_URL="https://raw.githubusercontent.com/alexeyroudenko/jamming-bot/main/portainer-template.json"

echo "📥 Setting up template URL in Portainer..."
echo "Template URL: $TEMPLATE_URL"

# Update settings with the template URL
SETTINGS_RESPONSE=$(curl -s -X PUT \
  "$PORTAINER_URL/api/settings" \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d "{
    \"TemplatesURL\": \"$TEMPLATE_URL\",
    \"EnableHostManagementFeatures\": true,
    \"AllowBindMountsForRegularUsers\": true,
    \"AllowPrivilegedModeForRegularUsers\": true,
    \"AllowVolumeBrowserForRegularUsers\": true,
    \"AllowHostNamespaceForRegularUsers\": true,
    \"AllowDeviceMappingForRegularUsers\": true,
    \"AllowStackManagementForRegularUsers\": true,
    \"AllowContainerCapabilitiesForRegularUsers\": true
  }")

if echo "$SETTINGS_RESPONSE" | grep -q "error"; then
    echo "❌ Failed to update Portainer settings."
    echo "Response: $SETTINGS_RESPONSE"
    exit 1
fi

echo "✅ Template URL configured successfully!"
echo ""

echo "🎉 Setup Complete!"
echo "=================="
echo ""
echo "Your Jamming Bot templates are now available in Portainer!"
echo ""
echo "To use the templates:"
echo "1. Go to your Portainer instance: $PORTAINER_URL"
echo "2. Navigate to 'App Templates'"
echo "3. Look for 'Jamming Bot' templates"
echo "4. Choose the appropriate template:"
echo "   - 'Jamming Bot (Production)' - Full production deployment"
echo "   - 'Jamming Bot (Development)' - Development environment"
echo "   - 'Jamming Bot (Minimal)' - Lightweight testing"
echo ""
echo "Or create a stack directly:"
echo "1. Go to 'Stacks' → 'Add Stack'"
echo "2. Choose 'Repository'"
echo "3. Repository URL: https://github.com/alexeyroudenko/jamming-bot"
echo "4. Compose file: docker-compose-prod.yml (or docker-compose.yml for dev)"
echo ""
echo "📖 For detailed instructions, see PORTAINER_README.md"
echo ""
echo "Happy jamming! 🎵"