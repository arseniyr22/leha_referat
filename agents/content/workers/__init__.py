"""
Content generation workers package.

Each worker generates one section of academic text by calling
AcademicGenerator.generate_section() from pipeline/generator.py.

Worker hierarchy:
- BaseSectionWorker (base class)
  - Multi-section workers: vkr_*, cw_*, res_*, ap_* (Prompt 3B)
  - Single-generation workers: text_*, essay_full, comp_full (Prompt 3C)

Workers are instantiated by MicroManagers and called in SECTION_ORDER sequence.
"""
