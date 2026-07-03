from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import subprocess
import socket
import requests
import json
import re
import hashlib
import os
import sys
import uuid
import urllib.parse
import datetime
import smtplib
import random
import string
from email.mime.text import MIMEText

app = Flask(__name__)
app.secret_key = "osint-pro-3d-secret-key-change-me"

# ---- SMTP Config ----
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SMTP_USER = os.environ.get("SMTP_USER", "osint.xlookup@gmail.com")
SMTP_PASS = os.environ.get("SMTP_PASS", "NIKEDZ213a.")
SMTP_FROM = os.environ.get("SMTP_FROM", "osint.xlookup@gmail.com")
SITE_URL = os.environ.get("SITE_URL", "https://osint-x.fr")
DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")

def send_email(to, subject, body):
    if not SMTP_USER or not SMTP_PASS:
        return False
    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = SMTP_FROM
        msg["To"] = to
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
            s.starttls()
            s.login(SMTP_USER, SMTP_PASS)
            s.send_message(msg)
        return True
    except:
        return False

USERS_FILE = os.path.join(os.path.dirname(__file__), "users.json")
if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, "w") as f:
        json.dump({}, f)

ADMIN_USER = "ah.md213"
ADMIN_PASS = "adminosintx2024"

def ensure_admin():
    users = load_users()
    if ADMIN_USER not in users:
        salt = os.urandom(16).hex()
        pwhash = hashlib.sha256((ADMIN_PASS + salt).encode()).hexdigest()
        users[ADMIN_USER] = {
            "password": pwhash, "salt": salt, "is_admin": True,
            "credits": -1, "created": datetime.datetime.now().isoformat()
        }
        save_users(users)

def deduct_credits(username, cost=5):
    if username == ADMIN_USER:
        return True
    users = load_users()
    u = users.get(username)
    if not u:
        return False
    credits = u.get("credits", 0)
    if credits <= 0:
        return False
    u["credits"] = credits - cost
    save_users(users)
    return True

COMMON_PASSWORDS = {
    "123456", "password", "12345678", "qwerty", "123456789", "12345", "1234",
    "111111", "1234567", "sunshine", "qwerty123", "iloveyou", "princess",
    "admin", "welcome", "666666", "abc123", "football", "123123", "monkey",
    "654321", "charlie", "aa123456", "donald", "dragon", "1234567890",
    "michael", "baseball", "ashley", "letmein", "shadow", "master", "121212",
    "flower", "hottie", "login", "passw0rd", "starwars", "ninja", "mustang",
    "qazwsx", "000000", "trustno1", "batman", "solo", "whatever", "test123",
    "pass123", "azerty", "azertyuiop", "motdepasse", "mdp", "soleil", "123abc",
    "mot2passe", "password123", "azerty123", "jesuis", "lol123", "fuckyou",
    "hello123", "thomas", "nicolas", "bonjour", "toto123", "tata123",
}

OPEN_PORTS = [21, 22, 23, 25, 53, 80, 110, 143, 443, 445, 993, 995, 1433, 1521, 3306, 3389, 5432, 5900, 6379, 8080, 8443, 27017]

SERVICES = {
    21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS",
    80: "HTTP", 110: "POP3", 143: "IMAP", 443: "HTTPS", 445: "SMB",
    993: "IMAPS", 995: "POP3S", 1433: "MSSQL", 1521: "Oracle",
    3306: "MySQL", 3389: "RDP", 5432: "PostgreSQL", 5900: "VNC",
    6379: "Redis", 8080: "HTTP-Proxy", 8443: "HTTPS-Alt", 27017: "MongoDB",
    8443: "HTTPS-Alt", 9200: "Elasticsearch", 11211: "Memcached",
    27017: "MongoDB", 5000: "Flask-DEV",
}

# ---- Captcha ----
import random
def generate_captcha():
    a = random.randint(3, 15)
    b = random.randint(1, 10)
    op = random.choice(["+", "-"])
    if op == "-" and a < b:
        a, b = b, a
    answer = a + b if op == "+" else a - b
    return {"question": f"{a} {op} {b} = ?", "answer": str(answer)}

@app.route("/api/captcha", methods=["GET"])
def api_captcha():
    cap = generate_captcha()
    session["captcha_answer"] = cap["answer"]
    return jsonify({"question": cap["question"]})

# ---- Auth ----
def load_users():
    with open(USERS_FILE) as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

ensure_admin()

@app.route("/api/register", methods=["POST"])
def api_register():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()
    email = (data.get("email") or "").strip()
    cap = (data.get("captcha") or "").strip()
    if not cap or session.get("captcha_answer") != cap:
        return jsonify({"error": "CAPTCHA invalide. Rechargez la page et reessayez."})
    if len(username) < 3 or len(password) < 4:
        return jsonify({"error": "Username (3+) and password (4+) required."})
    if not email or not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return jsonify({"error": "Email invalide."})
    users = load_users()
    if username in users:
        return jsonify({"error": "Username already exists."})
    for u, ud in users.items():
        if ud.get("email") == email:
            return jsonify({"error": "Email deja utilise."})
    salt = os.urandom(16).hex()
    pwhash = hashlib.sha256((password + salt).encode()).hexdigest()
    users[username] = {
        "password": pwhash, "salt": salt, "is_admin": False, "credits": 100,
        "email": email, "theme": "red", "avatar": "1",
        "created": datetime.datetime.now().isoformat()
    }
    save_users(users)
    session["user"] = username
    return jsonify({"success": True, "user": username})

@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()
    users = load_users()
    if username not in users:
        return jsonify({"error": "Invalid credentials."})
    user = users[username]
    pwhash = hashlib.sha256((password + user["salt"]).encode()).hexdigest()
    if pwhash != user["password"]:
        return jsonify({"error": "Invalid credentials."})
    if user.get("banned"):
        return jsonify({"error": "Compte banni. Contactez l'administrateur."})
    session["user"] = username
    return jsonify({"success": True, "user": username})

@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.pop("user", None)
    return jsonify({"success": True})

def login_required(f):
    def wrap(*args, **kwargs):
        if "user" not in session:
            return jsonify({"error": "Authentification requise."}), 401
        users = load_users()
        u = users.get(session["user"], {})
        if u.get("banned"):
            session.pop("user", None)
            return jsonify({"error": "Compte banni. Contactez l'administrateur."}), 403
        return f(*args, **kwargs)
    wrap.__name__ = f.__name__
    return wrap

@app.route("/api/me", methods=["GET"])
def api_me():
    if "user" in session:
        users = load_users()
        u = users.get(session["user"], {})
    return jsonify({
        "user": session["user"],
        "email": u.get("email", ""),
        "created": u.get("created", "N/A"),
        "credits": u.get("credits", "N/A"),
        "is_admin": u.get("is_admin", False),
        "theme": u.get("theme", "red"),
        "avatar": u.get("avatar", "1"),
        "banned": u.get("banned", False),
        "warnings": u.get("warnings", [])
    })
    return jsonify({"user": None})

@app.route("/api/profile", methods=["GET"])
@login_required
def api_profile():
    users = load_users()
    u = users.get(session["user"], {})
    return jsonify({
        "username": session["user"],
        "created": u.get("created", "N/A"),
        "queries": len(load_history().get(session["user"], [])),
        "credits": u.get("credits", "N/A"),
        "is_admin": u.get("is_admin", False),
        "theme": u.get("theme", "red"),
        "avatar": u.get("avatar", "1"),
        "warnings": u.get("warnings", [])
    })

@app.route("/api/change_password", methods=["POST"])
@login_required
def api_change_password():
    data = request.get_json() or {}
    old = (data.get("old_password") or "").strip()
    new_pw = (data.get("new_password") or "").strip()
    if len(new_pw) < 4:
        return jsonify({"error": "New password must be 4+ characters."})
    users = load_users()
    u = users.get(session["user"])
    if not u:
        return jsonify({"error": "User not found."})
    pwhash = hashlib.sha256((old + u["salt"]).encode()).hexdigest()
    if pwhash != u["password"]:
        return jsonify({"error": "Current password incorrect."})
    salt = os.urandom(16).hex()
    u["password"] = hashlib.sha256((new_pw + salt).encode()).hexdigest()
    u["salt"] = salt
    u["changed"] = datetime.datetime.now().isoformat()
    save_users(users)
    return jsonify({"success": True})

@app.route("/api/update_settings", methods=["POST"])
@login_required
def api_update_settings():
    data = request.get_json() or {}
    users = load_users()
    u = users.get(session["user"])
    if not u:
        return jsonify({"error": "User not found."})
    if "theme" in data:
        u["theme"] = data["theme"]
    if "avatar" in data:
        u["avatar"] = str(data["avatar"])
    save_users(users)
    return jsonify({"success": True, "theme": u.get("theme","red"), "avatar": u.get("avatar","1")})

# ---- Admin ----
def admin_required(f):
    def wrap(*args, **kwargs):
        if "user" not in session:
            return jsonify({"error": "Auth required."}), 401
        users = load_users()
        u = users.get(session["user"], {})
        if not u.get("is_admin"):
            return jsonify({"error": "Admin only."}), 403
        return f(*args, **kwargs)
    wrap.__name__ = f.__name__
    return wrap

@app.route("/api/admin/check", methods=["GET"])
@login_required
def api_admin_check():
    users = load_users()
    u = users.get(session["user"], {})
    return jsonify({"is_admin": u.get("is_admin", False)})

@app.route("/api/admin/users", methods=["GET"])
@admin_required
def api_admin_users():
    users = load_users()
    result = []
    for uname, data in users.items():
        result.append({
            "username": uname,
            "credits": data.get("credits", 0),
            "is_admin": data.get("is_admin", False),
            "created": data.get("created", "N/A"),
            "queries": len(load_history().get(uname, [])),
            "banned": data.get("banned", False),
            "warnings": data.get("warnings", [])
        })
    return jsonify({"users": result})

@app.route("/api/admin/set_credits", methods=["POST"])
@admin_required
def api_admin_set_credits():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    amount = data.get("amount")
    if not username or amount is None:
        return jsonify({"error": "Missing username or amount."})
    users = load_users()
    if username not in users:
        return jsonify({"error": "User not found."})
    users[username]["credits"] = int(amount)
    save_users(users)
    return jsonify({"success": True, "username": username, "credits": int(amount)})

@app.route("/api/admin/ban", methods=["POST"])
@admin_required
def api_admin_ban():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    ban = data.get("ban", True)
    if not username:
        return jsonify({"error": "Missing username."})
    users = load_users()
    if username not in users:
        return jsonify({"error": "User not found."})
    if users[username].get("is_admin"):
        return jsonify({"error": "Cannot ban admin."})
    users[username]["banned"] = ban
    save_users(users)
    return jsonify({"success": True, "username": username, "banned": ban})

@app.route("/api/admin/warn", methods=["POST"])
@admin_required
def api_admin_warn():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    reason = (data.get("reason") or "").strip()
    if not username or not reason:
        return jsonify({"error": "Missing username or reason."})
    users = load_users()
    if username not in users:
        return jsonify({"error": "User not found."})
    if "warnings" not in users[username]:
        users[username]["warnings"] = []
    users[username]["warnings"].append({
        "reason": reason,
        "date": datetime.datetime.now().isoformat(),
        "by": session["user"]
    })
    save_users(users)
    return jsonify({"success": True, "username": username, "warnings": users[username]["warnings"]})

@app.route("/api/admin/clear_warnings", methods=["POST"])
@admin_required
def api_admin_clear_warnings():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    if not username:
        return jsonify({"error": "Missing username."})
    users = load_users()
    if username not in users:
        return jsonify({"error": "User not found."})
    users[username]["warnings"] = []
    save_users(users)
    return jsonify({"success": True, "username": username})

@app.route("/api/admin/announce", methods=["POST"])
@admin_required
def api_admin_announce():
    data = request.get_json() or {}
    message = (data.get("message") or "").strip()
    level = data.get("level", "info")
    if not message:
        return jsonify({"error": "Missing message."})
    ann = load_announcements()
    ann.insert(0, {
        "id": str(uuid.uuid4())[:8],
        "message": message,
        "level": level,
        "date": datetime.datetime.now().isoformat(),
        "by": session["user"]
    })
    save_announcements(ann)
    return jsonify({"success": True, "announcements": ann})

@app.route("/api/admin/delete_announce", methods=["POST"])
@admin_required
def api_admin_delete_announce():
    data = request.get_json() or {}
    aid = (data.get("id") or "").strip()
    if not aid:
        return jsonify({"error": "Missing id."})
    ann = load_announcements()
    ann = [a for a in ann if a["id"] != aid]
    save_announcements(ann)
    return jsonify({"success": True, "announcements": ann})

@app.route("/api/admin/delete_user", methods=["POST"])
@admin_required
def api_admin_delete_user():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    if not username:
        return jsonify({"error": "Missing username."})
    users = load_users()
    if username not in users:
        return jsonify({"error": "User not found."})
    if users[username].get("is_admin"):
        return jsonify({"error": "Cannot delete admin."})
    del users[username]
    save_users(users)
    history = load_history()
    if username in history:
        del history[username]
        with open(HISTORY_FILE, "w") as f:
            json.dump(history, f, indent=2)
    return jsonify({"success": True, "message": "User " + username + " deleted."})

@app.route("/api/announcements", methods=["GET"])
def api_announcements():
    ann = load_announcements()
    return jsonify({"announcements": ann})

# ---- History ----
HISTORY_FILE = os.path.join(os.path.dirname(__file__), "history.json")
if not os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, "w") as f:
        json.dump({}, f)

ANNOUNCEMENTS_FILE = os.path.join(os.path.dirname(__file__), "announcements.json")
if not os.path.exists(ANNOUNCEMENTS_FILE):
    with open(ANNOUNCEMENTS_FILE, "w") as f:
        json.dump([], f)

def load_announcements():
    with open(ANNOUNCEMENTS_FILE) as f:
        return json.load(f)

def save_announcements(ann):
    with open(ANNOUNCEMENTS_FILE, "w") as f:
        json.dump(ann, f, indent=2)

def load_history():
    with open(HISTORY_FILE) as f:
        return json.load(f)

def save_history(h):
    with open(HISTORY_FILE, "w") as f:
        json.dump(h, f, indent=2)

def add_history(user, tool, target, result_summary):
    h = load_history()
    if user not in h:
        h[user] = []
    h[user].insert(0, {
        "tool": tool, "target": target, "summary": result_summary[:120],
        "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    h[user] = h[user][:30]
    save_history(h)

@app.route("/api/history", methods=["GET"])
@login_required
def api_history():
    h = load_history()
    return jsonify({"history": h.get(session["user"], [])})

@app.route("/api/export", methods=["POST"])
@login_required
def api_export():
    d = request.get_json() or {}
    data = d.get("data", "")
    fmt = d.get("format", "txt")
    name = d.get("name", "export")
    return jsonify({"content": data, "filename": f"{name}.{fmt}", "format": fmt})

# ---- Helpers ----
def resolve_domain(domain):
    try:
        return socket.gethostbyname(domain)
    except:
        return None

def dns_lookup(domain):
    try:
        r = subprocess.run(["nslookup", domain], capture_output=True, text=True, timeout=10)
        return r.stdout or "No DNS info."
    except:
        return "DNS lookup failed."

def dns_record(domain, rtype):
    try:
        r = subprocess.run(["nslookup", "-type=" + rtype, domain], capture_output=True, text=True, timeout=10)
        lines = [l.strip() for l in r.stdout.split("\n") if l.strip()]
        return "\n".join(lines[:25]) if lines else "No records"
    except:
        return f"{rtype} lookup failed"

def geolocate_ip(ip):
    try:
        resp = requests.get(f"http://ip-api.com/json/{ip}", timeout=10)
        if resp.status_code == 200:
            d = resp.json()
            if d.get("status") == "success":
                return {
                    "ip": ip, "country": d.get("country","N/A"), "region": d.get("regionName","N/A"),
                    "city": d.get("city","N/A"), "zip": d.get("zip","N/A"), "lat": d.get("lat","N/A"),
                    "lon": d.get("lon","N/A"), "isp": d.get("isp","N/A"), "org": d.get("org","N/A"),
                    "as": d.get("as","N/A"), "timezone": d.get("timezone","N/A"),
                }
        return {"error": "Geolocation failed."}
    except:
        return {"error": "Geolocation failed."}

def whois_lookup(domain):
    try:
        r = subprocess.run(["whois", domain], capture_output=True, text=True, timeout=15)
        lines = r.stdout.split("\n")[:40]
        return "\n".join(lines) if lines else "No WHOIS data."
    except:
        return "WHOIS lookup failed."

def scan_ports(host):
    open_ports = []
    for port in OPEN_PORTS:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1.5)
            if sock.connect_ex((host, port)) == 0:
                open_ports.append(port)
            sock.close()
        except:
            pass
    return open_ports

# ---- Routes ----
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/dns", methods=["POST"])
@login_required
def api_dns():
    if not deduct_credits(session["user"]):
        return jsonify({"error": "Credits insuffisants. 5 cr\u00e9dits requis par requ\u00eate."})
    d = request.get_json()
    domain = d.get("target","").strip()
    if not domain:
        return jsonify({"error": "No target."})
    ip = resolve_domain(domain)
    dns = dns_lookup(domain)
    records = {}
    for rt in ["A", "AAAA", "MX", "NS", "TXT", "CNAME"]:
        records[rt] = dns_record(domain, rt)
    add_history(session["user"], "DNS", domain, f"IP: {ip or 'N/A'}")
    return jsonify({"domain": domain, "ip": ip, "dns_result": dns, "records": records})

@app.route("/api/ip", methods=["POST"])
@login_required
def api_ip():
    if not deduct_credits(session["user"]):
        return jsonify({"error": "Credits insuffisants. 5 cr\u00e9dits requis par requ\u00eate."})
    d = request.get_json()
    target = d.get("target","").strip()
    if not target:
        return jsonify({"error": "No target."})
    if not re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", target):
        ip = resolve_domain(target)
        if not ip:
            return jsonify({"error": "Could not resolve."})
        target = ip
    result = geolocate_ip(target)
    add_history(session["user"], "IP", d.get("target","").strip(), f"{result.get('country','?')} / {result.get('city','?')}")
    return jsonify(result)

@app.route("/api/whois", methods=["POST"])
@login_required
def api_whois():
    if not deduct_credits(session["user"]):
        return jsonify({"error": "Credits insuffisants. 5 cr\u00e9dits requis par requ\u00eate."})
    d = request.get_json()
    domain = d.get("target","").strip()
    if not domain:
        return jsonify({"error": "No target."})
    result = whois_lookup(domain)
    add_history(session["user"], "WHOIS", domain, f"{len(result.split(chr(10)))} lines")
    return jsonify({"domain": domain, "result": result})

@app.route("/api/headers", methods=["POST"])
@login_required
def api_headers():
    if not deduct_credits(session["user"]):
        return jsonify({"error": "Credits insuffisants. 5 cr\u00e9dits requis par requ\u00eate."})
    d = request.get_json()
    url = d.get("target","").strip()
    if not url:
        return jsonify({"error": "No URL."})
    try:
        if not url.startswith("http"):
            url = "https://" + url
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        h = dict(resp.headers)
        return jsonify({
            "status_code": resp.status_code, "server": h.get("Server","N/A"),
            "content_type": h.get("Content-Type","N/A"), "x_powered_by": h.get("X-Powered-By","N/A"),
            "x_frame_options": h.get("X-Frame-Options","N/A"),
            "strict_transport": h.get("Strict-Transport-Security","N/A"),
            "cors": h.get("Access-Control-Allow-Origin","N/A"),
            "cookies": h.get("Set-Cookie","N/A"),
        })
    except Exception as e:
        return jsonify({"error": f"Header check failed: {e}"})

@app.route("/api/ports", methods=["POST"])
@login_required
def api_ports():
    if not deduct_credits(session["user"]):
        return jsonify({"error": "Credits insuffisants. 5 cr\u00e9dits requis par requ\u00eate."})
    d = request.get_json()
    target = d.get("target","").strip()
    if not target:
        return jsonify({"error": "No target."})
    targets = [t.strip() for t in target.replace(","," ").split() if t.strip()]
    all_results = []
    for t in targets[:5]:
        if not re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", t):
            ip = resolve_domain(t)
            if ip:
                t = ip
            else:
                continue
        ports = scan_ports(t)
        all_results.append({"host": t, "open_ports": [{"port": p, "service": SERVICES.get(p, "Unknown"), "state": "open"} for p in ports], "count": len(ports)})
    if not all_results:
        return jsonify({"error": "Could not resolve any target."})
    add_history(session["user"], "Ports", " / ".join(targets[:3]), f"{sum(r['count'] for r in all_results)} ports open")
    return jsonify({"results": all_results, "total_targets": len(all_results)})

@app.route("/api/email", methods=["POST"])
@login_required
def api_email():
    if not deduct_credits(session["user"]):
        return jsonify({"error": "Credits insuffisants. 5 cr\u00e9dits requis par requ\u00eate."})
    d = request.get_json()
    email = d.get("target","").strip()
    if not email or "@" not in email:
        return jsonify({"error": "Invalid email."})
    domain = email.split("@")[1]

    mx_servers = []
    try:
        r = subprocess.run(["nslookup", "-type=MX", domain], capture_output=True, text=True, timeout=10)
        for line in r.stdout.split("\n"):
            if "MX" in line or "mail exchanger" in line.lower():
                mx_servers.append(line.strip())
    except:
        mx_servers = ["MX lookup failed."]

    breach_details = []
    try:
        resp = requests.get(
            f"https://haveibeenpwned.com/api/v3/breachedaccount/{email}?truncateResponse=false",
            timeout=10, headers={"hibp-api-key": "", "User-Agent": "OSINT-Pro-Toolkit"}
        )
        if resp.status_code == 200:
            for b in resp.json():
                breach_details.append({
                    "name": b.get("Name","Unknown"), "domain": b.get("Domain","N/A"),
                    "date": b.get("BreachDate","N/A"), "data_classes": b.get("DataClasses",[]),
                    "pwn_count": b.get("PwnCount",0), "is_verified": b.get("IsVerified",False),
                    "is_sensitive": b.get("IsSensitive",False), "is_spam_list": b.get("IsSpamList",False),
                })
    except:
        pass

    all_data_types = set()
    for bd in breach_details:
        for dc in bd.get("data_classes",[]):
            all_data_types.add(dc)
    has_password_leak = "Passwords" in all_data_types

    password_analysis = {
        "common_password_detected": False, "reused_password_risk": has_password_leak, "advice": []
    }
    local_part = email.split("@")[0].lower()
    for cp in COMMON_PASSWORDS:
        if cp in local_part:
            password_analysis["common_password_detected"] = True
            password_analysis["advice"].append("Votre email contient un mot de passe courant.")
            break
    if has_password_leak:
        password_analysis["advice"].append("Mot de passe fuité ! Changez-le immédiatement.")
        password_analysis["advice"].append("Ne le réutilisez jamais ailleurs.")

    tips = [
        {"icon": "<svg viewBox=\"0 0 16 16\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.4\" width=\"16\" height=\"16\"><circle cx=\"5\" cy=\"8\" r=\"3.5\"/><path d=\"M8 8l5.5 5.5\"/><line x1=\"11\" y1=\"11\" x2=\"13\" y2=\"13\"/></svg>", "title": "Mot de passe unique partout", "desc": "Utilisez Bitwarden ou 1Password."},
        {"icon": "<svg viewBox=\"0 0 16 16\" fill=\"currentColor\" width=\"16\" height=\"16\"><path d=\"M8 1l6 2.09v3.455c0 2.544-1.45 4.773-3.6 5.736L8 13.5l-2.4-1.21A6.218 6.218 0 0 1 2 6.545V3.09L8 1z\"/></svg>", "title": "Activez la 2FA", "desc": "Authy, Google Authenticator, clé FIDO2."},
        {"icon": "<svg viewBox=\"0 0 16 16\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.2\" width=\"16\" height=\"16\"><path d=\"M1 3h14v10H1V3z\"/><polyline points=\"1 3 8 9 15 3\"/></svg>", "title": "Alias email", "desc": "SimpleLogin ou Firefox Relay pour les inscriptions."},
        {"icon": "<svg viewBox=\"0 0 16 16\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.4\" width=\"16\" height=\"16\"><rect x=\"2\" y=\"3\" width=\"12\" height=\"10\" rx=\"1.5\"/><circle cx=\"9\" cy=\"8\" r=\"1.5\"/><path d=\"M5 8h.5M10.5 8H11\"/></svg>", "title": "Surveillez HaveIBeenPwned", "desc": "Créez une alerte sur HIBP."},
        {"icon": "<svg viewBox=\"0 0 16 16\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.4\" width=\"16\" height=\"16\"><path d=\"M2 8a6 6 0 0 1 11.6-2.5\"/><polyline points=\"12 1 13.6 5.5 9 5.5\"/><path d=\"M14 8a6 6 0 0 1-11.6 2.5\"/><polyline points=\"4 15 2.4 10.5 7 10.5\"/></svg>", "title": "Rotation régulière", "desc": "Changez vos mots de passe tous les 3-6 mois."},
        {"icon": "<svg viewBox=\"0 0 16 16\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.4\" width=\"16\" height=\"16\"><circle cx=\"7.5\" cy=\"10\" r=\"3\"/><path d=\"M6 3h4l2 3-1.5 3h-5L4 6l2-3z\"/></svg>", "title": "Méfiez-vous du phishing", "desc": "Ne cliquez jamais sur un lien suspect."},
    ]

    return jsonify({
        "email": email, "domain": domain, "mx_servers": mx_servers,
        "breach_details": breach_details, "all_data_types": sorted(list(all_data_types)),
        "has_password_leak": has_password_leak,
        "password_analysis": password_analysis, "protection_tips": tips,
    })

# ---- Bulk ----
@app.route("/api/bulk", methods=["POST"])
@login_required
def api_bulk():
    if not deduct_credits(session["user"]):
        return jsonify({"error": "Credits insuffisants. 5 cr\u00e9dits requis par requ\u00eate."})
    d = request.get_json()
    targets = d.get("targets", "").strip()
    tool = d.get("tool", "dns")
    items = [t.strip() for t in targets.replace(","," ").split() if t.strip()][:10]
    results = []
    for item in items:
        if tool == "dns":
            ip = resolve_domain(item)
            results.append({"target": item, "ip": ip or "N/A"})
        elif tool == "ip":
            ip = resolve_domain(item) if not re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", item) else item
            if ip:
                geo = geolocate_ip(ip)
                results.append({"target": item, "ip": ip, "country": geo.get("country","N/A")})
            else:
                results.append({"target": item, "error": "Unresolved"})
    add_history(session["user"], f"Bulk-{tool}", f"{len(items)} targets", f"{len(results)} done")
    return jsonify({"results": results, "count": len(results)})

# ---- Tech Detect ----
@app.route("/api/tech", methods=["POST"])
@login_required
def api_tech():
    if not deduct_credits(session["user"]):
        return jsonify({"error": "Credits insuffisants. 5 cr\u00e9dits requis par requ\u00eate."})
    d = request.get_json()
    url = d.get("target","").strip()
    if not url:
        return jsonify({"error": "No URL."})
    if not url.startswith("http"):
        url = "https://" + url
    try:
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        html = r.text.lower()
        techs = []
        headers_str = json.dumps(dict(r.headers)).lower()
        if "nginx" in headers_str: techs.append("Nginx")
        if "apache" in headers_str: techs.append("Apache")
        if "cloudflare" in headers_str: techs.append("Cloudflare")
        if "wordpress" in headers_str or "/wp-content/" in html: techs.append("WordPress")
        if "jquery" in html: techs.append("jQuery")
        if "react" in html or "reactdom" in html: techs.append("React")
        if "vue" in html or "vuejs" in html: techs.append("Vue.js")
        if "angular" in html: techs.append("Angular")
        if "bootstrap" in html: techs.append("Bootstrap")
        if "laravel" in html or "livewire" in html: techs.append("Laravel")
        if "django" in html: techs.append("Django")
        if "flask" in html or "werkzeug" in headers_str: techs.append("Flask")
        if "express" in html: techs.append("Express")
        if "next" in html or "_next/" in html: techs.append("Next.js")
        if "shopify" in html or "myshopify" in html: techs.append("Shopify")
        if not techs:
            techs.append("Generic / Unknown")
        add_history(session["user"], "Tech", url, f"{len(techs)} tech(s) detected")
        return jsonify({"url": url, "status": r.status_code, "technologies": techs, "count": len(techs)})
    except Exception as e:
        return jsonify({"error": f"Tech detect failed: {e}"})

# ===== NEW TOOLS =====

# 1. Subdomain Scanner (via crt.sh)
@app.route("/api/subdomains", methods=["POST"])
@login_required
def api_subdomains():
    if not deduct_credits(session["user"]):
        return jsonify({"error": "Credits insuffisants. 5 cr\u00e9dits requis par requ\u00eate."})
    d = request.get_json()
    domain = d.get("target","").strip().lower()
    if not domain:
        return jsonify({"error": "No domain."})
    try:
        resp = requests.get(f"https://crt.sh/?q=%.{domain}&output=json", timeout=15)
        if resp.status_code == 200:
            entries = resp.json()
            subs = set()
            for e in entries[:100]:
                name = e.get("name_value", "")
                for n in name.split("\n"):
                    n = n.strip().lower()
                    if n.endswith("." + domain) or n == domain:
                        subs.add(n)
            return jsonify({"domain": domain, "count": len(subs), "subdomains": sorted(list(subs))[:50]})
        return jsonify({"error": "crt.sh API error."})
    except Exception as e:
        return jsonify({"error": f"Subdomain scan failed: {e}"})

# 2. SSL Certificate Checker
@app.route("/api/ssl", methods=["POST"])
@login_required
def api_ssl():
    if not deduct_credits(session["user"]):
        return jsonify({"error": "Credits insuffisants. 5 cr\u00e9dits requis par requ\u00eate."})
    d = request.get_json()
    host = d.get("target","").strip()
    if not host:
        return jsonify({"error": "No host."})
    host = host.replace("https://","").replace("http://","").split("/")[0].split(":")[0]
    try:
        ctx = ssl_lib.create_default_context()
        with socket.create_connection((host, 443), timeout=8) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert()
                issuer = dict(x[0] for x in cert.get("issuer", []))
                subject = dict(x[0] for x in cert.get("subject", []))
                return jsonify({
                    "host": host,
                    "issuer": issuer.get("organizationName", issuer.get("commonName", "N/A")),
                    "subject": subject.get("commonName", "N/A"),
                    "valid_from": cert.get("notBefore", "N/A"),
                    "valid_to": cert.get("notAfter", "N/A"),
                    "serial": cert.get("serialNumber", "N/A"),
                    "algo": cert.get("signatureAlgorithm", "N/A"),
                    "san": cert.get("subjectAltName", [("DNS", "N/A")])[0][1],
                    "expired": cert.get("notAfter", "N/A") < datetime.datetime.now().strftime("%b %d %H:%M:%S %Y GMT"),
                })
    except Exception as e:
        return jsonify({"error": f"SSL check failed: {e}"})

# 3. Phone Number Info
@app.route("/api/phone", methods=["POST"])
@login_required
def api_phone():
    if not deduct_credits(session["user"]):
        return jsonify({"error": "Credits insuffisants. 5 cr\u00e9dits requis par requ\u00eate."})
    d = request.get_json()
    phone = d.get("target","").strip()
    phone_clean = re.sub(r"[^\d+]", "", phone)
    if not phone_clean:
        return jsonify({"error": "Invalid phone number."})
    country_codes = {
        "33": "France", "1": "USA/Canada", "44": "UK", "49": "Germany",
        "39": "Italy", "34": "Spain", "31": "Netherlands", "32": "Belgium",
        "41": "Switzerland", "46": "Sweden", "47": "Norway", "45": "Denmark",
        "48": "Poland", "351": "Portugal", "353": "Ireland", "30": "Greece",
        "90": "Turkey", "7": "Russia", "86": "China", "81": "Japan",
        "82": "South Korea", "91": "India", "55": "Brazil", "52": "Mexico",
        "61": "Australia", "971": "UAE", "966": "Saudi Arabia", "972": "Israel",
    }
    detected = "Unknown"
    for code, country in sorted(country_codes.items(), key=lambda x: -len(x[0])):
        if phone_clean.startswith("+" + code) or phone_clean.startswith(code):
            detected = country
            break
    length = len(phone_clean.replace("+",""))
    return jsonify({
        "phone": phone_clean, "country": detected,
        "length": length, "format": "International" if phone_clean.startswith("+") else "Local",
        "possible_carrier": "N/A (no API key)",
    })

# 4. Username / Social Search
SOCIAL_SITES = [
    {"name": "GitHub", "url": "https://github.com/{u}"},
    {"name": "Twitter/X", "url": "https://twitter.com/{u}"},
    {"name": "Instagram", "url": "https://instagram.com/{u}"},
    {"name": "Reddit", "url": "https://reddit.com/user/{u}"},
    {"name": "Medium", "url": "https://medium.com/@{u}"},
    {"name": "Pinterest", "url": "https://pinterest.com/{u}"},
    {"name": "TikTok", "url": "https://tiktok.com/@{u}"},
    {"name": "YouTube", "url": "https://youtube.com/@{u}"},
    {"name": "Twitch", "url": "https://twitch.tv/{u}"},
    {"name": "Dev.to", "url": "https://dev.to/{u}"},
    {"name": "Keybase", "url": "https://keybase.io/{u}"},
    {"name": "About.me", "url": "https://about.me/{u}"},
]

@app.route("/api/username", methods=["POST"])
@login_required
def api_username():
    if not deduct_credits(session["user"], 20):
        return jsonify({"error": "Credits insuffisants. 20 cr\u00e9dits requis par requ\u00eate."})
    d = request.get_json()
    username = d.get("target","").strip()
    if not username or len(username) < 2:
        return jsonify({"error": "Invalid username."})
    results = []
    for site in SOCIAL_SITES:
        url = site["url"].replace("{u}", username)
        try:
            r = requests.head(url, timeout=5, allow_redirects=True)
            if r.status_code < 400:
                results.append({"name": site["name"], "url": url, "status": "found"})
            else:
                results.append({"name": site["name"], "url": url, "status": "not_found"})
        except:
            results.append({"name": site["name"], "url": url, "status": "error"})
    found = [r for r in results if r["status"] == "found"]
    return jsonify({"username": username, "found_count": len(found), "results": results})

# 5. MAC Address Lookup
@app.route("/api/mac", methods=["POST"])
@login_required
def api_mac():
    if not deduct_credits(session["user"]):
        return jsonify({"error": "Credits insuffisants. 5 cr\u00e9dits requis par requ\u00eate."})
    d = request.get_json()
    mac = d.get("target","").strip().upper()
    mac = re.sub(r"[^A-F0-9]", "", mac)[:12]
    if len(mac) < 6:
        return jsonify({"error": "Invalid MAC (need at least 6 hex chars)."})
    oui = mac[:6]
    try:
        resp = requests.get(f"https://api.macvendors.com/{oui}", timeout=8)
        vendor = resp.text.strip() if resp.status_code == 200 else "Unknown"
        return jsonify({"mac": mac, "oui": oui, "vendor": vendor, "format": ":".join(mac[i:i+2] for i in range(0,12,2))})
    except:
        return jsonify({"mac": mac, "oui": oui, "vendor": "Lookup failed"})

# 6. Hash Type Identifier
HASH_PATTERNS = [
    (re.compile(r"^[a-f0-9]{32}$"), "MD5", 32),
    (re.compile(r"^[a-f0-9]{40}$"), "SHA1", 40),
    (re.compile(r"^[a-f0-9]{56}$"), "SHA224", 56),
    (re.compile(r"^[a-f0-9]{64}$"), "SHA256", 64),
    (re.compile(r"^[a-f0-9]{96}$"), "SHA384", 96),
    (re.compile(r"^[a-f0-9]{128}$"), "SHA512", 128),
    (re.compile(r"^[a-f0-9]{16}$"), "MySQL3 / NTLM", 16),
    (re.compile(r"^\$2[aby]\$.{56}$"), "bcrypt", 60),
    (re.compile(r"^\$5\$.{43}$"), "SHA256-Crypt", 43),
    (re.compile(r"^\$6\$.{86}$"), "SHA512-Crypt", 86),
    (re.compile(r"^[a-f0-9]{32}:[a-f0-9]{32}$"), "MD5($pass.$salt)", 65),
    (re.compile(r"^[0-9a-f]{32,40}$"), "MD5/SHA1 (mixed)", None),
]

@app.route("/api/hash", methods=["POST"])
@login_required
def api_hash():
    if not deduct_credits(session["user"]):
        return jsonify({"error": "Credits insuffisants. 5 cr\u00e9dits requis par requ\u00eate."})
    d = request.get_json()
    h = d.get("target","").strip()
    if not h:
        return jsonify({"error": "No hash provided."})
    results = []
    for pattern, name, length in HASH_PATTERNS:
        if pattern.match(h):
            results.append({"type": name, "length": length or len(h), "char_count": len(h)})
    if not results:
        results.append({"type": "Unknown / Custom", "length": len(h), "char_count": len(h)})
    return jsonify({"hash": h, "length": len(h), "possible_types": results})

# ===== 7. TikTok Lookup =====
@app.route("/api/tiktok", methods=["POST"])
@login_required
def api_tiktok():
    if not deduct_credits(session["user"], 20):
        return jsonify({"error": "Credits insuffisants. 20 cr\u00e9dits requis par requ\u00eate."})
    d = request.get_json()
    username = d.get("target","").strip().lower().replace("@","")
    if not username or len(username) < 2:
        return jsonify({"error": "Invalid username."})
    try:
        resp = requests.get(f"https://www.tiktok.com/@{username}", timeout=10,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                     "Accept-Language": "en-US,en;q=0.9"})
        if resp.status_code != 200:
            return jsonify({"username": username, "exists": False, "error": "Profil introuvable."})
        html = resp.text
        nickname = username
        bio = ""
        followers = "N/A"
        following = "N/A"
        likes = "N/A"
        verified = False
        avatar = ""
        m = re.search(r'"nickname"\s*:\s*"([^"]+)"', html)
        if m: nickname = m.group(1)
        m = re.search(r'"uniqueId"\s*:\s*"([^"]+)"', html)
        if m: username = m.group(1)
        m = re.search(r'"signature"\s*:\s*"([^"]+)"', html)
        if m: bio = m.group(1).replace("\\n","\n")
        m = re.search(r'"followerCount"\s*:\s*(\d+)', html)
        if m: followers = int(m.group(1))
        m = re.search(r'"followingCount"\s*:\s*(\d+)', html)
        if m: following = int(m.group(1))
        m = re.search(r'"heartCount"\s*:\s*(\d+)', html)
        if m: likes = int(m.group(1))
        m = re.search(r'"verified"\s*:\s*(true|false)', html)
        if m: verified = m.group(1) == "true"
        m = re.search(r'"avatarLarger"\s*:\s*"([^"]+)"', html)
        if m: avatar = m.group(1).replace("\\u002F","/")
        return jsonify({
            "username": username, "nickname": nickname, "bio": bio,
            "followers": followers, "following": following, "likes": likes,
            "verified": verified, "avatar": avatar, "exists": True,
            "url": f"https://www.tiktok.com/@{username}"
        })
    except Exception as e:
        return jsonify({"error": f"TikTok lookup failed: {str(e)}"})

# ===== 8. Snapchat Lookup =====
@app.route("/api/snapchat", methods=["POST"])
@login_required
def api_snapchat():
    if not deduct_credits(session["user"], 20):
        return jsonify({"error": "Credits insuffisants. 20 cr\u00e9dits requis par requ\u00eate."})
    d = request.get_json()
    username = d.get("target","").strip().lower()
    if not username or len(username) < 2:
        return jsonify({"error": "Invalid username."})
    try:
        resp = requests.get(f"https://www.snapchat.com/add/{username}", timeout=10,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                     "Accept-Language": "en-US,en;q=0.9"},
            allow_redirects=True)
        exists = resp.status_code == 200 and "this content could not be found" not in resp.text.lower() and "page not found" not in resp.text.lower()
        display_name = username
        if exists:
            m = re.search(r'"displayName"\s*:\s*"([^"]+)"', resp.text)
            if m: display_name = m.group(1)
            m = re.search(r'"bitmojiAvatarUrl"\s*:\s*"([^"]+)"', resp.text)
        return jsonify({
            "username": username, "exists": exists,
            "display_name": display_name if exists else "N/A",
            "url": f"https://www.snapchat.com/add/{username}"
        })
    except Exception as e:
        return jsonify({"error": f"Snapchat lookup failed: {str(e)}"})

# ===== 9. Instagram Lookup =====
@app.route("/api/instagram", methods=["POST"])
@login_required
def api_instagram():
    if not deduct_credits(session["user"], 20):
        return jsonify({"error": "Credits insuffisants. 20 cr\u00e9dits requis par requ\u00eate."})
    d = request.get_json()
    username = d.get("target","").strip().lower().replace("@","")
    if not username or len(username) < 2:
        return jsonify({"error": "Invalid username."})
    try:
        resp = requests.get(f"https://www.instagram.com/{username}/", timeout=10,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                     "Accept-Language": "en-US,en;q=0.9"})
        if resp.status_code != 200 and resp.status_code != 404:
            return jsonify({"error": f"HTTP {resp.status_code}"})
        html = resp.text
        if "the link you followed may be broken" in html.lower() or "page isn't available" in html.lower() or resp.status_code == 404:
            return jsonify({"username": username, "exists": False, "error": "Profil introuvable."})
        full_name = username
        bio = ""
        posts = "N/A"
        followers = "N/A"
        following = "N/A"
        verified = False
        private = False
        avatar = ""
        m = re.search(r'"full_name"\s*:\s*"([^"]+)"', html)
        if m: full_name = m.group(1)
        m = re.search(r'"biography"\s*:\s*"([^"]+)"', html)
        if m: bio = m.group(1).replace("\\n","\n")
        m = re.search(r'"edge_followed_by"\s*:\s*{\s*"count"\s*:\s*(\d+)', html)
        if m: followers = int(m.group(1))
        m = re.search(r'"edge_follow"\s*:\s*{\s*"count"\s*:\s*(\d+)', html)
        if m: following = int(m.group(1))
        m = re.search(r'"edge_owner_to_timeline_media"\s*:\s*{\s*"count"\s*:\s*(\d+)', html)
        if m: posts = int(m.group(1))
        m = re.search(r'"is_verified"\s*:\s*(true|false)', html)
        if m: verified = m.group(1) == "true"
        m = re.search(r'"is_private"\s*:\s*(true|false)', html)
        if m: private = m.group(1) == "true"
        m = re.search(r'"profile_pic_url_hd"\s*:\s*"([^"]+)"', html)
        if m: avatar = m.group(1).replace("\\u002F","/")
        m = re.search(r'property="og:image"[^>]*content="([^"]+)"', html)
        if not avatar and m: avatar = m.group(1)
        return jsonify({
            "username": username, "full_name": full_name, "bio": bio,
            "posts": posts, "followers": followers, "following": following,
            "verified": verified, "private": private, "avatar": avatar,
            "exists": True, "url": f"https://www.instagram.com/{username}/"
        })
    except Exception as e:
        return jsonify({"error": f"Instagram lookup failed: {str(e)}"})

# ===== 10. YouTube Lookup (Admin only) =====
@app.route("/api/yt", methods=["POST"])
@admin_required
def api_yt():
    d = request.get_json()
    username = d.get("target","").strip().lower().replace("@","")
    if not username or len(username) < 2:
        return jsonify({"error": "Invalid channel."})
    try:
        resp = requests.get(f"https://www.youtube.com/@{username}", timeout=10,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
        if resp.status_code != 200:
            resp = requests.get(f"https://www.youtube.com/channel/{username}", timeout=10,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
        if resp.status_code != 200 and resp.status_code != 404:
            return jsonify({"error": f"HTTP {resp.status_code}"})
        html = resp.text
        if "content is not available" in html.lower() or resp.status_code == 404:
            return jsonify({"exists": False, "error": "Cha\u00eene introuvable."})
        name = username
        subs = "N/A"
        verified = False
        avatar = ""
        m = re.search(r'"name"\s*:\s*"([^"]+)"', html)
        if m: name = m.group(1)
        m = re.search(r'"subscriberCount"\s*:\s*"(\d+)"', html)
        if m: subs = int(m.group(1))
        m = re.search(r'"subscriberCount"\s*:\s*(\d+)', html)
        if m: subs = int(m.group(1))
        m = re.search(r'<meta itemprop="interactionCount"[^>]*content="(\d+)"', html)
        if m: subs = int(m.group(1))
        m = re.search(r'"avatar"\s*:\s*\{\s*"thumbnails"\s*:\s*\[\s*\{\s*"url"\s*:\s*"([^"]+)"', html)
        if m: avatar = m.group(1).replace("\\/","/")
        return jsonify({
            "username": username, "name": name, "subscribers": subs,
            "verified": verified, "avatar": avatar,
            "exists": True, "url": f"https://www.youtube.com/@{username}"
        })
    except Exception as e:
        return jsonify({"error": f"YT lookup failed: {str(e)}"})

# ===== 11. Dark Web Scan (Admin only) =====
@app.route("/api/darkweb", methods=["POST"])
@admin_required
def api_darkweb():
    d = request.get_json()
    target = d.get("target","").strip().lower()
    if not target:
        return jsonify({"error": "No target."})
    results = []
    sources = [
        ("HaveIBeenPwned", f"https://haveibeenpwned.com/api/v3/breachedaccount/{urllib.parse.quote(target)}"),
        ("LeakCheck", f"https://leakcheck.io/api/public?check={target}"),
    ]
    for name, url in sources:
        try:
            r = requests.get(url, timeout=8,
                headers={"User-Agent": "Mozilla/5.0", "hibp-api-key": ""})
            if r.status_code == 200:
                results.append({"source": name, "found": True, "detail": "Donn\u00e9es compromise d\u00e9tect\u00e9es"})
            else:
                results.append({"source": name, "found": False, "detail": "Aucune fuite"})
        except:
            results.append({"source": name, "found": False, "detail": "Erreur requ\u00eate"})
    return jsonify({"target": target, "results": results})

# ===== 12. Facebook Lookup (Admin only) =====
@app.route("/api/fb", methods=["POST"])
@admin_required
def api_fb():
    d = request.get_json()
    username = d.get("target","").strip().lower().replace("@","")
    if not username or len(username) < 2:
        return jsonify({"error": "Invalid username."})
    try:
        resp = requests.get(f"https://www.facebook.com/{username}/", timeout=10,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                     "Accept-Language": "en-US,en;q=0.9"},
            allow_redirects=True)
        if resp.status_code != 200:
            return jsonify({"exists": False, "error": "Profil introuvable."})
        html = resp.text
        if "this content isn't available" in html.lower() or "page not found" in html.lower():
            return jsonify({"exists": False, "error": "Profil introuvable."})
        name = username
        m = re.search(r'"name"\s*:\s*"([^"]+)"', html)
        if m: name = m.group(1)
        m = re.search(r'<meta property="og:title"[^>]*content="([^"]+)"', html)
        if m: name = m.group(1)
        followers = "N/A"
        m = re.search(r'"follower_count"\s*:\s*(\d+)', html)
        if m: followers = int(m.group(1))
        verified = False
        m = re.search(r'"verified"\s*:\s*(true|false)', html)
        if m: verified = m.group(1) == "true"
        return jsonify({
            "username": username, "name": name,
            "followers": followers, "verified": verified,
            "exists": True, "url": f"https://www.facebook.com/{username}/"
        })
    except Exception as e:
        return jsonify({"error": f"FB lookup failed: {str(e)}"})

# ===== 18. Discord Lookup (20 credits) =====
@app.route("/api/discord", methods=["POST"])
@login_required
def api_discord():
    if not deduct_credits(session["user"], 20):
        return jsonify({"error": "Credits insuffisants. 20 cr\u00e9dits requis."})
    data = request.get_json() or {}
    target = (data.get("target") or "").strip()
    if not target:
        return jsonify({"error": "Entrez un ID Discord ou utilisateur#0000."})
    try:
        user_id = target
        if "#" in target:
            parts = target.split("#")
            username_part = parts[0]
            discrim = parts[1] if len(parts) > 1 else "0"
            url = f"https://discord.com/api/v9/users?limit=1&query={urllib.parse.quote(username_part)}"
            if DISCORD_BOT_TOKEN:
                h = {"Authorization": f"Bot {DISCORD_BOT_TOKEN}"}
                r = requests.get(url, headers=h, timeout=10)
                if r.status_code == 200:
                    users_data = r.json()
                    for u2 in users_data:
                        if u2.get("discriminator") == discrim:
                            user_id = u2["id"]
                            break
        result = {
            "id": user_id,
            "username": target,
            "exists": False,
            "global_name": "N/A",
            "discriminator": "N/A",
            "avatar_url": "",
            "banner_url": "",
            "bot": False,
            "created_at": "N/A"
        }
        if DISCORD_BOT_TOKEN:
            h = {"Authorization": f"Bot {DISCORD_BOT_TOKEN}"}
            r = requests.get(f"https://discord.com/api/v9/users/{user_id}", headers=h, timeout=10)
            if r.status_code == 200:
                du = r.json()
                result["exists"] = True
                result["username"] = du.get("username", target)
                result["global_name"] = du.get("global_name") or du.get("display_name", "N/A")
                result["discriminator"] = du.get("discriminator", "0")
                result["bot"] = du.get("bot", False)
                avatar_hash = du.get("avatar")
                if avatar_hash:
                    ext = "gif" if avatar_hash.startswith("a_") else "png"
                    result["avatar_url"] = f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}.{ext}?size=256"
                banner_hash = du.get("banner")
                if banner_hash:
                    ext2 = "gif" if banner_hash.startswith("a_") else "png"
                    result["banner_url"] = f"https://cdn.discordapp.com/banners/{user_id}/{banner_hash}.{ext2}?size=512"
                snowflake = int(user_id)
                epoch = 1420070400000
                created_ts = (snowflake >> 22) + epoch
                result["created_at"] = datetime.datetime.utcfromtimestamp(created_ts / 1000).strftime("%Y-%m-%d %H:%M:%S")
            else:
                result["exists"] = True
                result["username"] = user_id
                snowflake = int(user_id)
                epoch = 1420070400000
                created_ts = (snowflake >> 22) + epoch
                result["created_at"] = datetime.datetime.utcfromtimestamp(created_ts / 1000).strftime("%Y-%m-%d %H:%M:%S")
        else:
            try:
                snowflake = int(user_id)
                epoch = 1420070400000
                created_ts = (snowflake >> 22) + epoch
                result["created_at"] = datetime.datetime.utcfromtimestamp(created_ts / 1000).strftime("%Y-%m-%d %H:%M:%S")
                result["exists"] = True
            except:
                pass
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"Discord lookup failed: {str(e)}"})

# ===== RUN =====
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
