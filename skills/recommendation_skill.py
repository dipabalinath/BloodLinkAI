"""
Recommendation Skill for BloodLink AI.
Generates ranked inventory recommendations.
"""

from typing import Dict, Any, List
from skills.shared_models import RecommendationResult
from mcp_server.registry import registry
from utils.logger import logger
from datetime import datetime

class RecommendationSkill:
    def recommend_inventory(
        self, 
        blood_group: str, 
        component_type: str, 
        latitude: float, 
        longitude: float, 
        required_units: int
    ) -> RecommendationResult:
        """
        Recommends and ranks available inventory based on multiple criteria.
        """
        logger.info(f"Generating recommendations for {blood_group} {component_type}")
        try:
            # Use MCP tool from request_tools (find_best_inventory)
            find_tool = registry.get_tool("find_best_inventory")
            
            # Fetch inventory (allow_substitutes=True is default in the tool)
            response = find_tool(
                blood_group=blood_group,
                component_type=component_type,
                latitude=latitude,
                longitude=longitude,
                required_units=required_units,
                allow_substitutes=True
            )
            
            if response.get("status") != "success":
                return RecommendationResult(
                    status="Error",
                    reason=f"Tool error: {response.get('message')}",
                    metadata={}
                )
                
            results = response.get("data", [])
            
            if not results:
                return RecommendationResult(
                    status="No Inventory",
                    reason="No exact or compatible blood inventory found.",
                    metadata={"options": []}
                )
                
            # Rank results using Python-side heuristics
            ranked_results = self._rank_inventory(results, blood_group)
            
            best_match = ranked_results[0]
            explanation = (
                f"Top recommendation is {best_match['facility_name']} "
                f"with {best_match['units_available']} units of {best_match['blood_group']}. "
                f"Ranked based on distance, compatibility, expiration dates, and facility rating."
            )
            
            if best_match['blood_group'] != blood_group:
                explanation += f" (Note: {best_match['blood_group']} is a compatible substitute for {blood_group})."
                
            return RecommendationResult(
                status="Success",
                reason=explanation,
                metadata={"options": ranked_results}
            )
            
        except Exception as e:
            logger.error(f"Error in recommend_inventory: {e}")
            return RecommendationResult(
                status="Error",
                reason=f"Internal error: {str(e)}",
                metadata={}
            )
            
    def _rank_inventory(self, items: List[Dict[str, Any]], target_group: str) -> List[Dict[str, Any]]:
        """
        Rank inventory by distance, available units, compatibility, expiry, and rating.
        """
        for item in items:
            # Base metrics
            distance = item.get('distance_sq', 0)
            units = item.get('units_available', 0)
            bg = item.get('blood_group')
            
            # Expiry penalty
            # We want to use blood that is expiring sooner (FIFO), so fewer days is better
            expiry_str = item.get('expiry_date')
            days_to_expiry = 30 # Default assumption
            if expiry_str:
                try:
                    exp_date = datetime.strptime(expiry_str, "%Y-%m-%d").date()
                    days_to_expiry = max(1, (exp_date - datetime.now().date()).days)
                except ValueError:
                    pass
                    
            # Placeholder hospital rating (1 to 5 scale)
            # Simulated using a deterministic hash of facility_id
            rating = 3.0 + (item.get('facility_id', 1) % 3)
            
            # Compatibility score (exact match = 0, substitute = 1)
            compat_score = 0 if bg == target_group else 1
            
            # Calculate composite score (Lower score = Better rank)
            # Distance is heavily weighted
            # Substitutes get a +50 penalty to prefer exact matches
            # Fewer days to expiry gives a lower score (prefer stock rotation)
            # Higher rating slightly lowers the score
            # More units available slightly lowers the score
            
            score = (
                (distance * 10) +
                (compat_score * 50) + 
                (days_to_expiry * 0.5) -
                (units * 0.1) -
                (rating * 2.0)
            )
            
            item['recommendation_score'] = score
            item['hospital_rating'] = rating
            item['days_to_expiry'] = days_to_expiry
            
        # Sort in ascending order of score
        return sorted(items, key=lambda x: x['recommendation_score'])
