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

async function getLogs() {
    const data = await apiFetch('/get_logs');
    updateLogPanel(data.logs);
}

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
// LOG PANEL
// ==========================

function updateLogPanel(logs) {
    const panel = document.getElementById('logPanel');

    panel.innerHTML = '';

    logs.forEach(line => {
        const div = document.createElement('div');
        div.classList.add('log-line');

        // crude level detection
        if (line.includes('ERROR')) {
            div.classList.add('log-error');
        } else if (line.includes('WARN')) {
            div.classList.add('log-warn');
        } else {
            div.classList.add('log-info');
        }

        div.textContent = line;
        panel.appendChild(div);
    });

    // auto-scroll to bottom
    panel.scrollTop = panel.scrollHeight;
}



// ==========================
// SAFE POLLING 
// ==========================

let logBusy = false;

async function safeGetLogs() {
    if (logBusy) return;
    logBusy = true;

    try {
        await getLogs();
    } finally {
        logBusy = false;
    }
}

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

    const AMPLITUDE = 0.3;

    const traces = [];
    const annotations = [];

    const period_ticks = pulseData[0][0][1];
    const period = period_ticks / clockSpeedHz;

    for (const [outputIdx, pulses] of Object.entries(pulseData)) {
        if (outputIdx == 0) continue;

        const numericOutput = Number(outputIdx);

        const x = [0];
        const y = [numericOutput - AMPLITUDE];

        // sort pulses
        pulses.sort((a, b) => a[0] - b[0]);

        let prevTime = 0;

        pulses.forEach(([start, stop]) => {
            const tStart = start / clockSpeedHz;
            const tStop = stop / clockSpeedHz;

            // -------- LOW SEGMENT --------
            if (tStart > prevTime) {
                const mid = (prevTime + tStart) / 2;
                const duration = tStart - prevTime;

                annotations.push({
                    x: mid,
                    y: numericOutput - AMPLITUDE * 1.2,
                    text: `${(duration * 1e6).toFixed(3)} µs`,
                    showarrow: false,
                    font: { size: 12, color: 'black' }
                });
            }

            // waveform: rising edge
            x.push(tStart, tStart);
            y.push(numericOutput - AMPLITUDE, numericOutput + AMPLITUDE);

            // waveform: high
            x.push(tStop);
            y.push(numericOutput + AMPLITUDE);

            // -------- HIGH SEGMENT --------
            const midHigh = (tStart + tStop) / 2;
            const highDuration = tStop - tStart;

            annotations.push({
                x: midHigh,
                y: numericOutput + AMPLITUDE * 1.2,
                text: `${(highDuration * 1e6).toFixed(3)} µs`,
                showarrow: false,
                font: { size: 12, color: 'black' }
            });

            // falling edge
            x.push(tStop);
            y.push(numericOutput - AMPLITUDE);

            prevTime = tStop;
        });

        // -------- FINAL LOW SEGMENT --------
        if (prevTime < period) {
            const mid = (prevTime + period) / 2;
            const duration = period - prevTime;

            annotations.push({
                x: mid,
                y: numericOutput - AMPLITUDE * 1.2,
                text: `${(duration * 1e6).toFixed(3)} µs`,
                showarrow: false,
                font: { size: 12, color: 'black' }
            });
        }

        // extend waveform to full period
        x.push(period);
        y.push(numericOutput - AMPLITUDE);

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
        showlegend: true,

        annotations: annotations   // 👈 KEY ADDITION
    };

    Plotly.react('pulsePlot', traces, layout);

    window._plotPeriod = period;
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
    await getCycleCount();
    await getLogs();
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
// INIT
// ==========================

refresh();

setInterval(safeGetLogs, 500);
setInterval(safeGetCycleCount, 500);