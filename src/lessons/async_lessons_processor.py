import os

from lessons_processor import extract_and_merge_lessons


def handler(event, context):
    """Process lessons extraction asynchronously with superseding logic"""
    try:
        # Handle sync-only events (from conflict resolution)
        if event.get("sync_only"):
            from sync_lessons_vectors import sync_lessons_to_vectors

            bucket_name = event["bucket_name"]
            lessons_key = event["lessons_key"]
            lessons = event["lessons"]
            project_name = event["project_name"]
            project_type = event.get("project_type")

            print(f"Syncing vectors only for {project_name}")
            sync_lessons_to_vectors(
                bucket_name, lessons_key, lessons, project_name, project_type
            )
            print(f"Vector sync complete for {project_name}")
            return

        # Handle normal lesson extraction events
        project_name = event["project_name"]
        project_type = event["project_type"]
        content_text = event["content"]
        filename = event["filename"]
        bucket_name = os.environ["BUCKET_NAME"]

        print(f"Starting async lessons processing for {project_name}")

        # Extract and merge lessons with superseding logic
        # Note: This also syncs vectors directly via sync_lessons_to_vectors
        stats = extract_and_merge_lessons(
            content=content_text,
            filename=filename,
            project_name=project_name,
            project_type=project_type,
            bucket_name=bucket_name,
        )

        print(f"Lessons processing complete for {project_name}:")
        print(
            f"  Project level: +{stats['project_added']} lessons, {stats.get('project_conflicts', 0)} conflicts"
        )
        print(
            f"  Type level: +{stats['type_added']} lessons, {stats.get('type_conflicts', 0)} conflicts"
        )

        return {
            "statusCode": 200,
            "message": "Lessons processed successfully",
            "stats": stats,
        }

    except Exception as e:
        print(f"Error processing lessons async: {str(e)}")
        import traceback

        traceback.print_exc()
        return {"statusCode": 500, "error": str(e)}
