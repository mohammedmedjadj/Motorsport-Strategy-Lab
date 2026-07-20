"""Multi-series data access.

Extends the project beyond Formula 1 (loaded via FastF1) to endurance racing
(IMSA / WEC), which FastF1 does not cover. Every loader normalises its source
into one common lap frame (see ``base_loader.LAP_COLUMNS``) so the downstream
degradation, safety-car and simulator layers stay series-agnostic.
"""
