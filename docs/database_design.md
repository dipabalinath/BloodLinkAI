# BloodLink AI - Database Design

This document outlines the final schema and structure for the BloodLink AI SQLite database, including all AI-specific fields, relationships, constraints, and performance indexes.

## Tables

### HealthcareFacility
Stores hospitals, blood banks, medical colleges, and NGOs.
- `id` (INTEGER PRIMARY KEY)
- `name` (TEXT)
- `facility_type` (TEXT) - Hospital, Blood Bank, Medical College, NGO
- `address`, `city` (TEXT)
- `latitude`, `longitude` (REAL)
- `phone`, `email` (TEXT)
- `is_active` (BOOLEAN) - Default 1
- `operating_hours` (TEXT)
- `license_number`, `contact_person` (TEXT)
- `service_radius_km` (INTEGER) - Default 25

### Donor
Stores donor profiles and their eligibility metrics.
- `id` (INTEGER PRIMARY KEY)
- `first_name`, `last_name` (TEXT)
- `age` (INTEGER) - Must be >= 18
- `weight` (REAL) - Must be >= 45.0
- `gender`, `blood_group` (TEXT)
- `last_donation_date` (DATE)
- `availability_status` (TEXT) - Available, Temporarily Deferred, Permanently Deferred
- `phone`, `email`, `address`, `city` (TEXT)
- `latitude`, `longitude` (REAL)
- `is_registered` (BOOLEAN)
- `last_health_screening` (DATE)
- `hemoglobin` (REAL)
- `blood_pressure` (TEXT)
- `medical_clearance` (BOOLEAN)
- `last_contacted` (DATETIME)
- `total_donations` (INTEGER)
- `eligible_after` (DATE)
- `created_at`, `updated_at` (DATETIME)

### Patient
Stores patients needing blood, including AI priority metrics.
- `id` (INTEGER PRIMARY KEY)
- `first_name`, `last_name` (TEXT)
- `blood_group` (TEXT)
- `medical_condition` (TEXT)
- `priority_score` (INTEGER)
- `facility_id` (INTEGER FK)
- `patient_category`, `hemodynamic_status` (TEXT)
- `ai_priority` (INTEGER)
- `priority_reason` (TEXT)
- `created_at`, `updated_at` (DATETIME)

### BloodInventory
Tracks physical units of blood and their shelf-life.
- `id` (INTEGER PRIMARY KEY)
- `facility_id` (INTEGER FK)
- `blood_group` (TEXT)
- `component_type` (TEXT) - Whole Blood, Packed RBC, Fresh Frozen Plasma, Platelets, Cryoprecipitate
- `units_available`, `reserved_units` (INTEGER)
- `collection_date`, `expiry_date` (DATE)
- `last_updated`, `created_at`, `updated_at` (DATETIME)
- `minimum_threshold` (INTEGER)
- `storage_location`, `batch_number` (TEXT)

### DonationHistory
Immutable ledger of past donations.
- `id` (INTEGER PRIMARY KEY)
- `donor_id`, `facility_id` (INTEGER FK)
- `donation_date` (DATE)
- `volume_ml` (INTEGER)
- `blood_component`, `status`, `remarks` (TEXT)
- `eligibility_checked` (BOOLEAN)

### BloodRequest
Logs requests made by hospitals.
- `id` (INTEGER PRIMARY KEY)
- `patient_id`, `requesting_facility_id`, `fulfilled_by_facility` (INTEGER FK)
- `blood_group`, `component_type` (TEXT)
- `requested_units` (INTEGER)
- `requested_priority` (TEXT) - TIER_1_IMMEDIATE, TIER_2_URGENT, TIER_3_SCHEDULED, TIER_4_ELECTIVE
- `ai_priority` (INTEGER)
- `explanation`, `status`, `created_by_agent` (TEXT)
- `request_date`, `required_by`, `decision_timestamp`, `created_at`, `updated_at` (DATETIME)
- `allocated_units`, `search_radius` (INTEGER)

### Reservation
Tracks which specific inventory units are locked for pending requests.
- `id` (INTEGER PRIMARY KEY)
- `request_id`, `inventory_id` (INTEGER FK)
- `reserved_units` (INTEGER)
- `reservation_date`, `expires_at` (DATETIME)
- `status`, `reserved_by_agent` (TEXT)

### InventoryAudit
Log for changes and debugging AI decisions.
- `id` (INTEGER PRIMARY KEY)
- `inventory_id`, `changed_by_facility_id` (INTEGER FK)
- `action`, `previous_status`, `new_status`, `ai_explanation`, `agent_name` (TEXT)
- `units_changed` (INTEGER)
- `timestamp` (DATETIME)

### EmergencyEvent
Tracks mass casualty or disaster events that prompt dynamic reallocation.
- `id` (INTEGER PRIMARY KEY)
- `event_name`, `location_city`, `severity_level`, `status` (TEXT)
- `latitude`, `longitude` (REAL)
- `declared_at`, `resolved_at` (DATETIME)
- `is_active` (BOOLEAN)
- `expected_units`, `affected_population` (INTEGER)

### Notification
Centralized system for donor alerts and AI notifications.
- `id` (INTEGER PRIMARY KEY)
- `donor_id`, `facility_id` (INTEGER FK)
- `notification_type`, `message`, `recipient_type`, `delivery_channel`, `delivery_status`, `response` (TEXT)
- `created_at`, `sent_at` (DATETIME)
- `is_read` (BOOLEAN)

### DonorNotificationResponse
Tracks donor responses to active notifications.
- `id` (INTEGER PRIMARY KEY)
- `notification_id`, `donor_id` (INTEGER FK)
- `response_type`, `additional_notes` (TEXT)
- `response_time` (DATETIME)

### AgentDecisionLog
Logs AI agent reasoning for explainability and transparency.
- `id` (INTEGER PRIMARY KEY)
- `agent_name`, `decision_type`, `context`, `reasoning` (TEXT)
- `timestamp` (DATETIME)

## Indexes
- `idx_donor_bg_city`: `Donor(blood_group, city, availability_status)`
- `idx_inventory_lookup`: `BloodInventory(facility_id, blood_group, expiry_date)`
- `idx_request_queue`: `BloodRequest(status, requested_priority, request_date)`
- `idx_patient_priority`: `Patient(priority_score)`
- `idx_bloodinventory_bg`: `BloodInventory(blood_group)`
- `idx_bloodinventory_expiry`: `BloodInventory(expiry_date)`
- `idx_donationhistory_date`: `DonationHistory(donation_date)`
- `idx_notification_status`: `Notification(delivery_status)`
- `idx_patient_category`: `Patient(patient_category)`
- `idx_bloodrequest_component`: `BloodRequest(component_type)`
- `idx_bloodinventory_component`: `BloodInventory(component_type)`
- `idx_donor_last_donation`: `Donor(last_donation_date)`
- `idx_notification_created_at`: `Notification(created_at)`
