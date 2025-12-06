import json
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import DBSCAN
from typing import Dict, Any, List

UA_GRADES_CACHE_FILE = "ua_grades_cache.json"
REPORT_FILE_AVERAGES = "ua_average_metrics_report.json"
MIN_SESSIONS_REQUIRED = 1 
USER_THRESHOLD_FOR_ANALYSIS = 500

DBSCAN_EPS = 0.1 
DBSCAN_MIN_SAMPLES = 2 

def load_and_calculate_averages(file_path: str) -> pd.DataFrame:

    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading cache file: {e}")
        return pd.DataFrame()

    profiles = []
    for ua, totals in data.items():
        count = totals.get("total_sessions", 0)
        if count < MIN_SESSIONS_REQUIRED: 
             continue 

        profiles.append({
            'user_agent': ua,
            'total_sessions': count,
            'avg_speed_px_ms': totals.get("speed_sum", 0.0) / count,
            'avg_accuracy_dev': totals.get("accuracy_dev_sum", 0.0) / count,
            'avg_ttfa_ms': totals.get("ttfa_ms_sum", 0.0) / count
        })

    df = pd.DataFrame(profiles)
    return df

def analyze_uniform_bot_clusters(df: pd.DataFrame):
    if df.empty:
        print("No user data available for analysis.")
        report_data = [] 
    else:
        print(f"--- Analyzing {len(df)} User Agents for Uniform Tendency Clusters (DBSCAN) ---")
        
        features = ['avg_speed_px_ms', 'avg_accuracy_dev', 'avg_ttfa_ms']
        X = df[features]
        
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        dbscan = DBSCAN(eps=DBSCAN_EPS, min_samples=DBSCAN_MIN_SAMPLES)
        df['cluster'] = dbscan.fit_predict(X_scaled)
        
        report_data = df.to_dict('records')

        num_clusters = len(np.unique(df['cluster'])) - (1 if -1 in df['cluster'].values else 0)
        print(f"DBSCAN found {num_clusters} tight clusters (Cluster IDs != -1 are suspicious).")
        print("Run the Flask /grades endpoint to trigger security actions.")

    try:
        with open(REPORT_FILE_AVERAGES, 'w') as f:
            json.dump(report_data, f, indent=4)
        print(f"\n Analysis complete. Results saved to {REPORT_FILE_AVERAGES}")
        
    except Exception as e:
        print(f" Error saving analysis report: {e}")

if __name__ == "__main__":
    
    profiles_df = load_and_calculate_averages(UA_GRADES_CACHE_FILE)
    active_user_count = len(profiles_df)
    
    if active_user_count < USER_THRESHOLD_FOR_ANALYSIS:
        print(f"Threshold not met. Skipping analysis. Active users: {active_user_count} (Required: {USER_THRESHOLD_FOR_ANALYSIS})")
        
        try:
            with open(REPORT_FILE_AVERAGES, 'w') as f:
                json.dump([], f)
            print(f"Cleared analysis report {REPORT_FILE_AVERAGES}.")
        except Exception as e:
            print(f"Could not write empty report file: {e}")
            
        exit()

    analyze_uniform_bot_clusters(profiles_df)