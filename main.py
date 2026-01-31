import os
import shutil
import uuid
import traceback
import firebase_admin
from firebase_admin import credentials, auth
from fastapi import FastAPI, Depends, HTTPException, File, UploadFile, Form, Query, Header
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
from contextlib import asynccontextmanager
import json

import database, schemas
from config import settings

# API Key for mobile app authentication
VALID_API_KEYS = [
    os.getenv("MOBILE_API_KEY", "veritas-mobile-key-2025"),  # Default key for development
]

print("=" * 60)
print("🚀 Starting Veritas API...")
print("=" * 60)

# 1. Initialize Firebase Admin with Environment Variable Support
try:
    # Try to get credentials from environment variable first (for Render/production)
    cred_json = os.environ.get('FIREBASE_CREDENTIALS')

    if cred_json:
        print("🔵 Loading Firebase credentials from environment variable")
        cred_dict = json.loads(cred_json)
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
        print("✅ Firebase initialized successfully from environment variable")
    else:
        # Fallback to file for local development
        print(f"🔄 Loading Firebase credentials from file: {settings.FIREBASE_JSON_PATH}")

        if not os.path.exists(settings.FIREBASE_JSON_PATH):
            print(f"❌ ERROR: Firebase JSON file not found at: {settings.FIREBASE_JSON_PATH}")
            print(f"   Current directory: {os.getcwd()}")
            raise FileNotFoundError(f"Firebase credentials not found")

        print(f"✅ Firebase JSON file found")
        cred = credentials.Certificate(settings.FIREBASE_JSON_PATH)
        firebase_admin.initialize_app(cred)
        print("✅ Firebase initialized successfully from file")

except json.JSONDecodeError as e:
    print(f"❌ Firebase initialization failed: Invalid JSON in FIREBASE_CREDENTIALS")
    print(f"   Error: {e}")
    traceback.print_exc()
except Exception as e:
    print(f"❌ Firebase initialization failed: {e}")
    traceback.print_exc()

# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🔄 Connecting to database...")
    await database.init_db()

    # Create tables if needed
    async with database.db_pool.acquire() as conn:
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS media_items (
                id SERIAL PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                category VARCHAR(50) NOT NULL,
                file_path VARCHAR(500) NOT NULL,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    print("✅ Database tables ready")

    yield

    # Shutdown
    print("🔄 Closing database connection...")
    await database.close_db()

app = FastAPI(title="Veritas Generation API", lifespan=lifespan)

# 2. CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://veritas-frontend.onrender.com",  # Update with your frontend URL
        "http://localhost:5173",
        "http://localhost:3000",
        "*"  # Remove in production
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Storage Initialization
os.makedirs("uploads", exist_ok=True)
app.mount("/files", StaticFiles(directory="uploads"), name="files")

print("✅ Uploads directory ready")
print("=" * 60)
print("✅ Veritas API startup complete!")
print("=" * 60)

# --- AUTH HELPERS ---
async def verify_firebase_token(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")

    id_token = authorization.split("Bearer ")[1]
    try:
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except Exception:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid Firebase Token")

async def verify_api_key(x_api_key: str = Header(None)):
    """Verify API key for mobile app authentication"""
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail=json.dumps({
                "success": False,
                "message": "Api key is wrong or not found",
                "data": None
            })
        )
    
    if x_api_key not in VALID_API_KEYS:
        raise HTTPException(
            status_code=401,
            detail=json.dumps({
                "success": False,
                "message": "Api key is wrong or not found",
                "data": None
            })
        )
    
    return x_api_key

# --- CONTENT ENDPOINTS ---

# CREATE - Web Admin Upload (Firebase Auth)
@app.post("/admin/upload")
async def upload_content(
    title: str = Form(...),
    category: str = Form(...),
    file: UploadFile = File(...),
    conn = Depends(database.get_db),
    user_data: dict = Depends(verify_firebase_token)
):
    ext = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{ext}"
    save_path = os.path.join("uploads", unique_filename)

    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Insert into database
    query = '''
        INSERT INTO media_items (title, category, file_path)
        VALUES ($1, $2, $3)
        RETURNING id, title, category, file_path, uploaded_at
    '''
    result = await conn.fetchrow(query, title, category, unique_filename)

    return {
        "status": "success",
        "item": {
            "id": result['id'],
            "title": result['title'],
            "category": result['category'],
            "file_path": result['file_path'],
            "uploaded_at": result['uploaded_at']
        }
    }

# CREATE - Mobile App Upload (API Key Auth)
@app.post("/mobile/upload")
async def mobile_upload_content(
    title: str = Form(...),
    category: str = Form(...),
    file: UploadFile = File(...),
    conn = Depends(database.get_db),
    api_key: str = Depends(verify_api_key)
):
    """Mobile app upload endpoint with API key authentication"""
    try:
        ext = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{ext}"
        save_path = os.path.join("uploads", unique_filename)

        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Insert into database
        query = '''
            INSERT INTO media_items (title, category, file_path)
            VALUES ($1, $2, $3)
            RETURNING id, title, category, file_path, uploaded_at
        '''
        result = await conn.fetchrow(query, title, category, unique_filename)

        return {
            "success": True,
            "message": "Upload successful",
            "data": {
                "id": result['id'],
                "title": result['title'],
                "category": result['category'],
                "file_path": result['file_path'],
                "uploaded_at": str(result['uploaded_at'])
            }
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Upload failed: {str(e)}",
            "data": None
        }

# READ (Listing with search)
@app.get("/content", response_model=List[schemas.MediaItemResponse])
async def list_content(
    q: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    conn = Depends(database.get_db)
):
    query = "SELECT * FROM media_items WHERE 1=1"
    params = []
    param_count = 1

    if category and category != "ALL":
        query += f" AND category = ${param_count}"
        params.append(category)
        param_count += 1

    if q:
        query += f" AND title ILIKE ${param_count}"
        params.append(f"%{q}%")

    rows = await conn.fetch(query, *params)

    base_url = f"http://{settings.SERVER_IP}:8000/files/"

    results = []
    for row in rows:
        results.append({
            "id": row['id'],
            "title": row['title'],
            "category": row['category'],
            "url": f"{base_url}{row['file_path']}",
            "uploaded_at": row['uploaded_at']
        })
    return results

# UPDATE
@app.patch("/content/{item_id}")
async def update_content(
    item_id: int,
    title: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    conn = Depends(database.get_db),
    user_data: dict = Depends(verify_firebase_token)
):
    # Check if item exists
    check_query = "SELECT * FROM media_items WHERE id = $1"
    existing = await conn.fetchrow(check_query, item_id)

    if not existing:
        raise HTTPException(status_code=404, detail="Item not found")

    # Build update query dynamically
    updates = []
    params = []
    param_count = 1

    if title:
        updates.append(f"title = ${param_count}")
        params.append(title)
        param_count += 1

    if category:
        updates.append(f"category = ${param_count}")
        params.append(category)
        param_count += 1

    if updates:
        params.append(item_id)
        query = f"UPDATE media_items SET {', '.join(updates)} WHERE id = ${param_count} RETURNING *"
        result = await conn.fetchrow(query, *params)

        return {
            "status": "updated",
            "item": dict(result)
        }

    return {"status": "no changes", "item": dict(existing)}

# DELETE
@app.delete("/content/{item_id}")
async def delete_item(
    item_id: int,
    conn = Depends(database.get_db),
    user_data: dict = Depends(verify_firebase_token)
):
    # Get item first
    query = "SELECT * FROM media_items WHERE id = $1"
    item = await conn.fetchrow(query, item_id)

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # Delete file
    file_path = os.path.join("uploads", item['file_path'])
    if os.path.exists(file_path):
        os.remove(file_path)

    # Delete from database
    delete_query = "DELETE FROM media_items WHERE id = $1"
    await conn.execute(delete_query, item_id)

    return {
        "message": f"Deleted {item['title']}",
        "admin": user_data.get('email')
    }