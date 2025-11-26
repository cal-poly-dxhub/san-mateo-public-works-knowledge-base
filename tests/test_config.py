import os
import warnings

# API Configuration
API_URL = os.getenv("API_URL", "")
if API_URL:
    API_URL = API_URL.rstrip('/')

# Cognito Configuration
USER_POOL_ID = os.getenv("USER_POOL_ID", "")
USER_POOL_CLIENT_ID = os.getenv("USER_POOL_CLIENT_ID", "")
TEST_USERNAME = os.getenv("TEST_USERNAME", "")
TEST_PASSWORD = os.getenv("TEST_PASSWORD", "")

# Validate required config
if not all([API_URL, USER_POOL_ID, USER_POOL_CLIENT_ID, TEST_USERNAME, TEST_PASSWORD]):
    warnings.warn(
        "Required environment variables not set. "
        "Set API_URL, USER_POOL_ID, USER_POOL_CLIENT_ID, TEST_USERNAME, TEST_PASSWORD. "
        "Integration tests will be skipped.",
        UserWarning
    )

# AWS Resources
S3_BUCKET = os.getenv("S3_BUCKET", "")
DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE", "")
KNOWLEDGE_BASE_ID = os.getenv("KNOWLEDGE_BASE_ID", "")

# Test Configuration
MAX_PROCESSING_TIMEOUT = int(os.getenv("MAX_PROCESSING_TIMEOUT", "180"))
POLLING_INTERVAL = int(os.getenv("POLLING_INTERVAL", "5"))
