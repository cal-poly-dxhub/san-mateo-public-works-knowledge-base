"""DynamoDB utility functions for pagination and queries"""


def query_all_items(table, **kwargs):
    """Query all items with automatic pagination"""
    items = []
    last_evaluated_key = None

    while True:
        if last_evaluated_key:
            kwargs["ExclusiveStartKey"] = last_evaluated_key

        response = table.query(**kwargs)
        items.extend(response.get("Items", []))

        last_evaluated_key = response.get("LastEvaluatedKey")
        if not last_evaluated_key:
            break

    return items


def scan_all_items(table, **kwargs):
    """Scan all items with automatic pagination (use sparingly)"""
    items = []
    last_evaluated_key = None

    while True:
        if last_evaluated_key:
            kwargs["ExclusiveStartKey"] = last_evaluated_key

        response = table.scan(**kwargs)
        items.extend(response.get("Items", []))

        last_evaluated_key = response.get("LastEvaluatedKey")
        if not last_evaluated_key:
            break

    return items


def list_all_s3_objects(s3_client, **kwargs):
    """List all S3 objects with pagination"""
    paginator = s3_client.get_paginator("list_objects_v2")
    objects = []

    for page in paginator.paginate(**kwargs):
        objects.extend(page.get("Contents", []))

    return objects
