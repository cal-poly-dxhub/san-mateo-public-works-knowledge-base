import json
import os
import sys
import uuid
from datetime import datetime, timezone

import boto3

from bedrock_utils import bedrock_converse

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

    # Process project-level lessons (saved to projects/ - triggers sync Lambda)
    project_stats = merge_lessons_with_superseding(
        new_lessons=new_lessons,
        existing_lessons_key=f"projects/{project_name}/lessons.json",
        bucket_name=bucket_name,
        context_type="project",
        project_name=project_name,
        project_type=project_type,
        sync_to_vectors=False,  # Don't sync project-specific lessons
    )

    # Process project-type-level lessons (saved to root lessons-learned/)
    type_lessons = [{"project_name": project_name, **lesson} for lesson in new_lessons]
    type_stats = merge_lessons_with_superseding(
        new_lessons=type_lessons,
        existing_lessons_key=f"lessons-learned/{project_type}/lessons.json",
        bucket_name=bucket_name,
        context_type="project_type",
        project_name=project_name,
        project_type=project_type,
        sync_to_vectors=True,  # Only sync master list
    )

    return {
        "project_added": project_stats["added"],
        "project_conflicts": project_stats["conflicts"],
        "type_added": type_stats["added"],
        "type_conflicts": type_stats["conflicts"],
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
        response = bedrock_converse(
            bedrock,
            modelId=os.environ["LESSONS_EXTRACTOR_MODEL_ID"],
            messages=[{"role": "user", "content": [{"text": prompt}]}],
        )

        lessons_text = response["output"]["message"]["content"][0]["text"]

        # Parse JSON array
        start = lessons_text.find("[")
        end = lessons_text.rfind("]") + 1
        if start >= 0 and end > start:
            lessons = json.loads(lessons_text[start:end])
            # Add unique id and source_document to each lesson
            for lesson in lessons:
                lesson["id"] = str(uuid.uuid4())
                lesson["source_document"] = filename
                lesson["created_at"] = timestamp
            return lessons

        return []

    except Exception as e:
        print(f"Error extracting lessons: {e}")
        raise


def merge_lessons_with_superseding(
    new_lessons,
    existing_lessons_key,
    bucket_name,
    context_type,
    project_name,
    project_type=None,
    sync_to_vectors=True,
):
    """Merge new lessons and create conflicts for review"""

    existing_lessons = load_lessons_file(bucket_name, existing_lessons_key)

    if not existing_lessons:
        save_lessons_file(bucket_name, existing_lessons_key, new_lessons)
        return {"added": len(new_lessons), "conflicts": 0}

    chunks = chunk_lessons(existing_lessons, CHUNK_SIZE)

    all_conflicts = []

    for chunk in chunks:
        conflicts = find_conflicts_with_llm(new_lessons, chunk, context_type)
        all_conflicts.extend(conflicts)

    # Add all new lessons (don't delete anything)
    updated_lessons = existing_lessons + new_lessons
    updated_lessons.sort(key=lambda x: x["id"], reverse=True)

    save_lessons_file(bucket_name, existing_lessons_key, updated_lessons)

    # Save conflicts for review
    if all_conflicts:
        conflicts_key = existing_lessons_key.replace(".json", "-conflicts.json")
        save_conflicts_file(bucket_name, conflicts_key, all_conflicts)

    return {
        "added": len(new_lessons),
        "conflicts": len(all_conflicts),
    }


def compare_lessons_with_llm(new_lessons, existing_lessons_chunk, context_type):
    """Use LLM with tool calling to determine which existing lessons to delete"""

    tools = [
        {
            "toolSpec": {
                "name": "delete_lessons",
                "description": "Delete lessons that are superseded by new lessons. Only delete if new lesson clearly replaces or makes obsolete an existing lesson.",
                "inputSchema": {
                    "json": {
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
                    }
                },
            }
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
        response = bedrock_converse(
            bedrock,
            modelId=os.environ["LESSONS_EXTRACTOR_MODEL_ID"],
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            toolConfig={"tools": tools},
        )

        # Check if tool was used
        for content_block in response["output"]["message"]["content"]:
            if content_block.get("toolUse"):
                tool_use = content_block["toolUse"]
                if tool_use["name"] == "delete_lessons":
                    lesson_ids = tool_use["input"].get("lesson_ids", [])
                    reasoning = tool_use["input"].get("reasoning", "")
                    print(f"LLM superseding: {reasoning}")
                    return lesson_ids

        return []

    except Exception as e:
        print(f"Error in LLM comparison: {e}")
        return []


def chunk_lessons(lessons, chunk_size):
    """Split lessons into chunks for processing"""
    return [lessons[i : i + chunk_size] for i in range(0, len(lessons), chunk_size)]


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


def find_conflicts_with_llm(new_lessons, existing_lessons_chunk, context_type):
    """Use LLM to find potential conflicts between new and existing lessons"""

    tools = [
        {
            "toolSpec": {
                "name": "report_conflicts",
                "description": "Report lessons that conflict or overlap with new lessons",
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "conflicts": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "new_lesson_id": {"type": "string"},
                                        "existing_lesson_id": {"type": "string"},
                                        "reason": {"type": "string"},
                                    },
                                },
                                "description": "Array of conflicts found",
                            },
                        },
                        "required": ["conflicts"],
                    }
                },
            }
        }
    ]

    prompt = f"""Compare NEW lessons against EXISTING lessons.

NEW:
{json.dumps(new_lessons, indent=2)}

EXISTING:
{json.dumps(existing_lessons_chunk, indent=2)}

Find conflicts where new lesson covers same topic, contradicts, or makes existing obsolete.
Use report_conflicts tool. If none, call with empty array."""

    try:
        print(
            f"Checking {len(new_lessons)} new lessons against {len(existing_lessons_chunk)} existing lessons"
        )
        response = bedrock_converse(
            bedrock,
            modelId=os.environ["CONFLICT_DETECTOR_MODEL_ID"],
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            toolConfig={"tools": tools},
        )

        print(f"LLM Response: {json.dumps(response['output']['message'], indent=2)}")

        for content in response["output"]["message"]["content"]:
            if (
                content.get("toolUse")
                and content["toolUse"]["name"] == "report_conflicts"
            ):
                conflicts = content["toolUse"]["input"].get("conflicts", [])
                print(f"Found {len(conflicts)} conflicts")
                enriched = []
                for conflict in conflicts:
                    new_lesson = next(
                        (
                            l
                            for l in new_lessons
                            if l["id"] == conflict["new_lesson_id"]
                        ),
                        None,
                    )
                    existing_lesson = next(
                        (
                            l
                            for l in existing_lessons_chunk
                            if l["id"] == conflict["existing_lesson_id"]
                        ),
                        None,
                    )
                    if new_lesson and existing_lesson:
                        enriched.append(
                            {
                                "id": f"conflict_{datetime.now(timezone.utc).isoformat()}",
                                "new_lesson": new_lesson,
                                "existing_lesson": existing_lesson,
                                "reason": conflict["reason"],
                                "status": "pending",
                            }
                        )
                return enriched

        print("No tool use found in response")
        return []

    except Exception as e:
        print(f"Error finding conflicts: {e}")
        import traceback

        traceback.print_exc()
        return []


def save_conflicts_file(bucket_name, conflicts_key, conflicts):
    """Save or append conflicts to S3"""
    try:
        response = s3.get_object(Bucket=bucket_name, Key=conflicts_key)
        existing_conflicts = json.loads(response["Body"].read())
    except:
        existing_conflicts = []

    existing_conflicts.extend(conflicts)

    print(
        f"Saving {len(conflicts)} new conflicts to {conflicts_key} (total: {len(existing_conflicts)})"
    )

    s3.put_object(
        Bucket=bucket_name,
        Key=conflicts_key,
        Body=json.dumps(existing_conflicts, indent=2),
        ContentType="application/json",
    )
