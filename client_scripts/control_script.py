from pulse_gen_client import PulseGenClient
from time import sleep 


pg = PulseGenClient("http://rp-f0f587.local:8000", debug=False)

pg.get_status()

print(pg.system_info)

pg.set_period(pg.time_to_ticks(1, "us"))

pg.set_pulse(
    output_idx=1,
    pulse_idx=0,
    start=pg.time_to_ticks(0.1, "us"),
    stop=pg.time_to_ticks(0.2, "us")
)

pg.set_pulse_train(
    output_idx=2,
    pulse_train=[
        (pg.time_to_ticks(0.1, "us"), pg.time_to_ticks(0.2, "us")),
        (pg.time_to_ticks(0.3, "us"), pg.time_to_ticks(0.4, "us")),
        (pg.time_to_ticks(0.5, "us"), pg.time_to_ticks(0.703, "us"))
    ]
)

# print(pg.set_from_file("timing_settings/worst_case.csv"))

pg.set_cycle_limit(max_cycles=1000000, enabled=True)

pg.get_cycle_config()

pg.start()

for _ in range(10):
    pg.get_cycle_count()
    sleep(0.1)

pg.get_status()

pg.get_pulse_config()