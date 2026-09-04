"""Inference for the published headline numbers.

Kept apart from the fitting code deliberately: `src/degradation/robust.py`
computes standard errors *inside* an estimator, while this describes uncertainty
*about a reported result*. They answer different questions and mixing them is
how a within-fit standard error ends up quoted as a claim about a finding.
"""
