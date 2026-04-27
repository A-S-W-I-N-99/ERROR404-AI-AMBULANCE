# AI-Based Smart Ambulance Routing and Traffic Control System

This is a complete software simulation of an AI-driven smart city infrastructure designed to route emergency vehicles efficiently and control traffic signals dynamically.

## 🚀 Key Features
1. **AI Route Optimization**: Utilizes the A* search algorithm considering both distance (heuristic) and dynamic node/edge "traffic" weights.
2. **Smart Traffic Signal Control**: As the ambulance traverses the calculated path, traffic signals at upcoming intersections turn **GREEN**, explicitly clearing the path while setting perpendicular traffic to **RED**.
3. **Dynamic Traffic Simulation**: Roads are initialized with randomized traffic levels (Low, Medium, High). Traffic can be simulated to "spontaneous shift" via the dashboard, modifying optimal routes.
4. **Emergency Priority Levels**: Selecting "High Priority" changes the logic (faster physical traversal, alert notifications, aggressively overriding standard traffic costs).
5. **Modern Dashboard UI**: A fully custom graphical representational interface using Canvas/SVG maps for seamless visualizations, without needing paid 3rd-party mapping APIs.

## 💻 Tech Stack
- **Frontend**: HTML5, CSS3, Vanilla JavaScript (DOM manipulation and SVG graphics)
- **Backend**: Python, Flask (RESTful APIs linking frontend layout to Python AI logic)

---

## 🛠️ How to Run the Project

### Prerequisites
You need Python installed on your machine (Python 3.8+ recommended).

### Step 1: Install Dependencies
Open your terminal/command prompt and run the following command to install Flask:

```bash
pip install flask
```

### Step 2: Run the Flask Server
Navigate to the root directory of this project in your terminal and execute:

```bash
python app.py
```

You should see output indicating that the server is running on `http://127.0.0.1:5000`.

### Step 3: Open the Dashboard
Open your web browser (Chrome, Edge, Firefox, etc.) and go to:
[http://localhost:5000](http://localhost:5000)

---

## 🖥️ Demo Explanation (For Presentation)

When presenting this to your evaluator, follow these steps to clearly demonstrate the underlying AI concepts:

1. **Explain the Setup**: 
   - Point out the city grid on the UI. Explain that every dot is an "intersection" (node) and every connecting line is a "road" (edge).
   - Point out the colors of the lines (Green = Low Traffic, Yellow = Medium Traffic, Red = Heavy Traffic).
2. **Explain the AI Logic**: 
   - When you input a Start and Destination, explain that the system uses the **A* Search Algorithm**. It doesn't just pick the *shortest* physical path, it calculates the *fastest* path based on combined distance weight and real-time traffic delay weight.
3. **Execute "Normal" Dispatch**: 
   - Pick a route (e.g., Start: `0,0`, End: `9,9`) with "Normal" priority and click Dispatch.
   - Look at the blue path drawn. Note how the path avoids red roads if a faster green route is available. Explain the alternate route (purple dotted line).
4. **Demonstrate Traffic Light Control**: 
   - As the yellow "ambulance" dot moves, point out how the node directly ahead turns green, simulating priority signal clearing.
5. **Demonstrate Dynamic Traffic updates**: 
   - Before dispatching again, click "Simulate Traffic Change". Observe the colors on the roads scramble. Explain that real-world conditions change, and a static map would fail; hence the AI recalibrates live traffic.
6. **Execute "High" Emergency Priority**: 
   - Change Priority to "High Emergency (Code 3)".
   - Click dispatch. Note the speed difference and the flashing "Approaching Intersection!" warning broadcast.
