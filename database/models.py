"""
Data models for BloodLink AI.
These dataclasses represent the structure of the SQLite database tables in Python.
"""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime, date

@dataclass
class HealthcareFacility:
    id: Optional[int]
    name: str
    facility_type: str
    city: str
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    is_active: bool = True
    operating_hours: Optional[str] = None
    license_number: Optional[str] = None
    contact_person: Optional[str] = None
    service_radius_km: int = 25

@dataclass
class Donor:
    id: Optional[int]
    first_name: str
    last_name: str
    age: int
    weight: float
    blood_group: str
    city: str
    gender: Optional[str] = None
    last_donation_date: Optional[date] = None
    availability_status: str = 'Available'
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_registered: bool = True
    last_health_screening: Optional[date] = None
    hemoglobin: Optional[float] = None
    blood_pressure: Optional[str] = None
    medical_clearance: bool = True
    last_contacted: Optional[datetime] = None
    total_donations: int = 0
    eligible_after: Optional[date] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

@dataclass
class Patient:
    id: Optional[int]
    first_name: str
    last_name: str
    blood_group: str
    facility_id: int
    medical_condition: Optional[str] = None
    priority_score: int = 0
    patient_category: Optional[str] = None
    hemodynamic_status: Optional[str] = None
    ai_priority: Optional[int] = None
    priority_reason: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

@dataclass
class BloodInventory:
    id: Optional[int]
    facility_id: int
    blood_group: str
    component_type: str
    collection_date: date
    expiry_date: date
    units_available: int = 0
    reserved_units: int = 0
    minimum_threshold: int = 5
    storage_location: Optional[str] = None
    batch_number: Optional[str] = None
    last_updated: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

@dataclass
class DonationHistory:
    id: Optional[int]
    donor_id: int
    facility_id: int
    donation_date: date
    volume_ml: int
    blood_component: str
    status: str = 'Testing'
    eligibility_checked: Optional[bool] = None
    remarks: Optional[str] = None

@dataclass
class BloodRequest:
    id: Optional[int]
    patient_id: int
    requesting_facility_id: int
    blood_group: str
    component_type: str
    requested_units: int
    requested_priority: str
    ai_priority: Optional[int] = None
    explanation: Optional[str] = None
    status: str = 'Pending'
    request_date: Optional[datetime] = None
    required_by: Optional[datetime] = None
    allocated_units: int = 0
    search_radius: int = 20
    fulfilled_by_facility: Optional[int] = None
    created_by_agent: Optional[str] = None
    decision_timestamp: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

@dataclass
class Reservation:
    id: Optional[int]
    request_id: int
    inventory_id: int
    reserved_units: int
    reservation_date: Optional[datetime] = None
    status: str = 'Active'
    expires_at: Optional[datetime] = None
    reserved_by_agent: Optional[str] = None

@dataclass
class InventoryAudit:
    id: Optional[int]
    inventory_id: int
    action: str
    units_changed: int
    changed_by_facility_id: Optional[int] = None
    previous_status: Optional[str] = None
    new_status: Optional[str] = None
    timestamp: Optional[datetime] = None
    ai_explanation: Optional[str] = None
    agent_name: Optional[str] = None

@dataclass
class EmergencyEvent:
    id: Optional[int]
    event_name: str
    location_city: str
    severity_level: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    declared_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    is_active: bool = True
    expected_units: Optional[int] = None
    affected_population: Optional[int] = None
    status: Optional[str] = None

@dataclass
class Notification:
    id: Optional[int]
    notification_type: str
    message: str
    donor_id: Optional[int] = None
    facility_id: Optional[int] = None
    created_at: Optional[datetime] = None
    is_read: bool = False
    recipient_type: Optional[str] = None
    delivery_channel: Optional[str] = None
    delivery_status: Optional[str] = None
    sent_at: Optional[datetime] = None
    response: Optional[str] = None

@dataclass
class DonorNotificationResponse:
    id: Optional[int]
    notification_id: int
    donor_id: int
    response_type: str
    response_time: Optional[datetime] = None
    additional_notes: Optional[str] = None

@dataclass
class AgentDecisionLog:
    id: Optional[int]
    agent_name: str
    decision_type: str
    context: Optional[str] = None
    reasoning: Optional[str] = None
    timestamp: Optional[datetime] = None
