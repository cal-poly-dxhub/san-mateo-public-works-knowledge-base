#!/bin/sh
set -e

# Replace placeholders in runtime-config.js with actual environment variables
cat > /app/public/runtime-config.js << EOF
window.__RUNTIME_CONFIG__ = {
  NEXT_PUBLIC_API_URL: "${NEXT_PUBLIC_API_URL}",
  NEXT_PUBLIC_USER_POOL_ID: "${NEXT_PUBLIC_USER_POOL_ID}",
  NEXT_PUBLIC_USER_POOL_CLIENT_ID: "${NEXT_PUBLIC_USER_POOL_CLIENT_ID}",
  NEXT_PUBLIC_AWS_REGION: "${NEXT_PUBLIC_AWS_REGION}"
};
EOF

# Start Next.js
exec "$@"
