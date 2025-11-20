#!/bin/sh
set -e

# Replace placeholders in runtime-config.js with actual environment variables
sed "s|__USER_POOL_ID__|${NEXT_PUBLIC_USER_POOL_ID}|g" /app/public/runtime-config.js > /tmp/runtime-config.js && mv /tmp/runtime-config.js /app/public/runtime-config.js
sed "s|__USER_POOL_CLIENT_ID__|${NEXT_PUBLIC_USER_POOL_CLIENT_ID}|g" /app/public/runtime-config.js > /tmp/runtime-config.js && mv /tmp/runtime-config.js /app/public/runtime-config.js
sed "s|__AWS_REGION__|${NEXT_PUBLIC_AWS_REGION}|g" /app/public/runtime-config.js > /tmp/runtime-config.js && mv /tmp/runtime-config.js /app/public/runtime-config.js

# Start Next.js
exec "$@"
