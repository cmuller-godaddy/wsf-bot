# Deployment (Digital Ocean Droplet)

## Droplet Setup

- **OS:** Ubuntu 24.04 (LTS) x64
- **Plan:** Basic, Regular SSD, $6/mo (1 vCPU, 1 GB RAM)
  - Playwright needs at least 1 GB RAM for the headless browser

## Initial Setup

SSH into the droplet and run:

```bash
# Install Docker (wait ~1 min after first boot for apt locks to clear)
curl -fsSL https://get.docker.com | sh

# Authenticate to GitHub Container Registry
# Requires a GitHub PAT with read:packages scope (image is private)
echo "<YOUR_GITHUB_PAT>" | docker login ghcr.io -u cmuller-godaddy --password-stdin

# Create config
nano config.yml
# See example.config.yml for the format

# Run the bot
docker run -d --restart unless-stopped --name wsf-bot \
  -v $(pwd)/config.yml:/usr/bot/config.yml \
  ghcr.io/cmuller-godaddy/wsf-bot:latest
```

## Updating

When new code is pushed to `main`, GitHub Actions rebuilds and pushes the image. To update the droplet:

```bash
docker pull ghcr.io/cmuller-godaddy/wsf-bot:latest
docker rm -f wsf-bot
docker run -d --restart unless-stopped --name wsf-bot \
  -v $(pwd)/config.yml:/usr/bot/config.yml \
  ghcr.io/cmuller-godaddy/wsf-bot:latest
```

## Useful Commands

```bash
docker logs -f wsf-bot    # tail logs
docker restart wsf-bot    # restart without pulling new image
```
