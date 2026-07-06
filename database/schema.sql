PRAGMA foreign_keys = ON;

CREATE TABLE HealthcareFacility (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    facility_type TEXT NOT NULL CHECK(facility_type IN ('Hospital', 'Blood Bank', 'Medical College', 'NGO')),
    address TEXT,
    city TEXT NOT NULL,
    latitude REAL,
    longitude REAL,
    phone TEXT,
    email TEXT,
    is_active BOOLEAN DEFAULT 1 CHECK(is_active IN (0, 1)),
    operating_hours TEXT,
    license_number TEXT,
    contact_person TEXT,
    service_radius_km INTEGER DEFAULT 25
);

CREATE TABLE Donor (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    age INTEGER NOT NULL,
    weight REAL NOT NULL,
    gender TEXT,
    blood_group TEXT NOT NULL,
    last_donation_date DATE,
    availability_status TEXT DEFAULT 'Registered',
    phone TEXT,
    email TEXT,
    address TEXT,
    city TEXT NOT NULL,
    state TEXT,
    pin_code TEXT,
    latitude REAL,
    longitude REAL,
    is_registered BOOLEAN DEFAULT 1,
    last_health_screening DATE,
    hemoglobin REAL,
    blood_pressure TEXT,
    medical_clearance BOOLEAN DEFAULT 1,
    last_contacted DATETIME,
    total_donations INTEGER DEFAULT 0,
    eligible_after DATE,
    medical_notes TEXT,
    assessment_date DATETIME,
    assessed_by TEXT,
    ai_recommendation TEXT,
    final_clinical_decision TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE Patient (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    blood_group TEXT NOT NULL CHECK(blood_group IN ('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-')),
    medical_condition TEXT,
    priority_score INTEGER DEFAULT 0,
    facility_id INTEGER NOT NULL,
    patient_category TEXT,
    hemodynamic_status TEXT,
    ai_priority INTEGER,
    priority_reason TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(facility_id) REFERENCES HealthcareFacility(id) ON DELETE CASCADE
);

CREATE TABLE BloodInventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    facility_id INTEGER NOT NULL,
    blood_group TEXT NOT NULL CHECK(blood_group IN ('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-')),
    component_type TEXT NOT NULL CHECK(component_type IN ('Whole Blood', 'Packed RBC', 'Fresh Frozen Plasma', 'Platelets', 'Cryoprecipitate')),
    units_available INTEGER NOT NULL DEFAULT 0 CHECK(units_available >= 0),
    reserved_units INTEGER NOT NULL DEFAULT 0 CHECK(reserved_units >= 0),
    collection_date DATE NOT NULL,
    expiry_date DATE NOT NULL,
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
    minimum_threshold INTEGER DEFAULT 5,
    storage_location TEXT,
    batch_number TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(facility_id) REFERENCES HealthcareFacility(id) ON DELETE CASCADE
);

CREATE TABLE DonationHistory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    donor_id INTEGER NOT NULL,
    facility_id INTEGER NOT NULL,
    donation_date DATE NOT NULL,
    volume_ml INTEGER NOT NULL CHECK(volume_ml > 0),
    blood_component TEXT NOT NULL,
    status TEXT DEFAULT 'Testing' CHECK(status IN ('Testing', 'Safe', 'Discarded')),
    eligibility_checked BOOLEAN CHECK(eligibility_checked IN (0, 1)),
    remarks TEXT,
    FOREIGN KEY(donor_id) REFERENCES Donor(id) ON DELETE CASCADE,
    FOREIGN KEY(facility_id) REFERENCES HealthcareFacility(id) ON DELETE CASCADE
);

CREATE TABLE BloodRequest (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    requesting_facility_id INTEGER NOT NULL,
    blood_group TEXT NOT NULL CHECK(blood_group IN ('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-')),
    component_type TEXT NOT NULL,
    requested_units INTEGER NOT NULL CHECK(requested_units > 0),
    requested_priority TEXT NOT NULL CHECK(requested_priority IN ('TIER_1_IMMEDIATE', 'TIER_2_URGENT', 'TIER_3_SCHEDULED', 'TIER_4_ELECTIVE')),
    ai_priority INTEGER,
    explanation TEXT,
    status TEXT DEFAULT 'Pending' CHECK(status IN ('Pending', 'Partially Fulfilled', 'Fulfilled', 'Cancelled')),
    request_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    required_by DATETIME,
    allocated_units INTEGER DEFAULT 0,
    search_radius INTEGER DEFAULT 20,
    fulfilled_by_facility INTEGER,
    created_by_agent TEXT,
    decision_timestamp DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(patient_id) REFERENCES Patient(id) ON DELETE CASCADE,
    FOREIGN KEY(requesting_facility_id) REFERENCES HealthcareFacility(id) ON DELETE CASCADE,
    FOREIGN KEY(fulfilled_by_facility) REFERENCES HealthcareFacility(id) ON DELETE SET NULL
);

CREATE TABLE Reservation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id INTEGER NOT NULL,
    inventory_id INTEGER NOT NULL,
    reserved_units INTEGER NOT NULL CHECK(reserved_units > 0),
    reservation_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'Active' CHECK(status IN ('Active', 'Completed', 'Released')),
    expires_at DATETIME,
    reserved_by_agent TEXT,
    FOREIGN KEY(request_id) REFERENCES BloodRequest(id) ON DELETE CASCADE,
    FOREIGN KEY(inventory_id) REFERENCES BloodInventory(id) ON DELETE CASCADE
);

CREATE TABLE InventoryAudit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    inventory_id INTEGER NOT NULL,
    changed_by_facility_id INTEGER,
    action TEXT NOT NULL,
    units_changed INTEGER NOT NULL,
    previous_status TEXT,
    new_status TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    ai_explanation TEXT,
    agent_name TEXT,
    FOREIGN KEY(inventory_id) REFERENCES BloodInventory(id) ON DELETE CASCADE,
    FOREIGN KEY(changed_by_facility_id) REFERENCES HealthcareFacility(id) ON DELETE SET NULL
);

CREATE TABLE EmergencyEvent (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_name TEXT NOT NULL,
    location_city TEXT NOT NULL,
    latitude REAL,
    longitude REAL,
    severity_level TEXT NOT NULL CHECK(severity_level IN ('Low', 'Moderate', 'High', 'Critical')),
    declared_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    resolved_at DATETIME,
    is_active BOOLEAN DEFAULT 1 CHECK(is_active IN (0, 1)),
    expected_units INTEGER,
    affected_population INTEGER,
    status TEXT
);

CREATE TABLE Notification (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    donor_id INTEGER,
    facility_id INTEGER,
    notification_type TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_read BOOLEAN DEFAULT 0 CHECK(is_read IN (0, 1)),
    recipient_type TEXT,
    delivery_channel TEXT,
    delivery_status TEXT,
    sent_at DATETIME,
    response TEXT,
    FOREIGN KEY(donor_id) REFERENCES Donor(id) ON DELETE CASCADE,
    FOREIGN KEY(facility_id) REFERENCES HealthcareFacility(id) ON DELETE CASCADE
);

CREATE TABLE DonorNotificationResponse (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    notification_id INTEGER NOT NULL,
    donor_id INTEGER NOT NULL,
    response_type TEXT NOT NULL,
    response_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    additional_notes TEXT,
    FOREIGN KEY(notification_id) REFERENCES Notification(id) ON DELETE CASCADE,
    FOREIGN KEY(donor_id) REFERENCES Donor(id) ON DELETE CASCADE
);

CREATE TABLE AgentDecisionLog (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT NOT NULL,
    decision_type TEXT NOT NULL,
    context TEXT,
    reasoning TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_donor_bg_city ON Donor(blood_group, city, availability_status);
CREATE INDEX idx_inventory_lookup ON BloodInventory(facility_id, blood_group, expiry_date);
CREATE INDEX idx_request_queue ON BloodRequest(status, requested_priority, request_date);
CREATE INDEX idx_patient_priority ON Patient(priority_score);

-- Additional requested indexes
CREATE INDEX idx_bloodinventory_bg ON BloodInventory(blood_group);
CREATE INDEX idx_bloodinventory_expiry ON BloodInventory(expiry_date);
CREATE INDEX idx_donationhistory_date ON DonationHistory(donation_date);
CREATE INDEX idx_notification_status ON Notification(delivery_status);
CREATE INDEX idx_patient_category ON Patient(patient_category);

-- New indexes
CREATE INDEX idx_bloodrequest_component ON BloodRequest(component_type);
CREATE INDEX idx_bloodinventory_component ON BloodInventory(component_type);
CREATE INDEX idx_donor_last_donation ON Donor(last_donation_date);
CREATE INDEX idx_notification_created_at ON Notification(created_at);
