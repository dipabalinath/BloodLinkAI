"""
Shared Pydantic models for BloodLink AI skills.
Provides standardized output formats across different AI capabilities.
"""

from pydantic import BaseModel, Field
from typing import Dict, Any
from datetime import datetime

class EligibilityResult(BaseModel):
    status: str = Field(description="The final eligibility status.")
    reason: str = Field(description="Detailed explanation of the eligibility decision.")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class PriorityDecision(BaseModel):
    status: str = Field(description="The determined priority tier.")
    reason: str = Field(description="Clinical reasoning behind the priority assignment.")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class RecommendationResult(BaseModel):
    status: str = Field(description="Status of the recommendation generation.")
    reason: str = Field(description="Explanation of why this recommendation was made.")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class NotificationResult(BaseModel):
    status: str = Field(description="Outcome of the notification process.")
    reason: str = Field(description="Details on successful delivery or failure reasons.")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ExplainabilityResult(BaseModel):
    status: str = Field(description="Status of the explainability trace.")
    reason: str = Field(description="Human-readable explanation of the AI's internal reasoning.")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
