from flask import Flask, request, render_template
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional

app = Flask(__name__)

UA_GRADES_CACHE_FILE = "ua_grades_cache.json" 
REPORT_FILE_AVERAGES = "ua_average_metrics_report.json" 
SUSPICIOUS_CLUSTER_IDS = [0, 1, 2, 3, 4] 
USER_THRESHOLD_FOR_ANALYSIS = 500
DATA_EXPIRY_HOURS = 1

# =========================================================================
#RAW METRICS EXTRACTION LOGIC
# =========================================================================

def extract_raw_metrics(session: dict) -> Dict[str, float]:
    avg_speed = session.get('avg_speed', 0.0) 
    max_dev = session.get('max_normalized_deviation', 1.0) 
    ttfa = session.get('time_to_first_action_ms', 99999.0) 
    
    return {
        "speed": avg_speed,
        "accuracy_dev": max_dev,
        "ttfa_ms": ttfa,
        "session_count": 1
    }

# =========================================================================
#PERSISTENCE/CACHE MANAGER LOGIC
# =========================================================================

ZERO_STATE = {
    "total_sessions": 0,
    "speed_sum": 0.0, 
    "accuracy_dev_sum": 0.0, 
    "ttfa_ms_sum": 0.0,
    "last_updated": None
}

def load_ua_hash_table() -> Dict[str, Dict[str, Any]]:
    ua_table = {}
    if os.path.exists(UA_GRADES_CACHE_FILE):
        try:
            with open(UA_GRADES_CACHE_FILE, 'r') as f:
                ua_table = json.load(f)
        except Exception:
            pass
            
    current_time = datetime.now(timezone.utc)
    expiry_threshold = current_time - timedelta(hours=DATA_EXPIRY_HOURS)
    
    fresh_ua_table = {}
    
    for ua, totals in ua_table.items():
        last_updated_str = totals.get("last_updated")
        
        if last_updated_str:
            try:
                last_updated_dt = datetime.fromisoformat(last_updated_str)
                
                if last_updated_dt >= expiry_threshold:
                    fresh_ua_table[ua] = totals
                
            except ValueError:
                continue
                
    return fresh_ua_table

def save_ua_hash_table(ua_table: Dict[str, Dict[str, Any]]):
    try:
        with open(UA_GRADES_CACHE_FILE, 'w') as f:
            json.dump(ua_table, f, indent=4)
    except Exception as e:
        print(f"Error saving cache file: {e}")

def update_ua_hash_table(ua_table: Dict[str, Dict[str, Any]], user_agent: str, metrics: Dict[str, float]):
    current_totals = ua_table.get(user_agent, ZERO_STATE.copy())

    current_totals["total_sessions"] += 1
    current_totals["speed_sum"] += metrics["speed"]
    current_totals["accuracy_dev_sum"] += metrics["accuracy_dev"]
    current_totals["ttfa_ms_sum"] += metrics["ttfa_ms"]
    
    current_totals["last_updated"] = datetime.now(timezone.utc).isoformat()
    
    ua_table[user_agent] = current_totals
    
    return True

# =========================================================================
# CONCEPTUAL FUNCTION: Invalidate session token or delete session record.
# =========================================================================

def disconnect_user_by_ua(user_agent: str) -> bool:
    print(f"ACTION: KICKED/INVALIDATED sessions for suspicious UA: {user_agent[:40]}...")
    return True

# =========================================================================
#FLASK ROUTES
# =========================================================================

@app.get("/")
def index():
    return render_template("UnbelievableChicken.html")

@app.post("/telemetry")
def telemetry():
    try:
        data = request.get_json(force=True, silent=False)
    except Exception:
        return {"status": "error", "reason": "invalid_json"}, 400

    metrics = extract_raw_metrics(data)
    user_agent = data.get("user_agent", "UNKNOWN_UA")

    ua_table = load_ua_hash_table()
    update_ua_hash_table(ua_table, user_agent, metrics)
    save_ua_hash_table(ua_table) 

    return {"status": "ok", "metrics": metrics}

@app.get("/grades")
def get_grades():
    ua_table = load_ua_hash_table()
    active_user_count = len(ua_table)
    
    if active_user_count < USER_THRESHOLD_FOR_ANALYSIS:
        return {
            "status": "pending",
            "reason": "User threshold not met for analysis.",
            "current_active_users": active_user_count,
            "required_users": USER_THRESHOLD_FOR_ANALYSIS
        }, 202
        
    try:
        with open(REPORT_FILE_AVERAGES, 'r') as f:
            report_data = json.load(f)
    except FileNotFoundError:
        return {"stcatus": "error", "reason": f"Analysis report {REPORT_FILE_AVERAGES} not found. Run analysis script first."}, 500
    except Exception as e:
        return {"status": "error", "reason": f"Failed to read analysis report: {e}"}, 500

    kick_count = 0
    
    for profile in report_data:
        if profile.get('cluster') in SUSPICIOUS_CLUSTER_IDS:
            disconnect_user_by_ua(profile['user_agent'])
            kick_count += 1
    
    return {
        "status": "ok", 
        "action_summary": f"Kicked {kick_count} users identified in uniform clusters.",
        "flagged_cluster_ids": SUSPICIOUS_CLUSTER_IDS,
        "total_profiles_analyzed": len(report_data),
        "data_preview": report_data[:5]
    }

if __name__ == "__main__":
    if 'TZ' not in os.environ:
        os.environ['TZ'] = 'UTC'
        
    app.run(debug=True)