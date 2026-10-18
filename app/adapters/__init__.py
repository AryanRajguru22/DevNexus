"""Replaceable adapters for the external systems of the design: LLM service, Git host, CI/CD runner.

The MVP ships local/mock implementations only (deviation D-4); real GitHub/GitLab/LLM adapters can be added
behind the same interfaces (NFR-10).
"""
