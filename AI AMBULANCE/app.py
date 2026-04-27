from flask import Flask, jsonify, request, send_from_directory
from flask_socketio import SocketIO, emit
import os
import json
import threading
import time
from datetime import datetime

from core.traffic_sim import TrafficSimulator
from core.pathfinding import a_star_search, yen_k_shortest_paths, predict_traffic
from core.database import init_db, log_route, log_ambulance, get_analytics
from core.weather import WEATHER_TYPES
from core.scenarios import SCENARIOS

app = Flask(__name__, static_folder='static', static_url_path='')
app.config['SECRET_KEY'] = 'smart-city-secret'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Global simulator
simulator = TrafficSimulator(width=12, height=12)
sim_running = True
sim_thread = None

# Prediction history
prediction_history = {}

# Active ambulances tracking
active_ambulances = {}

def simulation_loop():
    global sim_running
    while sim_running:
        simulator.update(dt=1)
        state = simulator.get_state()
        socketio.emit('sim_update', state)
        time.sleep(0.5)  # 2 ticks per second

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/grid', methods=['GET'])
def get_grid():
    return jsonify(simulator.get_state())

@app.route('/api/toggle_block', methods=['POST'])
def toggle_block():
    data = request.json
    u = data.get('u')
    v = data.get('v')
    graph = simulator.edges
    if u in graph and v in graph[u]:
        current = graph[u][v].get('blocked', False)
        graph[u][v]['blocked'] = not current
        graph[v][u]['blocked'] = not current
        return jsonify({"success": True, "blocked": not current})
    return jsonify({"success": False}), 400

@app.route('/api/route', methods=['POST'])
def calculate_route():
    data = request.json
    start = data.get('start', '0,0')
    end = data.get('end', '11,11')
    priority = data.get('priority', 'Normal')
    hospital_id = data.get('hospital', None)
    
    # If hospital specified, route to hospital node
    if hospital_id == 'nearest':
        best_cost = float('inf')
        best_end = end
        graph = simulator.get_graph()
        weather_mult = simulator.weather.speed_multiplier
        predictions = predict_traffic(graph, prediction_history)
        for h in simulator.hospitals:
            _, cost = a_star_search(graph, start, h['node'], priority, weather_mult, predictions)
            if cost < best_cost and cost > 0:
                best_cost = cost
                best_end = h['node']
        end = best_end
    elif hospital_id:
        for h in simulator.hospitals:
            if h['id'] == hospital_id:
                end = h['node']
                break
    
    graph = simulator.get_graph()
    weather_mult = simulator.weather.speed_multiplier
    
    # Get predictions
    predictions = predict_traffic(graph, prediction_history)
    
    # Main route
    main_path, main_cost = a_star_search(graph, start, end, priority, weather_mult, predictions)
    
    # Alternate routes using Yen's algorithm
    alt_paths = yen_k_shortest_paths(graph, start, end, k=2, priority=priority, weather_mult=weather_mult)
    alt_route = None
    if len(alt_paths) > 1:
        alt_route = {"path": alt_paths[1][0], "cost": alt_paths[1][1]}
    
    # Log to database
    log_route(start, end, priority, main_path, main_cost, main_cost, 
              simulator.weather.current, simulator.scenario.current)
    
    return jsonify({
        "main_route": {"path": main_path, "cost": main_cost},
        "alternate_route": alt_route,
        "weather": simulator.weather.get_state(),
        "scenario": simulator.scenario.current
    })

@app.route('/api/hospitals', methods=['GET'])
def get_hospitals():
    return jsonify(simulator.hospitals)

@app.route('/api/scenarios', methods=['GET'])
def get_scenarios():
    return jsonify(simulator.scenario.get_all())

@app.route('/api/scenario', methods=['POST'])
def set_scenario():
    data = request.json
    name = data.get('name', 'Normal')
    success = simulator.scenario.load(name)
    return jsonify({"success": success, "current": simulator.scenario.current})

@app.route('/api/weather', methods=['GET'])
def get_weather():
    return jsonify(simulator.weather.get_state())

@app.route('/api/analytics', methods=['GET'])
def get_analytics_data():
    return jsonify(get_analytics())

@app.route('/api/signals/toggle_rl', methods=['POST'])
def toggle_rl():
    data = request.json
    node = data.get('node')
    if node and node in simulator.signals:
        enabled = simulator.signals[node].toggle_rl()
        return jsonify({"node": node, "rl_enabled": enabled})
    return jsonify({"error": "Invalid node"}), 400

# SocketIO events
@socketio.on('connect')
def handle_connect():
    emit('init_state', simulator.get_state())

@socketio.on('dispatch_ambulance')
def handle_dispatch(data):
    amb_id = data.get('id', f"amb_{int(time.time())}")
    path = data['path']
    priority = data.get('priority', 'Normal')
    
    simulator.add_ambulance(amb_id, path, priority)
    active_ambulances[amb_id] = {
        "path": path,
        "priority": priority,
        "start_time": datetime.now(),
        "index": 0
    }
    
    emit('ambulance_dispatched', {"id": amb_id, "path": path, "priority": priority}, broadcast=True)

@socketio.on('ambulance_position')
def handle_amb_position(data):
    amb_id = data['id']
    index = data['index']
    progress = data.get('progress', 0)
    
    path = active_ambulances.get(amb_id, {}).get('path', [])
    next_node = path[index + 1] if index + 1 < len(path) else None
    
    simulator.update_ambulance(amb_id, index, progress, next_node)
    
    if index >= len(path) - 1:
        # Arrived
        end_time = datetime.now()
        start_time = active_ambulances[amb_id]['start_time']
        duration = (end_time - start_time).total_seconds()
        
        log_ambulance(amb_id, path, active_ambulances[amb_id]['priority'], 
                      start_time, end_time, 0, len(path))
        
        simulator.remove_ambulance(amb_id)
        del active_ambulances[amb_id]
        
        emit('ambulance_arrived', {"id": amb_id, "duration": duration}, broadcast=True)

@socketio.on('request_state')
def handle_request_state():
    emit('sim_update', simulator.get_state())

if __name__ == '__main__':
    init_db()
    
    # Start simulation thread
    sim_thread = threading.Thread(target=simulation_loop, daemon=True)
    sim_thread.start()
    
    socketio.run(app, debug=True, host='0.0.0.0', port=5000, use_reloader=False, allow_unsafe_werkzeug=True)

