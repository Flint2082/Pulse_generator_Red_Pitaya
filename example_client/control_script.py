from pulse_gen_client import RedPitayaClient


rp = RedPitayaClient("http://rp-f0f587.local:8000")

print(rp.stop())

print(rp.reset())

# print(rp.set_period(1000))

# print(rp.set_pulse(
#     output_idx=1,
#     pulse_idx=0,
#     start=100,
#     stop=200
# ))

print(rp.set_from_file("timing_settings/settings.csv"))

print(rp.start())

print(rp.status())

print(rp.get_pulse_config())