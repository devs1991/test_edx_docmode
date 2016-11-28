"""
Unit tests for user_management management commands.
"""
import itertools
import sys

import ddt
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command, CommandError
from django.test import TestCase

TEST_EMAIL = 'test@example.com'
TEST_GROUP = 'test-group'
TEST_USERNAME = 'test-user'
TEST_DATA = (
    {},
    {
        TEST_GROUP: ['add_group', 'change_group', 'change_group'],
    },
    {
        'other-group': ['add_group', 'change_group', 'change_group'],
    },
)


@ddt.ddt
class TestManageGroupCommand(TestCase):
    """
    Tests the `manage_group` command.
    """

    def set_group_permissions(self, group_permissions):
        """
        Sets up a before-state for groups and permissions in tests, which
        can be checked afterward to ensure that a failed atomic
        operation has not had any side effects.
        """
        content_type = ContentType.objects.get_for_model(Group)
        for group_name, permission_codenames in group_permissions.items():
            group = Group.objects.create(name=group_name)
            for codename in permission_codenames:
                group.permissions.add(
                    Permission.objects.get(content_type=content_type, codename=codename)  # pylint: disable=no-member
                )

    def check_group_permissions(self, group_permissions):
        """
        Checks that the current state of the database matches the specified groups and
        permissions.
        """
        self.check_groups(group_permissions.keys())
        for group_name, permission_codenames in group_permissions.items():
            self.check_permissions(group_name, permission_codenames)

    def check_groups(self, group_names):
        """
        DRY helper.
        """
        self.assertEqual(set(group_names), {g.name for g in Group.objects.all()})  # pylint: disable=no-member

    def check_permissions(self, group_name, permission_codenames):
        """
        DRY helper.
        """
        self.assertEqual(
            set(permission_codenames),
            {p.codename for p in Group.objects.get(name=group_name).permissions.all()}  # pylint: disable=no-member
        )

    @ddt.data(
        *(
            (data, args, exception)
            for data in TEST_DATA
            for args, exception in (
                ((), 'too few arguments' if sys.version_info.major == 2 else 'required: group_name'),  # no group name
                (('x' * 81,), 'invalid group name'),  # invalid group name
                ((TEST_GROUP, 'some-other-group'), 'unrecognized arguments'),  # multiple arguments
                ((TEST_GROUP, '--some-option', 'dummy'), 'unrecognized arguments')  # unexpected option name
            )
        )
    )
    @ddt.unpack
    def test_invalid_input(self, initial_group_permissions, command_args, exception_message):
        """
        Ensures that invalid inputs result in errors with relevant output,
        and that no persistent state is changed.
        """
        self.set_group_permissions(initial_group_permissions)

        with self.assertRaises(CommandError) as exc_context:
            call_command('manage_group', *command_args)
        self.assertIn(exception_message, str(exc_context.exception).lower())
        self.check_group_permissions(initial_group_permissions)

    @ddt.data(*TEST_DATA)
    def test_invalid_permission(self, initial_group_permissions):
        """
        Ensures that a permission that cannot be parsed or resolved results in
        and error and that no persistent state is changed.
        """
        self.set_group_permissions(initial_group_permissions)

        # not parseable
        with self.assertRaises(CommandError) as exc_context:
            call_command('manage_group', TEST_GROUP, '--permissions', 'fail')
        self.assertIn('invalid permission option', str(exc_context.exception).lower())
        self.check_group_permissions(initial_group_permissions)

        # not parseable
        with self.assertRaises(CommandError) as exc_context:
            call_command('manage_group', TEST_GROUP, '--permissions', 'f:a:i:l')
        self.assertIn('invalid permission option', str(exc_context.exception).lower())
        self.check_group_permissions(initial_group_permissions)

        # invalid app label
        with self.assertRaises(CommandError) as exc_context:
            call_command('manage_group', TEST_GROUP, '--permissions', 'nonexistent-label:dummy-model:dummy-perm')
        self.assertIn('no installed app', str(exc_context.exception).lower())
        self.assertIn('nonexistent-label', str(exc_context.exception).lower())
        self.check_group_permissions(initial_group_permissions)

        # invalid model name
        with self.assertRaises(CommandError) as exc_context:
            call_command('manage_group', TEST_GROUP, '--permissions', 'auth:nonexistent-model:dummy-perm')
        self.assertIn('nonexistent-model', str(exc_context.exception).lower())
        self.check_group_permissions(initial_group_permissions)

        # invalid model name
        with self.assertRaises(CommandError) as exc_context:
            call_command('manage_group', TEST_GROUP, '--permissions', 'auth:Group:nonexistent-perm')
        self.assertIn('invalid permission codename', str(exc_context.exception).lower())
        self.assertIn('nonexistent-perm', str(exc_context.exception).lower())
        self.check_group_permissions(initial_group_permissions)

    def test_group(self):
        """
        Ensures that groups are created if they don't exist and reused if they do.
        """
        self.check_groups([])
        call_command('manage_group', TEST_GROUP)
        self.check_groups([TEST_GROUP])

        # check idempotency
        call_command('manage_group', TEST_GROUP)
        self.check_groups([TEST_GROUP])

    def test_group_remove(self):
        """
        Ensures that groups are removed if they exist and we exit cleanly otherwise.
        """
        self.set_group_permissions({TEST_GROUP: ['add_group']})
        self.check_groups([TEST_GROUP])
        call_command('manage_group', TEST_GROUP, '--remove')
        self.check_groups([])

        # check idempotency
        call_command('manage_group', TEST_GROUP, '--remove')
        self.check_groups([])

    def test_permissions(self):
        """
        Ensures that permissions are set on the group as specified.
        """
        self.check_groups([])
        call_command('manage_group', TEST_GROUP, '--permissions', 'auth:Group:add_group')
        self.check_groups([TEST_GROUP])
        self.check_permissions(TEST_GROUP, ['add_group'])

        # check idempotency
        call_command('manage_group', TEST_GROUP, '--permissions', 'auth:Group:add_group')
        self.check_groups([TEST_GROUP])
        self.check_permissions(TEST_GROUP, ['add_group'])

        # check adding a permission
        call_command('manage_group', TEST_GROUP, '--permissions', 'auth:Group:add_group', 'auth:Group:change_group')
        self.check_groups([TEST_GROUP])
        self.check_permissions(TEST_GROUP, ['add_group', 'change_group'])

        # check removing a permission
        call_command('manage_group', TEST_GROUP, '--permissions', 'auth:Group:change_group')
        self.check_groups([TEST_GROUP])
        self.check_permissions(TEST_GROUP, ['change_group'])

        # check removing all permissions
        call_command('manage_group', TEST_GROUP)
        self.check_groups([TEST_GROUP])
        self.check_permissions(TEST_GROUP, [])


@ddt.ddt
class TestManageUserCommand(TestCase):
    """
    Tests the `manage_user` command.
    """

    def test_user(self):
        """
        Ensures that users are created if they don't exist and reused if they do.
        """
        # pylint: disable=no-member
        self.assertEqual([], list(User.objects.all()))
        call_command('manage_user', TEST_USERNAME, TEST_EMAIL)
        self.assertEqual([(TEST_USERNAME, TEST_EMAIL)], [(u.username, u.email) for u in User.objects.all()])

        # check idempotency
        call_command('manage_user', TEST_USERNAME, TEST_EMAIL)
        self.assertEqual([(TEST_USERNAME, TEST_EMAIL)], [(u.username, u.email) for u in User.objects.all()])

    def test_remove(self):
        """
        Ensures that users are removed if they exist and exit cleanly otherwise.
        """
        # pylint: disable=no-member
        User.objects.create(username=TEST_USERNAME, email=TEST_EMAIL)
        self.assertEqual([(TEST_USERNAME, TEST_EMAIL)], [(u.username, u.email) for u in User.objects.all()])
        call_command('manage_user', TEST_USERNAME, TEST_EMAIL, '--remove')
        self.assertEqual([], list(User.objects.all()))

        # check idempotency
        call_command('manage_user', TEST_USERNAME, TEST_EMAIL, '--remove')
        self.assertEqual([], list(User.objects.all()))

    def test_wrong_email(self):
        """
        Ensure that the operation is aborted if the username matches an
        existing user account but the supplied email doesn't match.
        """
        # pylint: disable=no-member
        User.objects.create(username=TEST_USERNAME, email=TEST_EMAIL)
        with self.assertRaises(CommandError) as exc_context:
            call_command('manage_user', TEST_USERNAME, 'other@example.com')
        self.assertIn('email addresses do not match', str(exc_context.exception).lower())
        self.assertEqual([(TEST_USERNAME, TEST_EMAIL)], [(u.username, u.email) for u in User.objects.all()])

        # check that removal uses the same check
        with self.assertRaises(CommandError) as exc_context:
            call_command('manage_user', TEST_USERNAME, 'other@example.com', '--remove')
        self.assertIn('email addresses do not match', str(exc_context.exception).lower())
        self.assertEqual([(TEST_USERNAME, TEST_EMAIL)], [(u.username, u.email) for u in User.objects.all()])

    @ddt.data(*itertools.product([(True, True), (True, False), (False, True), (False, False)], repeat=2))
    @ddt.unpack
    def test_bits(self, initial_bits, expected_bits):
        """
        Ensure that the 'staff' and 'superuser' bits are set according to the
        presence / absence of the associated command options, regardless of
        any previous state.
        """
        initial_staff, initial_super = initial_bits
        User.objects.create(
            username=TEST_USERNAME,
            email=TEST_EMAIL,
            is_staff=initial_staff,
            is_superuser=initial_super
        )

        expected_staff, expected_super = expected_bits
        args = [opt for bit, opt in ((expected_staff, '--staff'), (expected_super, '--superuser')) if bit]
        call_command('manage_user', TEST_USERNAME, TEST_EMAIL, *args)
        user = User.objects.all().first()  # pylint: disable=no-member
        self.assertEqual(user.is_staff, expected_staff)
        self.assertEqual(user.is_superuser, expected_super)

    @ddt.data(*itertools.product(('', 'a', 'ab', 'abc'), repeat=2))
    @ddt.unpack
    def test_groups(self, initial_groups, expected_groups):
        """
        Ensures groups assignments are created and deleted idempotently.
        """
        groups = {}
        for group_name in 'abc':
            groups[group_name] = Group.objects.create(name=group_name)

        user = User.objects.create(username=TEST_USERNAME, email=TEST_EMAIL)
        for group_name in initial_groups:
            user.groups.add(groups[group_name])

        call_command('manage_user', TEST_USERNAME, TEST_EMAIL, '-g', *expected_groups)
        actual_groups = [group.name for group in user.groups.all()]
        self.assertEqual(actual_groups, list(expected_groups))

    def test_nonexistent_group(self):
        """
        Ensures the command does not fail if specified groups cannot be found.
        """
        user = User.objects.create(username=TEST_USERNAME, email=TEST_EMAIL)
        groups = {}
        for group_name in 'abc':
            groups[group_name] = Group.objects.create(name=group_name)
            user.groups.add(groups[group_name])

        call_command('manage_user', TEST_USERNAME, TEST_EMAIL, '-g', 'b', 'c', 'd')
        actual_groups = [group.name for group in user.groups.all()]
        self.assertEqual(actual_groups, ['b', 'c'])
