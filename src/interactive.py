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

pulseGen = PulseGenInterface(rp_ip)

ns = globals()
ns.update(
    {
        name: getattr(pulseGen, name)
        for name in dir(pulseGen)
        if not name.startswith("_")
    }
)

start_ipython(argv=[], user_ns=ns)


