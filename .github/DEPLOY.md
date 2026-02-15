# K3s Deployment Setup

This guide explains how to configure the CI/CD pipeline to deploy jamming-bot to your K3s cluster at `b0ts.arthew0.online`.

## Prerequisites

1. **K3s cluster** running on `b0ts.arthew0.online`
2. **SSH access** to the server with Docker and kubectl available
3. **Git repository** cloned on the server at the deploy path

## One-time Server Setup

SSH into your server and run:

```bash
# Clone the repo (if not already present)
sudo mkdir -p /opt
sudo git clone https://github.com/YOUR_USERNAME/jamming-bot.git /opt/jamming-bot
cd /opt/jamming-bot

# Ensure kubectl uses k3s config
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
# Or add to ~/.bashrc for your deploy user
```

## GitHub Secrets

Add these secrets in your repo: **Settings → Secrets and variables → Actions**

| Secret | Required | Description |
|--------|----------|-------------|
| `K3S_SSH_HOST` | No | SSH host (default: `b0ts.arthew0.online`) |
| `K3S_SSH_USER` | **Yes** | SSH username (e.g. `root` or `deploy`) |
| `K3S_SSH_PRIVATE_KEY` | **Yes** | Full contents of your SSH private key |
| `K3S_SSH_PORT` | No | SSH port (default: `22`) |
| `K3S_DEPLOY_PATH` | No | Path to repo on server (default: `/opt/jamming-bot`) |

### Generate SSH key for deploy

```bash
ssh-keygen -t ed25519 -C "github-actions-deploy" -f deploy_key -N ""
# Add deploy_key.pub to server's ~/.ssh/authorized_keys
# Add deploy_key contents to K3S_SSH_PRIVATE_KEY secret
```

## Workflow Triggers

- **Push to `main`** – deploys automatically
- **Manual** – run via Actions → Deploy to K3s → Run workflow

## Deployment Flow

1. GitHub Actions SSHs into the server
2. Pulls latest code from `main`
3. Builds all Docker images locally on the server
4. Imports images into K3s (`k3s ctr images import`)
5. Applies `deployment.yaml`
6. Restarts all deployments for rolling update
