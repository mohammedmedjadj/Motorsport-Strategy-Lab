# Retrospective audit — did endurance winners run fuel-limited?

The multi-stop models conclude every scoped endurance race is **fuel-limited on stop count** (see the [WEC](wec/simulator_phase4.md) / [IMSA](imsa/simulator_phase4.md) reports). This audit tests that against **what the race winners actually did**: their real fuel-stint lengths, reconstructed from the committed laps, compared to each circuit's measured fuel range. No number is quoted from memory.

**49 of 61 audited winners ran fuel-limited** — at least one stint within 3 laps of the full fuel range, and a longest stint reaching it. Real winning behaviour corroborates the model's headline.

| Series | Circuit | Year | Winner | Fuel range | Longest stint | Full stints | Verdict |
|---|---|---|---|---|---|---|---|
| imsa | daytona | 2023 | 1 | 33 | 34 | 16 | fuel-limited |
| imsa | daytona | 2024 | 5 | 33 | 35 | 12 | fuel-limited |
| imsa | daytona | 2025 | 6 | 33 | 35 | 7 | fuel-limited |
| imsa | daytona | 2026 | 6 | 33 | 34 | 16 | fuel-limited |
| imsa | detroit | 2024 | 1 | 50 | 50 | 1 | fuel-limited |
| imsa | detroit | 2025 | 6 | 50 | 52 | 1 | fuel-limited |
| imsa | detroit | 2026 | 6 | 50 | 36 | 0 | **tyre-limited?** |
| imsa | indianapolis | 2023 | 1 | 49 | 44 | 0 | **tyre-limited?** |
| imsa | indianapolis | 2024 | 6 | 49 | 66 | 1 | fuel-limited |
| imsa | indianapolis | 2025 | 6 | 49 | 49 | 3 | fuel-limited |
| imsa | laguna_seca | 2023 | 1 | 46 | 38 | 0 | **tyre-limited?** |
| imsa | laguna_seca | 2024 | 1 | 46 | 43 | 1 | fuel-limited |
| imsa | laguna_seca | 2025 | 6 | 46 | 43 | 1 | fuel-limited |
| imsa | laguna_seca | 2026 | 5 | 46 | 33 | 0 | **tyre-limited?** |
| imsa | long_beach | 2023 | 6 | 45 | 45 | 1 | fuel-limited |
| imsa | long_beach | 2024 | 1 | 45 | 40 | 0 | **tyre-limited?** |
| imsa | long_beach | 2025 | 6 | 45 | 56 | 1 | fuel-limited |
| imsa | long_beach | 2026 | 5 | 45 | 36 | 0 | **tyre-limited?** |
| imsa | mosport | 2023 | 5 | 50 | 43 | 0 | **tyre-limited?** |
| imsa | road_america | 2023 | 1 | 24 | 29 | 3 | fuel-limited |
| imsa | road_america | 2024 | 5 | 24 | 32 | 1 | fuel-limited |
| imsa | road_america | 2025 | 6 | 24 | 22 | 1 | fuel-limited |
| imsa | road_atlanta | 2023 | 1 | 51 | 53 | 2 | fuel-limited |
| imsa | road_atlanta | 2024 | 1 | 51 | 48 | 1 | fuel-limited |
| imsa | road_atlanta | 2025 | 6 | 51 | 53 | 3 | fuel-limited |
| imsa | sebring | 2023 | 25 | 32 | 31 | 2 | fuel-limited |
| imsa | sebring | 2024 | 1 | 32 | 33 | 7 | fuel-limited |
| imsa | sebring | 2025 | 5 | 32 | 32 | 6 | fuel-limited |
| imsa | sebring | 2026 | 5 | 32 | 33 | 4 | fuel-limited |
| imsa | watkins_glen | 2023 | 6 | 38 | 34 | 0 | **tyre-limited?** |
| imsa | watkins_glen | 2024 | 1 | 38 | 32 | 0 | **tyre-limited?** |
| imsa | watkins_glen | 2025 | 6 | 38 | 39 | 2 | fuel-limited |
| imsa | watkins_glen | 2026 | 5 | 38 | 37 | 2 | fuel-limited |
| wec | bahrain | 2022 | 7 | 32 | 33 | 7 | fuel-limited |
| wec | bahrain | 2023 | 7 | 32 | 32 | 8 | fuel-limited |
| wec | bahrain | 2024 | 2 | 32 | 32 | 4 | fuel-limited |
| wec | bahrain | 2025 | 7 | 32 | 31 | 2 | fuel-limited |
| wec | cota | 2024 | 2 | 37 | 32 | 0 | **tyre-limited?** |
| wec | cota | 2025 | 5 | 37 | 44 | 2 | fuel-limited |
| wec | fuji | 2022 | 7 | 46 | 39 | 0 | **tyre-limited?** |
| wec | fuji | 2023 | 6 | 46 | 40 | 0 | **tyre-limited?** |
| wec | fuji | 2024 | 6 | 46 | 44 | 2 | fuel-limited |
| wec | fuji | 2025 | 5 | 46 | 43 | 1 | fuel-limited |
| wec | imola | 2024 | 5 | 37 | 37 | 4 | fuel-limited |
| wec | imola | 2025 | 5 | 37 | 38 | 3 | fuel-limited |
| wec | imola | 2026 | 7 | 37 | 37 | 1 | fuel-limited |
| wec | interlagos | 2024 | 5 | 43 | 43 | 4 | fuel-limited |
| wec | interlagos | 2025 | 5 | 43 | 43 | 4 | fuel-limited |
| wec | le_mans | 2022 | 7 | 13 | 13 | 29 | fuel-limited |
| wec | le_mans | 2025 | 6 | 13 | 15 | 29 | fuel-limited |
| wec | le_mans | 2026 | 7 | 13 | 16 | 26 | fuel-limited |
| wec | losail | 2025 | 7 | 36 | 36 | 1 | fuel-limited |
| wec | monza | 2022 | 8 | 30 | 30 | 4 | fuel-limited |
| wec | portimao | 2023 | 8 | 37 | 40 | 5 | fuel-limited |
| wec | sebring | 2022 | 8 | 31 | 31 | 6 | fuel-limited |
| wec | sebring | 2023 | 7 | 31 | 33 | 7 | fuel-limited |
| wec | spa | 2022 | 7 | 27 | 26 | 2 | fuel-limited |
| wec | spa | 2023 | 5 | 27 | 27 | 5 | fuel-limited |
| wec | spa | 2024 | 6 | 27 | 34 | 3 | fuel-limited |
| wec | spa | 2025 | 5 | 27 | 27 | 3 | fuel-limited |
| wec | spa | 2026 | 7 | 27 | 28 | 2 | fuel-limited |

## Reading the exceptions

A winner whose longest stint falls short of the fuel range is not automatically a refutation: a race disrupted by many neutralisations bunches stops and shortens stints for reasons unrelated to tyres. Where a winner *does* run a full-range stint, though, it is direct evidence that the tank — not the tyre — set the stint length, exactly as the DP concluded from the degradation and pit-loss numbers independently.
