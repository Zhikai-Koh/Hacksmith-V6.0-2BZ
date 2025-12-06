import json
import random
import numpy as np
from datetime import datetime, timezone

NUM_BOTS_A = 200
NUM_BOTS_B = 150
NUM_NORMAL_USERS = 150
TOTAL_USERS = NUM_BOTS_A + NUM_BOTS_B + NUM_NORMAL_USERS
OUTPUT_FILE = "ua_grades_cache.json"

BOT_A_FINGERPRINT = {
    'speed_mean': 0.25, 
    'acc_dev_mean': 0.05, 
    'ttfa_mean': 150.0, 
    'variance': 0.001
}

BOT_B_FINGERPRINT = {
    'speed_mean': 0.8, 
    'acc_dev_mean': 0.01, 
    'ttfa_mean': 10.0, 
    'variance': 0.0005
}

NORMAL_RANGES = {
    'speed_min': 0.1, 'speed_max': 0.5,
    'acc_dev_min': 0.5, 'acc_dev_max': 5.0,
    'ttfa_min': 500.0, 'ttfa_max': 5000.0
}

def generate_profile(prefix: str, index: int, fingerprint: dict = None) -> dict:
    
    total_sessions = random.randint(10, 50)
    
    if fingerprint:
        std_dev = fingerprint['variance'] ** 0.5
        speed = np.random.normal(fingerprint['speed_mean'], std_dev)
        acc_dev = np.random.normal(fingerprint['acc_dev_mean'], std_dev)
        ttfa = np.random.normal(fingerprint['ttfa_mean'], std_dev * 10)
        
        speed = max(0.001, speed)
        acc_dev = max(0.001, acc_dev)
        ttfa = max(1.0, ttfa)
    else:
        speed = random.uniform(NORMAL_RANGES['speed_min'], NORMAL_RANGES['speed_max'])
        acc_dev = random.uniform(NORMAL_RANGES['acc_dev_min'], NORMAL_RANGES['acc_dev_max'])
        ttfa = random.uniform(NORMAL_RANGES['ttfa_min'], NORMAL_RANGES['ttfa_max'])

    return {
        f"{prefix}_{index}": {
            "total_sessions": total_sessions,
            "speed_sum": speed * total_sessions,
            "accuracy_dev_sum": acc_dev * total_sessions,
            "ttfa_ms_sum": ttfa * total_sessions,
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
    }

def generate_test_data() -> dict:
    ua_table = {}

    for i in range(NUM_BOTS_A):
        ua_table.update(generate_profile("BOT_A", i, BOT_A_FINGERPRINT))

    for i in range(NUM_BOTS_B):
        ua_table.update(generate_profile("BOT_B", i, BOT_B_FINGERPRINT))

    for i in range(NUM_NORMAL_USERS):
        ua_table.update(generate_profile("HUMAN", i))
        
    print(f"Generated {len(ua_table)} total profiles for testing.")
    return ua_table

if __name__ == "__main__":
    
    if TOTAL_USERS < 500:
        print(f"Error: Total users ({TOTAL_USERS}) is less than the required 500.")
        exit()

    test_data = generate_test_data()

    try:
        with open(OUTPUT_FILE, 'w') as f:
            json.dump(test_data, f, indent=4, default=float)
        print(f"Created test cache file: {OUTPUT_FILE}")
        
    except Exception as e:
        print(f"Write file fail: {e}")