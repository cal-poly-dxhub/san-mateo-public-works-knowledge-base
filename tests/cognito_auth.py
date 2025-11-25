"""Cognito authentication helper for integration tests"""

import os

import boto3
from botocore.exceptions import ClientError

cognito_client = boto3.client("cognito-idp")


def get_auth_token():
    """Get JWT token from Cognito for testing"""
    user_pool_id = os.getenv("USER_POOL_ID", "YOUR_USER_POOL_ID")
    client_id = os.getenv("USER_POOL_CLIENT_ID", "YOUR_CLIENT_ID")
    username = os.getenv("TEST_USERNAME", "test-user@example.com")
    password = os.getenv("TEST_PASSWORD", "YOUR_TEST_PASSWORD")

    if not password:
        raise ValueError(
            "TEST_PASSWORD environment variable required. "
            "Set it to your Cognito user password."
        )

    try:
        # Initiate auth
        response = cognito_client.initiate_auth(
            ClientId=client_id,
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": username, "PASSWORD": password},
        )

        # Return ID token (used for API Gateway authorization)
        return response["AuthenticationResult"]["IdToken"]

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "NotAuthorizedException":
            raise ValueError(
                f"Authentication failed for {username}. "
                "Check TEST_PASSWORD is correct."
            ) from e
        elif error_code == "UserNotFoundException":
            raise ValueError(
                f"User {username} not found in pool {user_pool_id}"
            ) from e
        else:
            raise


def get_auth_headers():
    """Get headers with Authorization token for API requests"""
    token = get_auth_token()
    return {"Content-Type": "application/json", "Authorization": token}
