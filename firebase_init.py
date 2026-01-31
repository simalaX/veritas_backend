import firebase_admin
from firebase_admin import credentials
import json
import os

def initialize_firebase():
    """
    Initialize Firebase Admin SDK using environment variables for production
    and local file for development.
    """
    # Check if Firebase is already initialized
    if firebase_admin._apps:
        return firebase_admin.get_app()
    
    # Try to get credentials from environment variable (for production/Render)
    cred_json = os.environ.get('FIREBASE_CREDENTIALS')
    
    if cred_json:
        print("🔵 Loading Firebase credentials from environment variable")
        try:
            cred_dict = json.loads(cred_json)
            cred = credentials.Certificate(cred_dict)
        except json.JSONDecodeError as e:
            print(f"❌ ERROR: Invalid JSON in FIREBASE_CREDENTIALS environment variable")
            raise e
    else:
        # Fallback to file for local development
        print("🔵 Loading Firebase credentials from local file")
        cred_path = 'serviceAccountKey.json'
        
        if not os.path.exists(cred_path):
            print(f"❌ ERROR: Firebase credentials not found!")
            print(f"   - For production: Set FIREBASE_CREDENTIALS environment variable")
            print(f"   - For local dev: Place serviceAccountKey.json in project root")
            raise FileNotFoundError(f"Firebase credentials file not found at: {cred_path}")
        
        cred = credentials.Certificate(cred_path)
    
    # Initialize the app
    app = firebase_admin.initialize_app(cred)
    print("✅ Firebase initialized successfully!")
    return app


# Call this function when your app starts
if __name__ == "__main__":
    initialize_firebase()
