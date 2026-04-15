// Automatically support both local Live Server and Red Pitaya hosting.
// If running on localhost/127.0.0.1, target RP manually.
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

    // reset classes
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

async function setMaxCycles() {
    const maxCycles = parseInt(document.getElementById('maxCycleCount').value);
    if (isNaN(maxCycles)) return alert('Enter a valid number for max cycles');

    await apiFetch('/set_max_cycles', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ max_cycles: maxCycles })
    });
}


async function refreshPlot() {
    try {
        const systemInfo = await getSystemInfo();
        const pulseData = await getPulseData();
        const cycleCount = await getCycleCount();
        plotPulseTrain(pulseData, systemInfo.fpga_clock_freq);
    } catch (err) {
        console.error('Plot refresh failed:', err);
    }
}

function plotPulseTrain(pulseData, clockSpeedHz) {
    const traces = [];
       

    period_length_ticks = pulseData[0][0][1] || 1; // Get period length from pulse data

    for (const [outputIdx, pulses] of Object.entries(pulseData)) {
        if (outputIdx == 0) continue; // Skip period length entry
        const numericOutput = Number(outputIdx);
        const x = [];
        const y = [];

        pulses.forEach(([start, stop]) => {
            x.push(start / clockSpeedHz, stop / clockSpeedHz, null);
            y.push(numericOutput, numericOutput, null);
        });

        traces.push({
            x,
            y,
            mode: 'lines',
            line: { width: 100 },
            name: `Output ${outputIdx}`
        });
    }

    const layout = {
        autosize: true,
        paper_bgcolor: '#d4d4d4',
        plot_bgcolor: '#f0f0f0',
        xaxis: {
            title: 'Time (s)',
            range: [0, period_length_ticks / clockSpeedHz]
        },
        yaxis: {
            title: 'Output',
            fixedrange: true,
            range: [0.5, 3 + 0.5] // TODO: Dynamically set y-axis range based on number of outputs
        },
        margin: { t: 20, r: 20, b: 20, l: 50 },
        showlegend: false,
        
    };

    Plotly.react('pulsePlot', traces, layout);
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
    await refresh(); // Refresh all data and plot after reset
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


refresh(); // Initial load
setInterval(getCycleCount, 100); // Update cycle count more frequently for responsiveness

