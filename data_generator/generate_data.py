import os
import json
import random
import pandas as pd
import numpy as np
from faker import Faker
from datetime import datetime, timedelta

# Cấu hình
NUM_USERS = 1000
START_DATE = datetime(2025, 11, 1)
DAYS_RANGE = 30  # Dữ liệu trong 30 ngày
DATA_DIR = "./data"

# Khởi tạo Faker
fake = Faker()
Faker.seed(42)
random.seed(42)

# Đảm bảo thư mục data tồn tại
os.makedirs(DATA_DIR, exist_ok=True)

# GAME CONFIGURATION
SOURCES = ['Organic', 'Facebook Ads', 'Google Ads', 'Unity Ads', 'TikTok Ads']
WEAPONS = ['Glock-17', 'AK-47', 'M4A1', 'Shotgun-S1', 'Sniper-AWP', 'Katana']
LEVELS = range(1, 21)  # Level 1 đến 20
EVENTS = ['session_start', 'level_start', 'level_complete', 'level_fail', 'ad_reward_claim', 'iap_purchase']

# HELPER FUNCTIONS

def generate_ga4_params(params_dict):
    """
    Chuyển đổi dict đơn giản sang cấu trúc Nested của BigQuery (GA4 Schema).
    Ví dụ: {'score': 100} -> [{'key': 'score', 'value': {'int_value': 100}}]
    """
    bq_params = []
    for key, val in params_dict.items():
        val_obj = {}
        if isinstance(val, int):
            val_obj['int_value'] = val
        elif isinstance(val, float):
            val_obj['float_value'] = val
        else:
            val_obj['string_value'] = str(val)

        bq_params.append({
            "key": key,
            "value": val_obj
        })
    return bq_params

def get_random_timestamp(date_obj):
    """Tạo giờ ngẫu nhiên trong ngày"""
    seconds = random.randint(0, 86399)
    return date_obj + timedelta(seconds=seconds)

# MAIN GENERATION

print("1. Đang khởi tạo hồ sơ người dùng (User Profiles)...")

users = []
for _ in range(NUM_USERS):
    user_id = fake.uuid4()
    join_date = START_DATE + timedelta(days=random.randint(0, DAYS_RANGE - 5))

    # Xác định Geo & Device cố định cho user đó
    country = random.choice(['Vietnam', 'USA', 'Thailand', 'Brazil', 'Philippines'])
    device_cat = random.choice(['mobile', 'tablet'])
    os_sys = 'Android' if random.random() > 0.3 else 'iOS'  # 70% Android

    # Xác định Source & CPI
    source = random.choice(SOURCES)
    cpi = 0.0
    if source == 'Facebook Ads':
        cpi = round(random.uniform(1.5, 3.0), 2)
    elif source == 'Google Ads':
        cpi = round(random.uniform(1.2, 2.5), 2)
    elif source == 'Unity Ads':
        cpi = round(random.uniform(0.8, 1.5), 2)
    elif source == 'TikTok Ads':
        cpi = round(random.uniform(0.5, 1.2), 2)

    users.append({
        'user_id': user_id,
        'user_pseudo_id': fake.md5(),  # Device ID
        'install_date': join_date,
        'country': country,
        'city': fake.city(),
        'device_category': device_cat,
        'mobile_os': os_sys,
        'source': source,
        'cpi': cpi,
        'campaign_id': f"CMP_{random.randint(100, 105)}" if source != 'Organic' else None
    })

# STEP 1: EXPORT USER ACQUISITION (CSV)
df_ua = pd.DataFrame(users)[['user_id', 'install_date', 'source', 'campaign_id', 'cpi']]
df_ua.to_csv(f"{DATA_DIR}/user_acquisition.csv", index=False)
print(f"-> Đã lưu {DATA_DIR}/user_acquisition.csv")

# STEP 2: GENERATE EVENTS (JSON & CSV)

all_events_nested = []  # Dành cho JSON (BigQuery)
all_events_flat = []  # Dành cho CSV (Tableau)

for user in users:
    # Mô phỏng user chơi game trong vài ngày sau khi cài đặt
    # Retention curve simulation: Rất nhiều user bỏ sau ngày 1
    play_days = random.choices(
        [1, 3, 7, 14, 30],
        weights=[40, 20, 15, 15, 10],
        k=1
    )[0]

    current_level = 1

    for day_offset in range(play_days):
        active_date = user['install_date'] + timedelta(days=day_offset)
        if active_date > START_DATE + timedelta(days=DAYS_RANGE):
            break

        # Mỗi ngày chơi 1-3 sessions
        num_sessions = random.randint(1, 3)
        for _ in range(num_sessions):
            session_time = get_random_timestamp(active_date)

            # --- Event: session_start ---
            base_event = {
                'event_date': session_time.strftime('%Y%m%d'),
                'event_timestamp': int(session_time.timestamp() * 1000000),
                'user_id': user['user_id'],
                'user_pseudo_id': user['user_pseudo_id'],
                'geo': {'country': user['country'], 'city': user['city']},
                'device': {'category': user['device_category'], 'mobile_os': user['mobile_os']}
            }

            # 1. Session Start
            evt_session = base_event.copy()
            evt_session['event_name'] = 'session_start'
            evt_session['event_params'] = generate_ga4_params({'ga_session_id': random.randint(1000, 9999)})
            all_events_nested.append(evt_session)

            # Flatten for CSV (chỉ lấy field quan trọng)
            flat_row = {k: v for k, v in base_event.items() if k not in ['geo', 'device']}
            flat_row.update({'event_name': 'session_start', 'country': user['country'], 'os': user['mobile_os']})
            all_events_flat.append(flat_row)

            # 2. Gameplay Loop (Chơi 1-5 levels mỗi session)
            num_levels = random.randint(1, 5)
            session_cursor = session_time

            for _ in range(num_levels):
                session_cursor += timedelta(minutes=random.randint(2, 10))  # Thời gian chơi mỗi màn

                # --- Event: level_start ---
                difficulty = 'Hard' if current_level % 5 == 0 else 'Normal'  # Level chia hết cho 5 thì khó
                weapon = random.choice(WEAPONS)

                evt_start = base_event.copy()
                evt_start['event_name'] = 'level_start'
                evt_start['event_timestamp'] = int(session_cursor.timestamp() * 1000000)
                params_dict = {'level_id': current_level, 'difficulty': difficulty, 'weapon_used': weapon}
                evt_start['event_params'] = generate_ga4_params(params_dict)
                all_events_nested.append(evt_start)

                # Flatten
                flat_row = {k: v for k, v in base_event.items() if k not in ['geo', 'device']}
                flat_row.update({'event_name': 'level_start', 'country': user['country'], 'os': user['mobile_os']})
                flat_row.update(params_dict)  # Bung param ra cột
                all_events_flat.append(flat_row)

                # Win or Lose? (Càng lên cao càng dễ thua)
                win_rate = max(0.2, 0.9 - (current_level * 0.03))
                is_win = random.random() < win_rate

                session_cursor += timedelta(minutes=random.randint(1, 3))

                if is_win:
                    # Event: level_complete
                    evt_end = base_event.copy()
                    evt_end['event_name'] = 'level_complete'
                    evt_end['event_timestamp'] = int(session_cursor.timestamp() * 1000000)
                    gold_earned = random.randint(50, 200)
                    params_dict = {'level_id': current_level, 'time_spent_sec': random.randint(60, 300),
                                   'gold_earned': gold_earned, 'status': 'Win'}
                    evt_end['event_params'] = generate_ga4_params(params_dict)
                    all_events_nested.append(evt_end)

                    # Flatten
                    flat_row = {k: v for k, v in base_event.items() if k not in ['geo', 'device']}
                    flat_row.update(
                        {'event_name': 'level_complete', 'country': user['country'], 'os': user['mobile_os']})
                    flat_row.update(params_dict)
                    all_events_flat.append(flat_row)

                    current_level += 1  # Lên cấp
                else:
                    # Event: level_fail
                    evt_fail = base_event.copy()
                    evt_fail['event_name'] = 'level_fail'
                    evt_fail['event_timestamp'] = int(session_cursor.timestamp() * 1000000)
                    params_dict = {'level_id': current_level,
                                   'death_reason': random.choice(['Zombie Bite', 'Out of Ammo', 'Time Out']),
                                   'status': 'Fail'}
                    evt_fail['event_params'] = generate_ga4_params(params_dict)
                    all_events_nested.append(evt_fail)

                    # Flatten
                    flat_row = {k: v for k, v in base_event.items() if k not in ['geo', 'device']}
                    flat_row.update({'event_name': 'level_fail', 'country': user['country'], 'os': user['mobile_os']})
                    flat_row.update(params_dict)
                    all_events_flat.append(flat_row)

                # 3. Monetization (Randomly)
                # Ad Watch (Sau khi chơi xong level)
                if random.random() < 0.3:
                    evt_ad = base_event.copy()
                    evt_ad['event_name'] = 'ad_reward_claim'
                    evt_ad['event_timestamp'] = int((session_cursor + timedelta(seconds=30)).timestamp() * 1000000)
                    params_dict = {'ad_type': 'Rewarded Video', 'placement': 'End Game', 'gold_reward': 50}
                    evt_ad['event_params'] = generate_ga4_params(params_dict)
                    all_events_nested.append(evt_ad)

                    # Flatten
                    flat_row = {k: v for k, v in base_event.items() if k not in ['geo', 'device']}
                    flat_row.update(
                        {'event_name': 'ad_reward_claim', 'country': user['country'], 'os': user['mobile_os']})
                    flat_row.update(params_dict)
                    all_events_flat.append(flat_row)

                # IAP Purchase (Hiếm hơn)
                if random.random() < 0.05:
                    evt_iap = base_event.copy()
                    evt_iap['event_name'] = 'iap_purchase'
                    evt_iap['event_timestamp'] = int((session_cursor + timedelta(seconds=60)).timestamp() * 1000000)
                    pack_price = random.choice([0.99, 4.99, 9.99])
                    product_id = f"pack_gem_{int(pack_price)}"
                    params_dict = {'product_id': product_id, 'price': pack_price, 'currency': 'USD', 'quantity': 1}
                    evt_iap['event_params'] = generate_ga4_params(params_dict)
                    all_events_nested.append(evt_iap)

                    # Flatten
                    flat_row = {k: v for k, v in base_event.items() if k not in ['geo', 'device']}
                    flat_row.update({'event_name': 'iap_purchase', 'country': user['country'], 'os': user['mobile_os']})
                    flat_row.update(params_dict)
                    all_events_flat.append(flat_row)

# STEP 3: EXPORT EVENTS

# Lưu JSON
json_path = f"{DATA_DIR}/user_events_nested.json"
with open(json_path, 'w', encoding='utf-8') as f:
    for entry in all_events_nested:
        json.dump(entry, f)
        f.write('\n')
print(f"-> Đã lưu {json_path} (Format: NDJSON cho BigQuery)")

# Lưu CSV
df_events = pd.DataFrame(all_events_flat)
# Sắp xếp lại cột cho đẹp (đưa param lên đầu hoặc cuối tùy ý)
cols = ['event_date', 'event_timestamp', 'event_name', 'user_id', 'country', 'os',
        'level_id', 'status', 'weapon_used', 'gold_earned', 'price', 'product_id']
# Lọc chỉ lấy các cột có trong df (vì params không đồng nhất giữa các rows)
exist_cols = [c for c in cols if c in df_events.columns]
df_events = df_events[exist_cols]
df_events.to_csv(f"{DATA_DIR}/user_events_flat.csv", index=False)
print(f"-> Đã lưu {DATA_DIR}/user_events_flat.csv (Format: CSV cho Tableau)")

print("DONE")
