import subprocess
from os.path import exists
from tempfile import NamedTemporaryFile
import os
import logging
from typing import Optional

# Import find executable engine
from typing import MutableMapping, Any

try:
    from shutil import which
except ImportError:
    from distutils.spawn import find_executable

    which = find_executable

# Path to the executable
PANDOC_PATH = which('pandoc')

logger = logging.getLogger('asyncio')


class Document:
    """A formatted document."""

    OUTPUT_FORMATS = frozenset([
        'asciidoc', 'beamer', 'commonmark', 'context', 'docbook',
        'docx', 'dokuwiki', 'dzslides', 'epub', 'epub3', 'fb2',
        'haddock', 'html', 'html5', 'icml', 'json', 'latex', 'man',
        'markdown', 'markdown_github', 'markdown_mmd',
        'markdown_phpextra', 'markdown_strict', 'mediawiki', 'native',
        'odt', 'opendocument', 'opml', 'org', 'pdf', 'plain',
        'revealjs', 'rst', 'rtf', 's5', 'slideous', 'slidy', 'texinfo',
        'textile'
    ])

    def __init__(self) -> None:
        self._content = None
        self._format = None
        self._register_formats()
        self.arguments = []

        if not exists(PANDOC_PATH):
            raise OSError("Path to pandoc executable does not exists")

    def template(self, template) -> None:
        if not exists(template):
            raise IOError("Template file not found: %s" % template)
        self.add_argument("template=%s" % template)

    def bib(self, bibfile) -> None:
        if not exists(bibfile):
            raise IOError("Bib file not found: %s" % bibfile)
        self.add_argument("bibliography=%s" % bibfile)

    def csl(self, cslfile) -> None:
        if not exists(cslfile):
            raise IOError("CSL file not found: %s" % cslfile)
        self.add_argument("csl=%s" % cslfile)

    def abbr(self, abbrfile) -> None:
        if not exists(abbrfile):
            raise IOError("Abbreviations file not found: " + abbrfile)
        self.add_argument("citation-abbreviations=%s" % abbrfile)

    def add_argument(self, arg) -> list:
        self.arguments.append("--%s" % arg)
        return self.arguments

    @staticmethod
    def setup(template_path: Optional[str] = None,
              bibliography_path: Optional[str] = None,
              csl_path: Optional[str] = None,
              citation_abbreviations_path: Optional[str] = None) -> 'Document':
        doc = Document()
        if template_path:
            doc.template(template_path)
        if bibliography_path:
            doc.bib(bibliography_path)
        if csl_path:
            doc.csl(csl_path)
        if citation_abbreviations_path:
            doc.abbr(citation_abbreviations_path)
        return doc

    @classmethod
    def _register_formats(cls):
        """Adds format properties."""
        for fmt in cls.OUTPUT_FORMATS:
            clean_fmt = fmt.replace('+', '_')
            setattr(cls, clean_fmt, property(
                (lambda x, fmt=fmt: cls._output(x, fmt)),  # fget
                (lambda x, y, fmt=fmt: cls._input(x, y, fmt))))  # fset

    def _input(self, value, format=None):
        self._content = value
        self._format = format

    def _output(self, format):
        subprocess_arguments = [PANDOC_PATH, '--from=%s' % self._format, '--to=%s' % format]
        subprocess_arguments.extend(self.arguments)

        p = subprocess.Popen(
            subprocess_arguments,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE
        )
        return p.communicate(self._content)[0]

    def to_file(self, output_filename):
        '''Handles pdf and epub format.
        Inpute: output_filename should have the proper extension.
        Output: The name of the file created, or an IOError if failed'''
        temp_file = NamedTemporaryFile(mode="w", suffix=".md", delete=False)
        temp_file.write(self._content)
        temp_file.close()

        subprocess_arguments = [PANDOC_PATH, temp_file.name, '-o %s' % output_filename]
        subprocess_arguments.extend(self.arguments)
        cmd = " ".join(subprocess_arguments)

        fin = os.popen(cmd)
        msg = fin.read()
        fin.close()
        if msg:
            logger.info("Pandoc message: {}", format(msg))

        os.remove(temp_file.name)

        if exists(output_filename):
            return output_filename
        else:
            raise IOError("Failed creating file: %s" % output_filename)
