"""
Gate agents for the multi-agent pipeline.

Gates validate state at critical transitions:
- ContentQAGate: validates Phase 0 output before humanization
- QA gates (Phase 5): validate after each HM stage
"""
