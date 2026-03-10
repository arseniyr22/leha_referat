"""
Micro Manager agents for content generation.

Each MicroManager handles one stream_id type and knows:
- SECTION_ORDER: exact sequence of sections to generate
- VIZ_MINIMUMS: minimum visualization count by level (БЛОК 16.2)
- DATA_HEAVY_SECTIONS: sections to re-generate if viz count is below minimum

Hierarchy: ContentManager → MicroManager → Worker (Phase 3)

7 concrete MMs:
- MicroManagerVKR (9 sections)
- MicroManagerCoursework (7 sections)
- MicroManagerResearch (8 sections)
- MicroManagerAbstractPaper (6 sections)
- MicroManagerText (4 subtypes, 1 section each)
- MicroManagerEssay (1 section)
- MicroManagerComposition (1 section)
"""
