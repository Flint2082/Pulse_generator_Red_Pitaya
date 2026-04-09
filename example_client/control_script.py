from pulse_gen_client import PulseGenClient


pg = PulseGenClient("http://rp-f0f587.local:8000", debug=False)

print(pg.status())

system_info = pg.system_info()
print(system_info)
print(system_info["fpga_clock_freq"])

print(pg.stop())

print(pg.reset())

# print(pg.set_period(1000))

# print(pg.set_pulse(
#     output_idx=1,
#     pulse_idx=0,
#     start=100,
#     stop=200
# ))

print(pg.set_from_file("timing_settings/settings.csv"))

print(pg.start())

print(pg.status())

print(pg.get_pulse_config())