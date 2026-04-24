// Automatically support both local Live Server and Red Pitaya hosting.
const API_BASE = (
    window.location.hostname === 'localhost' ||
    window.location.hostname === '127.0.0.1'
)
    ? 'http://rp-f0f587.local:8000/api'
    : '/api';

async function apiFetch(path, options = {}) {
    const res = await fetch(`${API_BASE}${path}`, options);

    let errorText = `HTTP ${res.status}`;

    // Try to extract JSON error body
    let body = null;

    try {
        body = await res.json();
    } catch {
        // ignore JSON parse failure
    }

    if (!res.ok) {

        if (body?.detail) {
            errorText = body.detail;
        } else if (body) {
            errorText = JSON.stringify(body);
        }

        throw new Error(errorText);
    }

    return body;
}

// ==========================
// DATA FETCHING
// ==========================

async function getLogs() {
    const data = await apiFetch('/get_logs');
    lastLogs = data.logs;

    if (!logsPaused) {
        updateLogPanel(lastLogs);
    }
}

async function getSystemInfo() {
    const data = await apiFetch('/get_system_info');

    window._clockFrequencyHz = data.fpga_clock_freq;

    document.getElementById('fpgaFile').textContent = data.fpg_file;
    document.getElementById('clockFreq').textContent =
        (data.fpga_clock_freq / 1e6).toFixed(0) + ' MHz';

    document.getElementById('numOutputs').textContent = data.num_outputs;
    document.getElementById('maxPulses').textContent = data.max_pulses_per_output;

    updateInputLimits(data);

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
    document.getElementById('period').textContent = data.period + ' ticks';
    return data.pulse_data;
}

async function getCycleCount() {
    const data = await apiFetch('/get_cycle_count');

    document.getElementById('cycleCount').textContent =
        data.cycle_count.toLocaleString();

    return data.cycle_count;
}

// ==========================
// DYNAMIC UI UPDATES
// ==========================

function updateInputLimits(systemInfo) {
    document.getElementById('outputIdx').max = systemInfo.num_outputs;
    document.getElementById('pulseIdx').max = systemInfo.max_pulses_per_output - 1;
}

// ==========================
// CYCLE LIMIT HANDLING
// ==========================

async function handleCycleSubmit(event) {
    event.preventDefault();

    await updateCycleLimit();
}


async function updateCycleLimit() {

    const input = document.getElementById('maxCycleCount');
    const button = document.getElementById('cycleLimitEnabled');

    const currentlyEnabled =
        button.textContent.includes('Disable');

    const newEnabledState = !currentlyEnabled;

    const maxCycles = parseInt(input.value);

    try {

        await apiFetch('/set_cycle_limit', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },

            body: JSON.stringify({
                enabled: newEnabledState,
                max_cycles: isNaN(maxCycles)
                    ? 0
                    : maxCycles
            })
        });

        await refreshCycleLimitUI();

    } catch (err) {

        console.error('Failed to update cycle limit:', err);

        alert(
            err.message ||
            'Failed to update cycle limit'
        );
    }
}


async function refreshCycleLimitUI() {
    try {
        const data = await apiFetch('/get_cycle_config');

        const button = document.getElementById('cycleLimitEnabled');
        const input = document.getElementById('maxCycleCount');
        const limitDisplay = document.getElementById('cycleLimit');

        const enabled = data.enabled;

        // --------------------------
        // button state
        // --------------------------

        button.textContent =
            enabled
                ? 'Disable Limit'
                : 'Enable Limit';


        // --------------------------
        // displayed value
        // --------------------------
        if (!enabled) {

            limitDisplay.textContent = 'Disabled';
        } else if (
            data.max_cycles !== null &&
            data.max_cycles !== undefined
        ) {

            input.value = data.max_cycles;

            limitDisplay.textContent =
                data.max_cycles.toLocaleString();

        } else {

            limitDisplay.textContent = '-';
        }

    } catch (err) {

        console.error(
            'Failed to refresh cycle limit UI:',
            err
        );
    }
}


async function toggleCycleLimit() {

    await updateCycleLimit();
}


// ==========================
// CSV FILE HANDLING
// ==========================

async function uploadCSV() {
    const fileInput = document.getElementById('csvFile');

    if (!fileInput.files.length) {
        alert('Select a CSV file first');
        return;
    }

    const file = fileInput.files[0];
    const text = await file.text();

    const lines = text.split('\n');

    const pulseMap = {}; // { output_idx: [[start, stop], ...] }
    let period = null;

    for (let line of lines) {
        line = line.trim();

        // skip empty or header
        if (!line || line.startsWith('out_idx')) continue;

        const parts = line.split(',').map(s => s.trim());

        if (parts.length < 3) continue;

        const out_idx = parseInt(parts[0]);
        const start = parseInt(parts[1]);
        const stop = parseInt(parts[2]);

        if ([out_idx, start, stop].some(isNaN)) {
            console.warn('Invalid row skipped:', line);
            continue;
        }

        // PERIOD
        if (out_idx === 0) {
            period = stop;
            continue;
        }

        if (!pulseMap[out_idx]) {
            pulseMap[out_idx] = [];
        }

        pulseMap[out_idx].push([start, stop]);
    }

    clearOutputs();

    try {
        // 1. Set period FIRST
        if (period !== null) {
            await apiFetch('/set_period', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ period_length_ticks: period })
            });
        }

        // 2. Send each output via set_pulse_train
        for (const [output_idx, pulses] of Object.entries(pulseMap)) {

            // sort pulses (important)
            pulses.sort((a, b) => a[0] - b[0]);

            await apiFetch('/set_pulse_train', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    output_idx: Number(output_idx),
                    pulse_train: pulses
                })
            });
        }

        await refresh();

    } catch (err) {
        console.error('CSV upload failed:', err);
        alert('Failed to apply CSV');
    }
}

async function downloadCSV() {
    try {
        const pulseData = await getPulseData();

        let csv = 'out_idx,start_ticks,stop_ticks\n';

        // Period (output 0)
        if (pulseData[0] && pulseData[0][0]) {
            const period = pulseData[0][0][1];
            csv += `0,0,${period}\n\n`;
        }

        // Outputs
        for (const [output_idx, pulses] of Object.entries(pulseData)) {
            if (output_idx == 0) continue;

            pulses.forEach(([start, stop]) => {
                csv += `${output_idx},${start},${stop}\n`;
            });

            csv += '\n';
        }

        const blob = new Blob([csv], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);

        const a = document.createElement('a');
        a.href = url;
        a.download = 'pulse_config.csv';
        a.click();

        window.URL.revokeObjectURL(url);

    } catch (err) {
        console.error('Download failed:', err);
        alert('Failed to download CSV');
    }
}

// ==========================
// LOG PANEL
// ==========================

let logsPaused = false;
let lastLogs = [];

function updateLogPanel(logs) {
    const panel = document.getElementById('logPanel');

    panel.innerHTML = '';

    logs.forEach(line => {
        const div = document.createElement('div');
        div.classList.add('log-line');

        if (line.includes('ERROR')) {
            div.classList.add('log-error');
        } else if (!line.includes('INFO') && !line.includes('DEBUG')) {
            div.classList.add('log-warn');
        } else if (line.includes('DEBUG')) {
            div.classList.add('log-debug');
        } else {
            div.classList.add('log-info');
        }

        div.textContent = line;
        panel.appendChild(div);
    });

}

function toggleLogs() {
    logsPaused = !logsPaused;

    const btn = document.getElementById('logToggleBtn');
    btn.textContent = logsPaused ? 'Resume' : 'Pause';

    // When resuming, immediately refresh
    if (!logsPaused) {
        updateLogPanel(lastLogs);
    }
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

    document.getElementById('period').textContent = period + ' s';

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

        margin: { t: 30, r: 40, b: 40, l: 40 },
        showlegend: false,

        annotations: annotations   
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
    await refreshCycleLimitUI();
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

    const output_idx = parseInt(
        document.getElementById('outputIdx').value
    );

    const pulse_idx = parseInt(
        document.getElementById('pulseIdx').value
    );

    // ---------------------------------
    // INPUT VALUES (seconds)
    // ---------------------------------

    const startSeconds = parseFloat(
        document.getElementById('startTick').value
    );

    const stopSeconds = parseFloat(
        document.getElementById('stopTick').value
    );

    // ---------------------------------
    // SYSTEM INFO
    // ---------------------------------

    const maxOutputs = parseInt(
        document.getElementById('numOutputs').textContent
    );

    const maxPulses = parseInt(
        document.getElementById('maxPulses').textContent
    );

    const periodTicks = window._plotPeriodTicks;

    const clockHz = window._clockFrequencyHz;

    if (!clockHz) {
        return alert('Clock frequency unavailable');
    }

    // ---------------------------------
    // CONVERT SECONDS -> TICKS
    // ---------------------------------

    // round to nearest FPGA clock cycle

    const start = Math.round(
        startSeconds * clockHz
    );

    const stop = Math.round(
        stopSeconds * clockHz
    );

    // actual quantized values

    const quantizedStartSeconds =
        start / clockHz;

    const quantizedStopSeconds =
        stop / clockHz;

    // ---------------------------------
    // VALIDATION
    // ---------------------------------

    if (
        [
            output_idx,
            pulse_idx,
            startSeconds,
            stopSeconds
        ].some(isNaN)
    ) {
        return alert('Fill all fields correctly');
    }

    if (
        output_idx < 1 ||
        output_idx > maxOutputs
    ) {
        return alert(
            `Output must be between 1 and ${maxOutputs}`
        );
    }

    if (
        pulse_idx < 0 ||
        pulse_idx >= maxPulses
    ) {
        return alert(
            `Pulse index must be 0–${maxPulses - 1}`
        );
    }

    if (
        start < 0 ||
        stop <= start
    ) {
        return alert(
            'Stop must be greater than start'
        );
    }

    if (stop > periodTicks) {
        return alert(
            `Stop exceeds period (${periodTicks} ticks)`
        );
    }

    // ---------------------------------
    // OPTIONAL USER FEEDBACK
    // ---------------------------------

    console.log(
        `Quantized pulse:
        start = ${quantizedStartSeconds}s (${start} ticks)
        stop  = ${quantizedStopSeconds}s (${stop} ticks)`
    );

    // ---------------------------------
    // SEND
    // ---------------------------------

    await apiFetch('/set_pulse', {
        method: 'POST',

        headers: {
            'Content-Type': 'application/json'
        },

        body: JSON.stringify({
            output_idx,
            pulse_idx,
            start,
            stop
        })
    });

    await refreshPlot();
}


// ==========================
// INIT
// ==========================

refresh();

setInterval(safeGetLogs, 1000);
setInterval(getStatus, 1000);
setInterval(safeGetCycleCount, 500);