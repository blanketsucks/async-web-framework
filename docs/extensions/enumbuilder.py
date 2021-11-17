from enum import IntEnum
from typing import Any, Optional, Type

from docutils.statemachine import StringList

from sphinx.application import Sphinx
from sphinx.ext.autodoc import ClassDocumenter, bool_option

# def get_reference(obj: Enum):
#     value = obj.value
#     cls = value.__class__.__name__

#     return f':class:`{cls}`'

# class EnumDocumenter(ClassDocumenter):
#     objtype = 'enum'
#     directivetype = 'class'
#     priority = 10 + ClassDocumenter.priority
#     option_spec = dict(ClassDocumenter.option_spec)
#     option_spec['hex'] = bool_option
#     option_spec['show-docs'] = bool_option
#     option_spec['show-values'] = bool_option

#     @classmethod
#     def can_document_member(cls,
#                             member: Any, membername: str,
#                             isattr: bool, parent: Any) -> bool:
        
#         return isinstance(member, Enum)

#     def add_directive_header(self, sig: str) -> None:
#         super().add_directive_header(sig)
#         self.add_line('   :final:', self.get_sourcename())

#     def add_empty_line(self) -> None:
#         source = self.get_sourcename()
#         self.add_line('', source)

#     def add_content(self,
#                     more_content: Optional[StringList],
#                     no_docstring: bool = False
#                     ) -> None:
#         super().add_content(more_content, no_docstring)
#         source = self.get_sourcename()

#         use_hex = self.options.hex
#         show_doc = self.options.show_docs
#         show_value = self.options.show_values

#         obj: Type[Enum] = self.object
#         self.add_empty_line()

#         for enum in obj:
#             name = enum.name
#             value = enum.value

#             if use_hex:
#                 value = hex(value)

#             ref = get_reference(enum)

#             line = f"**{name}** ({ref})"
#             if show_value and show_doc:
#                 line += f": {value}"

#                 self.add_line(line, source)
#                 self.add_line(f'    {enum.__doc__}', source)
                
#                 self.add_empty_line()

#                 continue
            
#             if show_doc:
#                 line += f': {enum.__doc__}'
#             elif show_value:
#                 line += f': {value}'
#             else:
#                 line = f'- {line}'


#             self.add_line(
#                 line=line, 
#                 source=source
#             )
#             self.add_empty_line()

class IntEnumDocumenter(ClassDocumenter):
    objtype = 'enum'
    directivetype = 'class'
    priority = 10 + ClassDocumenter.priority
    option_spec = dict(ClassDocumenter.option_spec)
    option_spec['hex'] = bool_option

    @classmethod
    def can_document_member(cls,
                            member: Any, membername: str,
                            isattr: bool, parent: Any) -> bool:
        return isinstance(member, IntEnum)

    def add_directive_header(self, sig: str) -> None:
        super().add_directive_header(sig)
        self.add_line('   :final:', self.get_sourcename())

    def add_content(self,
                    more_content: Optional[StringList],
                    no_docstring: bool = False
                    ) -> None:

        super().add_content(more_content, no_docstring)

        source_name = self.get_sourcename()
        enum_object: Type[IntEnum] = self.object
        use_hex = self.options.hex
        self.add_line('', source_name)

        for enum_value in enum_object:
            the_value_name = enum_value.name
            the_value_value = enum_value.value
            if use_hex:
                the_value_value = hex(the_value_value)

            self.add_line(
                f"**{the_value_name}**: {the_value_value}", source_name)
            self.add_line('', source_name)

def setup(app: Sphinx) -> None:
    app.setup_extension('sphinx.ext.autodoc')  # Require autodoc extension
    app.add_autodocumenter(IntEnumDocumenter)