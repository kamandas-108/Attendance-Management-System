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
]

def get_db_connection():
    return psycopg2.connect(NEON_DB_STRING)

def init_db():
    if not NEON_DB_STRING: return
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute('''CREATE TABLE IF NOT EXISTS faculty (id SERIAL PRIMARY KEY, name VARCHAR(100), email VARCHAR(100) UNIQUE, password VARCHAR(100), subject VARCHAR(50))''')
    cur.execute('''CREATE TABLE IF NOT EXISTS students (roll_no INTEGER PRIMARY KEY, name VARCHAR(100))''')
    cur.execute('''CREATE TABLE IF NOT EXISTS attendance (id SERIAL PRIMARY KEY, roll_no INTEGER, date DATE DEFAULT CURRENT_DATE, status VARCHAR(20), subject VARCHAR(50), UNIQUE(roll_no, date, subject))''')
            
    cur.execute("SELECT COUNT(*) FROM students")
    if cur.fetchone()[0] == 0:
        for idx, name in enumerate(STUDENTS, 1):
            cur.execute("INSERT INTO students (roll_no, name) VALUES (%s, %s)", (idx, name))
            
    conn.commit()
    cur.close()
    conn.close()

try:
    init_db()
except Exception as e:
    print("DB Init Error:", e)

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO faculty (name, email, password, subject) VALUES (%s, %s, %s, %s)", 
                    (data['name'], data['email'], data['password'], data['subject']))
        conn.commit()
        return jsonify({"success": True, "message": "Registration successful. Please log in."})
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        return jsonify({"success": False, "message": "Email already exists."}), 400
    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "message": "Registration failed."}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT name, subject FROM faculty WHERE email = %s AND password = %s", (data['email'], data['password']))
    user = cur.fetchone()
    cur.close()
    conn.close()
    if user: return jsonify({"success": True, "name": user[0], "subject": user[1]})
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
            cur.execute('''INSERT INTO attendance (roll_no, status, subject) VALUES (%s, %s, %s) ON CONFLICT (roll_no, date, subject) DO UPDATE SET status = EXCLUDED.status''', (record['roll_no'], record['status'], data['subject']))
        conn.commit()
        success = True
    except:
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
    cur.execute('''SELECT s.roll_no, s.name, a.date, a.status FROM students s LEFT JOIN attendance a ON s.roll_no = a.roll_no AND a.subject = %s ORDER BY s.roll_no''', (subject,))
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['Roll No', 'Name', 'Date', 'Status', 'Subject'])
    for row in cur.fetchall(): cw.writerow([row[0], row[1], row[2], row[3], subject])
    cur.close()
    conn.close()
    return Response(si.getvalue(), mimetype="text/csv", headers={"Content-Disposition": f"attachment;filename=attendance_{subject}.csv"})

@app.route('/api/send_card', methods=['POST'])
def send_card():
    data = request.json
    return jsonify({"success": True, "message": f"Card sent to {data['email']}"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
