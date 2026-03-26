from IPython import start_ipython
import casperfpga.casperfpga as casperfpga
import sys
import os

# import casperfpga.casperfpga as casperfpga
from packages.pulse_gen_interface import PulseGenInterface 

if len(sys.argv) > 1:
    rp_ip = sys.argv[1]
else:
    quit("Usage: python interactive.py <rp_ip_address>")
    
# Remove custom args so IPython doesn't see them
sys.argv = [sys.argv[0]]

fpga = casperfpga.CasperFpga(rp_ip)
pulseGen = PulseGenInterface(rp_ip)

base_dir = os.path.dirname(os.path.abspath(__file__))
directory = os.path.join(base_dir, "..", "model_composer", "pulse_generator", "outputs")
newest_file = max(
    (os.path.join(directory, f) for f in os.listdir(directory)),
    key=os.path.getmtime
)

try:
    fpga.upload_to_ram_and_program(newest_file)
except Exception as e:
    print(f"Failed to upload FPGA program: {e}")
    raise

start_ipython()

