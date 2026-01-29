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

import database, schemas
from config import settings

print("=" * 60)
print("🚀 Starting Veritas API...")
print("=" * 60)

# 1. Initialize Firebase Admin
try:
    print(f"🔄 Loading Firebase credentials from: {settings.FIREBASE_JSON}")

    if not os.path.exists(settings.FIREBASE_JSON):
        print(f"❌ ERROR: Firebase JSON file not found at: {settings.FIREBASE_JSON}")
        print(f"   Current directory: {os.getcwd()}")
    else:
        print(f"✅ Firebase JSON file found")
        cred = credentials.Certificate(settings.FIREBASE_JSON)
        firebase_admin.initialize_app(cred)
        print("✅ Firebase initialized successfully")

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

# --- AUTH HELPER ---
async def verify_firebase_token(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")

    id_token = authorization.split("Bearer ")[1]
    try:
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except Exception:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid Firebase Token")

# --- CONTENT ENDPOINTS ---

# CREATE
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