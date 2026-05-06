import csv
import os
from unittest import case
import requests
import logging
import http.client




class PulseGenClient:
    NUM_OUTPUTS = 3
    MAX_PULSES_PER_OUTPUT = 8
    
    
    def __init__(self, base_url: str, debug: bool = False):
        self.base_url = base_url.rstrip("/")
        self.debug = debug
        
        self.session = requests.Session()
        
        self.load_bitstream()
        
        self.system_info = self.get_system_info()  # Cache system info for later use
        
        # Enable detailed logging if debug mode is on
        if self.debug:
            http.client.HTTPConnection.debuglevel = 1
            logging.basicConfig()
            logging.getLogger().setLevel(logging.DEBUG)
            requests_log = logging.getLogger("requests.packages.urllib3")
            requests_log.setLevel(logging.DEBUG)
            requests_log.propagate = True


    def _post(self, endpoint: str, payload: dict | None = None):
        response = self.session.post(
            f"{self.base_url}{endpoint}",
            json=payload
        )
        response.raise_for_status()
        return response.json()

    def _get(self, endpoint: str):
        response = self.session.get(f"{self.base_url}{endpoint}")
        response.raise_for_status()
        return response.json()

    # ----------------------
    # Pulse Generator Methods
    # ----------------------
    
    # Tools
    
    def time_to_ticks(self, time: float, units: str = "ms"):
        if not self.system_info:
            raise ValueError("System info not loaded. Cannot convert time to ticks.")
        
        clock_freq_hz = self.system_info["fpga_clock_freq"]
        match units:
            case "s":
                ticks_per_unit = clock_freq_hz 
            case "ms": 
                ticks_per_unit = clock_freq_hz / 1000
            case "us":
                ticks_per_unit = clock_freq_hz / 1_000_000
            case "ns":
                ticks_per_unit = clock_freq_hz / 1_000_000_000
            case _:
                raise ValueError(f"Unsupported time unit: {units}")
        
        ticks = int(time * ticks_per_unit)
        
        print(f"Converting {time} {units} to ticks: {ticks} ticks at {clock_freq_hz} Hz. Quantization error: {time - self.ticks_to_time(ticks, units)} {units}")
            
        return ticks
    
    def ticks_to_time(self, ticks: int, units: str = "ms"):
        if not self.system_info:
            raise ValueError("System info not loaded. Cannot convert ticks to time.")
        
        clock_freq_hz = self.system_info["fpga_clock_freq"]
        match units:
            case "s":
                ticks_per_unit = clock_freq_hz 
            case "ms": 
                ticks_per_unit = clock_freq_hz / 1000
            case "us":
                ticks_per_unit = clock_freq_hz / 1_000_000
            case "ns":
                ticks_per_unit = clock_freq_hz / 1_000_000_000
            case _:
                raise ValueError(f"Unsupported time unit: {units}")
        return ticks / ticks_per_unit
    
    # GET endpoints
        
    def get_status(self):
        data = self._get("/api/get_status")

        print("\n=== STATUS ===")
        print(f"State : {data.get('status', 'unknown')}")

        return data


    def get_system_info(self):
        data = self._get("/api/get_system_info")

        self.system_info = data

        print("\n=== SYSTEM INFO ===")
        print(f"FPGA file          : {data.get('fpg_file')}")
        print(f"Clock frequency    : {data.get('fpga_clock_freq'):,} Hz ({self.ticks_to_time(1, 'ns'):.1f} ns per tick)")
        print(f"Number of outputs  : {data.get('num_outputs')}")
        print(f"Max pulses/output  : {data.get('max_pulses_per_output')}")

        return data


    def get_cycle_config(self):
        data = self._get("/api/get_cycle_config")

        print("\n=== CYCLE CONFIG ===")

        enabled = data.get("enabled", False)
        max_cycles = data.get("max_cycles")

        print(f"Cycle limit enabled : {enabled}")

        if enabled:
            print(f"Max cycles          : {max_cycles:,}")
        else:
            print("Max cycles          : disabled")

        return data


    def get_pulse_config(self):
        data = self._get("/api/get_pulse_config")

        pulse_data = data.get("pulse_data", {})

        print("\n=== PULSE CONFIG ===")

        # Period info
        if 0 in pulse_data or "0" in pulse_data:
            period_entry = pulse_data.get(0) or pulse_data.get("0")

            if period_entry and len(period_entry) > 0:
                period_ticks = period_entry[0][1]

                try:
                    period_us = self.ticks_to_time(period_ticks, "us")

                    print(
                        f"Period : {period_ticks:,} ticks "
                        f"({period_us:.3f} us)"
                    )

                except Exception:
                    print(f"Period : {period_ticks:,} ticks")

        # Outputs
        for output_idx, pulses in pulse_data.items():

            if str(output_idx) == "0":
                continue

            print(f"\nOutput {output_idx}")

            if not pulses:
                print("  No pulses configured")
                continue

            for idx, (start, stop) in enumerate(pulses):

                width = stop - start

                try:
                    start_us = self.ticks_to_time(start, "us")
                    stop_us = self.ticks_to_time(stop, "us")
                    width_us = self.ticks_to_time(width, "us")

                    print(
                        f"  Pulse {idx:02d} | "
                        f"start={start:,} ticks ({start_us:.3f} us) | "
                        f"stop={stop:,} ticks ({stop_us:.3f} us) | "
                        f"width={width:,} ticks ({width_us:.3f} us)"
                    )

                except Exception:
                    print(
                        f"  Pulse {idx:02d} | "
                        f"start={start:,} | stop={stop:,}"
                    )

        return data


    def get_logs(self):
        data = self._get("/api/get_logs")

        logs = data.get("logs", [])

        print("\n=== LOGS ===")

        if not logs:
            print("No logs available")
            return data

        for line in logs:
            print(line)

        return data


    def get_cycle_count(self):
        data = self._get("/api/get_cycle_count")

        cycle_count = data.get("cycle_count", 0)

        print("\n=== CYCLE COUNT ===")
        print(f"Cycles completed : {cycle_count:,}")

        return data
    # POST endpoints 
    
    def load_bitstream(self):
        return self._post("/api/load_bitstream")

    def start(self):
        return self._post("/api/start")

    def stop(self):
        return self._post("/api/stop")

    def reset(self):
        return self._post("/api/reset")
    
    def clear_outputs(self):
        return self._post("/api/clear_outputs")

    def set_period(self, period_length_ticks: int):
        return self._post(
            "/api/set_period",
            {"period_length_ticks": period_length_ticks}
        )
    
    def set_cycle_limit(self, max_cycles: int, enabled: bool):
        return self._post(
            "/api/set_cycle_limit",
            {"max_cycles": max_cycles, "enabled": enabled}
        )

    def set_pulse(
        self,
        output_idx: int,
        pulse_idx: int,
        start: int,
        stop: int
    ):
        return self._post(
            "/api/set_pulse",
            {
                "output_idx": output_idx,
                "pulse_idx": pulse_idx,
                "start": start,
                "stop": stop
            }
        )
        
    def set_pulse_train(self, output_idx: int, pulse_train: list[tuple[int, int]]):
        return self._post(
            "/api/set_pulse_train",
            {
                "output_idx": output_idx,
                "pulse_train": pulse_train
            }
        )

    # load pulse trains from a file with format:
    # output_idx,start_ticks,stop_ticks
    # where out_idx 0 corresponds to the max counter value (i.e. the period) 
    def set_from_file(self, file_path):
        if not os.path.isfile(file_path):
            raise ValueError(f"File {file_path} does not exist")

        # Create list of empty lists (one per output and one for the period)
        timing_data = [[] for _ in range(self.NUM_OUTPUTS + 1)]

        with open(file_path, "r") as csvfile:
            reader = csv.DictReader(csvfile, delimiter=",", skipinitialspace=True, strict=True)

            for row in reader:
                if not row["out_idx"] or not row["start_ticks"] or not row["stop_ticks"]:
                    continue
                output_idx = int(row["out_idx"])
                start_ticks = int(row["start_ticks"])
                stop_ticks = int(row["stop_ticks"])

                timing_data[output_idx].append((start_ticks, stop_ticks))
                
        # Set pulse trains for each output based on loaded data
        for output_idx, pulse_train in enumerate(timing_data):
            if output_idx == 0:
                self.set_period(pulse_train[0][1])  # Set period using stop time of first pulse
            else:
                self.set_pulse_train(output_idx, pulse_train)
        
    

