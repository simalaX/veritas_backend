# Veritas Backend - API Key Authentication Setup

## Overview

The backend now supports two authentication methods:

1. **Firebase Token Authentication** - For web admin dashboard
2. **API Key Authentication** - For mobile app (Kotlin)

## API Key Configuration

### Environment Variable Setup

Add the following to your `.env` file:

```env
MOBILE_API_KEY=veritas-mobile-key-2025
```

For production (Render), set this as an environment variable in your Render dashboard:
- Go to your Render service settings
- Add environment variable: `MOBILE_API_KEY` with your desired key value

### Default API Key

If no `MOBILE_API_KEY` environment variable is set, the backend defaults to:
```
veritas-mobile-key-2025
```

## Mobile App Integration (Kotlin)

### Upload Endpoint

**Endpoint:** `POST /mobile/upload`

**Headers Required:**
```
X-API-Key: veritas-mobile-key-2025
Content-Type: multipart/form-data
```

**Form Parameters:**
- `title` (string, required) - Title of the media item
- `category` (string, required) - Category of the media item
- `file` (file, required) - The file to upload

### Example Request (Kotlin)

```kotlin
val client = OkHttpClient()

val requestBody = MultipartBody.Builder()
    .setType(MultipartBody.FORM)
    .addFormDataPart("title", "My Video")
    .addFormDataPart("category", "Sermons")
    .addFormDataPart("file", "video.mp4", 
        RequestBody.create(MediaType.parse("video/mp4"), file))
    .build()

val request = Request.Builder()
    .url("https://your-backend-url.onrender.com/mobile/upload")
    .addHeader("X-API-Key", "veritas-mobile-key-2025")
    .post(requestBody)
    .build()

val response = client.newCall(request).execute()
```

### Success Response (200 OK)

```json
{
  "success": true,
  "message": "Upload successful",
  "data": {
    "id": 1,
    "title": "My Video",
    "category": "Sermons",
    "file_path": "550e8400-e29b-41d4-a716-446655440000.mp4",
    "uploaded_at": "2025-01-31T15:02:28.341000"
  }
}
```

### Error Response (401 Unauthorized)

```json
{
  "success": false,
  "message": "Api key is wrong or not found",
  "data": null
}
```

## Troubleshooting

### Error: "Api key is wrong or not found"

**Causes:**
1. Missing `X-API-Key` header in the request
2. Incorrect API key value
3. API key not set in environment variables

**Solutions:**
1. Ensure the header is named exactly `X-API-Key` (case-sensitive)
2. Verify the API key matches the one in your `.env` file or Render environment variables
3. Check that the backend has restarted after updating environment variables

### Error: "Upload failed: 401"

This error occurs when the API key validation fails. Make sure:
- The API key is correctly set in your Kotlin app
- The backend is using the correct API key configuration
- The request includes the `X-API-Key` header

## Deployment to Render

1. Push your code to GitHub
2. In Render dashboard, go to your service settings
3. Add environment variable:
   - Key: `MOBILE_API_KEY`
   - Value: `veritas-mobile-key-2025` (or your custom key)
4. Redeploy the service

## Security Recommendations

For production:
1. Use a strong, randomly generated API key (not the default)
2. Store the API key securely in your Kotlin app (consider using encrypted SharedPreferences)
3. Rotate API keys periodically
4. Consider implementing rate limiting
5. Use HTTPS only (Render provides this by default)

## Multiple API Keys

To support multiple API keys (e.g., for different mobile app versions):

Edit `main.py` and modify the `VALID_API_KEYS` list:

```python
VALID_API_KEYS = [
    os.getenv("MOBILE_API_KEY", "veritas-mobile-key-2025"),
    "backup-api-key-2025",
    "legacy-api-key-2024"
]
```

## Testing the API

### Using cURL

```bash
curl -X POST "http://localhost:8000/mobile/upload" \
  -H "X-API-Key: veritas-mobile-key-2025" \
  -F "title=Test Video" \
  -F "category=Sermons" \
  -F "file=@/path/to/video.mp4"
```

### Using Postman

1. Create a new POST request to `http://localhost:8000/mobile/upload`
2. Go to Headers tab, add:
   - Key: `X-API-Key`
   - Value: `veritas-mobile-key-2025`
3. Go to Body tab, select `form-data`
4. Add fields:
   - `title`: Test Video
   - `category`: Sermons
   - `file`: Select your file
5. Click Send

## Additional Endpoints

### List Content (No Auth Required)

```
GET /content?category=Sermons&q=search_term
```

### Update Content (Firebase Auth Required)

```
PATCH /content/{item_id}
Authorization: Bearer {firebase_token}
```

### Delete Content (Firebase Auth Required)

```
DELETE /content/{item_id}
Authorization: Bearer {firebase_token}
```
