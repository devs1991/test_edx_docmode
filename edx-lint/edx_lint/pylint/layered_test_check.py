"""Pylint plugin: test classes derived from test classes."""

import astroid

from pylint.checkers import BaseChecker, utils
from pylint.interfaces import IAstroidChecker

from .common import BASE_ID


def register_checkers(linter):
    """Register checkers."""
    linter.register_checker(LayeredTestClassChecker(linter))


class LayeredTestClassChecker(BaseChecker):
    """Pylint checker for tests inheriting test methods from other tests."""

    __implements__ = (IAstroidChecker,)

    name = 'layered-test-class-checker'

    MESSAGE_ID = "test-inherits-tests"
    msgs = {
        'E%d03' % BASE_ID: (
            "test class %s inherits tests from %s",
            MESSAGE_ID,
            "Used when a test class inherits test methods from another test "
            "class, meaning the inherited tests will run more than once.",
        ),
    }

    @utils.check_messages(MESSAGE_ID)
    def is_test_case_class(self, node):
        """Is this node a test class?

        To be a test class, it has to derive from unittest.TestCase, and not
        have __test__ defined as False.

        """
        if not node.is_subtype_of('unittest.case.TestCase'):
            return False

        dunder_test = node.locals.get("__test__")
        if dunder_test:
            if isinstance(dunder_test[0], astroid.AssName):
                value = list(dunder_test[0].assigned_stmts())
                if len(value) == 1 and isinstance(value[0], astroid.Const):
                    return value[0].value

        return True

    def visit_class(self, node):
        """Check each class."""
        if not self.is_test_case_class(node):
            return

        for anc in node.ancestors():
            if not self.is_test_case_class(anc):
                continue
            for meth in anc.mymethods():
                if meth.name.startswith("test_"):
                    self.add_message(self.MESSAGE_ID, args=(node.name, anc.name), node=node)
                    # No need to belabor the point.
                    return
