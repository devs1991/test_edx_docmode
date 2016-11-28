"""Test main for edx-lint."""

import os
import unittest

from logilab.common import testlib


def load_tests(loader, tests, pattern):
    # Have to import this in the function, because the module does
    # initialization on import! ugh.
    from pylint.testutils import make_tests, LintTestUsingFile, cb_test_gen, linter

    # Load our plugin, and disable messages we don't want noising up our tests.
    linter.load_plugin_modules(['edx_lint.pylint'])
    linter.disable("missing-module-attribute")

    here = os.path.dirname(os.path.abspath(__file__))

    tests = make_tests(
        input_dir=os.path.join(here, 'input'),
        msg_dir=os.path.join(here, 'messages'),
        filter_rgx=None,
        callbacks=[cb_test_gen(LintTestUsingFile)],
    )

    cls = testlib.TestSuite
    return cls(unittest.makeSuite(test, suiteClass=cls) for test in tests)
