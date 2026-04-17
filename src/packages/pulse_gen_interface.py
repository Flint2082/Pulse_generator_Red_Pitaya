from packages.fpga_interface import FPGAInterface
import os
import csv

class PulseGenInterface:
    def __init__(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        directory = os.path.join(base_dir, "..", "..", "model_composer", "pulse_generator", "outputs")
        self.fpg_file = max(
            (os.path.join(directory, f) for f in os.listdir(directory)),
            key=os.path.getmtime
        )
 
        # Constants
        self.MAX_PULSES_PER_OUTPUT = 32
        self.NUM_OUTPUTS = 3
        
        self.BITSTREAM_PATH = os.path.join(base_dir, "root", "top.bit.bin")

        print("Newest file", self.fpg_file)
 
        try:
            self.fpga = FPGAInterface()
            self.fpga.load_register_map(self.fpg_file)
            self.fpga_clock_freq_Hz = self.fpga.get_clock_freq(self.fpg_file)
            self.fpga.test_fpga_interface("counter_en")
        except Exception as e:
            print(f"Failed to upload FPGA program: {e}")
            raise
        
    def load_bitstream(self):
        result = self.fpga.load_bitstream()
        if result["status"] == "error":
            print(f"Error loading bitstream: {result.get('message', result.get('stderr', 'Unknown error'))}")
        else:
            print(f"Bitstream loaded successfully: {result.get('stdout', '')}")
        
    def start(self):
        if(self.fpga.read_register("counter_en") == 1):
            print("Pulse generator is already running")
            return
        self.fpga.write_register("counter_en", 1)
        print("Starting pulse generator")
    
    def stop(self):
        if(self.fpga.read_register("counter_en") == 0):
            print("Pulse generator is already stopped")
            return
        self.fpga.write_register("counter_en", 0)
        print("Stopping pulse generator")
    
    def get_status(self):
        self.fpga.read_register("counter_en")
        status = "running" if self.fpga.read_register("counter_en") == 1 else "stopped"
        print(f"Pulse generator is currently {status}")
        return status
    
    def reset(self):
        self.fpga.write_register("reset", 1)
        print("Resetting pulse generator")
        self.fpga.write_register("reset", 0)
    
    def time_to_ticks(self, time_sec):
        return int(time_sec * self.fpga_clock_freq_Hz)
    
    def ticks_to_time(self, ticks):
        return ticks / self.fpga_clock_freq_Hz
    
    def set_period(self, period_length_ticks):
        if period_length_ticks <= 0:
            raise ValueError("Period length must be greater than 0")
        if period_length_ticks > 2**32 - 1:
            raise ValueError(f"Period length must be less than {2**32 - 1}")
        print(f"Setting period length to {self.ticks_to_time(period_length_ticks)} seconds ({period_length_ticks} ticks)")
        self.fpga.write_register("period", period_length_ticks)
        
    def enable_cycle_limit(self, enabled):
        self.fpga.write_register("cycle_limit_enable", 1 if enabled else 0)
    
    def set_max_cycles(self, max_cycles):
        self.fpga.write_register("max_cycles", max_cycles)
        
    def get_cycle_count(self):
        return self.fpga.read_register("cycle_counter")
    
    def set_pulse(self, output_idx, pulse_idx, start, stop):
        # Validate inputs
        if stop < start:
            raise ValueError("Stop time must be greater than start time")
        if pulse_idx >= self.MAX_PULSES_PER_OUTPUT:
            raise ValueError(f"Pulse index must be less than {self.MAX_PULSES_PER_OUTPUT}")
        if output_idx > self.NUM_OUTPUTS:
            raise ValueError(f"Output index must be no greater than {self.NUM_OUTPUTS}")
        if output_idx == 0:
            raise ValueError("Output index cannot be 0, as the lowest output is 1")
        
        # Write to FPGA registers
        self.fpga.write_register(f"out_{output_idx}_start_{pulse_idx}", start)
        self.fpga.write_register(f"out_{output_idx}_stop_{pulse_idx}", stop)
        
        print(f"Writing pulse to output {output_idx}, pulse {pulse_idx}: start={start}, stop={stop}")  
    
    def set_pulse_train(self, output_idx, pulse_train):
        for pulse_idx, pulse in enumerate(pulse_train):
            self.set_pulse(output_idx, pulse_idx, pulse[0], pulse[1])
    
    
    def set_pulse_trains(self, pulse_trains):
        for output_idx, pulse_train in enumerate(pulse_trains):
            if output_idx == 0:
                self.set_period(pulse_train[0][1])  # Set period using stop time of first pulse
            else:
                self.set_pulse_train(output_idx, pulse_train)


    # load pulse trains from a file with format:
    # output_idx,start_ticks,stop_ticks
    # where out_idx 0 corresponds to the max counter value (i.e. the period) 
    def get_pulse_data_from_file(self, file_path):
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

        return timing_data


    def get_pulse_data(self):
        pulse_data = {}
        for output_idx in range(self.NUM_OUTPUTS + 1):
            if output_idx == 0:
                period = self.fpga.read_register("period")
                pulse_data[0] = [(0, period)]
            else:
                for pulse_idx in range(self.MAX_PULSES_PER_OUTPUT):
                    start = self.fpga.read_register(f"out_{output_idx}_start_{pulse_idx}")
                    stop = self.fpga.read_register(f"out_{output_idx}_stop_{pulse_idx}")
                    if start != 0 or stop != 0:
                        if output_idx not in pulse_data:
                            pulse_data[output_idx] = []
                        pulse_data[output_idx].append((start, stop))
            
        return pulse_data

    def clear_output(self, output_idx):
        for pulse_idx in range(self.MAX_PULSES_PER_OUTPUT):
            self.set_pulse(output_idx, pulse_idx, 0, 0)
        print(f"Cleared output {output_idx}")
    
    def clear_all_outputs(self):
        for output_idx in range(1, self.NUM_OUTPUTS + 1):
            self.clear_output(output_idx)
        print("Cleared all outputs")
