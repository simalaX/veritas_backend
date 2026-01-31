// Kotlin Example - Upload to Backend with API Key Authentication

import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import java.io.File

class VeritasUploadManager {
    
    companion object {
        private const val API_KEY = "veritas-mobile-key-2025"
        private const val BACKEND_URL = "https://your-backend-url.onrender.com"
        private const val UPLOAD_ENDPOINT = "$BACKEND_URL/mobile/upload"
    }
    
    private val client = OkHttpClient()
    
    /**
     * Upload media file to backend with API key authentication
     * 
     * @param title - Title of the media item
     * @param category - Category of the media item
     * @param file - File to upload
     * @param onSuccess - Callback for successful upload
     * @param onError - Callback for upload error
     */
    fun uploadMedia(
        title: String,
        category: String,
        file: File,
        onSuccess: (response: String) -> Unit,
        onError: (error: String) -> Unit
    ) {
        try {
            // Build multipart request body
            val requestBody = MultipartBody.Builder()
                .setType(MultipartBody.FORM)
                .addFormDataPart("title", title)
                .addFormDataPart("category", category)
                .addFormDataPart(
                    "file",
                    file.name,
                    RequestBody.create(
                        "application/octet-stream".toMediaType(),
                        file
                    )
                )
                .build()
            
            // Build request with API key header
            val request = Request.Builder()
                .url(UPLOAD_ENDPOINT)
                .addHeader("X-API-Key", API_KEY)  // IMPORTANT: API Key header
                .post(requestBody)
                .build()
            
            // Execute request asynchronously
            client.newCall(request).enqueue(object : Callback {
                override fun onFailure(call: Call, e: IOException) {
                    onError("Network error: ${e.message}")
                }
                
                override fun onResponse(call: Call, response: Response) {
                    response.use { resp ->
                        if (resp.isSuccessful) {
                            val responseBody = resp.body?.string() ?: ""
                            onSuccess(responseBody)
                        } else {
                            val errorBody = resp.body?.string() ?: "Unknown error"
                            onError("Upload failed: ${resp.code} - $errorBody")
                        }
                    }
                }
            })
        } catch (e: Exception) {
            onError("Exception: ${e.message}")
        }
    }
}

// Usage Example in your Activity/Fragment:
/*
val uploadManager = VeritasUploadManager()

val videoFile = File("/path/to/video.mp4")

uploadManager.uploadMedia(
    title = "My Sermon",
    category = "Sermons",
    file = videoFile,
    onSuccess = { response ->
        Log.d("Upload", "Success: $response")
        // Parse JSON response and handle success
        // Example response:
        // {
        //   "success": true,
        //   "message": "Upload successful",
        //   "data": {
        //     "id": 1,
        //     "title": "My Sermon",
        //     "category": "Sermons",
        //     "file_path": "550e8400-e29b-41d4-a716-446655440000.mp4",
        //     "uploaded_at": "2025-01-31T15:02:28.341000"
        //   }
        // }
    },
    onError = { error ->
        Log.e("Upload", "Error: $error")
        // Handle error - show toast or dialog to user
        // Common error: "Upload failed: 401 - {"success":false,"message":"Api key is wrong or not found","data":null}"
    }
)
*/

// Alternative: Using Retrofit (if you prefer)
/*
interface VeritasApiService {
    @Multipart
    @POST("mobile/upload")
    suspend fun uploadMedia(
        @Header("X-API-Key") apiKey: String,
        @Part("title") title: RequestBody,
        @Part("category") category: RequestBody,
        @Part file: MultipartBody.Part
    ): UploadResponse
}

data class UploadResponse(
    val success: Boolean,
    val message: String,
    val data: MediaData?
)

data class MediaData(
    val id: Int,
    val title: String,
    val category: String,
    val file_path: String,
    val uploaded_at: String
)

// Usage with Retrofit:
val retrofit = Retrofit.Builder()
    .baseUrl("https://your-backend-url.onrender.com/")
    .addConverterFactory(GsonConverterFactory.create())
    .build()

val apiService = retrofit.create(VeritasApiService::class.java)

val file = File("/path/to/video.mp4")
val requestFile = RequestBody.create("video/mp4".toMediaType(), file)
val body = MultipartBody.Part.createFormData("file", file.name, requestFile)

val response = apiService.uploadMedia(
    apiKey = "veritas-mobile-key-2025",
    title = RequestBody.create("text/plain".toMediaType(), "My Sermon"),
    category = RequestBody.create("text/plain".toMediaType(), "Sermons"),
    file = body
)

if (response.success) {
    Log.d("Upload", "File uploaded: ${response.data?.file_path}")
} else {
    Log.e("Upload", "Error: ${response.message}")
}
*/
