from neomodel import (
    StructuredNode,
    StringProperty,
    IntegerProperty,
    ArrayProperty,
    RelationshipTo,
    RelationshipFrom,
)

class BaseNodeMixin:
    name = StringProperty(required=True, index=True)
    lineno = IntegerProperty(required=True)
    code = StringProperty(required=True)
    parameters = ArrayProperty(StringProperty(), default=[])
    code_embedding = ArrayProperty(default=[])
    summary = StringProperty(required=True)
    summary_embedding = ArrayProperty(default=[])
    parent_source_identifier = StringProperty()
    children_source_identifiers = ArrayProperty(StringProperty(), default=[])

    # Relationships (shared across all node types)
    parent = RelationshipFrom('BaseNode', 'PARENT')
    children = RelationshipTo('BaseNode', 'CHILD')


# Node Types
class FileNode(StructuredNode, BaseNodeMixin):
    type = StringProperty(default="file")


class ClassNode(StructuredNode, BaseNodeMixin):
    type = StringProperty(default="class")


class FunctionNode(StructuredNode, BaseNodeMixin):
    type = StringProperty(default="function")

class RepositoryNode(StructuredNode):
    name = StringProperty(required=True, unique_index=True)
    type = StringProperty(default="Code repository")
    children = RelationshipTo('BaseNode', 'CHILD')



# For relationship references
BaseNode = StructuredNode  # Alias to use in RelationshipTo/From declarations
