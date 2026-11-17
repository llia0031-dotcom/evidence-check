"""evcheck: check every number and quotation in a finished draft against your own sources."""
__version__ = "0.5.0"


def check(draft_path, source_paths) -> dict:
    """Check a draft file against source files or folders; returns the same result as `evcheck --json -`."""
    from .check import check_draft
    from .readers import read, read_sources

    return check_draft(read(draft_path), read_sources(source_paths))
