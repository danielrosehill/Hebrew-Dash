import os
import json
import threading
from datetime import datetime, timedelta, timezone
import email.utils as eut
from dotenv import load_dotenv

from flask import Flask, jsonify, render_template, send_from_directory, request, redirect, url_for
from pathlib import Path

# Load environment variables from .env file
load_dotenv()

# Optional imports guarded for environments without deps installed yet
try:
    import requests
    import feedparser  # type: ignore
    from dateutil import tz
except Exception:  # pragma: no cover
    requests = None
    feedparser = None
    tz = None

try:
    from google.oauth2.credentials import Credentials  # type: ignore
    from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore
    from googleapiclient.discovery import build  # type: ignore
    from googleapiclient.errors import HttpError  # type: ignore
    import google.auth.transport.requests  # type: ignore
except Exception:  # pragma: no cover
    Credentials = None
    InstalledAppFlow = None
    build = None
    HttpError = Exception


APP_TITLE = os.environ.get("APP_TITLE", "Hebrew Dashboard")
CLIENT_SECRET_GLOB = "client_secret_"  # prefix to locate the installed-app OAuth client
TOKENS_DIR = Path(os.path.dirname(__file__)) / "tokens"
os.makedirs(TOKENS_DIR, exist_ok=True)
CONFIG_PATH = Path(os.path.dirname(__file__)) / "config.json"

# Environment-based OAuth credentials (no fallback hardcoded credentials)
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
GOOGLE_PROJECT_ID = os.environ.get("GOOGLE_PROJECT_ID")

# In-memory credential storage
_user_credentials = {}
_user_credentials_lock = threading.Lock()

# Jerusalem lat/lon
DEFAULT_LAT = 31.7683
DEFAULT_LON = 35.2137

# Scopes for Gmail (readonly) and Calendar (readonly)
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
]

app = Flask(__name__, static_folder="static", template_folder="templates")
_token_lock = threading.Lock()
_account_cache = {}
_account_emails = []
_config_lock = threading.Lock()

# Simple in-memory cache: key -> (expires_ts, value)
_cache = {}


def cache_get(key):
    try:
        exp, val = _cache.get(key, (0, None))
        if exp and exp > datetime.now(timezone.utc).timestamp():
            return val
    except Exception:
        pass
    return None


def cache_set(key, val, ttl_seconds: int):
    try:
        _cache[key] = (datetime.now(timezone.utc).timestamp() + ttl_seconds, val)
    except Exception:
        pass


def cache_invalidate(prefix: str):
    try:
        for k in list(_cache.keys()):
            if k.startswith(prefix):
                _cache.pop(k, None)
    except Exception:
        pass


def _get_oauth_config() -> dict:
    """Get OAuth configuration from environment variables, user input, config file, or client secret file."""
    with _user_credentials_lock:
        # First check in-memory user credentials
        if _user_credentials.get("client_id") and _user_credentials.get("client_secret"):
            return {
                "client_id": _user_credentials["client_id"],
                "project_id": _user_credentials.get("project_id", GOOGLE_PROJECT_ID),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_secret": _user_credentials["client_secret"],
                "redirect_uris": ["http://localhost"]
            }
    
    # Check environment variables first
    if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
        return {
            "client_id": GOOGLE_CLIENT_ID,
            "project_id": GOOGLE_PROJECT_ID or "hebrew-dashboard",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uris": ["http://localhost"]
        }
    
    # Check config file for saved credentials
    cfg = _load_config()
    if cfg.get("google_client_id") and cfg.get("google_client_secret"):
        return {
            "client_id": cfg["google_client_id"],
            "project_id": cfg.get("google_project_id", GOOGLE_PROJECT_ID or "hebrew-dashboard"),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": cfg["google_client_secret"],
            "redirect_uris": ["http://localhost"]
        }
    
    # Check for existing client_secret_*.json file
    client_secret_path = _find_client_secret_file()
    if client_secret_path:
        try:
            with open(client_secret_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("installed", {})
        except Exception:
            pass
    
    # Return empty config if no credentials found
    return {}

def _find_client_secret_file() -> str | None:
    """Find existing client_secret_*.json file."""
    try:
        for fn in os.listdir(os.path.dirname(__file__)):
            if fn.startswith(CLIENT_SECRET_GLOB) and fn.endswith(".json"):
                return os.path.join(os.path.dirname(__file__), fn)
    except Exception:
        pass
    return None

def _set_user_credentials(client_id: str, client_secret: str, project_id: str = None):
    """Set user-provided OAuth credentials in memory."""
    with _user_credentials_lock:
        _user_credentials["client_id"] = client_id.strip()
        _user_credentials["client_secret"] = client_secret.strip()
        if project_id:
            _user_credentials["project_id"] = project_id.strip()
        else:
            _user_credentials["project_id"] = GOOGLE_PROJECT_ID or "hebrew-dashboard"

def _get_user_credentials():
    """Get current user credentials from memory."""
    with _user_credentials_lock:
        return _user_credentials.copy()

def _clear_user_credentials():
    """Clear user credentials from memory."""
    with _user_credentials_lock:
        _user_credentials.clear()


def _load_all_credentials() -> list:
    creds_list = []
    if Credentials is None:
        return creds_list
    with _token_lock:
        for fn in os.listdir(TOKENS_DIR):
            if not fn.endswith(".json"):
                continue
            path = os.path.join(TOKENS_DIR, fn)
            try:
                creds = Credentials.from_authorized_user_file(path, SCOPES)
                if creds:
                    # If credentials are expired but have refresh token, refresh them
                    if not creds.valid and creds.expired and creds.refresh_token:
                        try:
                            request = google.auth.transport.requests.Request()
                            creds.refresh(request)
                            # Save the refreshed credentials
                            with open(path, "w", encoding="utf-8") as f:
                                f.write(creds.to_json())
                        except Exception as e:
                            print(f"Failed to refresh token for {fn}: {e}")
                            continue
                    
                    # Only add if credentials are now valid
                    if creds.valid:
                        creds_list.append(creds)
            except Exception as e:
                print(f"Error loading credentials from {fn}: {e}")
                continue
    return creds_list


def _get_tz_jerusalem():
    try:
        return tz.gettz("Asia/Jerusalem")
    except Exception:
        return _get_local_tz()


def _list_accounts(force_refresh: bool = False) -> list[str]:
    global _account_cache, _account_emails
    if Credentials is None:
        return []
    if _account_emails and not force_refresh:
        return _account_emails
    emails = []
    cache = {}
    for creds in _load_all_credentials():
        try:
            gmail = build("gmail", "v1", credentials=creds, cache_discovery=False)
            profile = gmail.users().getProfile(userId="me").execute()
            email = profile.get("emailAddress")
            if email:
                email = email.lower()
                emails.append(email)
                cache[email] = creds
        except Exception:
            continue
    _account_cache = cache
    _account_emails = emails
    return emails


def _get_creds_for_email(email: str):
    if not email:
        return None
    email = email.lower()
    if not _account_cache or email not in _account_cache:
        _list_accounts(force_refresh=True)
    creds = _account_cache.get(email)
    
    # Double-check credentials and refresh if needed
    if creds and not creds.valid and creds.expired and creds.refresh_token:
        try:
            request = google.auth.transport.requests.Request()
            creds.refresh(request)
            # Update the cached credentials
            _account_cache[email] = creds
        except Exception as e:
            print(f"Failed to refresh token for {email}: {e}")
            return None
    
    return creds if creds and creds.valid else None


def _save_credentials(creds, email_hint: str = "account"):
    TOKENS_DIR.mkdir(exist_ok=True)
    with _token_lock:
        email_hint = (email_hint or "account").lower()
        safe = email_hint.replace("@", "_").replace(".", "_")
        path = TOKENS_DIR / f"token_{safe}.json"
        with open(path, "w", encoding="utf-8") as f:
            f.write(creds.to_json())


def _get_local_tz():
    try:
        return tz.tzlocal()
    except Exception:
        return timezone.utc


def _load_config():
    # Configuration with environment variable defaults
    default_cfg = {
        "personal": os.environ.get("PERSONAL_EMAIL", ""),
        "business": os.environ.get("BUSINESS_EMAIL", ""),
        "waqi_token": os.environ.get("WAQI_API_KEY", ""),
        "google_client_id": os.environ.get("GOOGLE_CLIENT_ID", ""),
        "google_client_secret": os.environ.get("GOOGLE_CLIENT_SECRET", ""),
        "google_project_id": os.environ.get("GOOGLE_PROJECT_ID", ""),
        "hebrew_date_language": os.environ.get("HEBREW_DATE_LANGUAGE", "english"),
    }
    with _config_lock:
        if not os.path.exists(CONFIG_PATH):
            return default_cfg
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {**default_cfg, **data}
        except Exception:
            return default_cfg


def _save_config(cfg: dict):
    with _config_lock:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)


@app.route("/")
def index():
    return render_template("index.html", title=APP_TITLE)


@app.route("/email")
def email_page():
    return render_template("email.html", title=f"{APP_TITLE} • Email")


@app.route("/calendar")
def calendar_page():
    return render_template("calendar.html", title=f"{APP_TITLE} • Calendar")


@app.route("/news")
def news_page():
    return render_template("news.html", title=f"{APP_TITLE} • News")


@app.route("/weather")
def weather_page():
    return render_template("weather.html", title=f"{APP_TITLE} • Weather")


# Video functionality removed


@app.route("/zmanim")
def zmanim_page():
    return render_template("zmanim.html", title=f"{APP_TITLE} • Zmanim")


@app.route("/settings", methods=["GET", "POST"])
def settings_page():
    cfg = _load_config()
    if request.method == "POST":
        waqi = request.form.get("waqi_token", "").strip()
        if waqi:
            cfg["waqi_token"] = waqi
        
        # Hebrew date language setting
        hebrew_lang = request.form.get("hebrew_date_language", "english")
        if hebrew_lang in ["english", "hebrew"]:
            cfg["hebrew_date_language"] = hebrew_lang
        
        # Google OAuth credentials
        google_client_id = request.form.get("google_client_id", "").strip()
        google_client_secret = request.form.get("google_client_secret", "").strip()
        google_project_id = request.form.get("google_project_id", "").strip()
        
        if google_client_id and google_client_secret:
            cfg["google_client_id"] = google_client_id
            cfg["google_client_secret"] = google_client_secret
            cfg["google_project_id"] = google_project_id or GOOGLE_PROJECT_ID or "hebrew-dashboard"
        elif not google_client_id and not google_client_secret:
            # Clear saved credentials if both fields are empty
            cfg["google_client_id"] = ""
            cfg["google_client_secret"] = ""
            cfg["google_project_id"] = ""
        
        _save_config(cfg)
        return redirect(url_for("settings_page"))
    
    emails = _list_accounts(force_refresh=True)
    current_oauth = _get_oauth_config()
    user_creds = _get_user_credentials()
    
    return render_template("settings.html", title=f"{APP_TITLE} • Settings", 
                         cfg=cfg, emails=emails, current_oauth=current_oauth, 
                         user_creds=user_creds)


@app.route("/api/time")
def api_time():
    now_local = datetime.now(_get_local_tz())
    now_utc = datetime.now(timezone.utc)
    payload = {
        "local": now_local.strftime("%H:%M"),
        "utc": now_utc.strftime("%H:%M"),
        "date": now_local.strftime("%a, %-d %b" if os.name != "nt" else "%a, %#d %b"),
        "hebrew": _hebrew_date(now_local),
    }
    return jsonify(payload)


@app.route("/api/status")
def api_status():
    cfg = _load_config()
    oauth_config = _get_oauth_config()
    user_creds = _get_user_credentials()
    
    # Determine credential source
    cred_source = "fallback"
    if user_creds.get("client_id"):
        cred_source = "memory"
    elif cfg.get("google_client_id"):
        cred_source = "config"
    elif _find_client_secret_file():
        cred_source = "file"
    
    return jsonify({
        "google_accounts": len(_load_all_credentials()),
        "accounts": _list_accounts(force_refresh=True),
        "labels": {"personal": cfg.get("personal"), "business": cfg.get("business")},
        "hebrew_date_language": cfg.get("hebrew_date_language", "english"),
        "credentials": {
            "source": cred_source,
            "client_id": oauth_config.get("client_id"),
            "project_id": oauth_config.get("project_id"),
            "using_fallback": False
        }
    })


def _gmail_fetch_latest(creds, n=20):
    if build is None:
        return []
    try:
        service = build("gmail", "v1", credentials=creds, cache_discovery=False)
        # Determine account email once
        try:
            profile = service.users().getProfile(userId="me").execute()
            acct_email = (profile.get("emailAddress") or "").lower()
        except Exception:
            acct_email = None
        # List messages in inbox
        res = service.users().messages().list(userId="me", labelIds=["INBOX"], maxResults=n).execute()
        messages = res.get("messages", [])
        items = []
        for m in messages:
            msg = service.users().messages().get(userId="me", id=m["id"], format="metadata", metadataHeaders=["From", "Subject", "Date"]).execute()
            headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
            subject = headers.get("subject", "(no subject)")
            from_ = headers.get("from", "")
            date_hdr = headers.get("date")
            try:
                dt = eut.parsedate_to_datetime(date_hdr) if date_hdr else None
            except Exception:
                dt = None
            
            # Determine account type based on email address
            account_type = "Personal"
            cfg = _load_config()
            if acct_email and acct_email.lower() == cfg.get("business", "").lower():
                account_type = "Business"
            
            items.append({
                "from": from_,
                "subject": subject,
                "received": (dt.isoformat() if dt else date_hdr),
                "id": m["id"],
                "account": acct_email,
                "account_type": account_type,
            })
        return items
    except HttpError:
        return []


def _calendar_fetch_events(creds, start_dt: datetime, end_dt: datetime, max_results=20):
    if build is None:
        return []
    try:
        service = build("calendar", "v3", credentials=creds, cache_discovery=False)
        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=start_dt.astimezone(timezone.utc).isoformat(),
                timeMax=end_dt.astimezone(timezone.utc).isoformat(),
                singleEvents=True,
                orderBy="startTime",
                maxResults=max_results,
            )
            .execute()
        )
        return events_result.get("items", [])
    except HttpError:
        return []


def _combine_calendars(start_dt: datetime, end_dt: datetime):
    events = []
    for creds in _load_all_credentials():
        events.extend(_calendar_fetch_events(creds, start_dt, end_dt))
    # sort by start
    def _parse_start(ev):
        when = ev.get("start", {}).get("dateTime") or ev.get("start", {}).get("date")
        try:
            if len(when) > 10:
                return datetime.fromisoformat(when.replace("Z", "+00:00"))
            return datetime.fromisoformat(when).replace(tzinfo=_get_local_tz())
        except Exception:
            return datetime.max.replace(tzinfo=timezone.utc)

    events.sort(key=_parse_start)
    return events


@app.route("/api/emails")
def api_emails():
    account = request.args.get("account")
    items = []
    if account:
        cache_key = f"emails:{account}"
        cached = cache_get(cache_key)
        if cached is not None:
            return jsonify(cached)
        creds = _get_creds_for_email(account)
        if creds:
            items.extend(_gmail_fetch_latest(creds, 20))
        # sort below and return
        # cache after sorting
        # fallthrough
    else:
        cache_key = "emails:combined"
        cached = cache_get(cache_key)
        if cached is not None:
            return jsonify(cached)
        for creds in _load_all_credentials():
            items.extend(_gmail_fetch_latest(creds, 20))
    # Keep top 20 overall by received date if available
    def _key(it):
        d = it.get("received")
        try:
            return datetime.fromisoformat(d)
        except Exception:
            try:
                return eut.parsedate_to_datetime(d)
            except Exception:
                return datetime.min

    items.sort(key=_key, reverse=True)
    result = items[:20]
    cache_set(cache_key, result, 15 * 60)
    return jsonify(result)


@app.route("/api/calendar")
def api_calendar():
    now = datetime.now(_get_local_tz())
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    tomorrow_end = today_start + timedelta(days=2)

    account = request.args.get("account")
    cache_key = f"cal:{account or 'combined'}:{today_start.date()}"
    cached = cache_get(cache_key)
    if cached is not None:
        return jsonify(cached)
    if account:
        creds = _get_creds_for_email(account)
        today_events = _calendar_fetch_events(creds, today_start, today_end) if creds else []
        tomorrow_events = _calendar_fetch_events(creds, today_end, tomorrow_end) if creds else []
    else:
        today_events = _combine_calendars(today_start, today_end)
        tomorrow_events = _combine_calendars(today_end, tomorrow_end)

    def simplify(ev):
        start = ev.get("start", {})
        end = ev.get("end", {})
        title = ev.get("summary", "(no title)")
        location = ev.get("location", "")
        start_str = start.get("dateTime") or start.get("date")
        end_str = end.get("dateTime") or end.get("date")
        return {"title": title, "location": location, "start": start_str, "end": end_str}

    payload = {
        "today": [simplify(e) for e in today_events],
        "tomorrow": [simplify(e) for e in tomorrow_events],
    }
    cache_set(cache_key, payload, 15 * 60)
    return jsonify(payload)


@app.route("/api/calendar/week")
def api_calendar_week():
    """Return events for the current week (Sun-Sat) grouped by day.
    Optional query param: account=email to filter by specific account.
    """
    now = datetime.now(_get_local_tz())
    # Python: Monday=0 ... Sunday=6. We want Sunday start.
    days_from_sunday = (now.weekday() + 1) % 7
    week_start = (now - timedelta(days=days_from_sunday)).replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = week_start + timedelta(days=7)

    account = request.args.get("account")
    cache_key = f"calweek:{account or 'combined'}:{week_start.date()}"
    cached = cache_get(cache_key)
    if cached is not None:
        return jsonify(cached)

    # Fetch events
    if account:
        creds = _get_creds_for_email(account)
        events = _calendar_fetch_events(creds, week_start, week_end) if creds else []
    else:
        events = _combine_calendars(week_start, week_end)

    def simplify(ev):
        start = ev.get("start", {})
        end = ev.get("end", {})
        title = ev.get("summary", "(no title)")
        location = ev.get("location", "")
        start_str = start.get("dateTime") or start.get("date")
        end_str = end.get("dateTime") or end.get("date")
        return {"title": title, "location": location, "start": start_str, "end": end_str}

    # Bucket events per local day
    buckets = {}
    for i in range(7):
        d = (week_start + timedelta(days=i))
        key = d.strftime("%Y-%m-%d")
        buckets[key] = {"date": key, "label": d.strftime("%a %d"), "events": []}

    for ev in events:
        s = ev.get("start", {})
        when = s.get("dateTime") or s.get("date")
        try:
            if when and "T" in when:
                dt = datetime.fromisoformat(when.replace("Z", "+00:00"))
                dt_local = dt.astimezone(_get_local_tz())
            elif when:
                # All-day event
                dt_local = datetime.fromisoformat(when).replace(tzinfo=_get_local_tz())
            else:
                continue
            key = dt_local.strftime("%Y-%m-%d")
            if key in buckets:
                buckets[key]["events"].append(simplify(ev))
        except Exception:
            continue

    # Sort events within each day by start
    def sort_key(item):
        s = item.get("start")
        try:
            if s and "T" in s:
                return datetime.fromisoformat(s.replace("Z", "+00:00"))
            elif s:
                return datetime.fromisoformat(s)
        except Exception:
            return datetime.max
        return datetime.max

    days = []
    for i in range(7):
        d = (week_start + timedelta(days=i)).strftime("%Y-%m-%d")
        day = buckets[d]
        day["events"].sort(key=sort_key)
        days.append(day)

    payload = {
        "range": {"start": week_start.strftime("%Y-%m-%d"), "end": (week_end - timedelta(days=1)).strftime("%Y-%m-%d")},
        "days": days,
        "today": now.strftime("%Y-%m-%d"),
    }
    cache_set(cache_key, payload, 15 * 60)
    return jsonify(payload)


@app.route("/api/next-meeting")
def api_next_meeting():
    account = request.args.get("account")
    now = datetime.now(_get_local_tz())
    end = now + timedelta(days=7)
    cache_key = f"next_meeting:{account or 'combined'}"
    cached = cache_get(cache_key)
    if cached is not None:
        return jsonify(cached)
    if account:
        creds = _get_creds_for_email(account)
        events = _calendar_fetch_events(creds, now, end) if creds else []
    else:
        events = _combine_calendars(now, end)
    next_ev = None
    for ev in events:
        start = ev.get("start", {})
        when = start.get("dateTime") or start.get("date")
        if not when:
            continue
        try:
            dt = datetime.fromisoformat(when.replace("Z", "+00:00")) if "T" in when else datetime.fromisoformat(when)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=_get_local_tz())
        except Exception:
            continue
        if dt > now:
            next_ev = {"title": ev.get("summary", "(no title)"), "start": dt.isoformat()}
            break
    if not next_ev:
        return jsonify({"title": None, "countdown": None, "start_time": None})
    dt = datetime.fromisoformat(next_ev["start"])
    delta = dt - now
    days = delta.days
    hours, rem = divmod(delta.seconds, 3600)
    mins = rem // 60
    
    # Format local start time
    local_start_time = dt.strftime("%a %b %d, %H:%M")
    
    payload = {
        "title": next_ev["title"],
        "in": f"{days}d {hours}h {mins}m" if days else f"{hours}h {mins}m",
        "start_time": local_start_time,
    }
    cache_set(cache_key, payload, 60)
    return jsonify(payload)


@app.route("/api/weather")
def api_weather():
    lat = float(request.args.get("lat", DEFAULT_LAT))
    lon = float(request.args.get("lon", DEFAULT_LON))
    cache_key = f"weather:{lat:.3f},{lon:.3f}"
    cached = cache_get(cache_key)
    if cached is not None:
        return jsonify(cached)
    if requests is None:
        return jsonify({})
    try:
        # Open-Meteo: no API key required
        # Enhanced request with more detailed weather data
        url = (
            "https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
            "&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m,wind_direction_10m,pressure_msl"
            "&daily=weather_code,temperature_2m_max,temperature_2m_min,sunrise,sunset,uv_index_max,precipitation_sum,wind_speed_10m_max"
            "&hourly=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m,wind_direction_10m,precipitation"
            "&timezone=auto&forecast_days=7"
        ).format(lat=lat, lon=lon)
        r = requests.get(url, timeout=8)
        r.raise_for_status()
        data = r.json()
        current = data.get("current", {})
        daily = data.get("daily", {})
        hourly = data.get("hourly", {})
        
        # Process current weather
        current_weather = {
            "temp": current.get("temperature_2m"),
            "feels_like": current.get("apparent_temperature"),
            "humidity": current.get("relative_humidity_2m"),
            "code": current.get("weather_code"),
            "wind_speed": current.get("wind_speed_10m"),
            "wind_direction": current.get("wind_direction_10m"),
            "pressure": current.get("pressure_msl"),
        }
        
        # Process today's weather
        today_weather = None
        if daily and daily.get("time") and len(daily["time"]) >= 1:
            today_weather = {
                "max": daily.get("temperature_2m_max", [None])[0],
                "min": daily.get("temperature_2m_min", [None])[0],
                "sunrise": daily.get("sunrise", [None])[0],
                "sunset": daily.get("sunset", [None])[0],
                "uv_index": daily.get("uv_index_max", [None])[0],
                "precipitation": daily.get("precipitation_sum", [None])[0],
                "wind_speed_max": daily.get("wind_speed_10m_max", [None])[0],
                "code": daily.get("weather_code", [None])[0],
            }
        
        # Process 7-day forecast
        forecast = []
        if daily and daily.get("time"):
            for i in range(min(7, len(daily["time"]))):
                day_data = {
                    "date": daily["time"][i],
                    "max": daily.get("temperature_2m_max", [None]*7)[i],
                    "min": daily.get("temperature_2m_min", [None]*7)[i],
                    "code": daily.get("weather_code", [None]*7)[i],
                    "precipitation": daily.get("precipitation_sum", [None]*7)[i],
                    "wind_speed_max": daily.get("wind_speed_10m_max", [None]*7)[i],
                }
                forecast.append(day_data)
        
        # Process hourly forecast for next 24 hours
        hourly_forecast = []
        if hourly and hourly.get("time"):
            # Get current time index
            now = datetime.now(timezone.utc)
            current_hour_index = 0
            
            # Find the closest hour
            for i, time_str in enumerate(hourly["time"][:25]):  # Check up to 25 hours
                try:
                    hour_time = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
                    if hour_time >= now:
                        current_hour_index = i
                        break
                except Exception:
                    continue
            
            # Get next 24 hours of data
            for i in range(current_hour_index, min(current_hour_index + 24, len(hourly["time"]))):
                hour_data = {
                    "time": hourly["time"][i],
                    "temp": hourly.get("temperature_2m", [None]*len(hourly["time"]))[i],
                    "feels_like": hourly.get("apparent_temperature", [None]*len(hourly["time"]))[i],
                    "humidity": hourly.get("relative_humidity_2m", [None]*len(hourly["time"]))[i],
                    "code": hourly.get("weather_code", [None]*len(hourly["time"]))[i],
                    "wind_speed": hourly.get("wind_speed_10m", [None]*len(hourly["time"]))[i],
                    "precipitation": hourly.get("precipitation", [None]*len(hourly["time"]))[i],
                }
                hourly_forecast.append(hour_data)
        
        payload = {
            "current": current_weather,
            "today": today_weather,
            "forecast": forecast,
            "hourly": hourly_forecast,
        }
        cache_set(cache_key, payload, 3600)
        return jsonify(payload)
    except Exception as e:
        print(f"Weather API error: {e}")
        return jsonify({})


@app.route("/api/news")
def api_news():
    # Google News RSS for Israel (English) or search feed via ?q=term
    if feedparser is None:
        return jsonify([])
    q = request.args.get("q")
    cache_key = f"news:{q or 'israel'}"
    cached = cache_get(cache_key)
    if cached is not None:
        return jsonify(cached)
    if q:
        feed_url = f"https://news.google.com/rss/search?q={q}&hl=en-IL&gl=IL&ceid=IL:en"
    else:
        feed_url = "https://news.google.com/rss?hl=en-IL&gl=IL&ceid=IL:en"
    try:
        d = feedparser.parse(feed_url)
        items = []
        for e in d.entries[:20]:  # Increased to 20 for better content
            # Extract source from title if available (Google News format: "Title - Source")
            title = e.get("title", "")
            source = None
            if " - " in title:
                parts = title.rsplit(" - ", 1)
                if len(parts) == 2:
                    title = parts[0]
                    source = parts[1]
            
            # Clean summary - remove HTML tags and limit length
            raw_summary = e.get("summary", "")
            clean_summary = None
            if raw_summary:
                # Remove HTML tags
                import re
                clean_summary = re.sub(r'<[^>]+>', '', raw_summary).strip()
                # Limit length
                if len(clean_summary) > 200:
                    clean_summary = clean_summary[:200] + "..."
                # Don't include if it's just empty or whitespace
                if not clean_summary or clean_summary.isspace():
                    clean_summary = None
            
            items.append({
                "title": title,
                "link": e.get("link"),
                "published": e.get("published"),
                "source": source,
                "summary": clean_summary,
            })
        cache_set(cache_key, items, 15 * 60)  # Reduced cache time to 15 minutes
        return jsonify(items)
    except Exception:
        return jsonify([])


@app.route("/api/alerts")
def api_alerts():
    # Latest Red Alert data
    if requests is None:
        return jsonify([])
    url = os.environ.get("RED_ALERT_HISTORY_URL")
    if not url:
        return jsonify([])
    cached = cache_get("alerts_latest")
    if cached is not None:
        return jsonify(cached)
    try:
        r = requests.get(url, timeout=6, headers={"User-Agent": "DailyDashboard/1.0"})
        r.raise_for_status()
        data = r.json()
        # Try a few common shapes, keep it robust
        items = []
        if isinstance(data, dict):
            seq = data.get("data") or data.get("alerts") or data.get("items") or []
        elif isinstance(data, list):
            seq = data
        else:
            seq = []
        # pick the last item only
        latest = None
        if seq:
            e = seq[-1]
            # Attempt to grab useful fields
            title = e.get("title") if isinstance(e, dict) else None
            where = (e.get("data") or e.get("location") or e.get("city")).__str__() if isinstance(e, dict) else None
            when = e.get("alertDate") if isinstance(e, dict) else None
            text = None
            if isinstance(e, dict):
                text = e.get("data") or e.get("title") or e.get("description")
                if isinstance(text, list):
                    text = ", ".join(str(x) for x in text)
            latest = {"title": title, "location": where, "when": when, "text": text}
        cache_set("alerts_latest", latest or {}, 30)
        return jsonify(latest or {})
    except Exception:
        return jsonify([])

def _hebrew_date(now_local: datetime) -> str | None:
    if requests is None:
        return None
    try:
        cfg = _load_config()
        language = cfg.get("hebrew_date_language", "english")
        
        date_str = now_local.strftime("%Y-%m-%d")
        url = f"https://www.hebcal.com/converter?cfg=json&date={date_str}&g2h=1&strict=1"
        cache_key = f"{url}:{language}"
        cached = cache_get(cache_key)
        if cached is not None:
            return cached
        r = requests.get(url, timeout=6, headers={"User-Agent": "HebrewDashboard/1.0"})
        r.raise_for_status()
        data = r.json()
        
        if language == "hebrew":
            # Return Hebrew characters: "כ״ב אלול תשפ״ה"
            hebrew_result = data.get("hebrew")
        else:
            # Format Hebrew date in English: "22 Elul 5785"
            hd = data.get("hd")  # day
            hm = data.get("hm")  # month in English
            hy = data.get("hy")  # year
            
            if hd and hm and hy:
                hebrew_result = f"{hd} {hm} {hy}"
            else:
                hebrew_result = data.get("hebrew")  # fallback to Hebrew if parsing fails
            
        cache_set(cache_key, hebrew_result, 24 * 3600)
        return hebrew_result
    except Exception:
        return None


def _decode_gmail_text(payload):
    import base64
    def _walk(p):
        if not p:
            return None
        data = p.get('body', {}).get('data')
        mime = p.get('mimeType')
        if data and (mime == 'text/plain' or mime == 'text/html'):
            try:
                return base64.urlsafe_b64decode(data.encode('utf-8')).decode('utf-8', errors='replace')
            except Exception:
                return None
        for part in (p.get('parts') or []):
            txt = _walk(part)
            if txt:
                return txt
        return None
    return _walk(payload)


@app.route('/api/email/<msg_id>')
def api_email_detail(msg_id):
    account = request.args.get('account')
    creds = _get_creds_for_email(account)
    if not creds or build is None:
        return jsonify({}), 404
    try:
        service = build('gmail', 'v1', credentials=creds, cache_discovery=False)
        msg = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
        headers = {h['name'].lower(): h['value'] for h in msg.get('payload', {}).get('headers', [])}
        body_text = _decode_gmail_text(msg.get('payload')) or msg.get('snippet')
        return jsonify({
            'id': msg_id,
            'subject': headers.get('subject'),
            'from': headers.get('from'),
            'to': headers.get('to'),
            'date': headers.get('date'),
            'snippet': (body_text or '')[:4000],
        })
    except HttpError:
        return jsonify({}), 404


@app.route("/api/zmanim")
def api_zmanim():
    """Get daily Zmanim (prayer times) for Jerusalem and next Shabbat info."""
    if requests is None:
        return jsonify({})
    
    # Use date parameter or default to today
    date_param = request.args.get("date")
    if date_param:
        try:
            target_date = datetime.fromisoformat(date_param).date()
        except Exception:
            target_date = datetime.now(_get_tz_jerusalem()).date()
    else:
        target_date = datetime.now(_get_tz_jerusalem()).date()
    
    cache_key = f"zmanim:{target_date}"
    cached = cache_get(cache_key)
    if cached is not None:
        return jsonify(cached)
    
    try:
        # Get daily Zmanim for Jerusalem (geonameid=281184)
        zmanim_url = f"https://www.hebcal.com/zmanim?cfg=json&geonameid=281184&date={target_date}"
        r = requests.get(zmanim_url, timeout=8, headers={"User-Agent": "DailyDashboard/1.0"})
        r.raise_for_status()
        zmanim_data = r.json()
        
        # Get Shabbat times and parsha
        shabbat_url = "https://www.hebcal.com/shabbat?cfg=json&geonameid=281184&M=on"
        r2 = requests.get(shabbat_url, timeout=8, headers={"User-Agent": "DailyDashboard/1.0"})
        r2.raise_for_status()
        shabbat_data = r2.json()
        
        # Extract Zmanim times
        times = zmanim_data.get("times", {})
        
        # Extract Shabbat information
        shabbat_info = {}
        if shabbat_data and 'items' in shabbat_data:
            for item in shabbat_data['items']:
                if item['category'] == 'candles':
                    shabbat_info['candle_lighting'] = {
                        'time': item['date'],
                        'title': item['title']
                    }
                elif item['category'] == 'havdalah':
                    shabbat_info['havdalah'] = {
                        'time': item['date'],
                        'title': item['title']
                    }
                elif item['category'] == 'parashat':
                    shabbat_info['parsha'] = item.get('hebrew', item.get('title', ''))
        
        payload = {
            'date': str(target_date),
            'zmanim': times,
            'shabbat': shabbat_info,
            'location': 'Jerusalem',
            'cached_at': datetime.now(_get_tz_jerusalem()).isoformat()
        }
        
        # Cache for 1 hour
        cache_set(cache_key, payload, 3600)
        return jsonify(payload)
    except Exception:
        return jsonify({})


@app.route("/api/shabbat")
def api_shabbat():
    cached = cache_get("shabbat")
    if cached:
        return jsonify(cached)
    try:
        # Shabbat times and parsha (Jerusalem)
        base = (
            "https://www.hebcal.com/shabbat?cfg=json&geonameid=281184&b=18&m=50&mod=on&leyning=off"
        )
        r = requests.get(base, timeout=8, headers={"User-Agent": "DailyDashboard/1.0"})
        r.raise_for_status()
        data = r.json()
        items = data.get("items", [])
        candle = None
        havdalah = None
        parsha = None
        for it in items:
            cat = it.get("category")
            title = it.get("title", "")
            dt = it.get("date")
            if cat == "candles" and not candle:
                candle = {"title": title, "time": dt}
            elif cat == "havdalah" and not havdalah:
                havdalah = {"title": title, "time": dt}
            elif cat == "parashat" and not parsha:
                parsha = title
        # Next upcoming Yom Tov/major holiday in Israel (after now)
        holiday_name = None
        holiday_date = None
        try:
            nx = (
                "https://www.hebcal.com/hebcal?v=1&cfg=json&maj=on&i=on&nx=on&c=on"
                "&year=now&geo=geoname&geonameid=281184&locale=en"
            )
            r2 = requests.get(nx, timeout=8, headers={"User-Agent": "DailyDashboard/1.0"})
            r2.raise_for_status()
            d2 = r2.json()
            now_jlm = datetime.now(_get_tz_jerusalem())
            upcoming = []
            for e in d2.get("items", []):
                try:
                    dt = e.get("date")
                    if not dt:
                        continue
                    when = datetime.fromisoformat(dt.replace("Z", "+00:00")).astimezone(_get_tz_jerusalem())
                except Exception:
                    continue
                # Prefer explicit yomtov flag; fallback to category=holiday
                is_major = bool(e.get("yomtov")) or e.get("category") == "holiday"
                if is_major and when > now_jlm:
                    upcoming.append((when, e.get("title")))
            if upcoming:
                upcoming.sort(key=lambda t: t[0])
                holiday_name = upcoming[0][1]
                holiday_date = upcoming[0][0].strftime("%b %-d" if os.name != "nt" else "%b %#d")
        except Exception:
            pass
        payload = {
            "candle": candle,
            "havdalah": havdalah,
            "parsha": parsha,
            "next_holiday": holiday_name,
            "next_holiday_date": holiday_date,
        }
        cache_set("shabbat", payload, 6 * 3600)
        return jsonify(payload)
    except Exception:
        return jsonify({})


@app.route("/api/accounts")
def api_accounts():
    emails = _list_accounts(force_refresh=True)
    return jsonify(emails)


@app.route("/api/credentials", methods=["GET", "POST", "DELETE"])
def api_credentials():
    """Manage OAuth credentials."""
    if request.method == "GET":
        oauth_config = _get_oauth_config()
        user_creds = _get_user_credentials()
        current_source = "fallback"
        if user_creds.get("client_id"):
            current_source = "memory"
        elif _load_config().get("google_client_id"):
            current_source = "config"
        elif _find_client_secret_file():
            current_source = "file"
        
        return jsonify({
            "client_id": oauth_config.get("client_id"),
            "project_id": oauth_config.get("project_id"),
            "source": current_source,
            "has_credentials": bool(oauth_config.get("client_id") and oauth_config.get("client_secret"))
        })
    
    elif request.method == "POST":
        data = request.get_json() or {}
        client_id = data.get("client_id", "").strip()
        client_secret = data.get("client_secret", "").strip()
        project_id = data.get("project_id", "").strip()
        
        if not client_id or not client_secret:
            return jsonify({"error": "Client ID and Client Secret are required"}), 400
        
        # Set in memory
        _set_user_credentials(client_id, client_secret, project_id)
        
        # Optionally save to config file
        if data.get("save_to_config", False):
            cfg = _load_config()
            cfg["google_client_id"] = client_id
            cfg["google_client_secret"] = client_secret
            cfg["google_project_id"] = project_id or GOOGLE_PROJECT_ID or "hebrew-dashboard"
            _save_config(cfg)
        
        return jsonify({"status": "success", "message": "Credentials updated"})
    
    elif request.method == "DELETE":
        # Clear from memory and config
        _clear_user_credentials()
        cfg = _load_config()
        cfg["google_client_id"] = ""
        cfg["google_client_secret"] = ""
        cfg["google_project_id"] = ""
        _save_config(cfg)
        
        return jsonify({"status": "success", "message": "Credentials cleared"})


@app.route("/api/aqi")
def api_aqi():
    if requests is None:
        return jsonify({})
    # Read token from config or env
    token = _load_config().get("waqi_token") or os.environ.get("WAQI_API_KEY", "")
    if not token:
        return jsonify({})
    lat = float(request.args.get("lat", DEFAULT_LAT))
    lon = float(request.args.get("lon", DEFAULT_LON))
    cache_key = f"aqi:{lat:.3f},{lon:.3f}"
    cached = cache_get(cache_key)
    if cached is not None:
        return jsonify(cached)
    url = f"https://api.waqi.info/feed/geo:{lat};{lon}/?token={token}"
    try:
        r = requests.get(url, timeout=8, headers={"User-Agent": "DailyDashboard/1.0"})
        r.raise_for_status()
        data = r.json()
        iaqi = data.get("data", {}).get("iaqi", {})
        pm25 = iaqi.get("pm25", {}).get("v")
        aqi = data.get("data", {}).get("aqi")
        payload = {"pm25": pm25, "aqi": aqi}
        cache_set(cache_key, payload, 3600)
        return jsonify(payload)
    except Exception:
        return jsonify({})


@app.route("/auth/google")
def auth_google():
    if InstalledAppFlow is None:
        return "Google auth libraries not installed.", 500
    
    oauth_config = _get_oauth_config()
    if not oauth_config.get("client_id") or not oauth_config.get("client_secret"):
        return "OAuth credentials not configured.", 404
    
    # Create client config for flow
    client_config = {
        "installed": oauth_config
    }
    
    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    creds = flow.run_local_server(port=0)
    # Try to determine email for token naming
    label = request.args.get("label")
    email_hint = request.args.get("label", "account")
    try:
        gmail = build("gmail", "v1", credentials=creds, cache_discovery=False)
        profile = gmail.users().getProfile(userId="me").execute()
        email_hint = profile.get("emailAddress", email_hint)
    except Exception:
        pass
    _save_credentials(creds, email_hint)
    # If labeled, save mapping to config and invalidate caches
    if label in ("personal", "business"):
        cfg = _load_config()
        cfg[label] = (email_hint or "").lower()
        _save_config(cfg)
        # Refresh account cache and invalidate email/cal caches
        _list_accounts(force_refresh=True)
        cache_invalidate("emails:")
        cache_invalidate("cal:")
    return redirect(url_for("settings_page"))


@app.route("/static/<path:filename>")
def static_proxy(filename):
    return send_from_directory(app.static_folder, filename)


@app.route("/api/calendar/three-day")
def api_calendar_three_day():
    """Return events for the next 3 days (today, tomorrow, day after) grouped by day."""
    now = datetime.now(_get_local_tz())
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    three_days_end = today_start + timedelta(days=3)

    account = request.args.get("account")
    cache_key = f"cal3day:{account or 'combined'}:{today_start.date()}"
    cached = cache_get(cache_key)
    if cached is not None:
        return jsonify(cached)

    # Fetch events
    if account:
        creds = _get_creds_for_email(account)
        events = _calendar_fetch_events(creds, today_start, three_days_end) if creds else []
    else:
        events = _combine_calendars(today_start, three_days_end)

    def simplify(ev):
        start = ev.get("start", {})
        end = ev.get("end", {})
        title = ev.get("summary", "(no title)")
        location = ev.get("location", "")
        start_str = start.get("dateTime") or start.get("date")
        end_str = end.get("dateTime") or end.get("date")
        return {"title": title, "location": location, "start": start_str, "end": end_str}

    # Bucket events per local day
    buckets = {}
    day_labels = ["Today", "Tomorrow", "Day After"]
    for i in range(3):
        d = (today_start + timedelta(days=i))
        key = d.strftime("%Y-%m-%d")
        buckets[key] = {
            "date": key, 
            "label": day_labels[i],
            "full_date": d.strftime("%a, %-d %b" if os.name != "nt" else "%a, %#d %b"),
            "events": []
        }

    for ev in events:
        s = ev.get("start", {})
        when = s.get("dateTime") or s.get("date")
        try:
            if when and "T" in when:
                dt = datetime.fromisoformat(when.replace("Z", "+00:00"))
                dt_local = dt.astimezone(_get_local_tz())
            elif when:
                # All-day event
                dt_local = datetime.fromisoformat(when).replace(tzinfo=_get_local_tz())
            else:
                continue
            key = dt_local.strftime("%Y-%m-%d")
            if key in buckets:
                buckets[key]["events"].append(simplify(ev))
        except Exception:
            continue

    # Sort events within each day by start
    def sort_key(item):
        s = item.get("start")
        try:
            if s and "T" in s:
                return datetime.fromisoformat(s.replace("Z", "+00:00"))
            elif s:
                return datetime.fromisoformat(s)
        except Exception:
            return datetime.max
        return datetime.max

    days = []
    for i in range(3):
        d = (today_start + timedelta(days=i)).strftime("%Y-%m-%d")
        day = buckets[d]
        day["events"].sort(key=sort_key)
        days.append(day)

    payload = {
        "days": days,
        "today": now.strftime("%Y-%m-%d"),
    }
    cache_set(cache_key, payload, 15 * 60)
    return jsonify(payload)


@app.route("/api/holidays/israel")
def api_israel_holidays():
    """Return the next 10 upcoming public holidays in Israel using HebCal API."""
    cache_key = "israel_holidays"
    cached = cache_get(cache_key)
    if cached:
        return jsonify(cached)
    
    if requests is None:
        return jsonify({"holidays": [], "count": 0, "error": "requests library not available"})
    
    try:
        now = datetime.now(_get_local_tz())
        current_year = now.year
        next_year = current_year + 1
        
        # Fetch holidays from HebCal API for current and next year
        all_holidays = []
        
        for year in [current_year, next_year]:
            # HebCal API for Israeli holidays including major Jewish holidays and Israeli national holidays
            url = f"https://www.hebcal.com/hebcal?v=1&cfg=json&maj=on&min=off&mod=on&nx=off&year={year}&month=x&ss=off&mf=off&c=on&geo=geoname&geonameid=281184&M=on&s=on"
            
            try:
                r = requests.get(url, timeout=10, headers={"User-Agent": "DailyDashboard/1.0"})
                r.raise_for_status()
                data = r.json()
                
                for item in data.get("items", []):
                    title = item.get("title", "")
                    date_str = item.get("date", "")
                    category = item.get("category", "")
                    
                    # Skip if no date or title
                    if not date_str or not title:
                        continue
                    
                    # Parse date
                    try:
                        if "T" in date_str:
                            holiday_date = datetime.fromisoformat(date_str.replace("Z", "+00:00")).date()
                        else:
                            holiday_date = datetime.fromisoformat(date_str).date()
                    except Exception:
                        continue
                    
                    # Only include future holidays
                    if holiday_date < now.date():
                        continue
                    
                    # Determine holiday type based on category and title
                    holiday_type = "Religious"
                    if "Independence" in title or "Memorial" in title or "Jerusalem" in title:
                        holiday_type = "National"
                    elif "Holocaust" in title or "Remembrance" in title:
                        holiday_type = "Memorial"
                    
                    # Calculate days until
                    days_until = (holiday_date - now.date()).days
                    
                    all_holidays.append({
                        "name": title,
                        "date": holiday_date.strftime("%Y-%m-%d"),
                        "type": holiday_type,
                        "days_until": days_until,
                        "formatted_date": holiday_date.strftime("%a, %-d %b %Y" if os.name != "nt" else "%a, %#d %b %Y")
                    })
                    
            except Exception as e:
                print(f"Error fetching holidays for year {year}: {e}")
                continue
        
        # Sort by date and take the next 10
        all_holidays.sort(key=lambda x: x["date"])
        next_10_holidays = all_holidays[:10]
        
        payload = {
            "holidays": next_10_holidays,
            "count": len(next_10_holidays),
            "last_updated": now.isoformat(),
            "source": "HebCal API"
        }
        
        # Cache for 24 hours since holidays don't change frequently
        cache_set(cache_key, payload, 24 * 60 * 60)
        return jsonify(payload)
        
    except Exception as e:
        print(f"Error in api_israel_holidays: {e}")
        # Fallback: try to get from the existing shabbat endpoint which uses HebCal
        try:
            fallback_url = "https://www.hebcal.com/hebcal?v=1&cfg=json&maj=on&i=on&nx=on&c=on&year=now&geo=geoname&geonameid=281184&locale=en"
            r = requests.get(fallback_url, timeout=8, headers={"User-Agent": "DailyDashboard/1.0"})
            r.raise_for_status()
            data = r.json()
            
            fallback_holidays = []
            for item in data.get("items", [])[:5]:  # Just get next 5 as fallback
                title = item.get("title", "")
                date_str = item.get("date", "")
                
                if not date_str or not title:
                    continue
                    
                try:
                    if "T" in date_str:
                        holiday_date = datetime.fromisoformat(date_str.replace("Z", "+00:00")).date()
                    else:
                        holiday_date = datetime.fromisoformat(date_str).date()
                        
                    if holiday_date >= now.date():
                        days_until = (holiday_date - now.date()).days
                        fallback_holidays.append({
                            "name": title,
                            "date": holiday_date.strftime("%Y-%m-%d"),
                            "type": "Religious",
                            "days_until": days_until,
                            "formatted_date": holiday_date.strftime("%a, %-d %b %Y" if os.name != "nt" else "%a, %#d %b %Y")
                        })
                except Exception:
                    continue
            
            return jsonify({
                "holidays": fallback_holidays, 
                "count": len(fallback_holidays), 
                "error": f"Primary API failed: {str(e)}, using fallback",
                "source": "HebCal API (fallback)"
            })
            
        except Exception as fallback_error:
            return jsonify({
                "holidays": [], 
                "count": 0, 
                "error": f"Both primary and fallback APIs failed: {str(e)}, {str(fallback_error)}"
            })


@app.route("/api/red-alert")
def api_red_alert():
    cache_key = "red_alert_data"
    cached_data = cache_get(cache_key)
    
    if cached_data:
        return jsonify(cached_data)
    
    try:
        # Using static alert history JSON feed from Pikud Haoref
        alert_url = os.environ.get("RED_ALERT_HISTORY_URL")
        if not alert_url:
            return jsonify({
                'alerts': [],
                'last_alert': None,
                'last_alert_display': 'RED_ALERT_HISTORY_URL not configured',
                'last_updated': datetime.now(_get_tz_jerusalem()).isoformat(),
                'status': 'error',
                'location_count': 0,
                'error': 'RED_ALERT_HISTORY_URL environment variable not set'
            })
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.oref.org.il/',
            'Accept': 'application/json, text/plain, */*'
        }
        
        response = requests.get(alert_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            alert_data = response.json()
            
            # Get Israel timezone for proper time handling
            israel_tz = _get_tz_jerusalem()
            now = datetime.now(israel_tz)
            
            # Process the alert history data to find the most recent alert
            last_alert = None
            last_alert_time = None
            
            if alert_data and isinstance(alert_data, list):
                # Sort alerts by date to find the most recent one
                valid_alerts = []
                
                for alert in alert_data:
                    try:
                        # Parse alert time - adjust format based on actual API response
                        alert_time_str = alert.get('alertDate', '')
                        if alert_time_str:
                            # Try different date formats that might be used
                            try:
                                alert_time = datetime.fromisoformat(alert_time_str.replace('Z', '+00:00'))
                            except:
                                try:
                                    alert_time = datetime.strptime(alert_time_str, '%Y-%m-%d %H:%M:%S')
                                except:
                                    continue
                            
                            alert_time = alert_time.astimezone(israel_tz)
                            locations = alert.get('data', [])
                            
                            if locations:  # Only consider alerts with locations
                                valid_alerts.append({
                                    'time': alert_time,
                                    'time_str': alert_time.isoformat(),
                                    'locations': locations,
                                    'category': alert.get('cat', 1)
                                })
                    except Exception:
                        continue
                
                # Sort by time and get the most recent
                if valid_alerts:
                    valid_alerts.sort(key=lambda x: x['time'], reverse=True)
                    last_alert = valid_alerts[0]
                    last_alert_time = last_alert['time']
            
            # Determine status based on how recent the last alert was
            if last_alert_time:
                time_since_last = now - last_alert_time
                
                # Consider "active" only if within the last 10 minutes
                if time_since_last.total_seconds() < 600:  # 10 minutes
                    status = 'active'
                    alert_locations = last_alert['locations']
                else:
                    status = 'clear'
                    alert_locations = []
                
                # Format last alert time for display
                if time_since_last.days > 0:
                    last_alert_display = f"{time_since_last.days}d ago"
                elif time_since_last.seconds > 3600:
                    hours = time_since_last.seconds // 3600
                    last_alert_display = f"{hours}h ago"
                elif time_since_last.seconds > 60:
                    minutes = time_since_last.seconds // 60
                    last_alert_display = f"{minutes}m ago"
                else:
                    last_alert_display = "Just now"
            else:
                status = 'clear'
                alert_locations = []
                last_alert_display = "No recent alerts"
            
            payload = {
                'alerts': alert_locations,
                'last_alert': last_alert,
                'last_alert_display': last_alert_display,
                'last_updated': now.isoformat(),
                'status': status,
                'location_count': len(alert_locations) if alert_locations else 0
            }
        else:
            payload = {
                'alerts': [],
                'last_alert': None,
                'last_alert_display': 'Unable to fetch data',
                'last_updated': datetime.now(_get_tz_jerusalem()).isoformat(),
                'status': 'unknown',
                'location_count': 0,
                'error': f'API returned status {response.status_code}'
            }
        
        # Cache for 2 minutes (balance between freshness and API load)
        cache_set(cache_key, payload, 120)
        return jsonify(payload)
        
    except Exception as e:
        print(f"Error fetching Red Alert data: {e}")
        payload = {
            'alerts': [],
            'last_alert': None,
            'last_alert_display': 'Connection error',
            'last_updated': datetime.now(_get_tz_jerusalem()).isoformat(),
            'status': 'error',
            'location_count': 0,
            'error': str(e)
        }
        return jsonify(payload)


def create_app():
    return app


if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "1") not in ("0", "false", "False")
    app.run(host=host, port=port, debug=debug)
