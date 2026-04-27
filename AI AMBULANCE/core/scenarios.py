import random

SCENARIOS = {
    "Normal": {
        "description": "Standard city conditions",
        "traffic_density": 0.3,
        "weather": "Clear",
        "event_chance": 0.001,
        "hospital_load": 0.5,
    },
    "Rush Hour": {
        "description": "Morning/evening peak traffic",
        "traffic_density": 0.8,
        "weather": "Clear",
        "event_chance": 0.003,
        "hospital_load": 0.7,
    },
    "Storm": {
        "description": "Heavy rain and reduced visibility",
        "traffic_density": 0.4,
        "weather": "Storm",
        "event_chance": 0.01,
        "hospital_load": 0.6,
    },
    "Multi-Casualty": {
        "description": "Major incident requiring multiple units",
        "traffic_density": 0.5,
        "weather": "Rain",
        "event_chance": 0.02,
        "hospital_load": 0.9,
    },
    "Stadium Event": {
        "description": "Large crowd event with congestion",
        "traffic_density": 0.9,
        "weather": "Clear",
        "event_chance": 0.005,
        "hospital_load": 0.6,
    },
    "Night Shift": {
        "description": "Low traffic but reduced visibility",
        "traffic_density": 0.15,
        "weather": "Fog",
        "event_chance": 0.002,
        "hospital_load": 0.3,
    },
}

class ScenarioEngine:
    def __init__(self):
        self.current = "Normal"
        self.config = SCENARIOS["Normal"].copy()
        
    def load(self, name):
        if name in SCENARIOS:
            self.current = name
            self.config = SCENARIOS[name].copy()
            return True
        return False
    
    def get_config(self):
        return self.config
    
    def get_all(self):
        return {k: {"description": v["description"]} for k, v in SCENARIOS.items()}

