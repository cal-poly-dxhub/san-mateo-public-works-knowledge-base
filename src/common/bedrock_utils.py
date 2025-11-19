"""Bedrock utility functions with retry logic"""
import time
from functools import wraps

from botocore.exceptions import ClientError


def bedrock_retry(max_attempts=3, backoff_base=2):
    """Retry decorator for Bedrock API calls with exponential backoff"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except ClientError as e:
                    error_code = e.response["Error"]["Code"]

                    # Retry on throttling or service errors
                    if error_code in [
                        "ThrottlingException",
                        "ServiceUnavailable",
                        "InternalServerError",
                        "TooManyRequestsException",
                    ]:
                        if attempt < max_attempts - 1:
                            wait_time = backoff_base**attempt
                            print(
                                f"Bedrock API throttled, retrying in {wait_time}s (attempt {attempt + 1}/{max_attempts})"
                            )
                            time.sleep(wait_time)
                            continue
                    raise
            return None

        return wrapper

    return decorator


@bedrock_retry(max_attempts=3)
def invoke_bedrock_model(bedrock_client, **kwargs):
    """Invoke Bedrock model with retry logic"""
    return bedrock_client.invoke_model(**kwargs)


@bedrock_retry(max_attempts=3)
def bedrock_converse(bedrock_client, **kwargs):
    """Bedrock converse with retry logic"""
    return bedrock_client.converse(**kwargs)
