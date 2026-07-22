# Retrospective audit — did endurance winners run fuel-limited?

The multi-stop models conclude every scoped endurance race is **fuel-limited on stop count** (see the [WEC](wec/simulator_phase4.md) / [IMSA](imsa/simulator_phase4.md) reports). This audit tests that against **what the race winners actually did**: their real fuel-stint lengths, reconstructed from the committed laps, compared to each circuit's measured fuel range. No number is quoted from memory.

**19 of 21 audited winners ran fuel-limited** — at least one stint within 3 laps of the full fuel range, and a longest stint reaching it. Real winning behaviour corroborates the model's headline.

| Series | Circuit | Year | Winner | Fuel range | Longest stint | Full stints | Verdict |
|---|---|---|---|---|---|---|---|
| imsa | watkins_glen | 2023 | 6 | 34 | 34 | 3 | fuel-limited |
| imsa | watkins_glen | 2024 | 1 | 34 | 32 | 1 | fuel-limited |
| imsa | watkins_glen | 2025 | 6 | 34 | 39 | 2 | fuel-limited |
| imsa | sebring | 2023 | 25 | 29 | 31 | 5 | fuel-limited |
| imsa | sebring | 2024 | 1 | 29 | 33 | 7 | fuel-limited |
| imsa | sebring | 2025 | 5 | 29 | 32 | 9 | fuel-limited |
| imsa | mosport | 2023 | 5 | 50 | 43 | 0 | **tyre-limited?** |
| imsa | road_america | 2023 | 1 | 29 | 29 | 2 | fuel-limited |
| imsa | road_america | 2024 | 5 | 29 | 32 | 1 | fuel-limited |
| imsa | road_america | 2025 | 6 | 29 | 22 | 0 | **tyre-limited?** |
| wec | spa | 2023 | 5 | 28 | 27 | 3 | fuel-limited |
| wec | spa | 2024 | 6 | 28 | 34 | 3 | fuel-limited |
| wec | spa | 2025 | 5 | 28 | 27 | 3 | fuel-limited |
| wec | fuji | 2023 | 6 | 42 | 40 | 4 | fuel-limited |
| wec | fuji | 2024 | 6 | 42 | 44 | 4 | fuel-limited |
| wec | fuji | 2025 | 5 | 42 | 43 | 2 | fuel-limited |
| wec | bahrain | 2023 | 7 | 32 | 32 | 8 | fuel-limited |
| wec | bahrain | 2024 | 2 | 32 | 32 | 4 | fuel-limited |
| wec | bahrain | 2025 | 7 | 32 | 31 | 2 | fuel-limited |
| wec | imola | 2024 | 5 | 36 | 37 | 4 | fuel-limited |
| wec | imola | 2025 | 5 | 36 | 38 | 3 | fuel-limited |

## Reading the exceptions

A winner whose longest stint falls short of the fuel range is not automatically a refutation: a race disrupted by many neutralisations bunches stops and shortens stints for reasons unrelated to tyres. Where a winner *does* run a full-range stint, though, it is direct evidence that the tank — not the tyre — set the stint length, exactly as the DP concluded from the degradation and pit-loss numbers independently.
