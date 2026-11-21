# Development and CI image for the web UI.
# There is no Node server in production: the built files are served by Django.
FROM node:24-slim AS dev

ENV CI=true \
    NPM_CONFIG_UPDATE_NOTIFIER=false \
    NPM_CONFIG_FUND=false \
    NPM_CONFIG_AUDIT=false

WORKDIR /app

# Sources and node_modules are provided by the compose service (bind mount and volume).
CMD ["npm", "run", "build"]
