import json
import google.generativeai as genai
from typing import Optional
from config.settings import settings
from utils.logger import logger
from utils.mock_ai import generate_mock_response

# Configure Gemini once at module load
if not settings.USE_MOCK_AI:
    try:
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        logger.info(f"Configured Gemini with model: {settings.MODEL_NAME}")
    except Exception as e:
        logger.error(f"Failed to configure Gemini: {e}")

def generate(prompt: str, agent_name: str = "general", system_instruction: Optional[str] = None) -> str:
    """
    Generate a response from the AI.
    If USE_MOCK_AI is True, it returns a deterministic mock response (as a JSON string).
    Otherwise, it calls the Gemini API.
    """
    logger.info(f"Generating AI response for agent: {agent_name}")
    
    if settings.USE_MOCK_AI:
        try:
            logger.debug(f"Using mock AI for {agent_name}")
            mock_dict = generate_mock_response(agent_name, prompt)
            return json.dumps(mock_dict)
        except Exception as e:
            logger.error(f"Error generating mock response: {e}")
            return json.dumps({"status": "Error", "message": str(e)})
            
    # Call actual Gemini API
    try:
        logger.debug(f"Calling Gemini API using {settings.MODEL_NAME}")
        
        # We only pass system_instruction if the model supports it and it's provided
        kwargs = {}
        if system_instruction:
            kwargs["system_instruction"] = system_instruction
            
        model = genai.GenerativeModel(
            model_name=settings.MODEL_NAME,
            **kwargs
        )
        
        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        logger.error(f"Error calling Gemini API: {e}", exc_info=True)
        # Return a fallback JSON string to avoid crashing agents that expect JSON
        return json.dumps({
            "status": "Error", 
            "error": "Failed to generate AI response.",
            "details": str(e)
        })
