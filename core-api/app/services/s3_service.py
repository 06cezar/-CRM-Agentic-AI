import json
import boto3
from botocore.exceptions import ClientError
from fastapi.concurrency import run_in_threadpool
from app.config import settings

def get_s3_client():
    """
    Returns a boto3 S3 client configured with settings from config.
    """
    protocol = "https" if settings.minio_secure else "http"
    endpoint_url = f"{protocol}://{settings.minio_endpoint}"
    
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key,
    )

def ensure_bucket_exists():
    """
    Checks if the target bucket exists, and creates it if it doesn't.
    Should be called during application startup.
    """
    s3 = get_s3_client()
    try:
        s3.head_bucket(Bucket=settings.minio_bucket_name)
    except ClientError as e:
        # If a client error is thrown, check if it was a 404 error.
        # If it was, then the bucket does not exist.
        error_code = e.response.get("Error", {}).get("Code")
        if error_code == "404" or error_code == "NoSuchBucket":
            s3.create_bucket(Bucket=settings.minio_bucket_name)
        else:
            raise

async def save_email_to_s3(user_id: int, lead_id: int, email_id: str, email_data: dict) -> str:
    """
    Serializes email_data to JSON and uploads it to MinIO.
    Path format: Users/{user_id}/leads/{lead_id}/emails/{email_id}.json
    """
    path = f"Users/{user_id}/leads/{lead_id}/emails/{email_id}.json"
    
    def _upload():
        s3 = get_s3_client()
        # Use default=str to handle datetime objects during serialization
        content = json.dumps(email_data, default=str)
        s3.put_object(
            Bucket=settings.minio_bucket_name,
            Key=path,
            Body=content,
            ContentType="application/json"
        )
        return path

    return await run_in_threadpool(_upload)
