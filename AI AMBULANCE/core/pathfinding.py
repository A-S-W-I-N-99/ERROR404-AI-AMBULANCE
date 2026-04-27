import heapq
import numpy as np
from datetime import datetime

def heuristic(a, b):
    (x1, y1) = a
    (x2, y2) = b
    return abs(x1 - x2) + abs(y1 - y2)

def parse_node(node_str):
    parts = node_str.split(',')
    return (int(parts[0]), int(parts[1]))

def a_star_search(graph, start, goal, priority="Normal", weather_mult=1.0, predictions=None):
    """
    Enhanced A* with:
    - Priority-based emergency override
    - Weather multipliers
    - Predictive traffic lookahead
    """
    start_pos = parse_node(start)
    goal_pos = parse_node(goal)
    
    frontier = []
    heapq.heappush(frontier, (0, start))
    
    came_from = {}
    cost_so_far = {}
    came_from[start] = None
    cost_so_far[start] = 0
    
    while frontier:
        current_priority, current = heapq.heappop(frontier)
        
        if current == goal:
            break
        
        if current not in graph:
            continue
            
        for next_node, edge_data in graph[current].items():
            if edge_data.get("blocked", False):
                continue
                
            weight = edge_data.get("weight", 1)
            
            # Priority override
            if priority == "High":
                weight *= 0.4
            elif priority == "Medium":
                weight *= 0.7
            
            # Weather
            weight = weight / weather_mult
            
            # Prediction bonus
            if predictions and (current, next_node) in predictions:
                pred = predictions[(current, next_node)]
                weight = 0.7 * weight + 0.3 * pred
            
            new_cost = cost_so_far[current] + weight
            
            if next_node not in cost_so_far or new_cost < cost_so_far[next_node]:
                cost_so_far[next_node] = new_cost
                priority_val = new_cost + heuristic(parse_node(next_node), goal_pos)
                heapq.heappush(frontier, (priority_val, next_node))
                came_from[next_node] = current
    
    # Reconstruct path
    if goal not in came_from:
        return [], 0
        
    path = []
    current = goal
    while current != start:
        path.append(current)
        current = came_from[current]
    path.append(start)
    path.reverse()
    
    return path, cost_so_far.get(goal, 0)

def yen_k_shortest_paths(graph, start, goal, k=3, priority="Normal", weather_mult=1.0):
    """Find k shortest paths using Yen's algorithm"""
    from copy import deepcopy
    
    paths = []
    first_path, first_cost = a_star_search(graph, start, goal, priority, weather_mult)
    if not first_path:
        return []
    paths.append((first_path, first_cost))
    
    candidates = []
    
    for i in range(1, k):
        for j in range(len(paths[-1][0]) - 1):
            spur_node = paths[-1][0][j]
            root_path = paths[-1][0][:j+1]
            
            # Temporarily remove edges used by other paths with same root
            temp_graph = deepcopy(graph)
            for p, _ in paths:
                if len(p) > j and p[:j+1] == root_path:
                    u, v = p[j], p[j+1]
                    if u in temp_graph and v in temp_graph[u]:
                        temp_graph[u][v]["blocked"] = True
            
            # Remove root path nodes (except spur)
            for node in root_path[:-1]:
                if node in temp_graph:
                    for neighbor in list(temp_graph[node].keys()):
                        temp_graph[node][neighbor]["blocked"] = True
            
            spur_path, spur_cost = a_star_search(temp_graph, spur_node, goal, priority, weather_mult)
            if spur_path:
                total_path = root_path[:-1] + spur_path
                total_cost = first_cost  # Approximate
                if (total_path, total_cost) not in candidates:
                    candidates.append((total_path, total_cost))
        
        if not candidates:
            break
        
        candidates.sort(key=lambda x: x[1])
        paths.append(candidates.pop(0))
    
    return paths

def predict_traffic(graph, history, horizon=5):
    """
    Simple exponential smoothing prediction.
    Returns predicted weights for edges.
    """
    predictions = {}
    alpha = 0.3
    
    for node, neighbors in graph.items():
        for neighbor, data in neighbors.items():
            current = data.get("weight", 1)
            key = (node, neighbor)
            
            if key in history:
                past = history[key]
                pred = alpha * current + (1 - alpha) * past
            else:
                pred = current
            
            predictions[key] = pred
    
    return predictions

