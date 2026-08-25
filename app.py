from flask import Flask, request, render_template, redirect, session, url_for, send_from_directory
from pymongo import MongoClient
from bson.objectid import ObjectId
import os
from datetime import datetime, timezone
import joblib
import pandas as pd
import json  # Added for Chart.js data passing

app = Flask(__name__)
app.secret_key = "aa"

app.config["UPLOAD_FOLDER"] = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

client = MongoClient("mongodb://localhost:27017/")
db = client["mydatabase"] 

# Create collections if they don't exist
existing_collections = db.list_collection_names()
for coll in ["users", "assignments", "submissions", "batches", "enrollments"]:
    if coll not in existing_collections:
        db.create_collection(coll)

users = db["users"]
assignments = db["assignments"]
submissions = db["submissions"]
batches = db["batches"]
enrollments = db["enrollments"]

# ==========================================
# 1. SUPPORT TICKETS DATABASE SETUP
# ==========================================
if "support_tickets" not in existing_collections:
    db.create_collection("support_tickets")
support_tickets = db["support_tickets"]

# Default Users
if not users.find_one({"email": "admin@gmail.com"}):
    users.insert_one({"email": "admin@gmail.com", "password": "admin123", "role": "admin"})

if not users.find_one({"email": "teacher@gmail.com"}):
    users.insert_one({"email": "teacher@gmail.com", "password": "teacher123", "role": "teacher"})

if not users.find_one({"email": "analyst@gmail.com"}):
    users.insert_one({"email": "analyst@gmail.com", "password": "analyst123", "role": "analyst"})

# --- MACHINE LEARNING MODEL LOADING ---
try:
    performance_model = joblib.load("performance_model.pkl")
    print("Success: performance_model.pkl loaded and ready for predictions!")
except FileNotFoundError:
    performance_model = None
    print("Warning: ML model not found. Please run train_model.py first.")

try:
    demand_model = joblib.load("demand_model.pkl")
except Exception:
    demand_model = None

# --- AUTHENTICATION ROUTES ---

@app.route("/")
def home():
    return redirect("/login")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        if users.find_one({"email": email}):
            return "User already exists"
        users.insert_one({"email": email, "password": password, "role": "student"})
        return redirect("/login")
    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = users.find_one({"email": email, "password": password})
        if not user:
            return "Invalid email or password"
        
        session["user"] = email
        session["role"] = user["role"]

        if user["role"] == "admin": return redirect("/admin")
        elif user["role"] == "teacher": return redirect("/teacher")
        elif user["role"] == "analyst": return redirect("/analyst")
        else: return redirect("/student")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# --- ADMIN ROUTES ---

@app.route("/admin")
def admin():
    if "user" not in session or session.get("role") != "admin": 
        return redirect("/login")
    
    all_users = users.find()
    all_batches = batches.find()
    teacher_list = users.find({"role": "teacher"})
    
    return render_template("admin.html", users=all_users, teacher_list=teacher_list, batches=all_batches)

@app.route("/change_role", methods=["POST"])
def change_role():
    email = request.form.get("email")
    new_role = request.form.get("role")
    if email and new_role:
        users.update_one({"email": email}, {"$set": {"role": new_role}})
    return redirect("/admin")

@app.route("/add_batches", methods=["POST"])
def add_batches():
    batch_code = request.form.get("batch_code")
    timing = request.form.get("timing")
    days = request.form.get("days")
    teacher = request.form.get("teacher")
    
    if batch_code and teacher:
        batches.insert_one({
            "batch_code": batch_code, 
            "timing": timing, 
            "days": days, 
            "teacher": teacher
        }) 
    return redirect("/admin")


# --- TEACHER ROUTES ---

@app.route("/teacher")
def teacher():
    if "user" not in session or session.get("role") != "teacher": 
        return redirect("/login")
    
    my_batches = batches.find({"teacher": session.get("user")})
    return render_template("teacher.html", batches=my_batches)


@app.route("/teacher_batch/<batch_id>", methods=["GET", "POST"])
def teacher_batch(batch_id):
    if "user" not in session or session.get("role") != "teacher": 
        return redirect("/login")
        
    if request.method == "POST":
        assignments.insert_one({
            "title": request.form.get("title"),
            "desc": request.form.get("desc"),
            "due_date": request.form.get("due_date"),
            "marks": request.form.get("marks"),
            "status": request.form.get("status"),
            "teacher": session.get("user"),
            "batch_id": str(batch_id)
        })

        # Notify all students enrolled in this batch
        enrolled = enrollments.find({"batch_id": str(batch_id)})
        for e in enrolled:
            create_notification(
                recipient_email=e["student"],
                title="📚 New Assignment Posted",
                message=f"New assignment '{request.form.get('title')}' added. Due: {request.form.get('due_date')}",
                alert_type="info"
            )
        return redirect(f"/teacher_batch/{batch_id}")
        
    batch = batches.find_one({"_id": ObjectId(batch_id)})
    batch_assignments = assignments.find({"batch_id": str(batch_id)})
    enrolled_students = enrollments.find({"batch_id": str(batch_id)})
    
    return render_template("teacher_batch.html", batch=batch, assignments=batch_assignments, students=enrolled_students)

@app.route("/edit_assignment/<id>", methods=["GET", "POST"])
def edit_assignment(id):
    assignment = assignments.find_one({"_id": ObjectId(id)})
    if request.method == "POST":
        assignments.update_one(
            {"_id": ObjectId(id)},
            {"$set": {
                "title": request.form.get("title"),
                "desc": request.form.get("desc"),
                "due_date": request.form.get("due_date"),
                "marks": request.form.get("marks"),
                "status": request.form.get("status")
            }}
        )
        return redirect(f"/teacher_batch/{assignment.get('batch_id')}")
    return render_template("edit_assignment.html", assignment=assignment)

@app.route("/delete_assignment/<id>")
def delete_assignment(id):
    assignment = assignments.find_one({"_id": ObjectId(id)})
    batch_id = assignment.get("batch_id") if assignment else None
    assignments.delete_one({"_id": ObjectId(id)})
    
    if batch_id:
        return redirect(f"/teacher_batch/{batch_id}")
    return redirect("/teacher")

@app.route("/submissions/<assignment_id>")
def view_submissions(assignment_id):
    assignment = assignments.find_one({"_id": ObjectId(assignment_id)})
    assignment_submissions = submissions.find({"assignment_id": ObjectId(assignment_id)})
    return render_template("submissions.html", assignment=assignment, submissions=assignment_submissions)

@app.route("/grade/<submission_id>", methods=["POST"])
def grade(submission_id):
    sub = submissions.find_one({"_id": ObjectId(submission_id)})
    submissions.update_one(
        {"_id": ObjectId(submission_id)},
        {"$set": {
            "marks": request.form.get("marks"), 
            "remarks": request.form.get("remarks"), 
            "graded": True
        }}
    )
    if sub:
        create_notification(
            recipient_email=sub["student"],
            title="📝 Assignment Graded",
            message=f"Your assignment submission has been graded. Marks: {request.form.get('marks')}",
            alert_type="success"
        )
    return redirect(request.referrer or url_for("teacher"))


# --- STUDENT ROUTES ---

@app.route("/student")
def student():
    if "user" not in session: 
        return redirect("/login")
        
    all_batches = batches.find()
    
    my_enroll_cursor = enrollments.find({"student": session.get("user")})
    my_enroll = list(my_enroll_cursor)
    
    enrolled_batch_ids = [str(e["batch_id"]) for e in my_enroll]
    my_assignments = assignments.find({"batch_id": {"$in": enrolled_batch_ids}})
    
    user_submissions = submissions.find({"student": session.get("user")})
    submission_map = {str(s["assignment_id"]): s for s in user_submissions}
    
    return render_template(
        "student.html", 
        assignments=my_assignments, 
        batches=all_batches, 
        enrollments=my_enroll,
        submission_map=submission_map
    )

@app.route("/enroll/<id>")
def enroll(id):
    batch = batches.find_one({"_id": ObjectId(id)})
    already = enrollments.find_one({"student": session["user"], "batch_id": id})
    
    if already:
        return redirect("/student")

    enrollments.insert_one({
        "student": session["user"],
        "batch_id": id,
        "batch_code": batch.get("batch_code"),
        "timing": batch.get("timing"),
        "days": batch.get("days"),
        "teacher": batch.get("teacher")
    })
    return redirect("/student")

@app.route("/submit/<assignment_id>", methods=["POST"])
def submit(assignment_id):
    student_email = session.get("user")
    submission_text = request.form.get("submission_text", "")
    filename = None
    
    if "submission_file" in request.files:
        file = request.files["submission_file"]
        if file and file.filename:
            filename = f"{student_email}_{file.filename}"
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            
    existing = submissions.find_one({"assignment_id": ObjectId(assignment_id), "student": student_email})
    
    update_fields = {"submission_text": submission_text, "submitted_on": datetime.now(timezone.utc)}
    if filename: update_fields["filename"] = filename
        
    if existing:
        submissions.update_one({"_id": existing["_id"]}, {"$set": update_fields})
    else:
        submissions.insert_one({
            "assignment_id": ObjectId(assignment_id),
            "student": student_email,
            "submission_text": submission_text,
            "submitted_on": datetime.now(timezone.utc),
            "filename": filename
        })
    return redirect("/student")

@app.route("/download/<filename>")
def download_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename, as_attachment=True)


# --- ANALYST ROUTE (UPDATED WITH CHART.JS VISUALIZATION) ---
@app.route("/analyst", methods=["GET", "POST"])
def analyst():
    if "user" not in session or session.get("role") != "analyst":
        return redirect("/login")
    
    prediction_result = None
    
    # 1. Handle ML Prediction Form
    if request.method == "POST":
        if not performance_model:
            prediction_result = "Error: ML Model not trained. Please run train_model.py first."
        else:
            try:
                attendance = float(request.form.get("attendance_pct", 0))
                assignments = float(request.form.get("assignment_avg", 0))
                participation = float(request.form.get("participation_score", 0))

                input_data = pd.DataFrame([[attendance, assignments, participation]], 
                                          columns=['attendance_pct', 'assignment_avg', 'participation_score'])
                
                predicted_grade = performance_model.predict(input_data)[0]
                prediction_result = f"Predicted Final Grade: {round(predicted_grade, 2)}%"
            except Exception as e:
                prediction_result = f"Error processing input: {str(e)}"

    # 2. Prepare Data for Chart.js Visualization
    chart_data = {}
    try:
        df = pd.read_csv('student_historical_data.csv')
        
        # Chart 1: Grade Distribution
        bins = [0, 50, 60, 70, 80, 90, 100]
        labels = ['<50', '50-60', '60-70', '70-80', '80-90', '90-100']
        grade_dist = pd.cut(df['final_grade'], bins=bins, labels=labels, include_lowest=True).value_counts().sort_index().tolist()
        
        # Chart 2: Dropout Risk (Check if flag exists to prevent errors)
        if 'dropout_flag' in df.columns:
            dropout_counts = df['dropout_flag'].value_counts().sort_index().tolist()
        else:
            dropout_counts = [len(df), 0]
        
        # Chart 3: Anomaly Detection Scatter (Sampled to prevent lag)
        scatter_sample = df.sample(min(150, len(df)))
        scatter_data = [{"x": row['attendance_pct'], "y": row['final_grade']} for _, row in scatter_sample.iterrows()]
        
        chart_data = {
            "grade_labels": labels,
            "grade_dist": grade_dist,
            "dropout_counts": dropout_counts,
            "scatter_data": scatter_data
        }
    except Exception as e:
        print(f"Visualization Error: {e}")

    # 3. Prepare Future Course Demand Predictions (e.g., Year 2026, Term 2)
    demand_predictions = []
    if demand_model:
        courses = {
            0: "Advance Diploma in Software Engineering",
            1: "Intermediate Computer Science",
            2: "MERN Stack Web Development",
            3: "Flutter Mobile App Development"
        }
        for c_id, c_name in courses.items():
            # Predict for Fall 2026
            input_features = pd.DataFrame([[2026, 2, c_id]], columns=['year', 'term', 'course_id'])
            predicted_enrollment = int(demand_model.predict(input_features)[0])
            demand_predictions.append({
                "course": c_name,
                "predicted_enrollment": predicted_enrollment
            })

    return render_template("analyst.html",
                           prediction=prediction_result,
                           chart_data=json.dumps(chart_data),
                           demand_predictions=demand_predictions)

# Create new collection for attendance to fulfill PDF requirements
if "attendance" not in existing_collections:
    db.create_collection("attendance")
attendance_db = db["attendance"]

# ==========================================
# 1. NOTIFICATIONS & ALERTS DATABASE SETUP
# ==========================================
if "notifications" not in existing_collections:
    db.create_collection("notifications")
notifications = db["notifications"]

if "alert_settings" not in existing_collections:
    db.create_collection("alert_settings")
alert_settings = db["alert_settings"]

# Initialize default configurable thresholds if not present
if not alert_settings.find_one({"type": "global_thresholds"}):
    alert_settings.insert_one({
        "type": "global_thresholds",
        "attendance_threshold": 75.0,  # Alert if attendance < 75%
        "grade_threshold": 50.0,       # Alert if predicted grade < 50%
        "enable_anomaly_alerts": True,
        "updated_at": datetime.now(timezone.utc)
    })

# Load Anomaly & Dropout Models if available
try:
    anomaly_model = joblib.load("anomaly_model.pkl")
    dropout_model = joblib.load("dropout_model.pkl")
except Exception:
    anomaly_model = None
    dropout_model = None


# ==========================================
# 2. HELPER FUNCTIONS & AUTOMATED SCAN ENGINE
# ==========================================
def create_notification(recipient_email, title, message, alert_type="info", role=None):
    """Inserts an automated notification into MongoDB."""
    notifications.insert_one({
        "recipient": recipient_email,       # Specific email or "all"
        "role": role,                       # Optional role-based broadcast
        "title": title,
        "message": message,
        "alert_type": alert_type,           # 'danger', 'warning', 'info', 'success'
        "read": False,
        "created_at": datetime.now(timezone.utc)
    })


# ==========================================
# 2. FEEDBACK & SUPPORT ROUTES
# ==========================================
@app.route("/support", methods=["GET", "POST"])
def support():
    """Allows any logged-in user to submit feedback or report an issue."""
    if "user" not in session:
        return redirect("/login")

    user_email = session.get("user")

    if request.method == "POST":
        subject = request.form.get("subject")
        category = request.form.get("category")  # e.g., 'Bug Report', 'General Feedback', 'Assistance'
        message = request.form.get("message")

        # Insert ticket into the database
        support_tickets.insert_one({
            "user_email": user_email,
            "role": session.get("role"),
            "subject": subject,
            "category": category,
            "message": message,
            "status": "Open",
            "submitted_on": datetime.now(timezone.utc)
        })

        # Notify the Admin that a new ticket was created
        create_notification(
            recipient_email="admin@gmail.com",
            title="🎫 New Support Ticket",
            message=f"[{category}] {subject} reported by {user_email}.",
            alert_type="info"
        )

        return redirect("/support?success=1")

    # Fetch user's past tickets to display status
    my_tickets = list(support_tickets.find({"user_email": user_email}).sort("submitted_on", -1))
    return render_template("support.html", tickets=my_tickets)


@app.route("/admin/support")
def admin_support():
    """Admin dashboard to view and manage all support tickets."""
    if session.get("role") != "admin":
        return redirect("/login")

    all_tickets = list(support_tickets.find().sort("submitted_on", -1))
    return render_template("admin_support.html", tickets=all_tickets)


@app.route("/admin/support/resolve/<ticket_id>")
def resolve_ticket(ticket_id):
    """Marks a ticket as resolved and notifies the user."""
    if session.get("role") != "admin":
        return redirect("/login")

    ticket = support_tickets.find_one_and_update(
        {"_id": ObjectId(ticket_id)},
        {"$set": {"status": "Resolved"}}
    )

    # Notify the user that their issue is resolved
    if ticket:
        create_notification(
            recipient_email=ticket["user_email"],
            title="✅ Support Ticket Resolved",
            message=f"Your ticket regarding '{ticket['subject']}' has been resolved by administration.",
            alert_type="success"
        )

    return redirect("/admin/support")


def run_system_academic_scan():
    """Scans student records against configured thresholds and ML anomalies."""
    config = alert_settings.find_one({"type": "global_thresholds"}) or {}
    att_thresh = config.get("attendance_threshold", 75.0)
    grade_thresh = config.get("grade_threshold", 50.0)

    students = list(users.find({"role": "student"}))
    alerts_generated = 0

    for student in students:
        email = student["email"]

        # Calculate student attendance percentage
        att_records = list(attendance_db.find({"student": email}))
        if att_records:
            present_count = sum(1 for a in att_records if a.get("status") == "present")
            att_pct = (present_count / len(att_records)) * 100.0
        else:
            att_pct = 100.0

        # Calculate average assignment marks
        subs = list(submissions.find({"student": email, "graded": True}))
        avg_marks = sum(float(s.get("marks", 0)) for s in subs) / len(subs) if subs else 0.0

        # 1. Attendance Threshold Alert
        if len(att_records) >= 3 and att_pct < att_thresh:
            existing = notifications.find_one({
                "recipient": email,
                "title": "⚠️ Low Attendance Warning",
                "read": False
            })
            if not existing:
                create_notification(
                    recipient_email=email,
                    title="⚠️ Low Attendance Warning",
                    message=f"Your current attendance is {round(att_pct, 1)}%, which is below the required {att_thresh}%.",
                    alert_type="danger"
                )
                alerts_generated += 1

        # 2. Performance Prediction & Anomaly Alert
        if performance_model:
            try:
                input_df = pd.DataFrame([[att_pct, avg_marks, 80.0]],
                                        columns=['attendance_pct', 'assignment_avg', 'participation_score'])
                predicted_grade = float(performance_model.predict(input_df)[0])

                if predicted_grade < grade_thresh:
                    existing = notifications.find_one({
                        "recipient": email,
                        "title": "🚨 Academic Risk Alert",
                        "read": False
                    })
                    if not existing:
                        create_notification(
                            recipient_email=email,
                            title="🚨 Academic Risk Alert",
                            message=f"Predicted course grade ({round(predicted_grade, 1)}%) is below the passing standard ({grade_thresh}%).",
                            alert_type="warning"
                        )
                        # Notify Analysts
                        create_notification(
                            recipient_email="analyst@gmail.com",
                            title="Student Academic Risk Flagged",
                            message=f"Student {email} predicted at risk with {round(predicted_grade, 1)}% projected grade.",
                            alert_type="warning",
                            role="analyst"
                        )
                        alerts_generated += 1
            except Exception as scan_err:
                print(f"Scan error for {email}: {scan_err}")

    return alerts_generated

# ==========================================
# 3. NOTIFICATION & ALERT ROUTES
# ==========================================
@app.route("/notifications")
def view_notifications():
    if "user" not in session:
        return redirect("/login")

    user_email = session.get("user")
    user_role = session.get("role")

    # Fetch alerts for specific email or role broadcast
    user_notifications = list(notifications.find({
        "$or": [
            {"recipient": user_email},
            {"recipient": "all"},
            {"role": user_role}
        ]
    }).sort("created_at", -1))

    return render_template("notifications.html", alerts=user_notifications)


@app.route("/notifications/mark_read/<id>")
def mark_notification_read(id):
    if "user" not in session:
        return redirect("/login")
    notifications.update_one({"_id": ObjectId(id)}, {"$set": {"read": True}})
    return redirect("/notifications")


@app.route("/notifications/mark_all_read")
def mark_all_notifications_read():
    if "user" not in session:
        return redirect("/login")
    user_email = session.get("user")
    user_role = session.get("role")

    notifications.update_many({
        "$or": [{"recipient": user_email}, {"role": user_role}]
    }, {"$set": {"read": True}})
    return redirect("/notifications")


@app.route("/api/unread_notifications_count")
def unread_notifications_count():
    """Real-time polling endpoint for frontend navbar badge."""
    if "user" not in session:
        return {"count": 0}
    user_email = session.get("user")
    user_role = session.get("role")

    count = notifications.count_documents({
        "read": False,
        "$or": [
            {"recipient": user_email},
            {"recipient": "all"},
            {"role": user_role}
        ]
    })
    return {"count": count}


@app.route("/analyst/configure_alerts", methods=["POST"])
def configure_alerts():
    """Allows Analysts/Admins to update alert trigger thresholds."""
    if session.get("role") not in ["analyst", "admin"]:
        return redirect("/login")

    att_thresh = float(request.form.get("attendance_threshold", 75))
    grade_thresh = float(request.form.get("grade_threshold", 50))

    alert_settings.update_one(
        {"type": "global_thresholds"},
        {"$set": {
            "attendance_threshold": att_thresh,
            "grade_threshold": grade_thresh,
            "updated_at": datetime.now(timezone.utc)
        }},
        upsert=True
    )
    # Trigger scan with new thresholds
    run_system_academic_scan()
    return redirect(request.referrer or url_for("analyst"))


@app.route("/analyst/run_scan", methods=["POST"])
def manual_scan_route():
    """Manual trigger to evaluate academic anomalies across the database."""
    if session.get("role") not in ["analyst", "admin"]:
        return redirect("/login")
    count = run_system_academic_scan()
    return redirect(request.referrer or url_for("analyst"))

# --- MODEL REFINEMENT & UPDATE ROUTE ---
@app.route("/analyst/retrain", methods=["POST"])
def retrain_models():
    if "user" not in session or session.get("role") != "analyst":
        return redirect("/login")
    
    all_students = list(users.find({"role": "student"}))
    live_data = []
    
    for student in all_students:
        email = student["email"]
        
        subs = list(submissions.find({"student": email, "graded": True}))
        avg_marks = sum(float(s.get("marks", 0)) for s in subs) / len(subs) if subs else 0
        
        att_records = list(attendance_db.find({"student": email}))
        att_pct = (sum(1 for a in att_records if a["status"] == "present") / len(att_records) * 100) if att_records else 0
        
        final_calculated_grade = (avg_marks * 0.7) + (att_pct * 0.3)
        
        live_data.append({
            "attendance_pct": att_pct,
            "assignment_avg": avg_marks,
            "participation_score": 80.0, 
            "final_grade": final_calculated_grade
        })
    
    if len(live_data) < 5:
        return "Not enough live LMS data to retrain models. Wait for more student activity.", 400
        
    df_live = pd.DataFrame(live_data)
    
    X_live = df_live[['attendance_pct', 'assignment_avg', 'participation_score']]
    y_live = df_live['final_grade']
    
    global performance_model
    from sklearn.ensemble import RandomForestRegressor
    perf_model_live = RandomForestRegressor(n_estimators=100, random_state=42)
    perf_model_live.fit(X_live, y_live)
    
    joblib.dump(perf_model_live, 'performance_model.pkl')
    performance_model = perf_model_live
    
    return "Success: Machine Learning models have been successfully refined using the latest LMS data!"

# --- LMS ATTENDANCE ROUTE ---
@app.route("/mark_attendance", methods=["POST"])
def mark_attendance():
    if "user" not in session or session.get("role") != "teacher":
        return redirect("/login")
        
    student_email = request.form.get("student_email")
    batch_id = request.form.get("batch_id")
    status = request.form.get("status") 
    
    attendance_db.insert_one({
        "student": student_email,
        "batch_id": batch_id,
        "date": datetime.now(timezone.utc),
        "status": status
    })

    if status == "absent":
        create_notification(
            recipient_email=student_email,
            title="⚠️ Attendance Marked Absent",
            message=f"You were marked absent on {datetime.now().strftime('%Y-%m-%d')}.",
            alert_type="warning"
        )
    
    return redirect(f"/teacher_batch/{batch_id}")

if __name__ == "__main__":
    app.run(debug=True)