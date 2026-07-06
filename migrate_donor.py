import sqlite3

def migrate():
    db_path = 'data/bloodlink.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. Rename existing table
    cursor.execute("ALTER TABLE Donor RENAME TO Donor_old")

    # 2. Create new table without the strict CHECK constraint on availability_status
    cursor.execute("""
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
    )
    """)

    # 3. Copy data
    cursor.execute("""
    INSERT INTO Donor (
        id, first_name, last_name, age, weight, gender, blood_group, last_donation_date, 
        availability_status, phone, email, address, city, state, pin_code, latitude, longitude, 
        is_registered, last_health_screening, hemoglobin, blood_pressure, medical_clearance, 
        last_contacted, total_donations, eligible_after, medical_notes, created_at, updated_at
    )
    SELECT 
        id, first_name, last_name, age, weight, gender, blood_group, last_donation_date, 
        availability_status, phone, email, address, city, state, pin_code, latitude, longitude, 
        is_registered, last_health_screening, hemoglobin, blood_pressure, medical_clearance, 
        last_contacted, total_donations, eligible_after, medical_notes, created_at, updated_at
    FROM Donor_old
    """)

    # 4. Update existing statuses to map to new workflow
    cursor.execute("UPDATE Donor SET availability_status = 'Available for Donation' WHERE availability_status = 'Available'")

    # 5. Drop old table
    cursor.execute("DROP TABLE Donor_old")

    conn.commit()
    print("Migration successful")

if __name__ == "__main__":
    migrate()
