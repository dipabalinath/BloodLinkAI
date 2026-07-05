import os
from dotenv import load_dotenv
import google.generativeai as genai

def main():
    # Load environment variables from .env file
    load_dotenv()

    # Retrieve the API key and model name
    api_key = os.getenv("GOOGLE_API_KEY")
    model_name = os.getenv("MODEL_NAME")

    if not api_key:
        print("Error: GOOGLE_API_KEY not found in .env")
        return
    
    if not model_name:
        print("Error: MODEL_NAME not found in .env")
        return

    # Configure the Gemini API
    genai.configure(api_key=api_key)

    try:
        # Connect to the specified Gemini model
        model = genai.GenerativeModel(model_name)
        
        # Send the requested prompt
        prompt = "Reply with only: BloodLink AI Ready"
        response = model.generate_content(prompt)
        
        # Print the response
        print(response.text.strip())
    except Exception as e:
        print(f"Failed to connect or generate content. Error: {e}")

if __name__ == "__main__":
    main()
