import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Explicitly load .env from current directory
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

print("=" * 60)
print("1. TESTING POSTGRESQL DATABASE CONNECTION")
print("=" * 60)
try:
    from src.database.core import engine, SessionLocal
    from sqlalchemy import text
    with engine.connect() as conn:
        res = conn.execute(text("SELECT current_database(), current_user, version();")).fetchone()
        print(f" Database connected successfully!")
        print(f" Database Name: {res[0]}")
        print(f" Connected User: {res[1]}")
        print(f" PostgreSQL Version: {res[2].split()[0]} {res[2].split()[1]}")
        
        # Verify tables count
        tables_res = conn.execute(text("SELECT count(*) FROM information_schema.tables WHERE table_schema='public';")).scalar()
        print(f" Public Tables Found: {tables_res}")
except Exception as e:
    print(f" Database connection FAILED: {e}")

print("\n" + "=" * 60)
print("2. TESTING CLOUDFLARE R2 STORAGE CONNECTION")
print("=" * 60)
try:
    from src.storage.cloudflare_service import get_s3_client, _get_bucket_name, _get_public_domain, is_r2_configured
    print(f" is_r2_configured(): {is_r2_configured()}")
    bucket_name = _get_bucket_name()
    public_domain = _get_public_domain()
    print(f" Target Bucket: {bucket_name}")
    print(f" Public Domain: {public_domain}")

    s3 = get_s3_client()
    if not s3:
        print(" S3 Client could not be initialized. Check credentials in .env")
    else:
        # Test listing bucket objects to verify credentials and connectivity
        response = s3.list_objects_v2(Bucket=bucket_name, MaxKeys=5)
        print(f" Cloudflare R2 connected successfully!")
        key_count = response.get('KeyCount', 0)
        print(f" Bucket '{bucket_name}' accessible. Existing objects in bucket: {key_count}")
except Exception as e:
    print(f" Cloudflare R2 connection FAILED: {e}")

print("\n" + "=" * 60)
print("3. TESTING FASTAPI APP INITIALIZATION")
print("=" * 60)
try:
    from src.main import app
    print(" FastAPI app initialized cleanly without errors!")
except Exception as e:
    print(f" FastAPI app initialization FAILED: {e}")

print("=" * 60)
