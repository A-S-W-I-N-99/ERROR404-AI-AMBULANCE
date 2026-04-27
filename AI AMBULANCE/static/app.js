let state = null;
let currentPath = [];
let altPath = [];

// DOM Elements
const dispatchBtn = document.getElementById('dispatch-btn');
const etaDisplay = document.getElementById('eta-display');
const statusIndicator = document.getElementById('mission-status');
const alertBox = document.getElementById('alert-box');
const hospitalSelect = document.getElementById('hospital-select');
const weatherDisplay = document.getElementById('weather-display');
const vehicleCountDisplay = document.getElementById('vehicle-count');
const fleetList = document.getElementById('fleet-list');
const routeLog = document.getElementById('route-log');

// Charts
let responseChart, trafficChart;

// Socket.IO
const socket = io();

socket.on('connect', () => {
    console.log("Connected to simulation server");
    document.body.insertAdjacentHTML('beforeend', '<div class="connection-status connection-online" title="Connected"></div>');
});

socket.on('disconnect', () => {
    console.log("Disconnected from server");
    const el = document.querySelector('.connection-status');
    if(el) { el.classList.remove('connection-online'); el.classList.add('connection-offline'); }
});

socket.on('init_state', (initState) => {
    state = initState;
    populateHospitals(state.hospitals);
    initCharts();
    updateUI();
});

socket.on('sim_update', (simState) => {
    state = simState;
    updateUI();
});

socket.on('ambulance_dispatched', (data) => {
    addFleetItem(data.id, data.priority);
});

socket.on('ambulance_arrived', (data) => {
    removeFleetItem(data.id);
    if (etaDisplay.innerText !== '--') {
        etaDisplay.innerText = "Arrived";
        statusIndicator.innerText = "Mission Complete";
        statusIndicator.className = "status-indicator standby";
    }
});

function init() {
    dispatchBtn.addEventListener('click', onDispatch);
    
    // Tabs
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            e.target.classList.add('active');
            document.getElementById(`${e.target.dataset.tab}-tab`).classList.add('active');
        });
    });
    
    // Scenarios
    document.getElementById('scenario-select').addEventListener('change', async (e) => {
        await fetch('/api/scenario', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: e.target.value })
        });
    });
}

function populateHospitals(hospitals) {
    if(!hospitals) return;
    hospitalSelect.innerHTML = '<option value="">-- Direct Coordinates --</option><option value="nearest">Nearest Hospital</option>';
    hospitals.forEach(h => {
        const opt = document.createElement('option');
        opt.value = h.id;
        opt.innerText = `${h.name} (${h.specialization})`;
        hospitalSelect.appendChild(opt);
    });
    document.getElementById('hospital-count').innerText = hospitals.length;
}

async function onDispatch() {
    const start = `${document.getElementById('start-x').value},${document.getElementById('start-y').value}`;
    const end = `${document.getElementById('end-x').value},${document.getElementById('end-y').value}`;
    const priority = document.getElementById('priority').value;
    const hospital = hospitalSelect.value;
    
    dispatchBtn.disabled = true;
    statusIndicator.innerText = "Calculating...";
    
    try {
        const res = await fetch('/api/route', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ start, end, priority, hospital })
        });
        
        const data = await res.json();
        currentPath = data.main_route.path;
        if(data.alternate_route) altPath = data.alternate_route.path;
        
        etaDisplay.innerText = data.main_route.cost.toFixed(1) + " mins";
        statusIndicator.innerText = "En Route";
        statusIndicator.className = "status-indicator active";
        
        // Add to route log
        addRouteLog(data.main_route.path, data.main_route.cost.toFixed(1));
        
        // Notify socket
        socket.emit('dispatch_ambulance', {
            path: currentPath,
            priority: priority
        });
        
    } catch(e) {
        console.error(e);
        statusIndicator.innerText = "Error";
    } finally {
        dispatchBtn.disabled = false;
    }
}

function updateUI() {
    if(!state) return;
    if(state.weather) {
        weatherDisplay.innerText = state.weather.weather;
        document.getElementById('weather-status').innerText = state.weather.weather;
        if(state.weather.weather === "Storm" || state.weather.weather === "Snow") {
            weatherDisplay.style.color = "var(--accent-red)";
        } else {
            weatherDisplay.style.color = "var(--text-primary)";
        }
    }
    if(state.vehicles) {
        vehicleCountDisplay.innerText = state.vehicles.length;
    }
    if(state.signals) {
        document.getElementById('signal-count').innerText = Object.keys(state.signals).length;
        let rlCount = 0;
        for (const key in state.signals) {
            if (state.signals[key].rl_enabled) rlCount++;
        }
        document.getElementById('rl-count').innerText = rlCount;
    }
}

function addRouteLog(path, cost) {
    const now = new Date();
    const time = `${now.getHours().toString().padStart(2,'0')}:${now.getMinutes().toString().padStart(2,'0')}`;
    const start = path[0];
    const end = path[path.length - 1];
    
    const empty = routeLog.querySelector('.log-item');
    if(empty && empty.querySelector('.log-text').innerText === 'No routes calculated yet') {
        empty.remove();
    }
    
    const div = document.createElement('div');
    div.className = 'log-item';
    div.innerHTML = `<span class="log-time">${time}</span><span class="log-text">${start} &rarr; ${end} (${cost}m)</span>`;
    routeLog.insertBefore(div, routeLog.firstChild);
    
    // Keep only last 10
    while(routeLog.children.length > 10) {
        routeLog.removeChild(routeLog.lastChild);
    }
}

function addFleetItem(id, priority) {
    const el = document.getElementById('fleet-list');
    const empty = el.querySelector('.empty-state');
    if(empty) empty.remove();
    
    const div = document.createElement('div');
    div.className = 'fleet-item';
    div.id = `fleet-${id}`;
    div.innerHTML = `
        <span>🚑 Unit ${id.split('_')[1] || id}</span>
        <span class="priority-badge priority-${priority}">${priority}</span>
    `;
    el.appendChild(div);
}

function removeFleetItem(id) {
    const item = document.getElementById(`fleet-${id}`);
    if(item) item.remove();
    const el = document.getElementById('fleet-list');
    if(el.children.length === 0) {
        el.innerHTML = '<div class="empty-state">No active ambulances</div>';
    }
}

function initCharts() {
    const ctxResp = document.getElementById('responseChart');
    const ctxTraf = document.getElementById('trafficChart');
    if(!ctxResp || !ctxTraf) return;
    
    Chart.defaults.color = '#94a3b8';
    Chart.defaults.borderColor = 'rgba(255,255,255,0.05)';
    
    responseChart = new Chart(ctxResp, {
        type: 'line',
        data: {
            labels: ['10m', '8m', '6m', '4m', '2m', 'Now'],
            datasets: [{
                label: 'Avg Response Time (min)',
                data: [12, 11.5, 13, 10, 9, 8.5],
                borderColor: '#38bdf8',
                tension: 0.4
            }]
        },
        options: { maintainAspectRatio: false, plugins: { legend: { display: false }, title: { display: true, text: 'Response Time Trend' } } }
    });
    
    trafficChart = new Chart(ctxTraf, {
        type: 'bar',
        data: {
            labels: ['Low', 'Med', 'High'],
            datasets: [{
                data: [60, 30, 10],
                backgroundColor: ['#22c55e', '#facc15', '#ef4444']
            }]
        },
        options: { maintainAspectRatio: false, plugins: { legend: { display: false }, title: { display: true, text: 'Congestion Levels' } } }
    });
    
    setInterval(async () => {
        try {
            const res = await fetch('/api/analytics');
            const data = await res.json();
            document.getElementById('stat-avg-response').innerText = data.avg_response_time ? data.avg_response_time.toFixed(1) : '--';
            document.getElementById('stat-total-routes').innerText = data.total_routes || '--';
            
            if(state && state.edges) {
                let counts = [0,0,0];
                for (let u in state.edges) {
                    for (let v in state.edges[u]) {
                        if(state.edges[u][v].level === 'Low') counts[0]++;
                        else if(state.edges[u][v].level === 'Medium') counts[1]++;
                        else counts[2]++;
                    }
                }
                trafficChart.data.datasets[0].data = counts;
                trafficChart.update();
            }
        } catch(e) {}
    }, 5000);
}

// Start
init();

