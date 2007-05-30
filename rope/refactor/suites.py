from rope.base import ast


def find_visible(ast, lines):
    """Return the line which is visible from all `lines`"""
    root = ast_suite_tree(ast)
    return find_visible_for_suite(root, lines)


def find_visible_for_suite(root, lines):
    line1 = lines[0]
    if len(lines) == 1:
        return line1
    suite1 = root.find_suite(lines[0])
    line2 = find_visible_for_suite(root, lines[1:])
    suite2 = root.find_suite(line2)
    while suite1 != suite2 and suite1.parent != None:
        if suite1._get_level() < suite2._get_level():
            suite2 = suite2.parent
        elif suite1._get_level() > suite2._get_level():
            suite1 = suite1.parent
        else:
            suite1 = suite1.parent
            suite2 = suite2.parent
    return min(suite1.local_start(), suite2.local_start())


def source_suite_tree(source):
    return ast_suite_tree(ast.parse(source))


def ast_suite_tree(ast):
    if hasattr(ast, 'lineno'):
        lineno = ast.lineno
    else:
        lineno = 1
    return Suite(ast.body, lineno)


def _find_visible_suite(root, lines):
    suite1 = root.find_suite(lines[0])
    if len(lines) == 1:
        return suite1
    suite2 = _find_visible_suite(root, lines[1:])
    while suite1 != suite2 and suite1.parent != None:
        if suite1._get_level() < suite2._get_level():
            suite2 = suite2.parent
        elif suite1._get_level() > suite2._get_level():
            suite1 = suite1.parent
        else:
            suite1 = suite1.parent
            suite2 = suite2.parent
    return suite1


class Suite(object):

    def __init__(self, child_nodes, lineno, parent=None):
        self.parent = parent
        self.lineno = lineno
        self.child_nodes = child_nodes
        self._children = None

    def get_start(self):
        return self.lineno

    def get_children(self):
        if self._children is None:
            walker = _SuiteWalker(self)
            for child in self.child_nodes:
                ast.walk(child, walker)
            self._children = walker.suites
        return self._children

    def local_start(self):
        return self.child_nodes[0].lineno

    def local_end(self):
        end = self.child_nodes[-1].lineno
        if self.get_children():
            end = max(end, self.get_children()[-1].local_end())
        return end

    def find_suite(self, line):
        for child in self.get_children():
            if child.local_start() <= line <= child.local_end():
                return child.find_suite(line)
        return self

    def _get_level(self):
        if self.parent is None:
            return 0
        return self.parent._get_level() + 1


class _SuiteWalker(object):

    def __init__(self, suite):
        self.suite = suite
        self.suites = []

    def _If(self, node):
        self._add_if_like_node(node)

    def _For(self, node):
        self._add_if_like_node(node)

    def _While(self, node):
        self._add_if_like_node(node)

    def _With(self, node):
        self.suites.append(Suite(node.body, node.lineno, self.suite))

    def _TryFinally(self, node):
        if len(node.finalbody) == 1 and \
           isinstance(node.body[0], ast.TryExcept):
            self._TryExcept(node.body[0])
        else:
            self.suites.append(Suite(node.body, node.lineno, self.suite))
        self.suites.append(Suite(node.finalbody, node.lineno, self.suite))

    def _TryExcept(self, node):
        self.suites.append(Suite(node.body, node.lineno, self.suite))
        for handler in node.handlers:
            self.suites.append(Suite(handler.body, node.lineno, self.suite))
        if node.orelse:
            self.suites.append(Suite(node.orelse, node.lineno, self.suite))

    def _add_if_like_node(self, node):
        self.suites.append(Suite(node.body, node.lineno, self.suite))
        if node.orelse:
            self.suites.append(Suite(node.orelse, node.lineno, self.suite))

    def _FunctionDef(self, node):
        pass

    def _ClassDef(self, node):
        pass
