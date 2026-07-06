import requests
from utils.logger import logger
from typing import Tuple, Optional

def geocode_address(address: str, city: str, state: str, pin_code: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Convert an address into latitude and longitude using OpenStreetMap Nominatim.
    
    Args:
        address: Street address (can be empty)
        city: City name
        state: State name
        pin_code: Postal/PIN code
        
    Returns:
        Tuple of (latitude, longitude). Returns (None, None) if geocoding fails.
    """
    parts = []
    if address: parts.append(address)
    if city: parts.append(city)
    if state: parts.append(state)
    if pin_code: parts.append(pin_code)
    
    query = ", ".join(parts)
    url = "https://nominatim.openstreetmap.org/search"
    headers = {"User-Agent": "BloodLinkAI/1.0 (bloodlink@example.com)"}
    params = {"q": query, "format": "json", "limit": 1}
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                return float(data[0]["lat"]), float(data[0]["lon"])
            else:
                logger.warning(f"Geocoding returned no results for: {query}")
        else:
            logger.warning(f"Geocoding failed with status {response.status_code} for: {query}")
    except Exception as e:
        logger.error(f"Geocoding exception for {query}: {e}")
        
    return None, None
