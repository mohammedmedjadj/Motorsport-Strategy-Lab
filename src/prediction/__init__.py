"""Forward prediction and calibration scoring.

Turns the project's probabilistic models from *retrospective fits* into
*predictions that get scored*: each probability is generated out-of-sample
(leave-one-race-out) and graded with proper scoring rules and a reliability
curve, so a claim like "safety cars here about 60% of the time" is checked
against how often it actually happens — the scientific method the rest of the
project's rigour is in service of.
"""
