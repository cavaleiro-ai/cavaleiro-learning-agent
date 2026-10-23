"""Frozen legacy commit-email → GitHub login mappings. Data only; never append.

The contributor-check CI job and ``scripts/audit_pr_attribution.py`` grep this
file for ``"<email>"``, so the entries must stay a literal dict here.
"""

# Cavaleiro Learning Agent carries none of the original project's commit
# history, so the legacy mappings that attributed that history were removed.
# New contributor mappings live as one-file-per-email entries under
# contributors/emails/ (see contributors/README.md); the effective AUTHOR_MAP
# in authors.py merges this dict with that directory (directory wins).
LEGACY_AUTHOR_MAP = {
}
