import csv
import os

import requests

from server import set_pulse, stop


class RedPitayaClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def _post(self, endpoint: str, payload: dict | None = None):
        response = requests.post(
            f"{self.base_url}{endpoint}",
            json=payload
        )
        response.raise_for_status()
        return response.json()

    def _get(self, endpoint: str):
        response = requests.get(f"{self.base_url}{endpoint}")
        response.raise_for_status()
        return response.json()

    # ----------------------
    # Pulse Generator Methods
    # ----------------------
    
    # GET endpoints
    
    def status(self):
        return self._get("/status")
    
    def get_pulse_config(self):
        return self._get("/pulse_config")
    
    # POST endpoints 

    def start(self):
        return self._post("/start")

    def stop(self):
        return self._post("/stop")

    def clear(self):
        return self._post("/clear")

    def set_period(self, period_length_ticks: int):
        return self._post(
            "/set_period",
            {"period_length_ticks": period_length_ticks}
        )

    def set_pulse(
        self,
        output_idx: int,
        pulse_idx: int,
        start: int,
        stop: int
    ):
        return self._post(
            "/set_pulse",
            {
                "output_idx": output_idx,
                "pulse_idx": pulse_idx,
                "start": start,
                "stop": stop
            }
        )
        
    def set_pulse_train(self, output_idx: int, pulse_train: list[tuple[int, int]]):
        return self._post(
            "/set_pulse_train",
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
        
    

