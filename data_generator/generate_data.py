import pandas as pd
import numpy as np
import random
import json
import os
from datetime import datetime, timedelta
from faker import Faker

fake = Faker()

# CẤU HÌNH GAME
USERS_NUM = 2000
START_DATE = datetime(2025, 1, 1)

def generate_data():
    flat_events = []  # Cho CSV (Streamlit)
    nested_events = []  # Cho JSON (BigQuery)

    for _ in range(USERS_NUM):
        user_id = fake.uuid4()
        join_date = START_DATE + timedelta(days=random.randint(0, 30))

        # Phân loại User: 90% dân cày (F2P), 10% đại gia (Whale)
        user_type = np.random.choice(['F2P', 'Whale'], p=[0.90, 0.10])
        skill = random.uniform(0.1, 0.9)

        # User Whale chơi lâu hơn
        retention = random.randint(1, 7) if user_type == 'F2P' else random.randint(7, 45)
        level = 1
        gold = 1000

        for day in range(retention):
            act_date = join_date + timedelta(days=day)
            ts = int(act_date.timestamp() * 1000000)  # Micros
            date_str = act_date.strftime("%Y-%m-%d")

            # EVENT 1: SESSION START
            # Data phẳng
            flat_events.append({
                "date": date_str, "user_id": user_id, "event_name": "session_start",
                "user_type": user_type, "level": level, "revenue": 0
            })

            # Data Nested (Chuẩn BigQuery)
            nested_events.append({
                "event_date": act_date.strftime("%Y%m%d"),
                "event_timestamp": ts,
                "event_name": "session_start",
                "user_pseudo_id": user_id,
                "event_params": [
                    {"key": "user_type", "value": {"string_value": user_type}},
                    {"key": "ga_session_id", "value": {"int_value": random.randint(1000, 9999)}}
                ]
            })

            # GAMEPLAY LOOP
            matches = random.randint(1, 5)
            for _ in range(matches):
                # Logic: Level cao khó hơn
                win_rate = skill - (level * 0.02) + 0.5
                is_win = random.random() < win_rate

                evt_name = "level_complete" if is_win else "level_fail"

                # Flat Log
                flat_events.append({
                    "date": date_str, "user_id": user_id, "event_name": evt_name,
                    "user_type": user_type, "level": level, "revenue": 0
                })

                # Nested Log
                nested_events.append({
                    "event_date": act_date.strftime("%Y%m%d"),
                    "event_timestamp": ts,
                    "event_name": evt_name,
                    "user_pseudo_id": user_id,
                    "event_params": [
                        {"key": "level", "value": {"int_value": level}},
                        {"key": "result", "value": {"string_value": "win" if is_win else "lose"}}
                    ]
                })

                if is_win:
                    level += 1

                # EVENT 2: MUA ĐỒ (SINK)
                if user_type == 'Whale' and random.random() < 0.3:
                    rev = 4.99
                    flat_events.append({
                        "date": date_str, "user_id": user_id, "event_name": "in_app_purchase",
                        "user_type": user_type, "level": level, "revenue": rev
                    })
                    nested_events.append({
                        "event_date": act_date.strftime("%Y%m%d"),
                        "event_timestamp": ts,
                        "event_name": "in_app_purchase",
                        "user_pseudo_id": user_id,
                        "event_params": [
                            {"key": "value", "value": {"double_value": rev}},
                            {"key": "item", "value": {"string_value": "starter_pack"}}
                        ]
                    })

    # LƯU FILE
    os.makedirs('data', exist_ok=True)

    # 1. Lưu CSV cho Streamlit
    pd.DataFrame(flat_events).to_csv('data/game_data.csv', index=False)

    # 2. Lưu JSON cho BigQuery
    with open('data/raw_logs.json', 'w') as f:
        for record in nested_events:
            json.dump(record, f)
            f.write('\n')

    print(f"Done.")

if __name__ == "__main__":
    generate_data()