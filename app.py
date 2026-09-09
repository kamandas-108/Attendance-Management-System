import os
import csv
import psycopg2
from io import StringIO
from flask import Flask, request, jsonify, send_from_directory, Response
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder='.')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default_secret')
NEON_DB_STRING = os.getenv('NEON_DB_STRING')

# Provided Data
FACULTY_LIST = [
    {"name": "Manas Kumar Swain", "email": "manas@soa.edu", "password": "password123", "subject": "AD 1"},
    {"name": "Malabika Talukdar", "email": "malabika@soa.edu", "password": "password123", "subject": "IES"},
    {"name": "Swagatika Panda", "email": "swagatika@soa.edu", "password": "password123", "subject": "IM"},
    {"name": "Sunita S Biswal", "email": "sunita@soa.edu", "password": "password123", "subject": "DLD"},
    {"name": "Subhashree Mohapatra", "email": "subhashree@soa.edu", "password": "password123", "subject": "MWDW 1"},
    {"name": "Subrat Kumar Nayak", "email": "subrat@soa.edu", "password": "password123", "subject": "PSPDU"},
    {"name": "Shahid Afridi Saikia", "email": "shahid@soa.edu", "password": "password123", "subject": "ITD"}
]

STUDENTS = [
    "MANYATA ACHARYA", "OWAIS AHMAD", "PRIYANSHU ARYA", "AYUSHI BASTIA", "RUDRANARAYAN BEHERA", "AMAR KUMAR BEHERA",
    "MANYA BHARADWAJ", "BAISHNABEE BISNUPRIYA", "PRIYANSHU PRIYADARSHI BISWAL", "SHUBHAM DALEI", "SWAGAT DAS", "KAMAN DAS",
    "SUBHRA SUBHRAJITA DASH", "NIRMALYA DASMOHAPATRA", "IPSITA DWIBEDI", "SIDDHYANT GIRI", "SYED ASAD IQBAL", "SAMPARK JEΝΑ",
    "RUDRA NARAYAN JETHY", "PUNAM KAR", "NIKHIL KUMAR", "RUDRA JYOTI LAHIRI", "OMM SHREE KRISHNA MOHAPATRA", "SWAYAM SAMPURNA MANSINGH",
    "SOURAJIT MISHRA", "PUNYASHLOK MOHANTY", "LORISA MOHANTY", "RITU RAJ MOHANTY", "CHOUDHURY JIGARDEV MOHAPATRA", "RUDRA NARAYAN MUDULI",
    "MATRU PRASAD NAYAK", "ANCHAL NAYAK", "ABHIJEET ОЈНА", "LESLI PANDA", "SUBHAM PANDA", "SHIVAM KUMAR PANI",
    "SUBHRAJEET PARIDA", "NIMESH CHANDRA PATEL", "SHREYA SALONI PATΤΑΝΑΙΚ", "RONIT KUMAR PAUL", "PRIYADARSINI PRADHAN", "MINUSHREE PRADHAN",
    "SUSHANT PRASAD", "V SURAT RAGINI", "ABHISHEK RATH", "ARYA ARPAN ROUT", "ARANI ROY", "ANUPRAVA SAHO0",
    "RUTUPURNA SAHOO", "PRATYUSH KUMAR SAHOO", "SRADHA RANI SAHU", "SUBHASHREE SAMAL", "PIYUSH KUMAR SATAPATHY", "ANSHIKA KUMARI SINGH",
    "NITYA SRIVASTAVA", "MADIHA SUNDUS", "SWAYAM SWAIN", "VANSH SHARMA", "ALOK TRIPATHY", "ASHUTOSH VAIBHAV"
] #[cite: 1]

def get_db_connection():
    return psycopg2.connect(NEON_DB_STRING)

def init_db():
    if not NEON_DB_STRING: return
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Create Tables
    cur.execute('''
        CREATE TABLE IF NOT EXISTS faculty (
            id SERIAL PRIMARY KEY, name VARCHAR(100), email VARCHAR(100) UNIQUE, password VARCHAR(100), subject VARCHAR(50)
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS students (
            roll_no INTEGER PRIMARY KEY, name VARCHAR(100)
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id SERIAL PRIMARY KEY, roll_no INTEGER, date DATE DEFAULT CURRENT_DATE, 
            status VARCHAR(20), subject VARCHAR(50), 
            UNIQUE(roll_no, date, subject)
        )
    ''')
    
    # Seed Data
    cur.execute("SELECT COUNT(*) FROM faculty")
    if cur.fetchone()[0] == 0:
        for f in FACULTY_LIST:
            cur.execute("INSERT INTO faculty (name, email, password, subject) VALUES (%s, %s, %s, %s)", 
                        (f['name'], f['email'], f['password'], f['subject']))
            
    cur.execute("SELECT COUNT(*) FROM students")
    if cur.fetchone()[0] == 0:
        for idx, name in enumerate(STUDENTS, 1):
            cur.execute("INSERT INTO students (roll_no, name) VALUES (%s, %s)", (idx, name))
            
    conn.commit()
    cur.close()
    conn.close()

# Initialize DB on startup
try:
    init_db()
except Exception as e:
    print("DB Init Error (Check NEON_DB_STRING):", e)

@app.route('/')
def serve_index():
    # Serve index.html directly from the root folder so Render shows it without errors
    return send_from_directory('.', 'index.html')

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT name, subject FROM faculty WHERE email = %s AND password = %s", (data['email'], data['password']))
    user = cur.fetchone()
    cur.close()
    conn.close()
    if user:
        return jsonify({"success": True, "name": user[0], "subject": user[1]})
    return jsonify({"success": False, "message": "Invalid credentials"}), 401

@app.route('/api/students', methods=['GET'])
def get_students():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT roll_no, name FROM students ORDER BY roll_no")
    students = [{"roll_no": row[0], "name": row[1]} for row in cur.fetchall()]
    cur.close()
    conn.close()
    return jsonify(students)

@app.route('/api/attendance', methods=['POST'])
def mark_attendance():
    data = request.json
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        for record in data['records']:
            cur.execute('''
                INSERT INTO attendance (roll_no, status, subject) 
                VALUES (%s, %s, %s)
                ON CONFLICT (roll_no, date, subject) DO UPDATE SET status = EXCLUDED.status
            ''', (record['roll_no'], record['status'], data['subject']))
        conn.commit()
        success = True
    except Exception as e:
        conn.rollback()
        success = False
    finally:
        cur.close()
        conn.close()
    return jsonify({"success": success})

@app.route('/api/export', methods=['GET'])
def export_csv():
    subject = request.args.get('subject')
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT s.roll_no, s.name, a.date, a.status 
        FROM students s 
        LEFT JOIN attendance a ON s.roll_no = a.roll_no AND a.subject = %s
        ORDER BY s.roll_no
    ''', (subject,))
    
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['Roll No', 'Name', 'Date', 'Status', 'Subject'])
    for row in cur.fetchall():
        cw.writerow([row[0], row[1], row[2], row[3], subject])
        
    cur.close()
    conn.close()
    return Response(si.getvalue(), mimetype="text/csv", headers={"Content-Disposition": f"attachment;filename=attendance_{subject}.csv"})

@app.route('/api/send_card', methods=['POST'])
def send_card():
    # Placeholder for actual SMTP email logic
    data = request.json
    print(f"Sending attendance card to {data['email']} for Roll No {data['roll_no']}")
    return jsonify({"success": True, "message": f"Card sent to {data['email']}"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
