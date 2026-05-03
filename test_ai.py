import json
from src.utils.ai_handler import AIHandler

def test_extraction():
    try:
        handler = AIHandler()
        print("--- Starting Profile Extraction Test ---")
        profile = handler.extract_profile()
        
        if profile:
            print("\nSuccessfully Extracted Profile:")
            print(json.dumps(profile, indent=4))
            
            # Basic validation
            if profile.get("years_of_experience"):
                print(f"\nYears of Experience: {profile['years_of_experience']}")
            
            if profile.get("full_name"):
                print(f"Candidate Name: {profile['full_name']}")
        else:
            print("Failed to extract profile.")
            
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    test_extraction()
