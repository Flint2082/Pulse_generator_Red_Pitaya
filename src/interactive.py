from IPython import start_ipython
import sys
import os

# import casperfpga.casperfpga as casperfpga
from packages.pulse_gen_interface import PulseGenInterface 

pulseGen = PulseGenInterface()

ns = globals()
ns.update(
    {
        name: getattr(pulseGen, name)
        for name in dir(pulseGen)
        if not name.startswith("_")
    }
)

start_ipython(argv=[], user_ns=ns)


