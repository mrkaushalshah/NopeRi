
import os
from src.client.naukri_client import NaukriLoginClient
from dotenv import load_dotenv

load_dotenv()

def test_otp():
    username = os.getenv("USERNAME")
    password = os.getenv("PASSWORD")
    
    client = NaukriLoginClient(username, password)
    
    print(f"Attempting to send OTP for {username}...")
    try:
        # Try sending OTP via email (is_mobile=False)
        response = client.send_otp(is_mobile=False)
        print("Response:", response)
        print("\nIf you received an OTP, please let me know. This confirms your account uses OTP login.")
    except Exception as e:
        print(f"Failed to send OTP: {e}")

if __name__ == "__main__":
    test_otp()
