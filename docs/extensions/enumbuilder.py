from enum import Enum
from typing import Any, Optional, Type

from docutils.statemachine import StringList

from sphinx.application import Sphinx
from sphinx.ext.autodoc import ClassDocumenter, bool_option

def get_reference(obj: Enum):
    value = obj.value
    cls = value.__class__.__name__

    return f':class:`{cls}`'

class EnumDocumenter(ClassDocumenter):
    objtype = 'enum'
    directivetype = 'class'
    priority = 10 + ClassDocumenter.priority
    option_spec = dict(ClassDocumenter.option_spec)
    option_spec['hex'] = bool_option

    @classmethod
    def can_document_member(cls,
                            member: Any, membername: str,
                            isattr: bool, parent: Any) -> bool:
        return isinstance(member, Enum)

    def add_directive_header(self, sig: str) -> None:
        super().add_directive_header(sig)
        self.add_line('   :final:', self.get_sourcename())

    def add_content(self,
                    more_content: Optional[StringList],
                    no_docstring: bool = False
                    ) -> None:
        
        super().add_content(more_content, no_docstring)

        source = self.get_sourcename()
        use_hex = self.options.hex

        obj: Type[Enum] = self.object
        self.add_line('', source)

        for enum in obj:
            name = enum.name
            value = enum.value

            if use_hex:
                value = hex(value)

            ref = get_reference(enum)
            self.add_line(
                line=f"**{name}** ({ref}) : {value}", 
                source=source
            )
            
            self.add_line('', source)

def setup(app: Sphinx) -> None:
    app.setup_extension('sphinx.ext.autodoc')  # Require autodoc extension
    app.add_autodocumenter(EnumDocumenter)