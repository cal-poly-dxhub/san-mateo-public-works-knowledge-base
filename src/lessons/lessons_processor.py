import json
import os
from datetime import datetime, timezone

import boto3

s3 = boto3.client("s3")
bedrock = boto3.client("bedrock-runtime")

CHUNK_SIZE = 100  # Number of lessons per chunk for comparison


def extract_and_merge_lessons(
    content, filename, project_name, project_type, bucket_name
):
    """Extract lessons from document and merge with existing using LLM tool calling"""

    # Extract new lessons from document
    new_lessons = extract_lessons_from_document(content, filename)

    if not new_lessons:
        return {
            "project_added": 0,
            "project_deleted": 0,
            "type_added": 0,
            "type_deleted": 0,
        }

    # Process project-level lessons
    project_stats = merge_lessons_with_superseding(
        new_lessons=new_lessons,
        existing_lessons_key=f"projects/{project_name}/lessons-learned.json",
        bucket_name=bucket_name,
        context_type="project",
        project_name=project_name,
    )

    # Process project-type-level lessons (add project_name attribution)
    type_lessons = [
        {"project_name": project_name, **lesson} for lesson in new_lessons
    ]
    type_stats = merge_lessons_with_superseding(
        new_lessons=type_lessons,
        existing_lessons_key=f"lessons-learned/{project_type}/master-lessons.json",
        bucket_name=bucket_name,
        context_type="project_type",
        project_name=project_name,
    )

    return {
        "project_added": project_stats["added"],
        "project_deleted": project_stats["deleted"],
        "type_added": type_stats["added"],
        "type_deleted": type_stats["deleted"],
    }


def extract_lessons_from_document(content, filename):
    """Extract lessons from document content"""

    timestamp = datetime.now(timezone.utc).isoformat()

    prompt = f"""Extract 3-5 key lessons learned from this document.

Return ONLY a JSON array in this exact format:
[
  {{
    "title": "Brief title",
    "lesson": "Core lesson learned",
    "impact": "What was affected (cost, timeline, quality, etc.)",
    "recommendation": "What to do differently",
    "severity": "Low|Medium|High"
  }}
]

Document:
{content}

Return only the JSON array."""

    try:
        response = bedrock.invoke_model(
            modelId=os.environ["LESSONS_MODEL_ID"],
            body=json.dumps(
                {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 4096,
                    "messages": [{"role": "user", "content": prompt}],
                }
            ),
        )

        result = json.loads(response["body"].read())
        lessons_text = result["content"][0]["text"]

        # Parse JSON array
        start = lessons_text.find("[")
        end = lessons_text.rfind("]") + 1
        if start >= 0 and end > start:
            lessons = json.loads(lessons_text[start:end])
            # Add id and source_document to each lesson
            for lesson in lessons:
                lesson["id"] = timestamp
                lesson["source_document"] = filename
            return lessons

        return []

    except Exception as e:
        print(f"Error extracting lessons: {e}")
        return []


def merge_lessons_with_superseding(
    new_lessons, existing_lessons_key, bucket_name, context_type, project_name
):
    """Merge new lessons with existing using LLM to determine superseding"""

    # Load existing lessons
    existing_lessons = load_lessons_file(bucket_name, existing_lessons_key)

    if not existing_lessons:
        # No existing lessons, just save new ones
        save_lessons_file(bucket_name, existing_lessons_key, new_lessons)
        return {"added": len(new_lessons), "deleted": 0}

    # Chunk existing lessons if too large
    chunks = chunk_lessons(existing_lessons, CHUNK_SIZE)

    all_ids_to_delete = []

    # Compare new lessons against each chunk
    for chunk in chunks:
        ids_to_delete = compare_lessons_with_llm(
            new_lessons, chunk, context_type
        )
        all_ids_to_delete.extend(ids_to_delete)

    # Apply changes: remove superseded, add new
    updated_lessons = [
        l for l in existing_lessons if l["id"] not in all_ids_to_delete
    ]
    updated_lessons.extend(new_lessons)

    # Sort by id (timestamp) descending
    updated_lessons.sort(key=lambda x: x["id"], reverse=True)

    # Save updated lessons
    save_lessons_file(bucket_name, existing_lessons_key, updated_lessons)

    return {"added": len(new_lessons), "deleted": len(all_ids_to_delete)}


def compare_lessons_with_llm(new_lessons, existing_lessons_chunk, context_type):
    """Use LLM with tool calling to determine which existing lessons to delete"""

    tools = [
        {
            "name": "delete_lessons",
            "description": "Delete lessons that are superseded by new lessons. Only delete if new lesson clearly replaces or makes obsolete an existing lesson.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "lesson_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Array of lesson IDs to delete",
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Brief explanation of why these lessons are being superseded",
                    },
                },
                "required": ["lesson_ids", "reasoning"],
            },
        }
    ]

    prompt = f"""Compare these NEW lessons against EXISTING lessons for a {context_type}.

NEW LESSONS:
{json.dumps(new_lessons, indent=2)}

EXISTING LESSONS:
{json.dumps(existing_lessons_chunk, indent=2)}

Determine if any EXISTING lessons should be deleted because they are superseded by NEW lessons.
Only delete if:
- New lesson covers the same topic but with better/updated information
- New lesson contradicts or corrects an old lesson
- New lesson makes an old lesson obsolete

Use the delete_lessons tool to specify which lesson IDs to delete. If no lessons should be deleted, don't call the tool."""

    try:
        response = bedrock.invoke_model(
            modelId=os.environ["LESSONS_MODEL_ID"],
            body=json.dumps(
                {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 2048,
                    "tools": tools,
                    "messages": [{"role": "user", "content": prompt}],
                }
            ),
        )

        result = json.loads(response["body"].read())

        # Check if tool was used
        for content_block in result.get("content", []):
            if (
                content_block.get("type") == "tool_use"
                and content_block.get("name") == "delete_lessons"
            ):
                tool_input = content_block.get("input", {})
                lesson_ids = tool_input.get("lesson_ids", [])
                reasoning = tool_input.get("reasoning", "")
                print(f"LLM superseding: {reasoning}")
                return lesson_ids

        return []

    except Exception as e:
        print(f"Error in LLM comparison: {e}")
        return []


def chunk_lessons(lessons, chunk_size):
    """Split lessons into chunks for processing"""
    return [
        lessons[i : i + chunk_size] for i in range(0, len(lessons), chunk_size)
    ]


def load_lessons_file(bucket_name, key):
    """Load lessons from S3 JSON file"""
    try:
        response = s3.get_object(Bucket=bucket_name, Key=key)
        data = json.loads(response["Body"].read().decode("utf-8"))
        return data.get("lessons", [])
    except s3.exceptions.NoSuchKey:
        return []
    except Exception as e:
        print(f"Error loading lessons from {key}: {e}")
        return []


def save_lessons_file(bucket_name, key, lessons):
    """Save lessons to S3 JSON file"""
    try:
        data = {"lessons": lessons}
        s3.put_object(
            Bucket=bucket_name,
            Key=key,
            Body=json.dumps(data, indent=2).encode("utf-8"),
            ContentType="application/json",
        )
        print(f"Saved {len(lessons)} lessons to {key}")
    except Exception as e:
        print(f"Error saving lessons to {key}: {e}")
        raise
