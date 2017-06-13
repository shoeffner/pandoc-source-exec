"""pandoc-source-exec is a panflute pandoc filter to execute source code and
add the output to the pandoc document."""

__version__ = '0.1.3'


from .pandoc_source_exec import prepare, action, finalize, main  # noqa
