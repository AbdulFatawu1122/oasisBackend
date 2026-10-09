import os
import logging
from uuid import UUID
from typing import Optional, Union
from fastapi import UploadFile, HTTPException
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def _get_account_id() -> str:
    return os.getenv("CLOUDFLARE_R2_ACCOUNT_ID", "").strip()


def _get_access_key() -> str:
    return os.getenv("CLOUDFLARE_R2_ACCESS_KEY_ID", "").strip()


def _get_secret_key() -> str:
    return os.getenv("CLOUDFLARE_R2_SECRET_ACCESS_KEY", "").strip()


def _get_bucket_name() -> str:
    return os.getenv("CLOUDFLARE_R2_BUCKET_NAME", "").strip()


def _get_public_domain() -> str:
    domain = os.getenv("CLOUDFLARE_R2_PUBLIC_DOMAIN", "").strip().rstrip("/")
    if domain and not (domain.startswith("http://") or domain.startswith("https://")):
        domain = f"https://{domain}"
    return domain


def _get_jurisdiction() -> str:
    return os.getenv("CLOUDFLARE_R2_JURISDICTION", "").strip().lower()


_s3_client = None


def get_s3_client():
    """
    Initializes and caches the boto3 S3 client configured for Cloudflare R2.
    R2 is fully S3-compatible: endpoint = https://<account_id>[.<jurisdiction>].r2.cloudflarestorage.com
    """
    global _s3_client
    if _s3_client is not None:
        return _s3_client

    account_id = _get_account_id()
    access_key = _get_access_key()
    secret_key = _get_secret_key()
    jurisdiction = _get_jurisdiction()

    if not (account_id and access_key and secret_key):
        return None

    try:
        import boto3
        from botocore.config import Config

        clean_jurisdiction = jurisdiction.lower().strip()
        if clean_jurisdiction in ("eu", "fedramp"):
            endpoint = f"https://{account_id}.{clean_jurisdiction}.r2.cloudflarestorage.com"
        else:
            endpoint = f"https://{account_id}.r2.cloudflarestorage.com"

        _s3_client = boto3.client(
            service_name="s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name="auto",
            config=Config(signature_version="s3v4")
        )
        logger.info("[CloudflareR2] S3 client initialized successfully.")
        return _s3_client
    except Exception as e:
        logger.error(f"[CloudflareR2] Failed to initialize S3 client: {e}")
        return None


def is_r2_configured() -> bool:
    """Returns True if Cloudflare R2 credentials and bucket name are configured."""
    return bool(
        _get_account_id() and
        _get_access_key() and
        _get_secret_key() and
        _get_bucket_name()
    )


def upload_file_to_r2(
    file: UploadFile,
    folder: str,
    unique_id: Union[UUID, str],
) -> dict:
    """
    Uploads a photo or video directly to Cloudflare R2 storage.
    Path format: oasis/{folder}/{unique_id}.{ext}
    Returns: {"file_path": str, "url": str, "filename": str}
    """
    client = get_s3_client()
    bucket_name = _get_bucket_name()

    if not client or not bucket_name:
        raise HTTPException(
            status_code=503,
            detail="Cloudflare R2 storage is not configured. Please verify your R2 environment variables in .env."
        )

    ext = file.filename.split(".")[-1].lower() if file.filename and "." in file.filename else "bin"
    clean_folder = folder.strip("/")
    unique_filename = f"oasis/{clean_folder}/{unique_id}.{ext}"

    try:
        file.file.seek(0)
        file_content = file.file.read()
        content_type = file.content_type or "application/octet-stream"

        try:
            client.put_object(
                Bucket=bucket_name,
                Key=unique_filename,
                Body=file_content,
                ContentType=content_type
            )
        except Exception as put_err:
            if "NoSuchBucket" in str(put_err) or "404" in str(put_err):
                logger.info(f"[CloudflareR2] Bucket '{bucket_name}' missing. Creating automatically...")
                client.create_bucket(Bucket=bucket_name)
                client.put_object(
                    Bucket=bucket_name,
                    Key=unique_filename,
                    Body=file_content,
                    ContentType=content_type
                )
            else:
                raise put_err

        public_url = get_public_url(unique_filename)
        logger.info(f"[CloudflareR2] Uploaded '{unique_filename}' successfully.")
        return {
            "file_path": unique_filename,
            "url": public_url,
            "filename": file.filename or f"{unique_id}.{ext}"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[CloudflareR2] Upload failed for '{unique_filename}': {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload media to Cloudflare R2: {str(e)}"
        )


def delete_file_from_r2(file_path: str) -> bool:
    """Deletes an object from Cloudflare R2."""
    if not file_path:
        return False

    client = get_s3_client()
    bucket_name = _get_bucket_name()
    if not client or not bucket_name:
        return False

    try:
        client.delete_object(Bucket=bucket_name, Key=file_path)
        logger.info(f"[CloudflareR2] Deleted '{file_path}'")
        return True
    except Exception as e:
        logger.warning(f"[CloudflareR2] Delete failed for '{file_path}': {e}")
        return False


def get_public_url(file_path: str) -> str:
    """
    Returns the public CDN URL using CLOUDFLARE_R2_PUBLIC_DOMAIN.
    """
    if not file_path:
        return ""

    trimmed = file_path.strip()
    if not trimmed:
        return ""

    if trimmed.startswith("http://") or trimmed.startswith("https://"):
        return trimmed

    public_domain = _get_public_domain()
    if public_domain:
        clean_path = trimmed.lstrip("/")
        return f"{public_domain}/{clean_path}"

    return f"https://{trimmed.lstrip('/')}"
