import logging
import pathlib
from pathlib import Path
from typing import Union, IO, Any

import pypandoc

logger = logging.getLogger('asyncio')


class PandocService(object):
    """
    Base class for converting provided HTML to a doc or docx
    """
    __FORMATS = pypandoc.get_pandoc_formats()

    INPUT_FORMATS = frozenset(__FORMATS[0])

    OUTPUT_FORMATS = frozenset(['pdf'] + __FORMATS[1])

    FORMATS = list(INPUT_FORMATS | OUTPUT_FORMATS)

    def __init__(self, **kwargs: dict):
        self.service = self.get_service()
        self._register_formats()
        self._source = None
        self._out_file = None
        self._from_format = None
        self._extra_args(**kwargs)

    def _extra_args(self, **kwargs):
        self.extra_args = []
        if 'template_path' in kwargs:
            self.template(kwargs['template_path'])

        if 'extra_args' in kwargs:
            for k, v in kwargs['extra_args'].items():
                if v is not None:
                    self.add_argument(f"{k}={v}")

    def template(self, template_path):
        p = Path(template_path)
        if not p.exists():
            raise IOError(f"Template file not found: {template_path}")
        self.add_argument(f"template={p.resolve()}")


    @classmethod
    def _register_formats(cls) -> None:
        """Adds format properties."""
        for fmt in cls.FORMATS:
            clean_fmt = fmt.replace('+', '_')
            setattr(cls, clean_fmt, property(
                (lambda x, fmt=fmt: cls._output(x, fmt)),  # fget
                (lambda x, y, fmt=fmt: cls._input(x, y, fmt))))  # fset

    def _input(self, source: IO[Any], from_format=None) -> None:
        if from_format not in self.INPUT_FORMATS:
            raise AttributeError(f"Not a valid input format: '{from_format}'")
        self._source = source
        self._form_format = from_format

    def _output(self, to_format, **kwargs) -> Union[str, pathlib.Path]:
        if to_format not in self.OUTPUT_FORMATS:
            raise AttributeError(f"Not a valid output format: '{to_format}'")

        self.add_argument('standalone')

        kwargs = {
            'source_file': self._source,
            'to': to_format,
            'format': getattr(self, '_form_format', None),
            'extra_args': self.extra_args,
            'encoding': 'utf-8',
            'filters': kwargs.get('filters', None),
        }

        if self._out_file:
            kwargs["outputfile"] = self._out_file
        return self.service.convert_file(**kwargs)



    @staticmethod
    def get_service() -> pypandoc:
        return pypandoc

    def add_argument(self, arg) -> list:
        self.extra_args.append(f"--{arg}")
        return self.extra_args
