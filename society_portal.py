from datetime import date, datetime
import os
from flask import Flask, flash, redirect, render_template_string, request, session, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = "cab_pro_secret_key"

# ---------------- SUPABASE POSTGRESQL CONFIGURATION ---------------- #
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres.fjfffxaxyrgejulcyag:YOUR_PASSWORD@aws-0-ap-south-1.pooler.supabase.com:6543/postgres",
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

CAR_FOLDER = "static/cars"
os.makedirs(CAR_FOLDER, exist_ok=True)


# ---------------- DATABASE MODELS ---------------- #
class Car(db.Model):
    __tablename__ = "cars"
    id = db.Column(db.Integer, primary_key=True)
    car_name = db.Column(db.String(100), nullable=False)
    car_type = db.Column(db.String(50), nullable=False)
    vehicle_number = db.Column(db.String(50), unique=True, nullable=False)
    owner_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    rate_per_day = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    driver_available = db.Column(db.String(50), default="Yes (With Driver)")
    engagement_type = db.Column(db.String(50), default="For Hire (Daily)")
    status = db.Column(db.String(50), default="Available")
    admin_status = db.Column(db.String(50), default="Pending")
    photo_path = db.Column(db.String(255))


class HireRequest(db.Model):
    __tablename__ = "hire_requests"
    id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(100), nullable=False)
    user_phone = db.Column(db.String(20), nullable=False)
    car_type_needed = db.Column(db.String(50), nullable=False)
    driver_needed = db.Column(db.String(50), default="Yes")
    pickup_location = db.Column(db.String(150), nullable=False)
    drop_location = db.Column(db.String(150), nullable=False)
    travel_date = db.Column(db.String(50), nullable=False)
    days_count = db.Column(db.Integer, nullable=False)
    notes = db.Column(db.Text)
    request_date = db.Column(db.String(50), nullable=False)
    request_status = db.Column(db.String(50), default="Pending")
    assigned_car_id = db.Column(db.Integer, db.ForeignKey("cars.id"), nullable=True)


with app.app_context():
    db.create_all()


def clean_phone_for_wa(phone):
    digits = "".join(filter(str.isdigit, str(phone)))
    if len(digits) == 10:
        return "91" + digits
    return digits


app.jinja_env.globals.update(clean_phone_for_wa=clean_phone_for_wa)

# ---------------- HTML TEMPLATES ---------------- #

BASE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CAB PRO - Professional Car Hire &amp; Dispatch Portal</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root { --primary: #1e3d59; --accent: #ff6e40; }
        body { background-color: #f5f7fa; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #333; }
        .navbar { background: linear-gradient(135deg, #1e3d59 0%, #17b978 100%); }
        .hero { background: linear-gradient(rgba(30,61,89,0.85), rgba(23,185,120,0.85)), url('https://images.unsplash.com/photo-1449965408869-eaa3f722e40d?auto=format&fit=crop&w=1200&q=80') center/cover; color: white; padding: 60px 0; }
        .card-custom { border: none; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); background: white; transition: 0.2s; }
        .card-custom:hover { transform: translateY(-3px); box-shadow: 0 8px 25px rgba(0,0,0,0.1); }
        .btn-wa { background-color: #25D366; color: white; border: none; }
        .btn-wa:hover { background-color: #1ebe5d; color: white; }
        .service-marquee-bar {
            background: linear-gradient(90deg, #1e3d59 0%, #0f172a 50%, #1e3d59 100%);
            color: #ffffff;
            border-radius: 10px;
            padding: 10px 14px;
            border-left: 5px solid #ffc107;
            box-shadow: 0 4px 12px rgba(0,0,0,0.12);
        }
        .marquee-badge {
            background: #ffc107;
            color: #111827;
            font-weight: 800;
            font-size: 0.78rem;
            padding: 4px 10px;
            border-radius: 6px;
            white-space: nowrap;
        }
        .filter-btn.active {
            background-color: #1e3d59 !important;
            color: #ffffff !important;
            border-color: #1e3d59 !important;
        }
    </style>
</head>
<body>
<nav class="navbar navbar-expand-lg navbar-dark shadow-sm sticky-top">
    <div class="container">
        <a class="navbar-brand fw-bold" href="/"><i class="fa-solid fa-car-side text-warning me-2"></i>CAB PRO</a>
        <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navMenu">
            <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="navMenu">
            <ul class="navbar-nav ms-auto gap-2">
                <li class="nav-item"><a class="nav-link text-white fw-semibold" href="/">Book Car</a></li>
                <li class="nav-item"><a class="nav-link text-warning fw-bold" href="/fleet">Approved Fleet</a></li>
                <li class="nav-item"><a class="nav-link text-info fw-bold" href="/owner_login"><i class="fa-solid fa-car-rear"></i> Owner Portal</a></li>
                <li class="nav-item"><a class="nav-link text-white fw-semibold" href="/admin_login"><i class="fa-solid fa-user-shield"></i> Admin</a></li>
            </ul>
        </div>
    </div>
</nav>

<div class="container mt-3">
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        {% for cat, msg in messages %}
          <div class="alert alert-{{ cat }} alert-dismissible fade show shadow-sm">
            {{ msg }}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
          </div>
        {% endfor %}
      {% endif %}
    {% endwith %}
</div>
"""

BASE_FOOT = """
<footer class="bg-white border-top py-4 mt-5 text-center text-muted">
    <div class="container">
        <p class="mb-1 fw-bold text-dark">CAB PRO - Professional Car Hire &amp; Dispatch Portal</p>
        <small class="d-block mb-1">Contact Admin: <strong>Future Computer</strong>, Below SBI, Birpara</small>
        <small class="text-primary"><i class="fa-solid fa-phone"></i> Mobile: 9733-290-230 / 7001-158-084</small>
    </div>
</footer>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

INDEX_HTML = (
    BASE_HTML
    + """
<div class="hero text-center mb-5">
    <div class="container">
        <h1 class="fw-bold mb-3">CAB PRO - Book Your Ride Professional &amp; Fast</h1>
        <p class="lead mb-4">Send your travel requirements. Admin will instantly assign the best available car!</p>
        <div class="d-flex justify-content-center gap-3 flex-wrap">
            <button class="btn btn-warning btn-lg fw-bold px-4 text-dark shadow" data-bs-toggle="modal" data-bs-target="#requestModal"><i class="fa-solid fa-paper-plane"></i> Request a Car Now</button>
            <button class="btn btn-success btn-lg fw-bold px-4 shadow" data-bs-toggle="modal" data-bs-target="#ownerModal"><i class="fa-solid fa-car"></i> Car Owner? List Your Car</button>
        </div>
    </div>
</div>

<div class="container mb-5">
    <div class="row align-items-center">
        <div class="col-md-6 mb-4 mb-md-0">
            <h2 class="fw-bold text-dark mb-3">System Features</h2>
            <ul class="list-unstyled fs-5 gap-3 d-flex flex-column">
                <li><i class="fa-solid fa-circle-check text-success me-2"></i> <strong>User Booking:</strong> Submit trip requirements easily.</li>
                <li><i class="fa-solid fa-circle-check text-success me-2"></i> <strong>Owner Self-Service:</strong> Owners can log in with their phone number to update car status!</li>
                <li><i class="fa-solid fa-circle-check text-success me-2"></i> <strong>Admin Dispatch:</strong> Seamless trip management and assignment.</li>
            </ul>
        </div>
        <div class="col-md-6 text-center">
            <div class="card-custom p-4 bg-white border-start border-5 border-success text-start">
                <h4 class="fw-bold text-success mb-3"><i class="fa-solid fa-car"></i> Available Fleet Highlights</h4>
                <div class="row g-3">
                    {% for c in cars[:4] %}
                    <div class="col-6">
                        <div class="p-2 border rounded bg-light">
                            <strong>{{ c.car_name }}</strong><br>
                            <small class="text-muted">{{ c.car_type }} &bull; ₹{{ c.rate_per_day }}/day</small><br>
                            <span class="badge bg-{{ 'success' if c.status=='Available' else 'secondary' }}">{{ c.status }}</span>
                        </div>
                    </div>
                    {% else %}
                    <p class="text-muted">No available cars right now.</p>
                    {% endfor %}
                </div>
                <div class="mt-3 text-end">
                    <a href="/fleet" class="btn btn-sm btn-outline-success fw-bold">View Full Fleet &rarr;</a>
                </div>
            </div>
        </div>
    </div>
</div>

<!-- USER REQUEST MODAL -->
<div class="modal fade" id="requestModal" tabindex="-1">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">
            <div class="modal-header bg-warning text-dark">
                <h5 class="modal-title fw-bold"><i class="fa-solid fa-car-side"></i> Car Hire Request Form</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <form method="POST" action="/submit_request">
                <div class="modal-body row g-3">
                    <div class="col-md-6"><label class="form-label fw-semibold">Your Full Name *</label><input type="text" name="user_name" class="form-control" required></div>
                    <div class="col-md-6"><label class="form-label fw-semibold">Mobile / WhatsApp *</label><input type="text" name="user_phone" class="form-control" required></div>
                    <div class="col-md-6">
                        <label class="form-label fw-semibold">Car Type Needed *</label>
                        <select name="car_type_needed" class="form-select" required>
                            <option value="">Select Category</option>
                            <option value="Sedan">Sedan (Dzire / Etios)</option>
                            <option value="SUV">SUV (Scorpio / Innova)</option>
                            <option value="Toto">Toto / E-Rickshaw</option>
                            <option value="Pickup">Pickup / Goods Carrier</option>
                            <option value="Traveler">Traveler / Bus</option>
                        </select>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label fw-semibold">Driver Preference *</label>
                        <select name="driver_needed" class="form-select" required>
                            <option value="Yes (With Driver)">With Driver</option>
                            <option value="No (Self Drive)">Without Driver</option>
                        </select>
                    </div>
                    <div class="col-md-6"><label class="form-label fw-semibold">Duration (Days) *</label><input type="number" name="days_count" class="form-control" min="1" required></div>
                    <div class="col-md-6"><label class="form-label fw-semibold">Travel Date *</label><input type="date" name="travel_date" class="form-control" required></div>
                    <div class="col-md-6"><label class="form-label fw-semibold">Pickup Location *</label><input type="text" name="pickup_location" class="form-control" required></div>
                    <div class="col-md-6"><label class="form-label fw-semibold">Drop Location *</label><input type="text" name="drop_location" class="form-control" required></div>
                    <div class="col-md-12"><label class="form-label fw-semibold">Notes</label><input type="text" name="notes" class="form-control" placeholder="Extra requirements..."></div>
                </div>
                <div class="modal-footer"><button type="submit" class="btn btn-warning w-100 fw-bold py-2 text-dark">Submit Hire Request</button></div>
            </form>
        </div>
    </div>
</div>

<!-- CAR OWNER LISTING MODAL -->
<div class="modal fade" id="ownerModal" tabindex="-1">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">
            <div class="modal-header bg-success text-white">
                <h5 class="modal-title fw-bold"><i class="fa-solid fa-car"></i> Car Owner Listing Form</h5>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
            </div>
            <form method="POST" action="/submit_car_request" enctype="multipart/form-data">
                <div class="modal-body row g-3">
                    <div class="col-md-6"><label class="form-label fw-semibold">Owner Name *</label><input type="text" name="owner_name" class="form-control" required></div>
                    <div class="col-md-6"><label class="form-label fw-semibold">Owner Phone / WhatsApp (Used for Login) *</label><input type="text" name="phone" class="form-control" required></div>
                    <div class="col-md-6">
                        <label class="form-label fw-semibold">Vehicle Type *</label>
                        <select name="car_type" class="form-select" required>
                            <option value="">Select Type</option>
                            <option value="Sedan">Sedan</option>
                            <option value="SUV">SUV</option>
                            <option value="Toto">Toto</option>
                            <option value="Pickup">Pickup</option>
                            <option value="Traveler">Traveler</option>
                        </select>
                    </div>
                    <div class="col-md-6"><label class="form-label fw-semibold">Car Name / Model *</label><input type="text" name="car_name" class="form-control" placeholder="e.g. Maruti Dzire" required></div>
                    <div class="col-md-6"><label class="form-label fw-semibold">Vehicle Number *</label><input type="text" name="vehicle_number" class="form-control" placeholder="WB-74..." required></div>
                    <div class="col-md-6"><label class="form-label fw-semibold">Location / Stand *</label><input type="text" name="location" class="form-control" required></div>
                    <div class="col-md-6"><label class="form-label fw-semibold">Rate Per Day (₹) *</label><input type="text" name="rate_per_day" class="form-control" required></div>
                    <div class="col-md-6">
                        <label class="form-label fw-semibold">Engagement Type *</label>
                        <select name="engagement_type" class="form-select" required>
                            <option value="For Hire (Daily)">For Hire (Daily / Per Trip)</option>
                            <option value="Monthly Contract">Monthly Contract / Engagement</option>
                        </select>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label fw-semibold">Driver Status *</label>
                        <select name="driver_available" class="form-select" required>
                            <option value="Yes (With Driver)">Driver Available with Car</option>
                            <option value="Car Only">Car Only (Without Driver)</option>
                        </select>
                    </div>
                    <div class="col-md-12"><label class="form-label fw-semibold">Car Photo</label><input type="file" name="photo" class="form-control" accept="image/*"></div>
                </div>
                <div class="modal-footer"><button type="submit" class="btn btn-success w-100 fw-bold py-2">Submit for Approval</button></div>
            </form>
        </div>
    </div>
</div>
"""
    + BASE_FOOT
)

FLEET_HTML = (
    BASE_HTML
    + """
<div class="container my-4">
    <!-- MARQUEE SCROLLING DIRECTLY ABOVE AVAILABLE CAR/TOTO/VAHICLE -->
    <div class="service-marquee-bar d-flex align-items-center gap-3 mb-4">
        <span class="marquee-badge"><i class="fa-solid fa-bullhorn me-1"></i>FUTURE COMPUTER</span>
        <marquee behavior="scroll" direction="left" scrollamount="5" onmouseover="this.stop();" onmouseout="this.start();" class="fw-semibold small mb-0">
            SOCIETY REGISTRATION (CLUB, PRY. SCHOOL, MANDIR, CHURCH, ETC.) &nbsp;&bull;&nbsp;
            GST REGISTRATION &nbsp;&bull;&nbsp;
            DIGITAL SIGNATURE &nbsp;&bull;&nbsp;
            PAN (NEW, MINOR, CORRECTION APPLY) &nbsp;&bull;&nbsp;
            VOTER (NEW / CORRECTION APPLY) &nbsp;&bull;&nbsp;
            RATION CORRECTION &nbsp;&bull;&nbsp;
            PVC PRINT &nbsp;&bull;&nbsp;
            ITR &nbsp;&mdash;&nbsp;
            AT FUTURE COMPUTER, BELOW SBI, BIRPARA (MOB: 9733-290-230 / 7001-158-084)
        </marquee>
    </div>

    <div class="text-center mb-3">
        <h2 class="fw-bold mb-1">Available Car/Toto/Vahicle</h2>
        <p class="text-muted small mb-0">Compact list for fast finding &bull; Filter by vehicle category below</p>
    </div>

    <!-- CATEGORY FILTER BUTTONS -->
    <div class="d-flex flex-wrap justify-content-center gap-2 mb-4" id="categoryFilterBar">
        <button type="button" class="btn btn-outline-dark btn-sm fw-bold px-3 filter-btn active" data-filter="all">All Vehicles</button>
        <button type="button" class="btn btn-outline-primary btn-sm fw-bold px-3 filter-btn" data-filter="toto"><i class="fa-solid fa-bolt me-1"></i>Toto</button>
        <button type="button" class="btn btn-outline-success btn-sm fw-bold px-3 filter-btn" data-filter="4wheeler"><i class="fa-solid fa-car me-1"></i>4 Wheeler</button>
        <button type="button" class="btn btn-outline-warning btn-sm fw-bold px-3 text-dark filter-btn" data-filter="pickup"><i class="fa-solid fa-truck-pickup me-1"></i>Pick Up</button>
        <button type="button" class="btn btn-outline-info btn-sm fw-bold px-3 text-dark filter-btn" data-filter="traveler"><i class="fa-solid fa-van-shuttle me-1"></i>Traveler</button>
        <button type="button" class="btn btn-outline-secondary btn-sm fw-bold px-3 filter-btn" data-filter="bus"><i class="fa-solid fa-bus me-1"></i>Bus</button>
    </div>

    <div class="row g-3" id="fleetList">
        {% for c in cars %}
        {% set t_lower = (c.car_type or '')|lower %}
        {% set n_lower = (c.car_name or '')|lower %}
        {% set combined = t_lower ~ ' ' ~ n_lower %}
        {% if 'toto' in combined or 'rickshaw' in combined or 'e-rickshaw' in combined %}
            {% set cat_key = 'toto' %}
        {% elif 'pickup' in combined or 'pick up' in combined or 'goods' in combined %}
            {% set cat_key = 'pickup' %}
        {% elif 'traveler' in combined or 'traveller' in combined %}
            {% set cat_key = 'traveler' %}
        {% elif 'bus' in combined %}
            {% set cat_key = 'bus' %}
        {% else %}
            {% set cat_key = '4wheeler' %}
        {% endif %}
        <div class="col-md-6 col-lg-4 fleet-item" data-cat="{{ cat_key }}">
            <div class="card-custom p-3 h-100 d-flex flex-column">
                <div class="d-flex justify-content-between align-items-start gap-2 mb-1">
                    <div>
                        <span class="badge bg-dark-subtle text-dark border mb-1">{{ c.car_type }}</span>
                        <h5 class="fw-bold text-dark mb-0">{{ c.car_name }}</h5>
                    </div>
                    <span class="badge bg-{{ 'success' if c.status=='Available' else 'secondary' }}">{{ c.status }}</span>
                </div>
                <div class="small text-muted mb-1"><i class="fa-solid fa-id-card me-1"></i><strong>No:</strong> {{ c.vehicle_number }}</div>
                <div class="small text-muted mb-1"><i class="fa-solid fa-user me-1"></i>{{ c.owner_name }} &bull; <i class="fa-solid fa-location-dot text-danger me-1"></i>{{ c.location }}</div>
                <div class="small text-success fw-bold mb-2">Rate: ₹{{ c.rate_per_day }} / Day</div>
                <div class="mt-auto pt-2 border-top d-flex gap-2">
                    <a href="tel:{{ c.phone }}" class="btn btn-primary btn-sm flex-grow-1"><i class="fa-solid fa-phone"></i> Call</a>
                    <a href="https://wa.me/{{ clean_phone_for_wa(c.phone) }}?text=Hello, I want to book your {{ c.car_name }} ({{ c.vehicle_number }})." target="_blank" class="btn btn-wa btn-sm flex-grow-1"><i class="fa-brands fa-whatsapp"></i> WhatsApp</a>
                </div>
            </div>
        </div>
        {% else %}
        <div class="col-12 text-center py-5 text-muted"><h5>No approved cars in fleet.</h5></div>
        {% endfor %}
    </div>
</div>

<script>
document.addEventListener("DOMContentLoaded", function() {
    const buttons = document.querySelectorAll("#categoryFilterBar .filter-btn");
    const items = document.querySelectorAll("#fleetList .fleet-item");

    buttons.forEach(btn => {
        btn.addEventListener("click", function() {
            buttons.forEach(b => b.classList.remove("active"));
            this.classList.add("active");

            const filter = this.getAttribute("data-filter");
            items.forEach(item => {
                const cat = item.getAttribute("data-cat");
                if (filter === "all" || cat === filter) {
                    item.style.display = "";
                } else {
                    item.style.display = "none";
                }
            });
        });
    });
});
</script>
"""
    + BASE_FOOT
)

OWNER_LOGIN_HTML = (
    BASE_HTML
    + """
<div class="container my-5" style="max-width: 420px;">
    <div class="card-custom p-4">
        <h4 class="text-center fw-bold mb-3"><i class="fa-solid fa-car-rear text-success"></i> Car Owner Portal Login</h4>
        <p class="small text-muted text-center mb-4">Enter your registered mobile number to manage your vehicle status.</p>
        <form method="POST" action="/owner_login">
            <div class="mb-3"><input type="text" name="phone" class="form-control" placeholder="Enter Mobile Number" required></div>
            <button type="submit" class="btn btn-success w-100 fw-bold">Login to Owner Dashboard</button>
        </form>
    </div>
</div>
"""
    + BASE_FOOT
)

OWNER_DASH_HTML = (
    BASE_HTML
    + """
<div class="container my-4" style="max-width: 800px;">
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h3 class="fw-bold text-dark"><i class="fa-solid fa-gauge text-success"></i> Welcome, Owner ({{ owner_phone }})</h3>
        <a href="/logout" class="btn btn-outline-danger btn-sm">Logout</a>
    </div>

    <div class="card-custom p-4">
        <h5 class="fw-bold mb-3">Your Registered Vehicles &amp; Status Control</h5>
        <div class="table-responsive">
            <table class="table table-bordered align-middle text-center">
                <thead class="table-dark"><tr><th>Car Model</th><th>Vehicle No.</th><th>Approval</th><th>Current Status</th><th>Change Status</th></tr></thead>
                <tbody>
                    {% for c in owner_cars %}
                    <tr>
                        <td class="fw-semibold text-start">{{ c.car_name }}<br><small class="text-muted">{{ c.car_type }}</small></td>
                        <td>{{ c.vehicle_number }}</td>
                        <td><span class="badge bg-{{ 'success' if c.admin_status=='Approved' else 'warning text-dark' }}">{{ c.admin_status }}</span></td>
                        <td><span class="badge bg-{{ 'success' if c.status=='Available' else 'secondary' }}">{{ c.status }}</span></td>
                        <td>
                            {% if c.admin_status == 'Approved' %}
                            <form method="POST" action="/owner/update_status/{{ c.id }}">
                                <select name="status" class="form-select form-select-sm d-inline-block w-auto" onchange="this.form.submit()">
                                    <option value="Available" {{ 'selected' if c.status=='Available' else '' }}>Available</option>
                                    <option value="Not Available / On Trip" {{ 'selected' if c.status=='Not Available / On Trip' else '' }}>Not Available / Busy</option>
                                </select>
                            </form>
                            {% else %}
                            <small class="text-muted">Awaiting Admin Approval</small>
                            {% endif %}
                        </td>
                    </tr>
                    {% else %}
                    <tr><td colspan="5" class="text-muted py-3">No cars registered with this phone number.</td></tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</div>
"""
    + BASE_FOOT
)

ADMIN_LOGIN_HTML = (
    BASE_HTML
    + """
<div class="container my-5" style="max-width: 420px;">
    <div class="card-custom p-4">
        <h4 class="text-center fw-bold mb-3"><i class="fa-solid fa-user-shield text-primary"></i> Admin Dispatch Login</h4>
        <form method="POST" action="/admin_login">
            <div class="mb-3">
                <label class="form-label fw-semibold text-muted small">Username</label>
                <input type="text" name="username" class="form-control" placeholder="Enter username" autocomplete="off" required>
            </div>
            <div class="mb-3">
                <label class="form-label fw-semibold text-muted small">Password</label>
                <input type="password" name="password" class="form-control" placeholder="••••••••" required>
            </div>
            <button type="submit" class="btn btn-dark w-100 fw-bold">Login to Dispatch Panel</button>
        </form>
    </div>
</div>
"""
    + BASE_FOOT
)

ADMIN_DASH_HTML = (
    BASE_HTML
    + """
<div class="container my-4">
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h3 class="fw-bold text-dark"><i class="fa-solid fa-sliders text-primary"></i> Admin Dispatch Panel</h3>
        <a href="/logout" class="btn btn-outline-danger btn-sm">Logout</a>
    </div>

    <ul class="nav nav-pills mb-4 gap-2" id="adminTabs">
        <li class="nav-item"><a class="nav-link active fw-bold" data-bs-toggle="pill" href="#requests_tab">Hire Requests ({{ requests|length }})</a></li>
        <li class="nav-item"><a class="nav-link fw-bold" data-bs-toggle="pill" href="#fleet_requests_tab">Owner Requests ({{ pending_cars|length }})</a></li>
        <li class="nav-item"><a class="nav-link fw-bold" data-bs-toggle="pill" href="#fleet_tab">Approved Fleet ({{ approved_cars|length }})</a></li>
    </ul>

    <div class="tab-content">
        <!-- HIRE REQUESTS TAB -->
        <div class="tab-pane fade show active" id="requests_tab">
            <div class="card-custom p-4">
                <h5 class="fw-bold mb-3">User Car Hire Requests &amp; Assignment</h5>
                <div class="table-responsive">
                    <table class="table table-bordered align-middle text-center">
                        <thead class="table-dark"><tr><th>User Info</th><th>Requirement</th><th>Route &amp; Date</th><th>Status</th><th>Assign / Complete</th></tr></thead>
                        <tbody>
                            {% for r in requests %}
                            <tr>
                                <td class="text-start"><strong>{{ r.user_name }}</strong><br><a href="tel:{{ r.user_phone }}" class="small text-primary"><i class="fa-solid fa-phone"></i> {{ r.user_phone }}</a></td>
                                <td><span class="badge bg-info text-dark">{{ r.car_type_needed }}</span><br><small>{{ r.days_count }} Days</small></td>
                                <td class="text-start small"><strong>Pickup:</strong> {{ r.pickup_location }}<br><strong>Drop:</strong> {{ r.drop_location }}<br><strong>Date:</strong> {{ r.travel_date }}</td>
                                <td>
                                    <span class="badge bg-{{ 'success' if r.request_status=='Confirmed' else ('primary' if r.request_status=='Completed' else 'warning text-dark') }}">{{ r.request_status }}</span>
                                    {% if r.assigned_car_name %}<br><small class="text-success fw-bold">Car: {{ r.assigned_car_name }}</small>{% endif %}
                                    {% if r.request_status == 'Confirmed' and r.assigned_car_id %}
                                    <form method="POST" action="/admin/complete_trip/{{ r.id }}" class="mt-1">
                                        <button type="submit" class="btn btn-xs btn-sm btn-outline-primary py-0 px-2" style="font-size: 0.75rem;"><i class="fa-solid fa-flag-checkered"></i> Trip Completed</button>
                                    </form>
                                    {% endif %}
                                </td>
                                <td>
                                    <form method="POST" action="/admin/assign_car/{{ r.id }}" class="d-flex flex-column gap-1">
                                        <select name="car_id" class="form-select form-select-sm" required>
                                            <option value="">-- Select Available Car --</option>
                                            {% for c in approved_cars %}
                                            {% if c.status == 'Available' %}
                                            <option value="{{ c.id }}" {{ 'selected' if r.assigned_car_id == c.id else '' }}>{{ c.car_name }} ({{ c.vehicle_number }})</option>
                                            {% endif %}
                                            {% endfor %}
                                        </select>
                                        <button type="submit" class="btn btn-sm btn-success fw-bold">Assign &amp; Confirm</button>
                                    </form>
                                </td>
                            </tr>
                            {% else %}
                            <tr><td colspan="5" class="text-muted py-3">No hire requests received.</td></tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- CAR OWNER REQUESTS TAB -->
        <div class="tab-pane fade" id="fleet_requests_tab">
            <div class="card-custom p-4">
                <h5 class="fw-bold mb-3">Car Owner Submission Requests</h5>
                <div class="table-responsive">
                    <table class="table table-bordered align-middle text-center">
                        <thead class="table-dark"><tr><th>Car Model</th><th>Type &amp; Number</th><th>Owner &amp; Phone</th><th>Rate &amp; Location</th><th>Action</th></tr></thead>
                        <tbody>
                            {% for c in pending_cars %}
                            <tr>
                                <td class="fw-semibold text-start">{{ c.car_name }}</td>
                                <td><span class="badge bg-warning text-dark">{{ c.car_type }}</span><br><small>{{ c.vehicle_number }}</small></td>
                                <td>{{ c.owner_name }}<br><small>{{ c.phone }}</small></td>
                                <td>₹{{ c.rate_per_day }}/day<br><small>{{ c.location }}</small></td>
                                <td>
                                    <div class="d-flex justify-content-center gap-2">
                                        <form method="POST" action="/admin/update_car_status/{{ c.id }}">
                                            <input type="hidden" name="status" value="Approved">
                                            <button type="submit" class="btn btn-sm btn-success fw-bold">Approve</button>
                                        </form>
                                        <a href="/admin/delete_car/{{ c.id }}" class="btn btn-sm btn-danger fw-bold">Remove</a>
                                    </div>
                                </td>
                            </tr>
                            {% else %}
                            <tr><td colspan="5" class="text-muted py-3">No pending owner requests.</td></tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- APPROVED FLEET TAB -->
        <div class="tab-pane fade" id="fleet_tab">
            <div class="card-custom p-4">
                <h5 class="fw-bold mb-3">Approved Fleet Management</h5>
                <div class="table-responsive">
                    <table class="table table-sm table-bordered align-middle text-center">
                        <thead class="table-dark"><tr><th>Name</th><th>Type</th><th>Number</th><th>Owner Phone</th><th>Status</th><th>Action</th></tr></thead>
                        <tbody>
                            {% for c in approved_cars %}
                            <tr>
                                <td class="fw-semibold text-start">{{ c.car_name }}</td>
                                <td>{{ c.car_type }}</td>
                                <td>{{ c.vehicle_number }}</td>
                                <td>{{ c.phone }}</td>
                                <td>
                                    <form method="POST" action="/admin/toggle_availability/{{ c.id }}" class="d-inline">
                                        <select name="status" class="form-select form-select-sm d-inline-block w-auto" onchange="this.form.submit()">
                                            <option value="Available" {{ 'selected' if c.status=='Available' else '' }}>Available</option>
                                            <option value="Not Available / On Trip" {{ 'selected' if c.status=='Not Available / On Trip' else '' }}>Not Available / On Trip</option>
                                        </select>
                                    </form>
                                </td>
                                <td><a href="/admin/delete_car/{{ c.id }}" class="btn btn-sm btn-outline-danger">Remove</a></td>
                            </tr>
                            {% else %}
                            <tr><td colspan="6" class="text-muted py-3">No approved cars in fleet.</td></tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
</div>
"""
    + BASE_FOOT
)


# ---------------- ROUTES ---------------- #


@app.route("/")
def index():
    cars = Car.query.filter_by(admin_status="Approved").order_by(Car.id.desc()).all()
    return render_template_string(INDEX_HTML, cars=cars)


@app.route("/fleet")
def fleet():
    cars = Car.query.filter_by(admin_status="Approved").order_by(Car.id.desc()).all()
    return render_template_string(FLEET_HTML, cars=cars)


@app.route("/owner_login", methods=["GET", "POST"])
def owner_login():
    if request.method == "POST":
        phone = request.form.get("phone").strip()
        cars = Car.query.filter_by(phone=phone).all()
        if cars:
            session["owner_phone"] = phone
            return redirect(url_for("owner_dashboard"))
        flash("No car found registered with this phone number!", "danger")
    return render_template_string(OWNER_LOGIN_HTML)


@app.route("/owner_dashboard")
def owner_dashboard():
    phone = session.get("owner_phone")
    if not phone:
        return redirect(url_for("owner_login"))
    owner_cars = Car.query.filter_by(phone=phone).order_by(Car.id.desc()).all()
    return render_template_string(
        OWNER_DASH_HTML, owner_cars=owner_cars, owner_phone=phone
    )


@app.route("/owner/update_status/<int:car_id>", methods=["POST"])
def owner_update_status(car_id):
    phone = session.get("owner_phone")
    if phone:
        status = request.form.get("status")
        car = Car.query.filter_by(id=car_id, phone=phone).first()
        if car:
            car.status = status
            db.session.commit()
            flash("Your car status updated successfully!", "success")
    return redirect(url_for("owner_dashboard"))


@app.route("/submit_request", methods=["POST"])
def submit_request():
    new_req = HireRequest(
        user_name=request.form.get("user_name"),
        user_phone=request.form.get("user_phone"),
        car_type_needed=request.form.get("car_type_needed"),
        driver_needed=request.form.get("driver_needed"),
        pickup_location=request.form.get("pickup_location"),
        drop_location=request.form.get("drop_location"),
        travel_date=request.form.get("travel_date"),
        days_count=int(request.form.get("days_count", 1)),
        notes=request.form.get("notes", ""),
        request_date=date.today().isoformat(),
    )
    db.session.add(new_req)
    db.session.commit()
    flash("Car hire request submitted successfully!", "success")
    return redirect(url_for("index"))


@app.route("/submit_car_request", methods=["POST"])
def submit_car_request():
    photo_path = ""
    f_photo = request.files.get("photo")
    if f_photo and f_photo.filename != "":
        fname = f"car_{datetime.now().strftime('%Y%m%d%H%M%S')}_{f_photo.filename}"
        photo_path = os.path.join(CAR_FOLDER, fname)
        f_photo.save(photo_path)

    try:
        new_car = Car(
            car_name=request.form.get("car_name"),
            car_type=request.form.get("car_type"),
            vehicle_number=request.form.get("vehicle_number"),
            owner_name=request.form.get("owner_name"),
            phone=request.form.get("phone"),
            rate_per_day=request.form.get("rate_per_day"),
            location=request.form.get("location"),
            engagement_type=request.form.get("engagement_type"),
            driver_available=request.form.get("driver_available"),
            status="Available",
            admin_status="Pending",
            photo_path=photo_path,
        )
        db.session.add(new_car)
        db.session.commit()
        flash("Car listed successfully! Awaiting Admin approval.", "success")
    except Exception:
        db.session.rollback()
        flash(
            "Vehicle number already registered or database error occurred!",
            "danger",
        )
    return redirect(url_for("index"))


@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if (
            request.form.get("username") == "admin"
            and request.form.get("password") == "admin123"
        ):
            session["role"] = "admin"
            return redirect(url_for("admin_dashboard"))
        flash("Invalid Admin Credentials!", "danger")
    return render_template_string(ADMIN_LOGIN_HTML)


@app.route("/admin_dashboard")
def admin_dashboard():
    if session.get("role") != "admin":
        return redirect(url_for("admin_login"))

    pending_cars = (
        Car.query.filter_by(admin_status="Pending").order_by(Car.id.desc()).all()
    )
    approved_cars = (
        Car.query.filter_by(admin_status="Approved").order_by(Car.id.desc()).all()
    )

    requests = (
        db.session.query(HireRequest, Car.car_name.label("assigned_car_name"))
        .outerjoin(Car, HireRequest.assigned_car_id == Car.id)
        .order_by(HireRequest.id.desc())
        .all()
    )

    formatted_requests = []
    for req, car_name in requests:
        r_dict = {c.name: getattr(req, c.name) for c in req.__table__.columns}
        r_dict["assigned_car_name"] = car_name
        formatted_requests.append(r_dict)

    return render_template_string(
        ADMIN_DASH_HTML,
        pending_cars=pending_cars,
        approved_cars=approved_cars,
        requests=formatted_requests,
    )


@app.route("/admin/update_car_status/<int:car_id>", methods=["POST"])
def update_car_status(car_id):
    if session.get("role") == "admin":
        car = Car.query.get(car_id)
        if car:
            car.admin_status = request.form.get("status")
            db.session.commit()
            flash("Car approved successfully!", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/toggle_availability/<int:car_id>", methods=["POST"])
def toggle_availability(car_id):
    if session.get("role") == "admin":
        car = Car.query.get(car_id)
        if car:
            car.status = request.form.get("status")
            db.session.commit()
            flash("Status updated.", "info")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/assign_car/<int:req_id>", methods=["POST"])
def assign_car(req_id):
    if session.get("role") == "admin":
        car_id = int(request.form.get("car_id"))
        req = HireRequest.query.get(req_id)
        car = Car.query.get(car_id)
        if req and car:
            req.assigned_car_id = car_id
            req.request_status = "Confirmed"
            car.status = "Not Available / On Trip"
            db.session.commit()
            flash("Car assigned successfully!", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/complete_trip/<int:req_id>", methods=["POST"])
def complete_trip(req_id):
    if session.get("role") == "admin":
        req = HireRequest.query.get(req_id)
        if req and req.assigned_car_id:
            car = Car.query.get(req.assigned_car_id)
            if car:
                car.status = "Available"
            req.request_status = "Completed"
            db.session.commit()
            flash("Trip completed! Car is now Available.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/delete_car/<int:car_id>")
def delete_car(car_id):
    if session.get("role") == "admin":
        car = Car.query.get(car_id)
        if car:
            db.session.delete(car)
            db.session.commit()
            flash("Car removed.", "info")
    return redirect(url_for("admin_dashboard"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5002))
    app.run(host="0.0.0.0", port=port, debug=False)
