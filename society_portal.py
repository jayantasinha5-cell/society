from datetime import date, datetime
import os
import csv
from io import StringIO
from flask import Flask, flash, redirect, render_template_string, request, session, url_for, make_response
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "wb_society_portal_secret_2026")

# ---------------- DIRECT SUPABASE DATABASE CONFIGURATION ---------------- #
supabase_db_url = "postgresql://postgres.ycmbkusbqpkxcgftzdze:Birpara123@aws-0-ap-south-1.pooler.supabase.com:6543/postgres"

db_url = os.environ.get("DATABASE_URL", supabase_db_url)
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

ADMIN_PASSWORD = os.environ.get("ADMIN_PASS", "admin123")


# ---------------- DATABASE MODEL ---------------- #
class Society(db.Model):
    __tablename__ = "wb_societies"
    id = db.Column(db.Integer, primary_key=True)
    society_name = db.Column(db.String(200), nullable=False)
    reg_number = db.Column(db.String(100), unique=True, nullable=False)
    reg_date = db.Column(db.String(50))
    address = db.Column(db.Text)
    pan_number = db.Column(db.String(30))
    bank_details = db.Column(db.Text)

    president_name = db.Column(db.String(100))
    president_phone = db.Column(db.String(20))

    secretary_name = db.Column(db.String(100))
    secretary_phone = db.Column(db.String(20))

    renewed_years = db.Column(db.String(250), default="")
    last_renewed_fy = db.Column(db.String(50), default="")
    renewal_status = db.Column(db.String(20), default="Pending")
    notes = db.Column(db.Text)
    updated_at = db.Column(db.String(50))


with app.app_context():
    db.create_all()


# ---------------- HELPER FUNCTIONS ---------------- #
def clean_phone_for_wa(phone):
    if not phone:
        return ""
    digits = "".join(filter(str.isdigit, str(phone)))
    if len(digits) == 10:
        return "91" + digits
    return digits


def get_current_fy():
    today = date.today()
    if today.month >= 4:
        return f"{today.year}-{str(today.year + 1)[-2:]}"
    else:
        return f"{today.year - 1}-{str(today.year)[-2:]}"


app.jinja_env.globals.update(
    clean_phone_for_wa=clean_phone_for_wa, current_fy=get_current_fy()
)

# ---------------- HTML TEMPLATES ---------------- #
LOGIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WB Society Portal - Admin Login</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css">
    <style>
        body { background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%); height: 100vh; display: flex; align-items: center; justify-content: center; font-family: 'Segoe UI', sans-serif; }
        .login-card { background: #fff; border-radius: 16px; padding: 35px; width: 100%; max-width: 400px; box-shadow: 0 15px 35px rgba(0,0,0,0.3); }
    </style>
</head>
<body>
    <div class="login-card text-center">
        <div class="mb-3 text-primary"><i class="fa-solid fa-building-columns fa-3x"></i></div>
        <h4 class="fw-bold mb-1">WB Society Registry</h4>
        <p class="text-muted small mb-4">Renewal & Client Database Management</p>
        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            {% for category, message in messages %}
              <div class="alert alert-{{ category }} py-2 small">{{ message }}</div>
            {% endfor %}
          {% endif %}
        {% endwith %}
        <form method="POST">
            <div class="mb-3 text-start">
                <label class="form-label small fw-bold">Admin Password</label>
                <input type="password" name="password" class="form-control form-control-lg" placeholder="Enter password" required autofocus>
            </div>
            <button type="submit" class="btn btn-primary w-100 btn-lg fw-bold">Unlock Dashboard</button>
        </form>
    </div>
</body>
</html>
"""

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WB Society Renewal Manager</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css">
    <style>
        body { background-color: #f1f5f9; font-family: 'Segoe UI', system-ui, sans-serif; }
        .navbar-custom { background: linear-gradient(90deg, #0f172a 0%, #1e40af 100%); }
        .stat-card { border: none; border-radius: 12px; transition: transform 0.2s; }
        .stat-card:hover { transform: translateY(-3px); }
        .society-card { background: #fff; border-radius: 14px; border: 1px solid #e2e8f0; transition: all 0.2s; }
        .society-card:hover { box-shadow: 0 10px 25px rgba(0,0,0,0.08); border-color: #cbd5e1; }
        .btn-wa { background-color: #25D366; color: white; border: none; }
        .btn-wa:hover { background-color: #1ebe5d; color: white; }
        .badge-fy { background-color: #e0f2fe; color: #0369a1; border: 1px solid #bae6fd; font-weight: 600; }
        .nav-pills .nav-link.active.pending-tab { background-color: #dc2626; }
        .nav-pills .nav-link.active.completed-tab { background-color: #16a34a; }
    </style>
</head>
<body>

<!-- NAVBAR -->
<nav class="navbar navbar-expand-lg navbar-dark navbar-custom shadow-sm sticky-top">
    <div class="container">
        <a class="navbar-brand fw-bold d-flex align-items-center" href="/">
            <i class="fa-solid fa-landmark me-2 text-warning"></i> WB SOCIETY MANAGER
        </a>
        <div class="d-flex flex-wrap gap-2">
            <button class="btn btn-warning btn-sm fw-bold" data-bs-toggle="modal" data-bs-target="#addSocietyModal">
                <i class="fa-solid fa-plus me-1"></i> New Society
            </button>
            <button class="btn btn-info btn-sm fw-bold text-dark" data-bs-toggle="modal" data-bs-target="#bulkModal">
                <i class="fa-solid fa-file-import me-1"></i> Bulk Import
            </button>
            <a href="/export_excel" class="btn btn-success btn-sm fw-bold">
                <i class="fa-solid fa-file-excel me-1"></i> Export Excel
            </a>
            <a href="/reset_all_pending" onclick="return confirm('আপনি কি নতুন আর্থিক বছরের (After March) জন্য সব সোসাইটিকে একসাথে Pending লিস্টে নিয়ে আসতে চান?')" class="btn btn-outline-light btn-sm" title="Start New Renewal Cycle">
                <i class="fa-solid fa-rotate"></i> New Year Cycle
            </a>
            <a href="/logout" class="btn btn-danger btn-sm"><i class="fa-solid fa-right-from-bracket"></i></a>
        </div>
    </div>
</nav>

<div class="container my-4">

    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        {% for category, message in messages %}
          <div class="alert alert-{{ category }} alert-dismissible fade show shadow-sm" role="alert">
            {{ message }}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
          </div>
        {% endfor %}
      {% endif %}
    {% endwith %}

    <!-- MARCH RENEWAL ALERT BANNER -->
    <div class="alert alert-warning border-warning d-flex flex-wrap justify-content-between align-items-center shadow-sm rounded-3 mb-4">
        <div>
            <h6 class="fw-bold mb-1 text-dark"><i class="fa-solid fa-bell text-danger me-2"></i>Annual Renewal Reminder (After March Rule)</h6>
            <small class="text-dark">মার্চ মাস শেষ হলে প্রতিটি সোসাইটির বার্ষিক রিনিউয়াল বাধ্যতামূলক। নিচের <strong>Pending</strong> ট্যাব থেকে সরাসরি প্রেসিডেন্ট বা সেক্রেটারিকে WhatsApp অ্যালার্ট পাঠান।</small>
        </div>
        <span class="badge bg-dark px-3 py-2 mt-2 mt-md-0">Active FY: {{ current_fy }}</span>
    </div>

    <!-- SUMMARY STATS -->
    <div class="row g-3 mb-4">
        <div class="col-md-4">
            <div class="card stat-card bg-white p-3 shadow-sm border-start border-primary border-4">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <p class="text-muted small mb-1 fw-bold">TOTAL SOCIETIES</p>
                        <h3 class="fw-bold mb-0 text-primary">{{ total_count }}</h3>
                    </div>
                    <div class="bg-primary bg-opacity-10 p-3 rounded-circle text-primary"><i class="fa-solid fa-folder-open fa-lg"></i></div>
                </div>
            </div>
        </div>
        <div class="col-md-4">
            <div class="card stat-card bg-white p-3 shadow-sm border-start border-danger border-4">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <p class="text-muted small mb-1 fw-bold">RENEWAL PENDING</p>
                        <h3 class="fw-bold mb-0 text-danger">{{ pending_list|length }}</h3>
                    </div>
                    <div class="bg-danger bg-opacity-10 p-3 rounded-circle text-danger"><i class="fa-solid fa-clock-rotate-left fa-lg"></i></div>
                </div>
            </div>
        </div>
        <div class="col-md-4">
            <div class="card stat-card bg-white p-3 shadow-sm border-start border-success border-4">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <p class="text-muted small mb-1 fw-bold">RENEWAL COMPLETED</p>
                        <h3 class="fw-bold mb-0 text-success">{{ completed_list|length }}</h3>
                    </div>
                    <div class="bg-success bg-opacity-10 p-3 rounded-circle text-success"><i class="fa-solid fa-circle-check fa-lg"></i></div>
                </div>
            </div>
        </div>
    </div>

    <!-- SEARCH BAR & TABS -->
    <div class="bg-white p-3 rounded-3 shadow-sm mb-4">
        <div class="row g-3 align-items-center">
            <div class="col-md-6">
                <ul class="nav nav-pills" id="renewalTabs" role="tablist">
                    <li class="nav-item" role="presentation">
                        <button class="nav-link active pending-tab fw-bold" id="pending-tab" data-bs-toggle="pill" data-bs-target="#pending" type="button">
                            <i class="fa-solid fa-hourglass-half me-1"></i> Pending ({{ pending_list|length }})
                        </button>
                    </li>
                    <li class="nav-item ms-2" role="presentation">
                        <button class="nav-link completed-tab fw-bold" id="completed-tab" data-bs-toggle="pill" data-bs-target="#completed" type="button">
                            <i class="fa-solid fa-check-double me-1"></i> Completed ({{ completed_list|length }})
                        </button>
                    </li>
                </ul>
            </div>
            <div class="col-md-6">
                <div class="input-group">
                    <span class="input-group-text bg-light border-end-0"><i class="fa-solid fa-magnifying-glass text-muted"></i></span>
                    <input type="text" id="searchInput" class="form-control border-start-0" placeholder="Search by Society Name, Reg No, PAN, President or Phone...">
                </div>
            </div>
        </div>
    </div>

    <!-- TAB CONTENTS -->
    <div class="tab-content" id="renewalTabsContent">
        
        <!-- PENDING TAB -->
        <div class="tab-pane fade show active" id="pending" role="tabpanel">
            <div class="row g-3">
                {% for s in pending_list %}
                <div class="col-md-6 society-item">
                    <div class="society-card p-4 h-100 d-flex flex-column">
                        <div class="d-flex justify-content-between align-items-start mb-2">
                            <div>
                                <span class="badge bg-danger mb-1">Renewal Pending</span>
                                <h5 class="fw-bold text-dark mb-0">{{ s.society_name }}</h5>
                                <small class="text-primary fw-bold"><i class="fa-solid fa-hashtag"></i> Reg No: {{ s.reg_number }}</small>
                                {% if s.reg_date %}<small class="text-muted ms-2">| Reg Date: {{ s.reg_date }}</small>{% endif %}
                            </div>
                            <div class="dropdown">
                                <button class="btn btn-light btn-sm border" data-bs-toggle="dropdown"><i class="fa-solid fa-ellipsis-vertical"></i></button>
                                <ul class="dropdown-menu dropdown-menu-end">
                                    <li><a class="dropdown-item" href="#" data-bs-toggle="modal" data-bs-target="#editModal{{ s.id }}"><i class="fa-solid fa-pen text-primary me-2"></i>Edit Details</a></li>
                                    <li><a class="dropdown-item text-danger" href="/delete/{{ s.id }}" onclick="return confirm('Delete this society permanently?')"><i class="fa-solid fa-trash me-2"></i>Delete</a></li>
                                </ul>
                            </div>
                        </div>

                        <div class="bg-light p-2 rounded small mb-3 border">
                            <div class="row g-1">
                                <div class="col-6"><strong>PAN:</strong> <span class="text-uppercase">{{ s.pan_number or 'N/A' }}</span></div>
                                <div class="col-6"><strong>Last FY:</strong> {{ s.last_renewed_fy or 'None' }}</div>
                                <div class="col-12 mt-1"><strong>Bank:</strong> {{ s.bank_details or 'Not Added' }}</div>
                                <div class="col-12 mt-1"><strong>Address:</strong> {{ s.address or 'N/A' }}</div>
                            </div>
                        </div>

                        <!-- RENEWED YEARS HISTORY -->
                        <div class="mb-3">
                            <small class="text-muted fw-bold d-block mb-1"><i class="fa-solid fa-calendar-check text-success me-1"></i> Renewed Years History:</small>
                            {% if s.renewed_years %}
                                {% for yr in s.renewed_years.split(',') %}
                                    <span class="badge badge-fy me-1">{{ yr.strip() }}</span>
                                {% endfor %}
                            {% else %}
                                <span class="text-muted small fst-italic">No previous renewal record</span>
                            {% endif %}
                        </div>

                        <!-- CONTACTS & WHATSAPP ALERT -->
                        <div class="border-top pt-2 mt-auto">
                            <!-- President -->
                            <div class="d-flex justify-content-between align-items-center mb-2">
                                <div class="small">
                                    <span class="badge bg-secondary">President</span> <strong>{{ s.president_name or 'N/A' }}</strong><br>
                                    <span class="text-muted">{{ s.president_phone or 'No Phone' }}</span>
                                </div>
                                {% if s.president_phone %}
                                <div class="d-flex gap-1">
                                    <a href="tel:{{ s.president_phone }}" class="btn btn-outline-primary btn-sm" title="Call President"><i class="fa-solid fa-phone"></i></a>
                                    <a href="https://wa.me/{{ clean_phone_for_wa(s.president_phone) }}?text={{ ('নমস্কার ' ~ (s.president_name or '') ~ ', আপনার সোসাইটি *' ~ s.society_name ~ '* (Reg No: ' ~ s.reg_number ~ ')-এর বার্ষিক রিনিউয়াল (Annual Renewal - FY ' ~ current_fy ~ ') মার্চ মাস শেষ হওয়ার পর এখন পেন্ডিং আছে। অনুগ্রহ করে প্রয়োজনীয় কাগজপত্র সহ দ্রুত রিনিউয়াল সম্পন্ন করুন।') | urlencode }}" target="_blank" class="btn btn-wa btn-sm fw-semibold">
                                        <i class="fa-brands fa-whatsapp"></i> Alert
                                    </a>
                                </div>
                                {% endif %}
                            </div>

                            <!-- Secretary -->
                            <div class="d-flex justify-content-between align-items-center mb-3">
                                <div class="small">
                                    <span class="badge bg-info text-dark">Secretary</span> <strong>{{ s.secretary_name or 'N/A' }}</strong><br>
                                    <span class="text-muted">{{ s.secretary_phone or 'No Phone' }}</span>
                                </div>
                                {% if s.secretary_phone %}
                                <div class="d-flex gap-1">
                                    <a href="tel:{{ s.secretary_phone }}" class="btn btn-outline-primary btn-sm" title="Call Secretary"><i class="fa-solid fa-phone"></i></a>
                                    <a href="https://wa.me/{{ clean_phone_for_wa(s.secretary_phone) }}?text={{ ('নমস্কার ' ~ (s.secretary_name or '') ~ ', আপনার সোসাইটি *' ~ s.society_name ~ '* (Reg No: ' ~ s.reg_number ~ ')-এর বার্ষিক রিনিউয়াল (Annual Renewal - FY ' ~ current_fy ~ ') মার্চ মাস শেষ হওয়ার পর এখন পেন্ডিং আছে। অনুগ্রহ করে প্রয়োজনীয় কাগজপত্র সহ দ্রুত রিনিউয়াল সম্পন্ন করুন।') | urlencode }}" target="_blank" class="btn btn-wa btn-sm fw-semibold">
                                        <i class="fa-brands fa-whatsapp"></i> Alert
                                    </a>
                                </div>
                                {% endif %}
                            </div>

                            <!-- MARK COMPLETED BUTTON -->
                            <button class="btn btn-success w-100 btn-sm fw-bold" data-bs-toggle="modal" data-bs-target="#completeModal{{ s.id }}">
                                <i class="fa-solid fa-check-circle me-1"></i> Mark Renewal Completed
                            </button>
                        </div>
                    </div>
                </div>
                {% else %}
                <div class="col-12 text-center py-5 bg-white rounded-3 shadow-sm">
                    <i class="fa-solid fa-party-horn fa-3x text-success mb-2"></i>
                    <h5 class="fw-bold text-muted">কোনো Pending রিনিউয়াল বাকি নেই!</h5>
                </div>
                {% endfor %}
            </div>
        </div>

        <!-- COMPLETED TAB -->
        <div class="tab-pane fade" id="completed" role="tabpanel">
            <div class="row g-3">
                {% for s in completed_list %}
                <div class="col-md-6 society-item">
                    <div class="society-card p-4 h-100 d-flex flex-column border-success border-opacity-50">
                        <div class="d-flex justify-content-between align-items-start mb-2">
                            <div>
                                <span class="badge bg-success mb-1"><i class="fa-solid fa-check"></i> Renewal Completed</span>
                                <h5 class="fw-bold text-dark mb-0">{{ s.society_name }}</h5>
                                <small class="text-primary fw-bold"><i class="fa-solid fa-hashtag"></i> Reg No: {{ s.reg_number }}</small>
                            </div>
                            <div class="dropdown">
                                <button class="btn btn-light btn-sm border" data-bs-toggle="dropdown"><i class="fa-solid fa-ellipsis-vertical"></i></button>
                                <ul class="dropdown-menu dropdown-menu-end">
                                    <li><a class="dropdown-item" href="#" data-bs-toggle="modal" data-bs-target="#editModal{{ s.id }}"><i class="fa-solid fa-pen text-primary me-2"></i>Edit Details</a></li>
                                    <li><a class="dropdown-item text-warning" href="/mark_pending/{{ s.id }}"><i class="fa-solid fa-rotate-left me-2"></i>Move back to Pending</a></li>
                                    <li><a class="dropdown-item text-danger" href="/delete/{{ s.id }}" onclick="return confirm('Delete this society permanently?')"><i class="fa-solid fa-trash me-2"></i>Delete</a></li>
                                </ul>
                            </div>
                        </div>

                        <div class="bg-light p-2 rounded small mb-3 border">
                            <div class="row g-1">
                                <div class="col-6"><strong>PAN:</strong> <span class="text-uppercase">{{ s.pan_number or 'N/A' }}</span></div>
                                <div class="col-6"><strong>Latest FY:</strong> <span class="text-success fw-bold">{{ s.last_renewed_fy }}</span></div>
                                <div class="col-12 mt-1"><strong>Bank:</strong> {{ s.bank_details or 'Not Added' }}</div>
                                <div class="col-12 mt-1"><strong>Address:</strong> {{ s.address or 'N/A' }}</div>
                            </div>
                        </div>

                        <div class="mb-3">
                            <small class="text-muted fw-bold d-block mb-1">All Completed Renewal Years:</small>
                            {% if s.renewed_years %}
                                {% for yr in s.renewed_years.split(',') %}
                                    <span class="badge badge-fy me-1">{{ yr.strip() }}</span>
                                {% endfor %}
                            {% endif %}
                        </div>

                        <div class="border-top pt-2 mt-auto">
                            <div class="d-flex justify-content-between align-items-center small mb-1">
                                <span><strong>Pres:</strong> {{ s.president_name or 'N/A' }} ({{ s.president_phone or '-' }})</span>
                                {% if s.president_phone %}
                                <div>
                                    <a href="tel:{{ s.president_phone }}" class="btn btn-outline-primary btn-sm py-0 px-2"><i class="fa-solid fa-phone"></i></a>
                                    <a href="https://wa.me/{{ clean_phone_for_wa(s.president_phone) }}?text={{ ('নমস্কার ' ~ (s.president_name or '') ~ ', আপনার সোসাইটি *' ~ s.society_name ~ '* (Reg No: ' ~ s.reg_number ~ ')-এর বার্ষিক রিনিউয়াল (' ~ s.last_renewed_fy ~ ') সফলভাবে সম্পন্ন হয়েছে। ধন্যবাদ।') | urlencode }}" target="_blank" class="btn btn-wa btn-sm py-0 px-2"><i class="fa-brands fa-whatsapp"></i></a>
                                </div>
                                {% endif %}
                            </div>
                            <div class="d-flex justify-content-between align-items-center small">
                                <span><strong>Secy:</strong> {{ s.secretary_name or 'N/A' }} ({{ s.secretary_phone or '-' }})</span>
                                {% if s.secretary_phone %}
                                <div>
                                    <a href="tel:{{ s.secretary_phone }}" class="btn btn-outline-primary btn-sm py-0 px-2"><i class="fa-solid fa-phone"></i></a>
                                    <a href="https://wa.me/{{ clean_phone_for_wa(s.secretary_phone) }}?text={{ ('নমস্কার ' ~ (s.secretary_name or '') ~ ', আপনার সোসাইটি *' ~ s.society_name ~ '* (Reg No: ' ~ s.reg_number ~ ')-এর বার্ষিক রিনিউয়াল (' ~ s.last_renewed_fy ~ ') সফলভাবে সম্পন্ন হয়েছে। ধন্যবাদ।') | urlencode }}" target="_blank" class="btn btn-wa btn-sm py-0 px-2"><i class="fa-brands fa-whatsapp"></i></a>
                                </div>
                                {% endif %}
                            </div>
                        </div>
                    </div>
                </div>
                {% else %}
                <div class="col-12 text-center py-5 bg-white rounded-3 shadow-sm">
                    <p class="text-muted mb-0">এখনও কোনো সোসাইটি Completed লিস্টে নেই।</p>
                </div>
                {% endfor %}
            </div>
        </div>

    </div>
</div>

<!-- MODALS FOR MARKING COMPLETE & EDITING -->
{% for s in all_societies %}
<!-- Complete Modal -->
<div class="modal fade" id="completeModal{{ s.id }}" tabindex="-1">
    <div class="modal-dialog">
        <form action="/mark_complete/{{ s.id }}" method="POST" class="modal-content">
            <div class="modal-header bg-success text-white">
                <h5 class="modal-title fw-bold">Complete Renewal: {{ s.society_name }}</h5>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <label class="form-label fw-bold">কোন আর্থিক বছরের (Financial Year) রিনিউয়াল কমপ্লিট হলো?</label>
                <input type="text" name="completed_fy" class="form-control form-control-lg" value="{{ current_fy }}" placeholder="e.g. 2026-27" required>
                <small class="text-muted d-block mt-2">এটি সাবমিট করলে বছরটি সোসাইটির Renewed Years হিস্ট্রিতে যুক্ত হয়ে যাবে এবং কার্ডটি Completed ট্যাবে চলে যাবে।</small>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                <button type="submit" class="btn btn-success fw-bold">Confirm & Save</button>
            </div>
        </form>
    </div>
</div>

<!-- Edit Modal -->
<div class="modal fade" id="editModal{{ s.id }}" tabindex="-1">
    <div class="modal-dialog modal-lg">
        <form action="/edit/{{ s.id }}" method="POST" class="modal-content">
            <div class="modal-header bg-primary text-white">
                <h5 class="modal-title fw-bold">Edit Society Details</h5>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <div class="row g-3">
                    <div class="col-md-8">
                        <label class="form-label small fw-bold">Society Name *</label>
                        <input type="text" name="society_name" class="form-control" value="{{ s.society_name }}" required>
                    </div>
                    <div class="col-md-4">
                        <label class="form-label small fw-bold">Registration Number *</label>
                        <input type="text" name="reg_number" class="form-control" value="{{ s.reg_number }}" required>
                    </div>
                    <div class="col-md-4">
                        <label class="form-label small fw-bold">Registration Date</label>
                        <input type="text" name="reg_date" class="form-control" value="{{ s.reg_date or '' }}" placeholder="DD-MM-YYYY">
                    </div>
                    <div class="col-md-4">
                        <label class="form-label small fw-bold">Society PAN Number</label>
                        <input type="text" name="pan_number" class="form-control text-uppercase" value="{{ s.pan_number or '' }}">
                    </div>
                    <div class="col-md-4">
                        <label class="form-label small fw-bold">Status</label>
                        <select name="renewal_status" class="form-select">
                            <option value="Pending" {% if s.renewal_status == 'Pending' %}selected{% endif %}>Pending</option>
                            <option value="Completed" {% if s.renewal_status == 'Completed' %}selected{% endif %}>Completed</option>
                        </select>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label small fw-bold">President Name</label>
                        <input type="text" name="president_name" class="form-control" value="{{ s.president_name or '' }}">
                    </div>
                    <div class="col-md-6">
                        <label class="form-label small fw-bold">President Mobile / WhatsApp</label>
                        <input type="text" name="president_phone" class="form-control" value="{{ s.president_phone or '' }}">
                    </div>
                    <div class="col-md-6">
                        <label class="form-label small fw-bold">Secretary Name</label>
                        <input type="text" name="secretary_name" class="form-control" value="{{ s.secretary_name or '' }}">
                    </div>
                    <div class="col-md-6">
                        <label class="form-label small fw-bold">Secretary Mobile / WhatsApp</label>
                        <input type="text" name="secretary_phone" class="form-control" value="{{ s.secretary_phone or '' }}">
                    </div>
                    <div class="col-12">
                        <label class="form-label small fw-bold">Bank Account Details (Bank Name, A/C No, IFSC)</label>
                        <input type="text" name="bank_details" class="form-control" value="{{ s.bank_details or '' }}">
                    </div>
                    <div class="col-12">
                        <label class="form-label small fw-bold">Registered Address</label>
                        <textarea name="address" class="form-control" rows="2">{{ s.address or '' }}</textarea>
                    </div>
                    <div class="col-12">
                        <label class="form-label small fw-bold">Renewed Years History (Comma separated, e.g. 2023-24, 2024-25)</label>
                        <input type="text" name="renewed_years" class="form-control" value="{{ s.renewed_years or '' }}">
                    </div>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                <button type="submit" class="btn btn-primary fw-bold">Update Record</button>
            </div>
        </form>
    </div>
</div>
{% endfor %}

<!-- BULK IMPORT MODAL -->
<div class="modal fade" id="bulkModal" tabindex="-1">
    <div class="modal-dialog">
        <form action="/bulk_import" method="POST" class="modal-content">
            <div class="modal-header bg-info text-dark">
                <h5 class="modal-title fw-bold"><i class="fa-solid fa-layer-group me-2"></i>Bulk Import Societies</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <label class="form-label small fw-bold">প্রতি লাইনে একটি করে সোসাইটির নাম পেস্ট করুন:</label>
                <textarea name="bulk_names" class="form-control" rows="8" placeholder="Birpara Jubilee Club&#10;Laxmi Welfare Society&#10;..." required></textarea>
                <small class="text-muted d-block mt-2">আপাতত অস্থায়ী রেজিস্ট্রেশন নম্বর দিয়ে সেভ হবে, পরে আপনি প্রতিটি কার্ডের <strong>Edit Details</strong> থেকে আসল রেজিস্ট্রেশন নম্বর, PAN ও ফোন নম্বর বসিয়ে নিতে পারবেন।</small>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                <button type="submit" class="btn btn-info fw-bold">Import All</button>
            </div>
        </form>
    </div>
</div>

<!-- ADD NEW SOCIETY MODAL -->
<div class="modal fade" id="addSocietyModal" tabindex="-1">
    <div class="modal-dialog modal-lg">
        <form action="/add_society" method="POST" class="modal-content">
            <div class="modal-header bg-dark text-white">
                <h5 class="modal-title fw-bold"><i class="fa-solid fa-folder-plus text-warning me-2"></i>Add New WB Society Record</h5>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <div class="row g-3">
                    <div class="col-md-8">
                        <label class="form-label small fw-bold">Society Name *</label>
                        <input type="text" name="society_name" class="form-control" placeholder="e.g. Birpara Jubilee Club" required>
                    </div>
                    <div class="col-md-4">
                        <label class="form-label small fw-bold">Registration Number *</label>
                        <input type="text" name="reg_number" class="form-control" placeholder="e.g. S/2L/12345" required>
                    </div>
                    <div class="col-md-4">
                        <label class="form-label small fw-bold">Registration Date</label>
                        <input type="text" name="reg_date" class="form-control" placeholder="DD-MM-YYYY">
                    </div>
                    <div class="col-md-4">
                        <label class="form-label small fw-bold">Society PAN Number</label>
                        <input type="text" name="pan_number" class="form-control text-uppercase" placeholder="AAAAB1234C">
                    </div>
                    <div class="col-md-4">
                        <label class="form-label small fw-bold">Current Renewal Status</label>
                        <select name="renewal_status" class="form-select">
                            <option value="Pending" selected>Pending</option>
                            <option value="Completed">Completed</option>
                        </select>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label small fw-bold">President Name</label>
                        <input type="text" name="president_name" class="form-control">
                    </div>
                    <div class="col-md-6">
                        <label class="form-label small fw-bold">President Mobile / WhatsApp</label>
                        <input type="text" name="president_phone" class="form-control" placeholder="10 digit number">
                    </div>
                    <div class="col-md-6">
                        <label class="form-label small fw-bold">Secretary Name</label>
                        <input type="text" name="secretary_name" class="form-control">
                    </div>
                    <div class="col-md-6">
                        <label class="form-label small fw-bold">Secretary Mobile / WhatsApp</label>
                        <input type="text" name="secretary_phone" class="form-control" placeholder="10 digit number">
                    </div>
                    <div class="col-12">
                        <label class="form-label small fw-bold">Bank Account Details (Bank Name, A/C No, IFSC)</label>
                        <input type="text" name="bank_details" class="form-control" placeholder="e.g. SBI Birpara, A/C: 30123456789, IFSC: SBIN0001234">
                    </div>
                    <div class="col-12">
                        <label class="form-label small fw-bold">Registered Address</label>
                        <textarea name="address" class="form-control" rows="2" placeholder="Full village/town, PO, PS, District, PIN"></textarea>
                    </div>
                    <div class="col-12">
                        <label class="form-label small fw-bold">Already Renewed Years (Optional, comma separated)</label>
                        <input type="text" name="renewed_years" class="form-control" placeholder="e.g. 2022-23, 2023-24, 2024-25">
                    </div>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                <button type="submit" class="btn btn-primary fw-bold px-4">Save Society Folder</button>
            </div>
        </form>
    </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
<script>
    document.getElementById('searchInput').addEventListener('keyup', function() {
        let filter = this.value.toLowerCase();
        let cards = document.querySelectorAll('.society-item');
        cards.forEach(function(card) {
            let text = card.innerText.toLowerCase();
            card.style.display = text.includes(filter) ? '' : 'none';
        });
    });
</script>
</body>
</html>
"""


# ---------------- ROUTES ---------------- #
@app.route("/bulk_import", methods=["POST"])
def bulk_import():
    if not session.get("admin_logged_in"):
        return redirect(url_for("login"))
    try:
        raw_text = request.form.get("bulk_names", "")
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        added_count = 0
        
        for idx, line in enumerate(lines, start=1):
            # স্ল্যাশ বা স্পেশাল ক্যারেক্টার ক্লিন করা
            clean_name = line.replace("\\", " ").replace("/", " ").strip()
            if not clean_name:
                continue
                
            # চেক করা যে নামটা আগে থেকেই ডাটাবেসে আছে কি না
            existing = Society.query.filter_by(society_name=clean_name).first()
            if not existing:
                unique_code = uuid.uuid4().hex[:6].upper()
                temp_reg = f"REG-{datetime.now().strftime('%H%M%S')}-{idx}-{unique_code}"
                
                new_soc = Society(
                    society_name=clean_name,
                    reg_number=temp_reg,
                    renewal_status="Pending",
                    updated_at=datetime.now().strftime("%Y-%m-%d"),
                )
                db.session.add(new_soc)
                added_count += 1
                
        db.session.commit()
        if added_count > 0:
            flash(f"মোট {added_count}টি নতুন সোসাইটি সফলভাবে ইমপোর্ট হয়েছে!", "success")
        else:
            flash("যে নামগুলো দিয়েছেন সেগুলো ইতিমধ্যে ডাটাবেসে ছিল অথবা খালি ছিল।", "warning")
            
    except Exception as e:
        db.session.rollback()
        flash(f"ইমপোর্ট করার সময় ডাটাবেসে সমস্যা হয়েছে: {str(e)}", "danger")
        
    return redirect(url_for("dashboard"))

@app.route("/export_excel")
def export_excel():
    if not session.get("admin_logged_in"):
        return redirect(url_for("login"))

    si = StringIO()
    cw = csv.writer(si)

    # Excel Headers
    cw.writerow([
        "ID",
        "Society Name",
        "Registration Number",
        "Registration Date",
        "PAN Number",
        "Bank Details",
        "Registered Address",
        "President Name",
        "President Phone",
        "Secretary Name",
        "Secretary Phone",
        "Renewal Status",
        "Last Renewed FY",
        "All Renewed Years History",
    ])

    societies = Society.query.order_by(Society.society_name.asc()).all()
    for s in societies:
        cw.writerow([
            s.id,
            s.society_name,
            s.reg_number,
            s.reg_date or "",
            s.pan_number or "",
            s.bank_details or "",
            s.address or "",
            s.president_name or "",
            s.president_phone or "",
            s.secretary_name or "",
            s.secretary_phone or "",
            s.renewal_status,
            s.last_renewed_fy or "",
            s.renewed_years or "",
        ])

    output = make_response(si.getvalue().encode("utf-8-sig"))
    output.headers["Content-Disposition"] = (
        "attachment; filename=WB_Societies_Renewal_Report.csv"
    )
    output.headers["Content-type"] = "text/csv; charset=utf-8-sig"
    return output


@app.route("/add_society", methods=["POST"])
def add_society():
    if not session.get("admin_logged_in"):
        return redirect(url_for("login"))
    try:
        renewed_yrs = request.form.get("renewed_years", "").strip()
        last_fy = (
            renewed_yrs.split(",")[-1].strip() if renewed_yrs else get_current_fy()
        )

        new_soc = Society(
            society_name=request.form.get("society_name").strip(),
            reg_number=request.form.get("reg_number").strip(),
            reg_date=request.form.get("reg_date", "").strip(),
            pan_number=request.form.get("pan_number", "").strip().upper(),
            bank_details=request.form.get("bank_details", "").strip(),
            address=request.form.get("address", "").strip(),
            president_name=request.form.get("president_name", "").strip(),
            president_phone=request.form.get("president_phone", "").strip(),
            secretary_name=request.form.get("secretary_name", "").strip(),
            secretary_phone=request.form.get("secretary_phone", "").strip(),
            renewed_years=renewed_yrs,
            last_renewed_fy=last_fy if renewed_yrs else "",
            renewal_status=request.form.get("renewal_status", "Pending"),
            updated_at=datetime.now().strftime("%Y-%m-%d"),
        )
        db.session.add(new_soc)
        db.session.commit()
        flash(
            f"'{new_soc.society_name}' সফলভাবে ক্লাউড ডাটাবেসে সেভ হয়েছে!",
            "success",
        )
    except Exception as e:
        db.session.rollback()
        flash(
            "এই Registration Number ইতিমধ্যে ডাটাবেসে আছে অথবা কোনো সমস্যা হয়েছে!",
            "danger",
        )
    return redirect(url_for("dashboard"))


@app.route("/edit/<int:id>", methods=["POST"])
def edit_society(id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("login"))
    soc = Society.query.get_or_404(id)
    try:
        soc.society_name = request.form.get("society_name").strip()
        soc.reg_number = request.form.get("reg_number").strip()
        soc.reg_date = request.form.get("reg_date", "").strip()
        soc.pan_number = request.form.get("pan_number", "").strip().upper()
        soc.bank_details = request.form.get("bank_details", "").strip()
        soc.address = request.form.get("address", "").strip()
        soc.president_name = request.form.get("president_name", "").strip()
        soc.president_phone = request.form.get("president_phone", "").strip()
        soc.secretary_name = request.form.get("secretary_name", "").strip()
        soc.secretary_phone = request.form.get("secretary_phone", "").strip()
        soc.renewed_years = request.form.get("renewed_years", "").strip()
        soc.renewal_status = request.form.get("renewal_status", "Pending")
        if soc.renewed_years:
            soc.last_renewed_fy = soc.renewed_years.split(",")[-1].strip()
        db.session.commit()
        flash("তথ্য সফলভাবে আপডেট করা হয়েছে!", "success")
    except Exception as e:
        db.session.rollback()
        flash("আপডেট করার সময় সমস্যা হয়েছে!", "danger")
    return redirect(url_for("dashboard"))


@app.route("/mark_complete/<int:id>", methods=["POST"])
def mark_complete(id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("login"))
    soc = Society.query.get_or_404(id)
    fy = request.form.get("completed_fy", "").strip()

    existing = [y.strip() for y in soc.renewed_years.split(",") if y.strip()]
    if fy and fy not in existing:
        existing.append(fy)

    soc.renewed_years = ", ".join(existing)
    soc.last_renewed_fy = fy
    soc.renewal_status = "Completed"
    db.session.commit()
    flash(
        f"'{soc.society_name}'-এর {fy} রিনিউয়াল Completed হিসেবে সেভ হয়েছে!",
        "success",
    )
    return redirect(url_for("dashboard"))


@app.route("/mark_pending/<int:id>")
def mark_pending(id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("login"))
    soc = Society.query.get_or_404(id)
    soc.renewal_status = "Pending"
    db.session.commit()
    flash(
        f"'{soc.society_name}'-কে আবার Pending তালিকায় নেওয়া হয়েছে।",
        "warning",
    )
    return redirect(url_for("dashboard"))


@app.route("/reset_all_pending")
def reset_all_pending():
    if not session.get("admin_logged_in"):
        return redirect(url_for("login"))
    Society.query.update({Society.renewal_status: "Pending"})
    db.session.commit()
    flash(
        "নতুন আর্থিক বছরের (After March) রিনিউয়াল সাইকেল শুরু হয়েছে—সব সোসাইটি এখন Pending লিস্টে!",
        "info",
    )
    return redirect(url_for("dashboard"))


@app.route("/delete/<int:id>")
def delete_society(id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("login"))
    soc = Society.query.get_or_404(id)
    db.session.delete(soc)
    db.session.commit()
    flash("সোসাইটি রেকর্ড ডিলিট করা হয়েছে।", "secondary")
    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5005, debug=True)
