import random
import math
from datetime import datetime

WEATHER_TYPES = {
    "Clear": {"speed_mult": 1.0, "accident_chance": 0.001, "visibility": 1.0},
    "Rain": {"speed_mult": 0.75, "accident_chance": 0.005, "visibility": 0.7},
    "Fog": {"speed_mult": 0.6, "accident_chance": 0.003, "visibility": 0.4},
    "Snow": {"speed_mult": 0.4, "accident_chance": 0.01, "visibility": 0.3},
    "Storm": {"speed_mult": 0.5, "accident_chance": 0.015, "visibility": 0.5},
}

EVENT_TYPES = {
    "Accident": {"blocks_edges": 1, "duration": 300, "severity": 0.8},
    "Construction": {"blocks_edges": 1, "duration": 600, "severity": 0.5},
    "Parade": {"blocks_edges": 2, "duration": 200, "severity": 0.9},
    "RoadClosure": {"blocks_edges": 1, "duration": 400, "severity": 1.0},
}

class WeatherSystem:
    def __init__(self):
        self.current = "Clear"
        self.speed_multiplier = 1.0
        self.events = []  # List of active events
        self.timer = 0
        
    def update(self, dt=1):
        self.timer += dt
        # Weather changes slowly (every ~5 min sim time)
        if self.timer % 300 == 0 or self.timer == 1:
            if random.random() < 0.3:  # 30% chance to change
                weights = {"Clear": 0.5, "Rain": 0.2, "Fog": 0.1, "Snow": 0.1, "Storm": 0.1}
                self.current = random.choices(list(weights.keys()), weights=list(weights.values()))[0]
                self.speed_multiplier = WEATHER_TYPES[self.current]["speed_mult"]
        
        # Random events
        if random.random() < WEATHER_TYPES[self.current]["accident_chance"]:
            self._spawn_event()
        
        # Update active events
        new_events = []
        for event in self.events:
            event["duration"] -= dt
            if event["duration"] > 0:
                new_events.append(event)
        self.events = new_events
        
        return self.current, self.speed_multiplier
    
    def _spawn_event(self):
        event_type = random.choice(list(EVENT_TYPES.keys()))
        event = {
            "type": event_type,
            "duration": EVENT_TYPES[event_type]["duration"],
            "severity": EVENT_TYPES[event_type]["severity"],
            "edges": [],  # Will be populated by traffic sim
        }
        self.events.append(event)
    
    def get_state(self):
        return {
            "weather": self.current,
            "speed_multiplier": self.speed_multiplier,
            "events": [{"type": e["type"], "duration": e["duration"], "severity": e["severity"]} for e in self.events]
        }
    
    def apply_weather_to_weight(self, base_weight):
        return base_weight / self.speed_multiplier

