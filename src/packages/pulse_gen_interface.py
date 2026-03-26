import casperfpga
import os
import csv

class PulseGenInterface:
    def __init__(self, RP_IP):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        directory = os.path.join(base_dir, "..", "..", "model_composer", "pulse_generator", "outputs")
        newest_file = max(
            (os.path.join(directory, f) for f in os.listdir(directory)),
            key=os.path.getmtime
        )
 
        # Constants
        self.FPGA_CLOCK_FREQ = 125e6  # 125 MHz
        self.MAX_PULSES_PER_OUTPUT = 8
        self.NUM_OUTPUTS = 3
        
        

        self.fpga = casperfpga.CasperFpga(RP_IP)
        print("CasperFpga connected to red pitaya")

        print("Newest file", newest_file)

        try:
            self.fpga.upload_to_ram_and_program(newest_file)
        except Exception as e:
            print(f"Failed to upload FPGA program: {e}")
            raise

    
    def reset(self):
        self.fpga.write_int("reset", 1)
        print("Resetting pulse generator")
        self.fpga.write_int("reset", 0)
    
    def time_to_cycles(self, time_sec):
        return int(time_sec * self.FPGA_CLOCK_FREQ)    
    
    def cycles_to_time(self, cycles):
        return cycles / self.FPGA_CLOCK_FREQ
    
    def set_period_length(self, period_length_cycles):
        if period_length_cycles <= 0:
            raise ValueError("Period length must be greater than 0")
        if period_length_cycles > 2**32 - 1:
            raise ValueError(f"Period length must be less than {2**32 - 1}")
        print(f"Setting period length to {self.cycles_to_time(period_length_cycles)} seconds ({period_length_cycles} cycles)")
        self.fpga.write_int("period", period_length_cycles)
    
    def write_pulse(self, output_idx, pulse_idx, start, stop):
        # Validate inputs
        if stop <= start:
            raise ValueError("Stop time must be greater than start time")
        if pulse_idx >= self.MAX_PULSES_PER_OUTPUT:
            raise ValueError(f"Pulse index must be less than {self.MAX_PULSES_PER_OUTPUT}")
        if output_idx >= self.NUM_OUTPUTS + 1:
            raise ValueError(f"Output index must be less than {self.NUM_OUTPUTS + 1}")
        if output_idx == 0:
            raise ValueError("Output index cannot be 0, as the lowest output is 1")
        
        # Write to FPGA registers
        self.fpga.write_int(f"out_{output_idx}_start_{pulse_idx}", start)
        self.fpga.write_int(f"out_{output_idx}_stop_{pulse_idx}", stop)
        
        print(f"Writing pulse to output {output_idx}, pulse {pulse_idx}: start={start}, stop={stop}")  
    
    def write_pulse_train(self, output_idx, pulse_train):
        for pulse_idx, pulse in enumerate(pulse_train):
            self.write_pulse(output_idx, pulse_idx, pulse[0], pulse[1])
    
    
    def write_pulse_trains(self, pulse_trains):
        for item in pulse_trains:
            output_idx = item["out_idx"]
            pulse_train = item["pulses"]
            self.write_pulse_train(output_idx, pulse_train)


    # load pulse trains from a file with format:
    # output_idx,start_cycles,stop_cycles
    # where out_idx 0 corresponds to the max counter value (i.e. the period) 
    def get_timing_from_file(self, file_path):
        if not os.path.isfile(file_path):
            raise ValueError(f"File {file_path} does not exist") 
        
        timing_data = {i: {"pulses": []} for i in range(self.NUM_OUTPUTS + 1)}
       

        with open(file_path, "r") as csvfile:
            reader = csv.DictReader(csvfile, delimiter=",", skipinitialspace=True, strict=True)
            
            for row in reader:
                output_idx = int(row["out_idx"])
                start_cycles = int(row["start_cycles"])
                stop_cycles = int(row["stop_cycles"])
                timing_data[output_idx]["pulses"].append((start_cycles, stop_cycles))

        return timing_data


    def print_timing(self, timing_data):
        for output_idx, timing in timing_data.items():
            if output_idx == 0:
                print(f"Output {output_idx} (period): {timing['pulses']}")
            else:
                print(f"Output {output_idx}:")
                for pulse in timing["pulses"]:
                    print(f"  Start: {pulse[0]} cycles, Stop: {pulse[1]} cycles")
