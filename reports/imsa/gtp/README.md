# IMSA GTP — manufacturer prototypes

The top class of the IMSA WeatherTech SportsCar Championship, and the closest
IMSA equivalent to WEC's Hypercar. **33 race-seasons, 10 circuits, 2023–2026.**

| | |
|---|---|
| median net slope | +0.0166 s/lap |
| median pit loss | 57.0 s |
| tyre-change premium | **8.7 s** — the cheapest in the project |
| tyre-limited races | 2 of 32 |
| best season-to-season transfer | +0.058 (Laguna Seca) |

## What GTP is for, in this project

**It is the control for the GT3 classes.** GTP and GTD race the same rounds on
the same weekends, so anything that differs between them is the car, not the
calendar or the conditions — and what differs is decisive:

- **The tyre-change premium is 8.7 s against GT3's 17.6 s.** A prototype's
  wheels come off faster. This is what showed the premium is a property of the
  machine and its service, not of the crew driving it.
- **The full stop costs 57 s against GTD's 24 s**, and that reverses the
  strategy regime: GTP is tyre-limited in 6% of its races, GTD in a quarter.
  For a while this project published GTP's answer as "IMSA's" answer.
- **GTP slopes do not transfer between seasons** (+0.058 at best) where GT3's
  reach +0.573. Whatever makes a circuit predictable, it is not the prototype.

## The one thing GTP does not have

**A Safety Car.** IMSA has never shown one in 63 races across any class — it
runs Full Course Yellow instead, in 61 of those 63. WEC prefers the Safety Car
and ELMS is dominated by it. Three championships, three regimes.

## The complete tables

Generated from the committed artifacts by
[`scripts/run_class_reports.py`](../../../scripts/run_class_reports.py), so they
cannot drift from the data:

- [lap accounting, every race](data_quality_all_races.md)
- [every fitted slope with its interval](degradation_all_races.md)
- [season-to-season transfer, every fold](transfer_all_races.md)
- [full-race stop plans, every race](strategy_all_races.md)

Plus [`audit_cases.md`](audit_cases.md) — three real stop decisions replayed in
depth — and the phase reports this class was built through:
[phase 1](data_quality_phase1.md) · [phase 2](degradation_phase2.md) ·
[phase 3](safety_car_phase3.md) · [phase 4](simulator_phase4.md).
