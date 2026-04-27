import sqlite3
import json
import os
from datetime import datetime
from threading import Lock

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'smart_city.db')
db_lock = Lock()

def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db_lock:
        conn = get_connection()
        c = conn.cursor()
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS routes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_node TEXT,
                end_node TEXT,
                priority TEXT,
                path TEXT,
                cost REAL,
                eta REAL,
                actual_time REAL,
                weather TEXT,
                scenario TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS traffic_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                node TEXT,
                neighbor TEXT,
                level TEXT,
                weight REAL,
                vehicle_count INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS ambulance_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ambulance_id TEXT,
                path TEXT,
                priority TEXT,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                avg_speed REAL,
                intersections_cleared INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS intersection_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                node TEXT,
                total_wait_time REAL,
                vehicles_passed INTEGER,
                signal_changes INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS weather_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                condition TEXT,
                speed_multiplier REAL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()

def log_route(start, end, priority, path, cost, eta, weather="Clear", scenario="Normal"):
    with db_lock:
        conn = get_connection()
        c = conn.cursor()
        c.execute('''
            INSERT INTO routes (start_node, end_node, priority, path, cost, eta, weather, scenario)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (start, end, priority, json.dumps(path), cost, eta, weather, scenario))
        conn.commit()
        conn.close()

def log_traffic(node, neighbor, level, weight, vehicle_count):
    with db_lock:
        conn = get_connection()
        c = conn.cursor()
        c.execute('''
            INSERT INTO traffic_history (node, neighbor, level, weight, vehicle_count)
            VALUES (?, ?, ?, ?, ?)
        ''', (node, neighbor, level, weight, vehicle_count))
        conn.commit()
        conn.close()

def log_ambulance(amb_id, path, priority, start_time, end_time, avg_speed, intersections_cleared):
    with db_lock:
        conn = get_connection()
        c = conn.cursor()
        c.execute('''
            INSERT INTO ambulance_logs (ambulance_id, path, priority, start_time, end_time, avg_speed, intersections_cleared)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (amb_id, json.dumps(path), priority, start_time, end_time, avg_speed, intersections_cleared))
        conn.commit()
        conn.close()

def log_weather(condition, speed_multiplier):
    with db_lock:
        conn = get_connection()
        c = conn.cursor()
        c.execute('''
            INSERT INTO weather_log (condition, speed_multiplier)
            VALUES (?, ?)
        ''', (condition, speed_multiplier))
        conn.commit()
        conn.close()

def get_analytics():
    with db_lock:
        conn = get_connection()
        c = conn.cursor()
        
        # Average response time by priority
        c.execute('''
            SELECT priority, AVG(actual_time) as avg_time, COUNT(*) as count
            FROM routes WHERE actual_time IS NOT NULL
            GROUP BY priority
        ''')
        priority_stats = [dict(row) for row in c.fetchall()]
        
        # Hourly traffic pattern
        c.execute('''
            SELECT strftime('%H', timestamp) as hour, AVG(weight) as avg_weight
            FROM traffic_history
            GROUP BY hour
            ORDER BY hour
        ''')
        hourly_traffic = [dict(row) for row in c.fetchall()]
        
        # Recent routes
        c.execute('''
            SELECT * FROM routes ORDER BY created_at DESC LIMIT 20
        ''')
        recent_routes = [dict(row) for row in c.fetchall()]
        
        # Weather impact
        c.execute('''
            SELECT weather, AVG(cost) as avg_cost, COUNT(*) as count
            FROM routes GROUP BY weather
        ''')
        weather_impact = [dict(row) for row in c.fetchall()]
        
        conn.close()
        
        return {
            "priority_stats": priority_stats,
            "hourly_traffic": hourly_traffic,
            "recent_routes": recent_routes,
            "weather_impact": weather_impact
        }

