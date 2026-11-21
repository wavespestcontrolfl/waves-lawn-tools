# Convert sprinkler run time to inches of water

Two sprinkler zones can run for the same number of minutes and deliver different amounts of water. The Python package `waves-lawn-tools` estimates weekly depth from the run time per zone, the watering days, and the type of sprinkler head.

## Try one 12-minute run

Install the package in your Python environment. This example uses version 1.2.0.

```sh
python -m pip install waves-lawn-tools==1.2.0
```

Use one watering day so the weekly total equals the depth of a single run.

```python
from waves_lawn_tools import derive_irrigation_inches_per_week

for head in ("spray", "rotor"):
    result = derive_irrigation_inches_per_week(
        run_minutes=12, watering_days=["Sat"], system_type=head
    )
    print(f"{head}  {result['inches_per_week']:.2f} inches")
```

```text
spray  0.30 inches
rotor  0.10 inches
```

## Read the result

Twelve minutes is one fifth of an hour. The library uses default rates of 1.5 inches per hour for spray heads and 0.5 for rotors. A catch-can test lets you compare those estimates with what reaches the grass in a particular zone.

For a drip-only zone, the function returns `None` for `inches_per_week` and `drip_only` for `reason`. A dashboard can use that reason to display “Drip zone” and leave the estimated depth blank.

For a weekly plan that also accounts for local rainfall and grass type, try the [Waves lawn watering calculator](https://www.wavespestcontrol.com/tools/lawn-watering-calculator/).
