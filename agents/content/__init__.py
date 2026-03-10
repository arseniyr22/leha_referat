"""
Content generation agents package.

ContentManager orchestrates Phase 0 content generation:
- Calls SourceFinder (Phase 0A)
- Routes to the correct MicroManager by stream_id (Phase 0B)
- MicroManager generates sections via workers (Phase 3)

Hierarchy: CEO → ContentManager → MicroManager → Worker (Phase 3)
"""
