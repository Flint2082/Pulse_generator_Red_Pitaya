// Automatically support both local Live Server and Red Pitaya hosting.
const API_BASE = (
    window.location.hostname === 'localhost' ||
    window.location.hostname === '127.0.0.1'
)
    ? 'http://rp-f0f587.local:8000/api'
    : '/api';

async function apiFetch(path, options = {}) {
    const res = await fetch(`${API_BASE}${path}`, options);

    if (!res.ok) {
        const errText = await res.text();
        throw new Error(errText || `HTTP ${res.status}`);
    }

    return res.json();
}

// ==========================
// DATA FETCHING
// ==========================

async function getSystemInfo() {
    const data = await apiFetch('/get_system_info');

    document.getElementById('fpgaFile').textContent = data.fpg_file;
    document.getElementById('clockFreq').textContent =
        (data.fpga_clock_freq / 1e6).toFixed(0) + ' MHz';

    document.getElementById('numOutputs').textContent = data.num_outputs;
    document.getElementById('maxPulses').textContent = data.max_pulses_per_output;

    return data;
}

async function getStatus() {
    const data = await apiFetch('/get_status');

    const el = document.getElementById('statusIndicator');

    el.textContent = data.status.toUpperCase();

    el.classList.remove('status-running', 'status-stopped', 'status-idle');

    if (data.status === 'running') {
        el.classList.add('status-running');
    } else if (data.status === 'stopped') {
        el.classList.add('status-stopped');
    } else {
        el.classList.add('status-idle');
    }

    return data;
}

async function getPulseData() {
    const data = await apiFetch('/get_pulse_config');
    return data.pulse_data;
}

async function getCycleCount() {
    const data = await apiFetch('/get_cycle_count');

    document.getElementById('cycleCount').textContent =
        data.cycle_count.toLocaleString();

    return data.cycle_count;
}

// ==========================
// SAFE POLLING 
// ==========================

let cycleBusy = false;

async function safeGetCycleCount() {
    if (cycleBusy) return;
    cycleBusy = true;

    try {
        await getCycleCount();
    } finally {
        cycleBusy = false;
    }
}

// ==========================
// PLOT REFRESH
// ==========================

let plotRefreshing = false;

async function refreshPlot() {
    if (plotRefreshing) return;

    plotRefreshing = true;

    const plotDiv = document.getElementById('pulsePlot');
    plotDiv.style.opacity = 0.6;

    try {
        const systemInfo = await getSystemInfo();
        const pulseData = await getPulseData();
        await getCycleCount();

        plotPulseTrain(pulseData, systemInfo.fpga_clock_freq);

    } catch (err) {
        console.error('Plot refresh failed:', err);
    } finally {
        plotDiv.style.opacity = 1;
        plotRefreshing = false;
    }
}

// ==========================
// PLOTTING
// ==========================

function plotPulseTrain(pulseData, clockSpeedHz) {
    if (!pulseData || !pulseData[0] || !pulseData[0][0]) {
        console.warn('Invalid pulse data');
        return;
    }

    const traces = [];

    const period_ticks = pulseData[0][0][1];
    const period = period_ticks / clockSpeedHz;

    for (const [outputIdx, pulses] of Object.entries(pulseData)) {
        if (outputIdx == 0) continue;

        const numericOutput = Number(outputIdx);

        const x = [0];
        const y = [numericOutput - 0.4]; // start LOW

        // sort pulses just in case
        pulses.sort((a, b) => a[0] - b[0]);

        pulses.forEach(([start, stop]) => {
            const tStart = start / clockSpeedHz;
            const tStop = stop / clockSpeedHz;

            // go HIGH
            x.push(tStart, tStart);
            y.push(numericOutput - 0.4, numericOutput + 0.4);

            // stay HIGH
            x.push(tStop);
            y.push(numericOutput + 0.4);

            // go LOW
            x.push(tStop);
            y.push(numericOutput - 0.4);
        });

        // extend to full period
        x.push(period);
        y.push(numericOutput - 0.4);

        traces.push({
            x,
            y,
            mode: 'lines',
            line: { width: 2, shape: 'hv' },
            name: `Output ${outputIdx}`,
            hovertemplate:
                'Output: ' + numericOutput +
                '<br>Time: %{x}s' +
                '<extra></extra>'
        });

        
    }

    const numOutputs = Object.keys(pulseData).length - 1;

    const layout = {
        autosize: true,
        paper_bgcolor: '#d4d4d4',
        plot_bgcolor: '#f0f0f0',

        xaxis: {
            title: 'Time (s)',
            range: [0, period]
        },

        yaxis: {
            title: 'Output',
            fixedrange: true,
            range: [0.5, numOutputs + 0.5],
            dtick: 1
        },

        margin: { t: 20, r: 20, b: 40, l: 60 },
        showlegend: true
    };

    Plotly.react('pulsePlot', traces, layout);


    window._plotPeriod = period;


}

let cursorPoints = [];

window.addEventListener('DOMContentLoaded', () => {


    const plotDiv = document.getElementById('pulsePlot');

    plotDiv.on('plotly_click', function(data) {

        const el = document.getElementById('deltaT');
            if (el) {
                el.textContent = `Δt: ? µs`;
            }
        if (!data.points || data.points.length === 0) return;

        const x = data.points[0].x;

        cursorPoints.push(x);

        // keep only last 2 points
        if (cursorPoints.length > 2) {
            cursorPoints.shift();
        }

        drawCursorLines(cursorPoints);

        // Δt calculation
        if (cursorPoints.length === 2) {
            const dt = Math.abs(cursorPoints[1] - cursorPoints[0]);

            console.log(`Δt = ${dt} s (${dt * 1e6} µs)`);

            const el = document.getElementById('deltaT');
            if (el) {
                el.textContent = `Δt: ${(dt * 1e6).toFixed(2)} µs`;
            }
        }
    });
});

function drawCursorLines(points) {
    const shapes = points.map(x => ({
        type: 'line',
        x0: x,
        x1: x,
        y0: 0,
        y1: 1,
        xref: 'x',
        yref: 'paper',
        line: {
            color: 'red',
            width: 2,
            dash: 'dot'
        }
    }));

    Plotly.relayout('pulsePlot', {
        shapes: shapes
    });
}


// ==========================
// CONTROL ACTIONS
// ==========================

async function loadBitstream() {
    await apiFetch('/load_bitstream', { method: 'POST' });
    await refresh();
}

async function startPulser() {
    await apiFetch('/start', { method: 'POST' });
    await refresh();
}

async function stopPulser() {
    await apiFetch('/stop', { method: 'POST' });
    await refresh();
}

async function resetPulser() {
    await apiFetch('/reset', { method: 'POST' });
    await refresh();
}

async function clearOutputs() {
    await apiFetch('/clear_outputs', { method: 'POST' });
    await refresh();
}

async function refresh() {
    await getSystemInfo();
    await getStatus();
    await refreshPlot();
}

async function setPeriod() {
    const ticks = parseInt(document.getElementById('periodTicks').value);
    if (isNaN(ticks)) return alert('Enter a valid number for ticks');

    await apiFetch('/set_period', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ period_length_ticks: ticks })
    });

    await refresh();
}

async function setPulse() {
    const output_idx = parseInt(document.getElementById('outputIdx').value);
    const pulse_idx = parseInt(document.getElementById('pulseIdx').value);
    const start = parseInt(document.getElementById('startTick').value);
    const stop = parseInt(document.getElementById('stopTick').value);

    if ([output_idx, pulse_idx, start, stop].some(isNaN)) {
        return alert('Fill all fields correctly');
    }

    await apiFetch('/set_pulse', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ output_idx, pulse_idx, start, stop })
    });

    await refreshPlot();
}

// ==========================
// DOUBLE-CLICK HANDLER 
// ==========================

window.addEventListener('DOMContentLoaded', () => {
    const plotDiv = document.getElementById('pulsePlot');

    plotDiv.addEventListener('dblclick', () => {
        console.log('Double click → update plot');

        refresh();
    });
});

// ==========================
// INIT
// ==========================

refresh();

// Reduced + safe polling
setInterval(safeGetCycleCount, 100);