import random
import math
import numpy as np
from collections import defaultdict
from .rl_signals import RLTrafficController
from .weather import WeatherSystem
from .scenarios import ScenarioEngine
from .database import log_traffic

TRAFFIC_LEVELS = {
    "Low": 1,
    "Medium": 3,
    "High": 10,
    "Blocked": 999
}

class Vehicle:
    def __init__(self, vid, route, sim):
        self.id = vid
        self.route = route
        self.sim = sim
        self.pos_idx = 0
        self.progress = 0.0  # 0 to 1 along current edge
        self.speed = 0.0
        self.max_speed = random.uniform(0.3, 0.5)  # nodes per tick
        self.state = "moving"  # moving, waiting, arrived
        self.wait_time = 0
        
    def current_edge(self):
        if self.pos_idx >= len(self.route) - 1:
            return None
        return (self.route[self.pos_idx], self.route[self.pos_idx + 1])
    
    def update(self, dt=1):
        if self.state == "arrived":
            return
        
        edge = self.current_edge()
        if edge is None:
            self.state = "arrived"
            return
        
        u, v = edge
        # Check signal at destination node
        signal = self.sim.signals.get(v)
        if signal:
            # If approaching and signal is red/yellow for our direction
            if self.progress > 0.7:
                phase_ok = (signal.phase == "NS" and self._is_ns_edge(u, v)) or \
                           (signal.phase == "EW" and self._is_ew_edge(u, v))
                if signal.state == "red" or (signal.state == "green" and not phase_ok):
                    self.speed = max(0, self.speed - 0.1)
                    self.wait_time += dt
                    return
        
        # Check vehicle ahead (simplified car-following)
        ahead = self.sim._vehicle_ahead_on_edge(self, edge)
        if ahead and ahead.progress - self.progress < 0.15:
            self.speed = max(0, min(self.speed, ahead.speed) - 0.05)
            if self.speed < 0.01:
                self.wait_time += dt
            return
        
        # Normal movement
        edge_weight = self.sim.get_edge_weight(u, v)
        target_speed = self.max_speed / max(1, edge_weight * 0.3)
        target_speed *= self.sim.weather.speed_multiplier
        
        self.speed = min(target_speed, self.speed + 0.02)
        self.progress += self.speed * dt
        
        if self.progress >= 1.0:
            self.progress = 0.0
            self.pos_idx += 1
            self.speed *= 0.8  # Slow down for turn
    
    def _is_ns_edge(self, u, v):
        ux, uy = self.sim._parse(u)
        vx, vy = self.sim._parse(v)
        return abs(ux - vx) == 0 and abs(uy - vy) == 1
    
    def _is_ew_edge(self, u, v):
        ux, uy = self.sim._parse(u)
        vx, vy = self.sim._parse(v)
        return abs(ux - vx) == 1 and abs(uy - vy) == 0
    
    def get_position(self):
        if self.pos_idx >= len(self.route) - 1:
            return self.sim._get_coords(self.route[-1])
        u = self.route[self.pos_idx]
        v = self.route[self.pos_idx + 1]
        x1, y1 = self.sim._get_coords(u)
        x2, y2 = self.sim._get_coords(v)
        t = self.progress
        return (x1 + (x2 - x1) * t, y1 + (y2 - y1) * t)

class TrafficSimulator:
    def __init__(self, width=12, height=12):
        self.width = width
        self.height = height
        self.edges = self._generate_base_edges()
        self.vehicles = []
        self.ambulances = {}
        self.signals = {}
        self.weather = WeatherSystem()
        self.scenario = ScenarioEngine()
        self.tick = 0
        self.max_vehicles = 150
        self.spawn_rate = 0.15
        
        # Hospitals
        self.hospitals = [
            {"id": "h1", "node": "2,2", "name": "General Hospital", "capacity": 50, "specialization": "General", "load": 0.5},
            {"id": "h2", "node": "9,9", "name": "Trauma Center", "capacity": 30, "specialization": "Trauma", "load": 0.7},
            {"id": "h3", "node": "1,10", "name": "Children's Hospital", "capacity": 25, "specialization": "Pediatric", "load": 0.4},
        ]
        
        # Init signals
        for y in range(height):
            for x in range(width):
                node = f"{x},{y}"
                self.signals[node] = RLTrafficController(node)
        
        self._init_traffic()
        
    def _generate_base_edges(self):
        edges = {}
        for y in range(self.height):
            for x in range(self.width):
                node = f"{x},{y}"
                edges[node] = {}
                neighbors = []
                if x > 0: neighbors.append(f"{x-1},{y}")
                if x < self.width - 1: neighbors.append(f"{x+1},{y}")
                if y > 0: neighbors.append(f"{x},{y-1}")
                if y < self.height - 1: neighbors.append(f"{x},{y+1}")
                for neighbor in neighbors:
                    edges[node][neighbor] = {"weight": 1, "level": "Low", "blocked": False, "vehicles": 0}
        return edges
    
    def _init_traffic(self):
        for _ in range(30):
            self._spawn_vehicle()
    
    def _parse(self, node_str):
        parts = node_str.split(',')
        return (int(parts[0]), int(parts[1]))
    
    def _get_coords(self, node_str):
        return self._parse(node_str)
    
    def _spawn_vehicle(self):
        if len(self.vehicles) >= self.max_vehicles:
            return
        # Pick random start and end
        nodes = list(self.edges.keys())
        start = random.choice(nodes)
        end = random.choice(nodes)
        if start == end:
            return
        # Simple random route (will follow edges)
        route = self._random_walk(start, end)
        if len(route) > 1:
            v = Vehicle(f"v{self.tick}_{random.randint(0,9999)}", route, self)
            self.vehicles.append(v)
    
    def _random_walk(self, start, goal, max_steps=30):
        # BFS-ish random walk
        current = start
        path = [current]
        visited = {current}
        for _ in range(max_steps):
            if current == goal:
                break
            neighbors = [n for n in self.edges[current].keys() 
                        if n not in visited and not self.edges[current][n].get("blocked", False)]
            if not neighbors:
                break
            # Weight toward goal slightly
            gx, gy = self._parse(goal)
            def score(n):
                nx, ny = self._parse(n)
                d = abs(nx - gx) + abs(ny - gy)
                return d + random.uniform(0, 2)
            current = min(neighbors, key=score)
            path.append(current)
            visited.add(current)
        if path[-1] != goal:
            return path  # partial route okay, will respawn
        return path
    
    def get_edge_weight(self, u, v):
        data = self.edges[u][v]
        if data.get("blocked", False):
            return 999
        w = data["weight"]
        # Add congestion penalty
        w = w * (1 + data.get("vehicles", 0) * 0.1)
        return self.weather.apply_weather_to_weight(w)
    
    def _vehicle_ahead_on_edge(self, vehicle, edge):
        u, v = edge
        ahead = None
        for other in self.vehicles:
            if other.id == vehicle.id or other.state == "arrived":
                continue
            o_edge = other.current_edge()
            if o_edge == edge and other.pos_idx == vehicle.pos_idx and other.progress > vehicle.progress:
                if ahead is None or other.progress < ahead.progress:
                    ahead = other
        return ahead
    
    def update(self, dt=1):
        self.tick += 1
        
        # Update weather
        self.weather.update(dt)
        
        # Apply scenario config
        config = self.scenario.get_config()
        self.spawn_rate = config["traffic_density"] * 0.3
        if config["weather"] != self.weather.current and self.tick % 100 == 0:
            self.weather.current = config["weather"]
            self.weather.speed_multiplier = {"Clear": 1.0, "Rain": 0.75, "Fog": 0.6, "Snow": 0.4, "Storm": 0.5}.get(config["weather"], 1.0)
        
        # Spawn vehicles
        if random.random() < self.spawn_rate:
            self._spawn_vehicle()
        
        # Update vehicles
        for v in self.vehicles:
            v.update(dt)
        
        # Remove arrived vehicles
        self.vehicles = [v for v in self.vehicles if v.state != "arrived"]
        
        # Count vehicles per edge
        edge_counts = defaultdict(int)
        for v in self.vehicles:
            edge = v.current_edge()
            if edge:
                edge_counts[edge] += 1
        
        # Update edge weights based on vehicle counts
        for node, neighbors in self.edges.items():
            for neighbor, data in neighbors.items():
                count = edge_counts.get((node, neighbor), 0) + edge_counts.get((neighbor, node), 0)
                data["vehicles"] = count
                if count == 0:
                    data["level"] = "Low"
                    data["weight"] = 1
                elif count <= 3:
                    data["level"] = "Medium"
                    data["weight"] = 3
                else:
                    data["level"] = "High"
                    data["weight"] = min(10, 3 + count * 0.5)
        
        # Update signals
        self._update_signals()
        
        # Log periodically
        if self.tick % 60 == 0:
            for node, neighbors in self.edges.items():
                for neighbor, data in neighbors.items():
                    if int(neighbor.split(',')[0]) > int(node.split(',')[0]) or int(neighbor.split(',')[1]) > int(node.split(',')[1]):
                        log_traffic(node, neighbor, data["level"], data["weight"], data["vehicles"])
    
    def _update_signals(self):
        for node, signal in self.signals.items():
            signal.timer += 1
            
            # Get queue lengths for RL state
            queues = {"N": 0, "S": 0, "E": 0, "W": 0}
            for v in self.vehicles:
                if v.state != "moving":
                    continue
                edge = v.current_edge()
                if edge and edge[1] == node and v.progress > 0.6:
                    # Approaching this intersection
                    ux, uy = self._parse(edge[0])
                    vx, vy = self._parse(edge[1])
                    if vy > uy: queues["S"] += 1
                    elif vy < uy: queues["N"] += 1
                    elif vx > ux: queues["E"] += 1
                    elif vx < ux: queues["W"] += 1
            
            action = signal.choose_action(queues)
            
            # Apply action
            if signal.state == "green":
                if action == 1 and signal.timer >= signal.min_green:
                    signal.state = "yellow"
                    signal.timer = 0
                signal.learn(-sum(queues.values()) * 0.01)  # Penalty for queues
            elif signal.state == "yellow":
                if signal.timer >= signal.yellow_time:
                    signal.state = "green"
                    signal.phase = "EW" if signal.phase == "NS" else "NS"
                    signal.timer = 0
            
            # Override for ambulance preemption
            if node in self.ambulances:
                amb = self.ambulances[node]
                if amb.get("preempt", False):
                    # Make green for ambulance direction
                    next_node = amb.get("next_node")
                    if next_node:
                        ux, uy = self._parse(node)
                        vx, vy = self._parse(next_node)
                        amb_phase = "NS" if ux == vx else "EW"
                        if signal.phase != amb_phase:
                            signal.phase = amb_phase
                        signal.state = "green"
                        signal.timer = 0
    
    def get_graph(self):
        return self.edges
    
    def get_vehicle_data(self):
        return [
            {
                "id": v.id,
                "x": v.get_position()[0],
                "y": v.get_position()[1],
                "speed": v.speed,
                "state": v.state
            }
            for v in self.vehicles
        ]
    
    def get_signal_data(self):
        return {node: s.get_signal_state() for node, s in self.signals.items()}
    
    def get_hospitals(self):
        return self.hospitals
    
    def get_state(self):
        return {
            "width": self.width,
            "height": self.height,
            "edges": self.get_graph(),
            "vehicles": self.get_vehicle_data(),
            "signals": self.get_signal_data(),
            "weather": self.weather.get_state(),
            "scenario": self.scenario.current,
            "hospitals": self.get_hospitals(),
            "tick": self.tick
        }
    
    def add_ambulance(self, amb_id, path, priority="Normal"):
        self.ambulances[amb_id] = {
            "path": path,
            "priority": priority,
            "index": 0,
            "progress": 0.0,
            "preempt": priority == "High",
            "next_node": path[1] if len(path) > 1 else None
        }
    
    def update_ambulance(self, amb_id, index, progress, next_node=None):
        if amb_id in self.ambulances:
            self.ambulances[amb_id]["index"] = index
            self.ambulances[amb_id]["progress"] = progress
            self.ambulances[amb_id]["next_node"] = next_node
    
    def remove_ambulance(self, amb_id):
        if amb_id in self.ambulances:
            del self.ambulances[amb_id]

