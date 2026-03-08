from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from datetime import timedelta, datetime

app = Flask(__name__)
app.secret_key = "supersecretkey"   # Required for session

# ===== SESSION CONFIGURATION FOR CONCURRENT ACCESS =====
# Each user gets their own encrypted session cookie
# Multiple users/admins can access simultaneously from different browsers
# Sessions persist even if other users login
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
app.config['SESSION_COOKIE_SECURE'] = False  # False for local testing, True for production
app.config['SESSION_COOKIE_HTTPONLY'] = True  # JavaScript can't access
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection
# ========================================================

# -------------------------------
# Dummy Users (For Demo Purpose)
# -------------------------------
users = {
    "admin": {"password": "admin123", "email": "admin@community.com", "role": "admin"},
    "john": {"password": "john123", "email": "john@gmail.com", "role": "user"},
    "sarah": {"password": "sarah123", "email": "sarah@gmail.com", "role": "user"},
    "mike": {"password": "mike123", "email": "mike@gmail.com", "role": "user"},
    "emma": {"password": "emma123", "email": "emma@gmail.com", "role": "user"},
    "david": {"password": "david123", "email": "david@gmail.com", "role": "user"}
}

# Email to username mapping for user login
email_to_username = {
    "john@gmail.com": "john",
    "sarah@gmail.com": "sarah",
    "mike@gmail.com": "mike",
    "emma@gmail.com": "emma",
    "david@gmail.com": "david"
}

# Workers Data (Assigned to specific problem categories)
workers = {
    "worker1": {
        "name": "John Worker",
        "phone": "+1-555-0101",
        "email": "john.worker@community.com",
        "password": "worker123",
        "role": "worker",
        "categories": [
            "Pothole",
            "Broken road",
            "Infrastructure",
            "Garbage",
            "Overflowing dustbins",
            "Public toilets not clean"
        ]
    },
    "worker2": {
        "name": "Sarah Maintenance",
        "phone": "+1-555-0102",
        "email": "sarah.maint@community.com",
        "password": "worker123",
        "role": "worker",
        "categories": [
            "Streetlight",
            "Power",
            "Water",
            "Water leakage in pipelines",
            "No water supply",
            "Loose electric wires",
            "Broken CCTV cameras"
        ]
    },
    "worker3": {
        "name": "Mike Repair",
        "phone": "+1-555-0103",
        "email": "mike.repair@community.com",
        "password": "worker123",
        "role": "worker",
        "categories": [
            "Water",
            "Power",
            "Infrastructure",
            "Drainage blockage",
            "Water leakage in pipelines",
            "No water supply"
        ]
    },
    "worker4": {
        "name": "Emma Cleanup",
        "phone": "+1-555-0104",
        "email": "emma.cleanup@community.com",
        "password": "worker123",
        "role": "worker",
        "categories": [
            "Garbage",
            "Overflowing dustbins",
            "Pothole",
            "Streetlight",
            "Public toilets not clean",
            "Mosquito breeding areas"
        ]
    },
    "worker5": {
        "name": "Ravi Electricals",
        "phone": "+1-555-0105",
        "email": "ravi.electricals@community.com",
        "password": "worker123",
        "role": "worker",
        "categories": [
            "Loose electric wires",
            "Broken CCTV cameras",
            "Streetlight",
            "Power"
        ]
    },
    "worker6": {
        "name": "Neha Sanitation",
        "phone": "+1-555-0106",
        "email": "neha.sanitation@community.com",
        "password": "worker123",
        "role": "worker",
        "categories": [
            "Overflowing dustbins",
            "Public toilets not clean",
            "Mosquito breeding areas",
            "Drainage blockage"
        ]
    }
}

# Priority assignment based on category
def get_default_priority(category):
    """Auto-assign priority based on complaint category"""
    priority_map = {
        "Pothole": "Medium",
        "Garbage": "Low",
        "Streetlight": "Medium",
        "Infrastructure": "High",
        "Water": "High",
        "Power": "Emergency",
        "Broken road": "High",
        "Overflowing dustbins": "Medium",
        "Water leakage in pipelines": "High",
        "No water supply": "Emergency",
        "Drainage blockage": "High",
        "Broken CCTV cameras": "Medium",
        "Loose electric wires": "Emergency",
        "Public toilets not clean": "Medium",
        "Mosquito breeding areas": "Emergency"
    }
    return priority_map.get(category, "Low")

# -------------------------------
# In-Memory Storage (Temporary)
# -------------------------------
complaints = []

def get_complaint_date(complaint):
    """Extract date from complaint's submitted_at timestamp"""
    submitted_at = complaint.get("submitted_at", "")
    return submitted_at.split(" ")[0] if submitted_at else ""

def find_duplicate_complaint(category, location, date):
    """Check if a complaint with same category, location, and date exists"""
    for complaint in complaints:
        if (complaint["category"] == category and 
            complaint["location"] == location and 
            get_complaint_date(complaint) == date):
            return complaint
    return None


# Notifications and Worker Assignments
# -----------------------------------
notifications = []  # Stores all notifications for all users
worker_status_updates = {}  # Stores worker status updates for complaints


def create_notification(user_type, username, title, message, complaint_id=None, data=None):
    """Create a notification for a user"""
    notification = {
        "id": len(notifications) + 1,
        "user_type": user_type,  # "worker", "admin", "user"
        "username": username,
        "title": title,
        "message": message,
        "complaint_id": complaint_id,
        "data": data or {},
        "read": False,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    notifications.append(notification)
    return notification


# Home Page
# -------------------------------
@app.route('/')
def home_page():
    return render_template("home.html")


# -------------------------------
# Admin Login Page
# -------------------------------
@app.route('/admin-login')
def admin_login_page():
    return render_template("admin_login.html")


# -------------------------------
# User Login Page
# -------------------------------
@app.route('/user-login')
def user_login_page():
    return render_template("user_login.html")


# Worker Login Page
# -------------------------------
@app.route('/worker-login')
def worker_login_page():
    return render_template("worker_login.html")


# -------------------------------
# Handle Login
# -------------------------------
@app.route('/login', methods=['POST'])
def login():
    email_or_username = request.form.get("email_or_username")
    password = request.form.get("password")
    login_type = request.form.get("login_type")  # "admin", "user", or "worker"

    username = None
    
    if login_type == "user":
        # User login with email or username
        if email_or_username in email_to_username:
            username = email_to_username[email_or_username]
        elif email_or_username in users and users[email_or_username]["role"] == "user":
            username = email_or_username
    elif login_type == "worker":
        # Worker login with username
        if email_or_username in workers:
            username = email_or_username
    else:
        # Admin login with username
        username = email_or_username
    
    # Check users dictionary for user/admin
    if username and username in users and users[username]["password"] == password:
        session.permanent = True
        session["username"] = username
        session["role"] = users[username]["role"]
        
        if users[username]["role"] == "admin":
            return redirect(url_for("admin_dashboard"))
        else:
            return redirect(url_for("user_dashboard"))
    # Check workers dictionary for worker
    elif username and login_type == "worker" and username in workers and workers[username]["password"] == password:
        session.permanent = True
        session["username"] = username
        session["role"] = "worker"
        return redirect(url_for("worker_dashboard"))
    else:
        return "Invalid credentials. Please try again."


# -------------------------------
# Admin Dashboard
# -------------------------------
@app.route('/admin-dashboard')
def admin_dashboard():
    if "username" not in session:
        return redirect(url_for("admin_login_page"))
    
    # Allow admin to access their dashboard
    if session.get("role") == "admin":
        return render_template("dashboard.html", username=session["username"])
    else:
        # If role is not admin but username exists, they're a regular user
        if session.get("role") == "user":
            return redirect(url_for("user_dashboard"))
        return render_template("dashboard.html", username=session["username"])


# Admin Workers Dashboard
# -------------------------------
@app.route('/admin-workers')
def admin_workers():
    if "username" not in session:
        return redirect(url_for("admin_login_page"))
    
    if session.get("role") != "admin":
        return redirect(url_for("admin_login_page"))
    
    return render_template("admin_workers.html", username=session["username"])


@app.route('/admin-users')
def admin_users():
    if "username" not in session:
        return redirect(url_for("admin_login_page"))
    
    if session.get("role") != "admin":
        return redirect(url_for("admin_login_page"))

    users_list = []
    for username, info in users.items():
        # Show only regular users (not admin) in this dashboard
        if info.get("role") == "user":
            users_list.append({
                "username": username,
                "email": info.get("email", ""),
                "password": info.get("password", "")
            })

    # Sort by username for stable display
    users_list.sort(key=lambda u: u["username"])

    return render_template(
        "admin_users.html",
        username=session["username"],
        users_list=users_list,
        error=None,
        success=None
    )


@app.route('/admin-users/add', methods=['POST'])
def admin_add_user():
    if "username" not in session:
        return redirect(url_for("admin_login_page"))
    
    if session.get("role") != "admin":
        return redirect(url_for("admin_login_page"))

    username = (request.form.get("username") or "").strip()
    email = (request.form.get("email") or "").strip()
    password = (request.form.get("password") or "").strip()

    error = None
    success = None

    if not username or not email or not password:
        error = "All fields are required."
    elif username in users:
        error = "Username already exists."
    elif email in email_to_username:
        error = "Email already exists."
    else:
        users[username] = {
            "password": password,
            "email": email,
            "role": "user"
        }
        email_to_username[email] = username
        success = "User added successfully."

    users_list = []
    for u_name, info in users.items():
        if info.get("role") == "user":
            users_list.append({
                "username": u_name,
                "email": info.get("email", ""),
                "password": info.get("password", "")
            })
    users_list.sort(key=lambda u: u["username"])

    return render_template(
        "admin_users.html",
        username=session["username"],
        users_list=users_list,
        error=error,
        success=success
    )


@app.route('/admin-profile', methods=['GET', 'POST'])
def admin_profile():
    if "username" not in session:
        return redirect(url_for("admin_login_page"))
    
    if session.get("role") != "admin":
        return redirect(url_for("admin_login_page"))

    error = None
    success = None

    admin_info = users.get("admin", {})

    if request.method == "POST":
        email = (request.form.get("email") or "").strip()
        password = (request.form.get("password") or "").strip()

        if not email:
            error = "Email cannot be empty."
        else:
            # Update email
            # Remove old mapping if email changed
            old_email = admin_info.get("email")
            if old_email and old_email in email_to_username and email_to_username[old_email] == "admin":
                del email_to_username[old_email]

            admin_info["email"] = email
            email_to_username[email] = "admin"

            # Update password only if provided
            if password:
                admin_info["password"] = password

            users["admin"] = admin_info
            success = "Admin profile updated successfully."

    admin_email = admin_info.get("email", "")

    return render_template(
        "admin_profile.html",
        username=session["username"],
        admin_username="admin",
        admin_email=admin_email,
        error=error,
        success=success
    )


# -------------------------------
# User Dashboard
# -------------------------------
@app.route('/user-dashboard')
def user_dashboard():
    if "username" not in session:
        return redirect(url_for("user_login_page"))
    
    # Allow users to access their dashboard
    if session.get("role") == "user":
        return render_template("index.html", username=session["username"])
    else:
        # If role is not user but username exists, still allow the view
        # but only if they're not admin
        if session.get("role") == "admin":
            return redirect(url_for("admin_dashboard"))
        return render_template("index.html", username=session["username"])


# Worker Dashboard
# -------------------------------
@app.route('/worker-dashboard')
def worker_dashboard():
    if "username" not in session:
        return redirect(url_for("home_page"))
    
    if session.get("role") != "worker":
        return redirect(url_for("home_page"))
    
    worker_info = workers.get(session["username"], {})
    return render_template("worker_dashboard.html", username=session["username"], worker_info=worker_info)


# -------------------------------
# Home Route (Role Based - For Backward Compatibility)
# -------------------------------
@app.route('/home')
def home():
    if "username" not in session:
        return redirect(url_for("home_page"))

    if session["role"] == "admin":
        return redirect(url_for("admin_dashboard"))
    else:
        return redirect(url_for("user_dashboard"))


# -------------------------------
# Logout
# -------------------------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for("home_page"))


# -------------------------------
# Submit Complaint (User Only)
# -------------------------------
@app.route('/submit', methods=['POST'])
def submit_complaint():
    if "username" not in session:
        return jsonify({"message": "Unauthorized"}), 401

    data = request.json
    category = data.get("category")
    location = data.get("location")
    submitted_date = datetime.now().strftime("%Y-%m-%d")

    # Check for duplicate complaint (same category, location, and date)
    duplicate = find_duplicate_complaint(category, location, submitted_date)
    if duplicate:
        return jsonify({
            "message": "Similar complaint already exists.",
            "suggestion": "Would you like to support it instead?",
            "existing_complaint_id": duplicate["id"],
            "is_duplicate": True
        }), 409  # 409 Conflict status code

    complaint = {
        "id": len(complaints) + 1,
        "user": session["username"],
        "category": category,
        "description": data.get("description"),
        "location": location,
        "image": data.get("image"),
        "status": "Pending",
        "priority": get_default_priority(category),
        "submitted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "support_count": 0,
        "supporters": [],
        "rating": None,
        "feedback": "",
        "assigned_worker": None,
        "worker_updates": []
    }

    complaints.append(complaint)
    
    # Create notification for admin
    create_notification(
        "admin", 
        "admin",
        f"New {category} Complaint",
        f"New complaint submitted at {complaint['location']}",
        complaint["id"]
    )

    return jsonify({"message": "Complaint submitted successfully"})


# -------------------------------
# Get All Complaints
# -------------------------------
@app.route('/complaints', methods=['GET'])
def get_complaints():
    if "username" not in session:
        return jsonify({"message": "Unauthorized"}), 401
    
    if session.get("role") != "admin":
        return jsonify({"message": "Access denied - Admin only"}), 403

    return jsonify(complaints)


# Support Complaint (User Support/Upvote)
# -------------------------------
@app.route('/support/<int:complaint_id>', methods=['POST'])
def support_complaint(complaint_id):
    if "username" not in session:
        return jsonify({"message": "Unauthorized"}), 401

    username = session["username"]

    for complaint in complaints:
        if complaint["id"] == complaint_id:
            # Initialize supporters list if missing (backward compatibility)
            supporters = complaint.get("supporters")
            if supporters is None:
                supporters = []
                complaint["supporters"] = supporters

            # If user already supported, do not increment again
            if username in supporters:
                return jsonify({
                    "message": "You have already supported this complaint.",
                    "support_count": complaint.get("support_count", len(supporters))
                })

            supporters.append(username)
            # Keep support_count in sync with supporters length
            complaint["support_count"] = len(supporters)

            return jsonify({
                "message": "Thank you for supporting this complaint!",
                "support_count": complaint["support_count"]
            })

    return jsonify({"message": "Complaint not found"}), 404


# Get All Workers (Admin Only)
# -------------------------------
@app.route('/workers', methods=['GET'])
def get_all_workers():
    if "username" not in session:
        return jsonify({"message": "Unauthorized"}), 401
    
    if session.get("role") != "admin":
        return jsonify({"message": "Access denied - Admin only"}), 403

    workers_list = []
    for username, worker_info in workers.items():
        workers_list.append({
            "username": username,
            "name": worker_info["name"],
            "phone": worker_info["phone"],
            "email": worker_info["email"],
            "categories": worker_info["categories"]
        })
    
    return jsonify(workers_list)


# Get Workers by Category (Admin Only)
# -------------------------------
@app.route('/workers/category/<category>', methods=['GET'])
def get_workers_by_category(category):
    if "username" not in session:
        return jsonify({"message": "Unauthorized"}), 401
    
    if session.get("role") != "admin":
        return jsonify({"message": "Access denied - Admin only"}), 403

    workers_list = []
    for username, worker_info in workers.items():
        if category in worker_info.get("categories", []):
            workers_list.append({
                "username": username,
                "name": worker_info["name"],
                "phone": worker_info["phone"],
                "email": worker_info["email"],
                "categories": worker_info["categories"]
            })
    
    return jsonify(workers_list)


# -------------------------------
# Get User's Own Complaints
# -------------------------------
@app.route('/my-complaints', methods=['GET'])
def get_user_complaints():
    if "username" not in session:
        return jsonify({"message": "Unauthorized"}), 401

    user_complaints = [c for c in complaints if c["user"] == session["username"]]
    return jsonify(user_complaints)


# -------------------------------
# Get Public Complaints (No Personal Details)
# -------------------------------
@app.route('/public-complaints', methods=['GET'])
def get_public_complaints():
    """Return public complaints without personal details (username)"""
    public_complaints = []
    for c in complaints:
        public_complaint = {
            "id": c["id"],
            "category": c["category"],
            "location": c["location"],
            "status": c["status"],
            "submitted_at": c.get("submitted_at", "N/A"),
            "priority": c.get("priority", "Low"),
            "support_count": c.get("support_count", 0),
            "rating": c.get("rating"),
            "feedback": c.get("feedback", "")
        }
        public_complaints.append(public_complaint)
    return jsonify(public_complaints)


@app.route('/complaint/<int:complaint_id>/feedback', methods=['POST'])
def submit_feedback(complaint_id):
    """Allow complaint owner to rate and leave feedback after resolution."""
    if "username" not in session:
        return jsonify({"message": "Unauthorized"}), 401

    username = session["username"]
    data = request.json or {}
    rating = data.get("rating")
    feedback = (data.get("feedback") or "").strip()

    # Basic validation
    try:
        rating = int(rating)
    except (TypeError, ValueError):
        return jsonify({"message": "Rating must be an integer between 1 and 5"}), 400

    if rating < 1 or rating > 5:
        return jsonify({"message": "Rating must be between 1 and 5"}), 400

    for complaint in complaints:
        if complaint["id"] == complaint_id:
            # Only the original reporting user can rate, and only after resolution
            if complaint["user"] != username:
                return jsonify({"message": "You can only rate your own complaints"}), 403
            if complaint["status"] != "Resolved":
                return jsonify({"message": "You can rate only after the complaint is resolved"}), 400

            complaint["rating"] = rating
            complaint["feedback"] = feedback

            # Notify admin
            create_notification(
                "admin",
                "admin",
                f"New Feedback: Complaint #{complaint_id}",
                f"User {username} rated complaint #{complaint_id} with {rating} stars.",
                complaint_id,
                {
                    "rating": rating,
                    "feedback": feedback,
                    "category": complaint["category"],
                    "location": complaint["location"]
                }
            )

            # Notify assigned worker if any
            if complaint.get("assigned_worker"):
                create_notification(
                    "worker",
                    complaint["assigned_worker"],
                    f"User Feedback: Complaint #{complaint_id}",
                    f"User {username} left feedback and rated this complaint {rating} stars.",
                    complaint_id,
                    {
                        "rating": rating,
                        "feedback": feedback,
                        "category": complaint["category"],
                        "location": complaint["location"]
                    }
                )

            return jsonify({
                "message": "Thank you for your feedback!",
                "rating": rating,
                "feedback": feedback
            })

    return jsonify({"message": "Complaint not found"}), 404


@app.route('/worker-complaints', methods=['GET'])
def get_worker_complaints_for_dashboard():
    """Get complaints assigned to the currently logged-in worker"""
    if "username" not in session:
        return jsonify({"message": "Unauthorized"}), 401

    if session.get("role") != "worker":
        return jsonify({"message": "Access denied - Worker only"}), 403

    worker_username = session["username"]
    worker_complaints = [c for c in complaints if c.get("assigned_worker") == worker_username]
    return jsonify(worker_complaints)


# Public view as HTML page
@app.route('/complaints-dashboard')
def complaints_dashboard():
    username = session.get("username") if "username" in session else None
    return render_template("public_complaints.html", username=username)


# -------------------------------
# Update Complaint Status (Admin Only)
# -------------------------------
@app.route('/update/<int:complaint_id>', methods=['PUT'])
def update_status(complaint_id):

    if session.get("role") != "admin":
        return jsonify({"message": "Access denied"}), 403

    data = request.json
    new_status = data.get("status")
    
    # Validate status
    valid_statuses = ["Pending", "In Progress", "Resolved"]
    if new_status not in valid_statuses:
        return jsonify({"message": "Invalid status"}), 400

    for complaint in complaints:
        if complaint["id"] == complaint_id:
            complaint["status"] = new_status
            return jsonify({"message": f"Status updated to {new_status}"})

    return jsonify({"message": "Complaint not found"}), 404


# -------------------------------
# Update Complaint Priority (Admin Only)
# -------------------------------
@app.route('/priority/<int:complaint_id>', methods=['PUT'])
def update_priority(complaint_id):

    if "username" not in session:
        return jsonify({"message": "Unauthorized"}), 401
        
    if session.get("role") != "admin":
        return jsonify({"message": "Access denied"}), 403

    data = request.json
    new_priority = data.get("priority")
    
    # Validate priority
    valid_priorities = ["Low", "Medium", "High", "Emergency"]
    if new_priority not in valid_priorities:
        return jsonify({"message": "Invalid priority"}), 400

    for complaint in complaints:
        if complaint["id"] == complaint_id:
            complaint["priority"] = new_priority
            return jsonify({"message": f"Priority updated to {new_priority}"})

    return jsonify({"message": "Complaint not found"}), 404


# Assign Complaint to Worker (Admin Only)
# -------------------------------
@app.route('/assign/<int:complaint_id>', methods=['POST'])
def assign_worker(complaint_id):
    if "username" not in session:
        return jsonify({"message": "Unauthorized"}), 401
    
    if session.get("role") != "admin":
        return jsonify({"message": "Access denied"}), 403

    data = request.json
    worker_username = data.get("worker_username")
    
    # Verify worker exists
    if worker_username not in workers:
        return jsonify({"message": "Worker not found"}), 404
    
    # Find complaint and assign
    for complaint in complaints:
        if complaint["id"] == complaint_id:
            complaint["assigned_worker"] = worker_username
            worker_info = workers[worker_username]
            
            # Create notification for worker
            create_notification(
                "worker",
                worker_username,
                f"New Assignment: {complaint['category']}",
                f"You have been assigned a new complaint at {complaint['location']}",
                complaint_id,
                {
                    "category": complaint["category"],
                    "location": complaint["location"],
                    "description": complaint["description"],
                    "priority": complaint["priority"]
                }
            )
            
            return jsonify({
                "message": f"Complaint assigned to {worker_info['name']}",
                "assigned_worker": worker_username,
                "worker_name": worker_info['name'],
                "worker_phone": worker_info['phone'],
                "worker_email": worker_info['email']
            })
    
    return jsonify({"message": "Complaint not found"}), 404


# Worker Update Complaint Status (Worker Only)
# -------------------------------
@app.route('/worker-update/<int:complaint_id>', methods=['POST'])
def worker_update_complaint(complaint_id):
    if "username" not in session:
        return jsonify({"message": "Unauthorized"}), 401
    
    if session.get("role") != "worker":
        return jsonify({"message": "Access denied"}), 403

    data = request.json
    status_update = data.get("status_update")
    current_status = data.get("status")  # Pending, In Progress, Resolved
    
    # Validate status
    valid_statuses = ["Pending", "In Progress", "Resolved"]
    if current_status and current_status not in valid_statuses:
        return jsonify({"message": "Invalid status"}), 400

    for complaint in complaints:
        if complaint["id"] == complaint_id:
            # Verify this worker is assigned to this complaint
            if complaint["assigned_worker"] != session["username"]:
                return jsonify({"message": "You are not assigned to this complaint"}), 403

            # Add worker update
            worker_update = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "worker": session["username"],
                "update": status_update,
                "status": current_status
            }
            complaint["worker_updates"].append(worker_update)
            
            # Update complaint status directly (worker has authorization)
            if current_status:
                complaint["status"] = current_status
            
            # Create notification for user about status change
            create_notification(
                "user",
                complaint["user"],
                f"Status Update: Your Complaint #{complaint_id}",
                f"Your complaint status has been updated to {current_status} by worker {session['username']}",
                complaint_id,
                {
                    "status": current_status,
                    "worker": session["username"],
                    "update": status_update
                }
            )
            
            # Create notification for admin about worker update
            create_notification(
                "admin",
                "admin",
                f"Worker Update: Complaint #{complaint_id}",
                f"Worker {session['username']} updated complaint status to {current_status}",
                complaint_id,
                {
                    "worker": session["username"],
                    "update": status_update,
                    "status": current_status
                }
            )
            
            return jsonify({
                "message": f"Status updated to {current_status}",
                "status": current_status,
                "update_id": len(complaint["worker_updates"]),
                "user_notified": True
            })
    
    return jsonify({"message": "Complaint not found"}), 404


# Worker Notify Admin Endpoint
# =============================
@app.route('/worker-notify-admin/<int:complaint_id>', methods=['POST'])
def worker_notify_admin(complaint_id):
    if "username" not in session:
        return jsonify({"message": "Unauthorized"}), 401
    
    if session.get("role") != "worker":
        return jsonify({"message": "Access denied"}), 403

    data = request.json
    message = data.get("message", "").strip()
    
    if not message:
        return jsonify({"message": "Message cannot be empty"}), 400

    for complaint in complaints:
        if complaint["id"] == complaint_id:
            # Verify this worker is assigned to this complaint
            if complaint["assigned_worker"] != session["username"]:
                return jsonify({"message": "You are not assigned to this complaint"}), 403

            # Create notification for admin
            create_notification(
                "admin",
                "admin",
                f"Message from Worker: Complaint #{complaint_id}",
                f"Worker {session['username']} sent: {message}",
                complaint_id,
                {
                    "worker": session["username"],
                    "message": message,
                    "complaint_category": complaint["category"],
                    "complaint_status": complaint["status"]
                }
            )
            
            return jsonify({
                "message": "Notification sent to admin",
                "success": True
            }), 200
    
    return jsonify({"message": "Complaint not found"}), 404


# Get Notifications (For any logged-in user)
# -------------------------------
@app.route('/notifications', methods=['GET'])
def get_notifications():
    if "username" not in session:
        return jsonify({"message": "Unauthorized"}), 401

    user_notifications = [
        n for n in notifications 
        if n["username"] == session["username"] and n["user_type"] == session.get("role")
    ]
    
    return jsonify(user_notifications)


# Mark Notification as Read
# -------------------------------
@app.route('/notifications/<int:notification_id>/read', methods=['POST'])
def mark_notification_read(notification_id):
    if "username" not in session:
        return jsonify({"message": "Unauthorized"}), 401

    for notification in notifications:
        if notification["id"] == notification_id and notification["username"] == session["username"]:
            notification["read"] = True
            return jsonify({"message": "Notification marked as read"})
    
    return jsonify({"message": "Notification not found"}), 404


# Get Worker Updates for Complaint (Admin Only)
# -------------------------------
@app.route('/complaint/<int:complaint_id>/worker-updates', methods=['GET'])
def get_worker_updates(complaint_id):
    if "username" not in session:
        return jsonify({"message": "Unauthorized"}), 401
    
    if session.get("role") != "admin":
        return jsonify({"message": "Access denied"}), 403

    for complaint in complaints:
        if complaint["id"] == complaint_id:
            return jsonify({
                "complaint_id": complaint_id,
                "assigned_worker": complaint["assigned_worker"],
                "worker_updates": complaint["worker_updates"],
                "current_status": complaint["status"]
            })
    
    return jsonify({"message": "Complaint not found"}), 404


# Get Complaint Details (For assigned worker)
# -------------------------------
@app.route('/complaint/<int:complaint_id>', methods=['GET'])
def get_complaint_detail(complaint_id):
    if "username" not in session:
        return jsonify({"message": "Unauthorized"}), 401

    for complaint in complaints:
        if complaint["id"] == complaint_id:
            # Allow worker assigned to this complaint, admin, and the complaint creator
            if (session.get("role") == "worker" and complaint["assigned_worker"] != session["username"]) and \
               (session.get("role") != "admin" and complaint["user"] != session["username"]):
                return jsonify({"message": "Access denied"}), 403
            
            return jsonify(complaint)
    
    return jsonify({"message": "Complaint not found"}), 404


# Apply Worker's Status Update (Admin Only)
# -------------------------------
@app.route('/apply-worker-status/<int:complaint_id>', methods=['POST'])
def apply_worker_status(complaint_id):
    if "username" not in session:
        return jsonify({"message": "Unauthorized"}), 401
    
    if session.get("role") != "admin":
        return jsonify({"message": "Access denied"}), 403

    for complaint in complaints:
        if complaint["id"] == complaint_id:
            if not complaint["worker_updates"]:
                return jsonify({"message": "No worker updates to apply"}), 400
            
            # Get the latest worker update
            latest_update = complaint["worker_updates"][-1]
            new_status = latest_update["status"]
            
            if not new_status:
                return jsonify({"message": "No status in latest update"}), 400
            
            # Update complaint status
            complaint["status"] = new_status
            
            # Create notification for the user about status update
            create_notification(
                "user",
                complaint["user"],
                f"Status Update: Your Complaint",
                f"Your complaint #{complaint_id} status has been updated to {new_status}",
                complaint_id,
                {
                    "status": new_status,
                    "worker_update": latest_update["update"]
                }
            )
            
            return jsonify({
                "message": f"Complaint status updated to {new_status}",
                "status": new_status
            })
    
    return jsonify({"message": "Complaint not found"}), 404


# Run Server
# -------------------------------
if __name__ == '__main__':
    app.run(debug=True)