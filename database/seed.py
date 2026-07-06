"""
Database Seeder for BloodLink AI.
Generates realistic dummy data for all tables using Faker.
"""

import os
import csv
import random
from datetime import timedelta
from faker import Faker
from database.database import DatabaseManager

def seed_db():
    # Set fixed seeds for reproducibility
    random.seed(42)
    fake = Faker('en_IN')
    Faker.seed(42)

    db = DatabaseManager()
    conn = db.connect()
    cursor = conn.cursor()

    print("Clearing existing data...")
    tables = [
        "AgentDecisionLog", "DonorNotificationResponse", "Notification",
        "EmergencyEvent", "InventoryAudit", "Reservation", "BloodRequest",
        "DonationHistory", "BloodInventory", "Patient", "Donor", "HealthcareFacility"
    ]
    for table in tables:
        cursor.execute(f"DELETE FROM {table}")
    
    print("Seeding Healthcare Facilities...")
    csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures', 'kolkata_facilities.csv')
    facilities = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            cursor.execute("""
                INSERT INTO HealthcareFacility 
                (name, facility_type, address, city, latitude, longitude, phone, email, operating_hours, service_radius_km)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row['name'], row['facility_type'], row['address'], row['city'],
                float(row['latitude']), float(row['longitude']), row['phone'], row['email'],
                row['operating_hours'], int(row['service_radius_km'])
            ))
            facilities.append(cursor.lastrowid)

    blood_groups = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
    component_types = ['Whole Blood', 'Packed RBC', 'Fresh Frozen Plasma', 'Platelets', 'Cryoprecipitate']

    print("Seeding Blood Inventory...")
    inventories = []
    for f_id in facilities:
        for bg in blood_groups:
            for ct in component_types:
                # Realistic stock: some components might be 0, some up to 50
                units = random.randint(0, 50)
                reserved = random.randint(0, min(10, units)) if units > 0 else 0
                collection = fake.date_between(start_date='-30d', end_date='today')
                # Calculate realistic expiry based on component
                if ct == 'Platelets':
                    expiry = collection + timedelta(days=5)
                elif ct == 'Packed RBC':
                    expiry = collection + timedelta(days=42)
                elif ct == 'Fresh Frozen Plasma' or ct == 'Cryoprecipitate':
                    expiry = collection + timedelta(days=365)
                else:
                    expiry = collection + timedelta(days=35) # Whole Blood
                    
                cursor.execute("""
                    INSERT INTO BloodInventory 
                    (facility_id, blood_group, component_type, units_available, reserved_units, collection_date, expiry_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (f_id, bg, ct, units, reserved, collection, expiry))
                inventories.append(cursor.lastrowid)

    print("Seeding 500 Donors...")
    donors = []
    for _ in range(500):
        # WHO Minimum age >= 18, weight >= 45.0
        age = random.randint(18, 65)
        weight = round(random.uniform(45.0, 110.0), 1)
        cursor.execute("""
            INSERT INTO Donor 
            (first_name, last_name, age, weight, gender, blood_group, city, phone, email, availability_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            fake.first_name(), fake.last_name(), age, weight, random.choice(['Male', 'Female']),
            random.choice(blood_groups), 'Kolkata', fake.phone_number(), fake.email(),
            random.choices(['Available', 'Temporarily Deferred', 'Permanently Deferred'], weights=[0.8, 0.15, 0.05])[0]
        ))
        donors.append(cursor.lastrowid)

    print("Seeding 1000 Donation History Records...")
    for _ in range(1000):
        d_id = random.choice(donors)
        f_id = random.choice(facilities)
        d_date = fake.date_between(start_date='-2y', end_date='today')
        cursor.execute("""
            INSERT INTO DonationHistory 
            (donor_id, facility_id, donation_date, volume_ml, blood_component, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            d_id, f_id, d_date, random.choice([350, 450]), random.choice(component_types),
            random.choices(['Testing', 'Safe', 'Discarded'], weights=[0.1, 0.85, 0.05])[0]
        ))

    print("Seeding 300 Patients...")
    conditions = ['Birthing Mothers', 'Thalassemia', 'Trauma', 'Cancer', 'Elective Surgery']
    patients = []
    for _ in range(300):
        cursor.execute("""
            INSERT INTO Patient 
            (first_name, last_name, blood_group, medical_condition, facility_id, priority_score)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            fake.first_name(), fake.last_name(), random.choice(blood_groups),
            random.choice(conditions), random.choice(facilities), random.randint(0, 100)
        ))
        patients.append(cursor.lastrowid)

    print("Seeding 200 Blood Requests...")
    priorities = ['TIER_1_IMMEDIATE', 'TIER_2_URGENT', 'TIER_3_SCHEDULED', 'TIER_4_ELECTIVE']
    requests = []
    for _ in range(200):
        p_id = random.choice(patients)
        cursor.execute("SELECT blood_group, facility_id FROM Patient WHERE id=?", (p_id,))
        patient_data = cursor.fetchone()
        bg, f_id = patient_data['blood_group'], patient_data['facility_id']
        
        cursor.execute("""
            INSERT INTO BloodRequest 
            (patient_id, requesting_facility_id, blood_group, component_type, requested_units, requested_priority, ai_priority, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            p_id, f_id, bg, random.choice(component_types), random.randint(1, 5),
            random.choice(priorities), random.randint(1, 4), random.choice(['Pending', 'Partially Fulfilled', 'Fulfilled', 'Cancelled'])
        ))
        requests.append(cursor.lastrowid)

    print("Seeding ancillary records (Reservations, Notifications, Audits, Emergencies)...")
    
    # Emergency Events
    emergencies_data = [
        ("Mass Transit Accident", "Kolkata", "Critical", 1, 150, 50, 22.5726, 88.3639),
        ("Industrial Explosion", "Howrah", "Critical", 1, 100, 30, 22.5958, 88.2636),
        ("Flood Disaster", "Salt Lake", "High", 1, 200, 100, 22.5867, 88.4170),
        ("Building Collapse", "Kolkata", "High", 1, 80, 20, 22.5600, 88.3700),
        ("Train Derailment", "Sealdah", "Critical", 1, 120, 40, 22.5697, 88.3697)
    ]
    
    for emg in emergencies_data:
        cursor.execute("""
            INSERT INTO EmergencyEvent 
            (event_name, location_city, severity_level, is_active, expected_units, affected_population, latitude, longitude)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, emg)
    
    # Audit Logs & Notifications
    for _ in range(50):
        cursor.execute("""
            INSERT INTO InventoryAudit 
            (inventory_id, changed_by_facility_id, action, units_changed, previous_status, new_status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (random.choice(inventories), random.choice(facilities), "Used", 1, "Available", "Used"))
        
        cursor.execute("""
            INSERT INTO Notification 
            (donor_id, notification_type, message, recipient_type, delivery_channel)
            VALUES (?, ?, ?, ?, ?)
        """, (random.choice(donors), "Urgent Appeal", "Your blood group is needed urgently in your area.", "Donor", "SMS"))

    # Reservations
    for req_id in random.sample(requests, 20):
        # Create 1 to 3 reservations for this request to simulate 1:N relation
        num_reservations = random.randint(1, 3)
        for _ in range(num_reservations):
            cursor.execute("""
                INSERT INTO Reservation 
                (request_id, inventory_id, reserved_units, status)
                VALUES (?, ?, ?, ?)
            """, (req_id, random.choice(inventories), random.randint(1, 3), "Active"))
            
    conn.commit()
    db.close()
    print("Database seeding completed successfully.")

if __name__ == "__main__":
    seed_db()
