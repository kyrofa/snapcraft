# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright (C) 2015-2017 Canonical Ltd
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import collections
import contextlib
import copy
import io
import inspect
import json
import os
import shutil
import string
import subprocess
import sys
import threading
import urllib.parse
import uuid
from functools import partial
from types import ModuleType
from unittest import mock
from subprocess import CalledProcessError

import fixtures
import xdg
import yaml

import snapcraft
from snapcraft.tests import fake_servers
from snapcraft.tests.fake_servers import (
    api,
    search,
    upload
)
from snapcraft.tests.subprocess_utils import (
    call,
    call_with_output,
)


class TempCWD(fixtures.TempDir):

    def setUp(self):
        """Create a temporary directory an cd into it for the test duration."""
        super().setUp()
        current_dir = os.getcwd()
        self.addCleanup(os.chdir, current_dir)
        os.chdir(self.path)


class TempXDG(fixtures.Fixture):
    """Isolate a test from xdg so a private temp config is used."""

    def __init__(self, path):
        super().setUp()
        self.path = path

    def setUp(self):
        super().setUp()
        patcher = mock.patch(
            'xdg.BaseDirectory.xdg_config_home',
            new=os.path.join(self.path, '.config'))
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch(
            'xdg.BaseDirectory.xdg_data_home',
            new=os.path.join(self.path, '.local'))
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch(
            'xdg.BaseDirectory.xdg_cache_home',
            new=os.path.join(self.path, '.cache'))
        patcher.start()
        self.addCleanup(patcher.stop)

        patcher_dirs = mock.patch(
            'xdg.BaseDirectory.xdg_config_dirs',
            new=[xdg.BaseDirectory.xdg_config_home])
        patcher_dirs.start()
        self.addCleanup(patcher_dirs.stop)

        patcher_dirs = mock.patch(
            'xdg.BaseDirectory.xdg_data_dirs',
            new=[xdg.BaseDirectory.xdg_data_home])
        patcher_dirs.start()
        self.addCleanup(patcher_dirs.stop)


class FakeProjectOptions(fixtures.Fixture):

    def __init__(self, **kwargs):
        self._kwargs = dict(
            arch_triplet=kwargs.pop('arch_triplet', 'x86_64-gnu-linux'),
            parts_dir=kwargs.pop('parts_dir', 'parts'),
            stage_dir=kwargs.pop('stage_dir', 'stage'),
            prime_dir=kwargs.pop('prime_dir', 'prime'),
            parallel_build_count=kwargs.pop('parallel_build_count', '1'),
        )
        if kwargs:
            raise NotImplementedError(
                'Handling of {!r} is not implemented'.format(kwargs.keys()))

    def setUp(self):
        super().setUp()

        patcher = mock.patch('snapcraft.ProjectOptions')
        patcher.start()
        self.addCleanup(patcher.stop)

        # Special handling is required as ProjectOptions attributes are
        # handled with the @property decorator.
        project_options_t = type(snapcraft.ProjectOptions.return_value)
        for key in self._kwargs:
            setattr(project_options_t, key, self._kwargs[key])


class SilentSnapProgress(fixtures.Fixture):

    def setUp(self):
        super().setUp()

        patcher = mock.patch('snapcraft.internal.lifecycle.ProgressBar')
        patcher.start()
        self.addCleanup(patcher.stop)


class CleanEnvironment(fixtures.Fixture):

    def setUp(self):
        super().setUp()

        current_environment = copy.deepcopy(os.environ)
        os.environ.clear()

        self.addCleanup(os.environ.update, current_environment)


class _FakeStdout(io.StringIO):
    """A fake stdout using StringIO implementing the missing fileno attrib."""

    def fileno(self):
        return 1


class _FakeStderr(io.StringIO):
    """A fake stderr using StringIO implementing the missing fileno attrib."""

    def fileno(self):
        return 2


class _FakeTerminalSize:

    def __init__(self, columns=80):
        self.columns = columns


class FakeTerminal(fixtures.Fixture):

    def __init__(self, columns=80, isatty=True):
        self.columns = columns
        self.isatty = isatty

    def _setUp(self):
        patcher = mock.patch('shutil.get_terminal_size')
        mock_terminal_size = patcher.start()
        mock_terminal_size.return_value = _FakeTerminalSize(self.columns)
        self.addCleanup(patcher.stop)

        patcher = mock.patch('sys.stdout', new_callable=_FakeStdout)
        self.mock_stdout = patcher.start()
        self.addCleanup(patcher.stop)

        patcher = mock.patch('sys.stderr', new_callable=_FakeStderr)
        self.mock_stderr = patcher.start()
        self.addCleanup(patcher.stop)

        patcher = mock.patch('os.isatty')
        mock_isatty = patcher.start()
        mock_isatty.return_value = self.isatty
        self.addCleanup(patcher.stop)

    def getvalue(self, stderr=False):
        if stderr:
            return self.mock_stderr.getvalue()
        else:
            return self.mock_stdout.getvalue()


class FakePartsWiki(fixtures.Fixture):

    def setUp(self):
        super().setUp()

        self.fake_parts_wiki_fixture = FakePartsWikiRunning()
        self.useFixture(self.fake_parts_wiki_fixture)
        self.useFixture(fixtures.EnvironmentVariable(
            'no_proxy', 'localhost,127.0.0.1'))


class FakePartsWikiWithSlashes(fixtures.Fixture):

    def setUp(self):
        super().setUp()

        self.fake_parts_wiki_with_slashes_fixture = (
            FakePartsWikiWithSlashesRunning())
        self.useFixture(self.fake_parts_wiki_with_slashes_fixture)
        self.useFixture(fixtures.EnvironmentVariable(
            'no_proxy', 'localhost,127.0.0.1'))


class FakePartsWikiOrigin(fixtures.Fixture):

    def setUp(self):
        super().setUp()

        self.fake_parts_wiki_origin_fixture = FakePartsWikiOriginRunning()
        self.useFixture(self.fake_parts_wiki_origin_fixture)
        self.useFixture(fixtures.EnvironmentVariable(
            'no_proxy', 'localhost,127.0.0.1'))


class FakeParts(fixtures.Fixture):

    def setUp(self):
        super().setUp()

        self.fake_parts_server_fixture = FakePartsServerRunning()
        self.useFixture(self.fake_parts_server_fixture)
        self.useFixture(fixtures.EnvironmentVariable(
            'SNAPCRAFT_PARTS_URI',
            urllib.parse.urljoin(
                self.fake_parts_server_fixture.url, 'parts.yaml')))
        self.useFixture(fixtures.EnvironmentVariable(
            'no_proxy', 'localhost,127.0.0.1'))


class FakeStore(fixtures.Fixture):

    def setUp(self):
        super().setUp()
        # In case the variable was not set or it was empty.
        self.useFixture(fixtures.EnvironmentVariable('TEST_STORE', 'fake'))

        self.needs_refresh = False

        self.fake_sso_server_fixture = FakeSSOServerRunning(self)
        self.useFixture(self.fake_sso_server_fixture)
        self.useFixture(fixtures.EnvironmentVariable(
            'UBUNTU_SSO_API_ROOT_URL',
            urllib.parse.urljoin(
                self.fake_sso_server_fixture.url, 'api/v2/')))

        self.useFixture(fixtures.EnvironmentVariable(
            'STORE_RETRIES', '1'))
        self.useFixture(fixtures.EnvironmentVariable(
            'STORE_BACKOFF', '0'))

        self.fake_store_upload_server_fixture = FakeStoreUploadServerRunning()
        self.useFixture(self.fake_store_upload_server_fixture)
        self.useFixture(fixtures.EnvironmentVariable(
            'UBUNTU_STORE_UPLOAD_ROOT_URL',
            self.fake_store_upload_server_fixture.url))

        self.fake_store_api_server_fixture = FakeStoreAPIServerRunning(self)
        self.useFixture(self.fake_store_api_server_fixture)
        self.useFixture(fixtures.EnvironmentVariable(
            'UBUNTU_STORE_API_ROOT_URL',
            urllib.parse.urljoin(
                self.fake_store_api_server_fixture.url, 'dev/api/')))

        self.fake_store_search_server_fixture = FakeStoreSearchServerRunning()
        self.useFixture(self.fake_store_search_server_fixture)
        self.useFixture(fixtures.EnvironmentVariable(
            'UBUNTU_STORE_SEARCH_ROOT_URL',
            self.fake_store_search_server_fixture.url))

        self.useFixture(fixtures.EnvironmentVariable(
            'no_proxy', 'localhost,127.0.0.1'))


class _FakeServerRunning(fixtures.Fixture):

    # To be defined by child fixtures.
    fake_server = None

    def setUp(self):
        super().setUp()
        self._start_fake_server()

    def _start_fake_server(self):
        server_address = ('', 0)
        self.server = self.fake_server(server_address)
        server_thread = threading.Thread(target=self.server.serve_forever)
        server_thread.start()
        self.addCleanup(self._stop_fake_server, server_thread)
        self.url = 'http://localhost:{}/'.format(self.server.server_port)

    def _stop_fake_server(self, thread):
        self.server.shutdown()
        self.server.socket.close()
        thread.join()


class FakePartsWikiOriginRunning(_FakeServerRunning):

    fake_server = fake_servers.FakePartsWikiOriginServer


class FakePartsWikiRunning(_FakeServerRunning):

    fake_server = fake_servers.FakePartsWikiServer


class FakePartsWikiWithSlashesRunning(_FakeServerRunning):

    fake_server = fake_servers.FakePartsWikiWithSlashesServer


class FakePartsServerRunning(_FakeServerRunning):

    fake_server = fake_servers.FakePartsServer


class FakeSSOServerRunning(_FakeServerRunning):

    def __init__(self, fake_store):
        super().__init__()
        self.fake_server = partial(fake_servers.FakeSSOServer, fake_store)


class FakeStoreUploadServerRunning(_FakeServerRunning):

    fake_server = upload.FakeStoreUploadServer


class FakeStoreAPIServerRunning(_FakeServerRunning):

    def __init__(self, fake_store):
        super().__init__()
        self.fake_server = partial(api.FakeStoreAPIServer, fake_store)


class FakeStoreSearchServerRunning(_FakeServerRunning):

    fake_server = search.FakeStoreSearchServer


class StagingStore(fixtures.Fixture):

    def setUp(self):
        super().setUp()
        self.useFixture(fixtures.EnvironmentVariable(
            'UBUNTU_STORE_API_ROOT_URL',
            'https://dashboard.staging.snapcraft.io/dev/api/'))
        self.useFixture(fixtures.EnvironmentVariable(
            'UBUNTU_STORE_UPLOAD_ROOT_URL',
            'https://upload.apps.staging.ubuntu.com/'))
        self.useFixture(fixtures.EnvironmentVariable(
            'UBUNTU_SSO_API_ROOT_URL',
            'https://login.staging.ubuntu.com/api/v2/'))
        self.useFixture(fixtures.EnvironmentVariable(
            'UBUNTU_STORE_SEARCH_ROOT_URL',
            'https://api.staging.snapcraft.io/'))


class TestStore(fixtures.Fixture):

    def setUp(self):
        super().setUp()
        test_store = os.getenv('TEST_STORE') or 'fake'
        if test_store == 'fake':
            self.useFixture(FakeStore())
            self.register_count_limit = 10
            self.reserved_snap_name = 'test-reserved-snap-name'
            self.already_owned_snap_name = 'test-already-owned-snap-name'
        elif test_store == 'staging':
            self.useFixture(StagingStore())
            self.register_count_limit = 100
            self.reserved_snap_name = 'bash'
        elif test_store == 'production':
            # Use the default server URLs
            self.register_count_limit = 10
            self.reserved_snap_name = 'bash'
        else:
            raise ValueError(
                'Unknown test store option: {}'.format(test_store))

        self.user_email = (
            os.getenv('TEST_USER_EMAIL') or
            'u1test+snapcraft@canonical.com')
        self.test_track_snap = os.getenv(
            'TEST_SNAP_WITH_TRACKS', 'test-snapcraft-tracks')
        if test_store == 'fake':
            self.user_password = 'test correct password'
        else:
            self.user_password = os.getenv('TEST_USER_PASSWORD')


class FakePlugin(fixtures.Fixture):
    '''Dynamically generate a new module containing the provided plugin'''

    def __init__(self, plugin_name, plugin_class):
        super().__init__()
        self._import_name = 'snapcraft.plugins.{}'.format(
            plugin_name.replace('-', '_'))
        self._plugin_class = plugin_class

    def _setUp(self):
        plugin_module = ModuleType(self._import_name)
        setattr(plugin_module, self._plugin_class.__name__, self._plugin_class)
        sys.modules[self._import_name] = plugin_module
        self.addCleanup(self._remove_module)

    def _remove_module(self):
        del sys.modules[self._import_name]


class FakeFilesystem(fixtures.Fixture):
    '''Keep track of created and removed directories'''

    def __init__(self):
        self.dirs = []

    def _setUp(self):
        patcher = mock.patch('os.makedirs')
        self.makedirs_mock = patcher.start()
        self.makedirs_mock.side_effect = self.makedirs_side_effect()
        self.addCleanup(patcher.stop)

        patcher = mock.patch('tempfile.mkdtemp')
        self.mkdtemp_mock = patcher.start()
        self.mkdtemp_mock.side_effect = self.mkdtemp_side_effect()
        self.addCleanup(patcher.stop)

        patcher = mock.patch('snapcraft.internal.lxd.open', mock.mock_open())
        self.open_mock = patcher.start()
        self.open_mock_default_side_effect = self.open_mock.side_effect
        self.open_mock.side_effect = self.open_side_effect()
        self.addCleanup(patcher.stop)

        patcher = mock.patch('shutil.copyfile')
        self.copyfile_mock = patcher.start()
        self.addCleanup(patcher.stop)

        patcher = mock.patch('shutil.rmtree')
        self.rmtree_mock = patcher.start()
        self.rmtree_mock.side_effect = self.rmtree_side_effect()
        self.addCleanup(patcher.stop)

    def makedirs_side_effect(self):
        def call_effect(*args, **kwargs):
            if args[0] not in self.dirs:
                self.dirs.append(args[0])
        return call_effect

    def mkdtemp_side_effect(self):
        def call_effect(*args, **kwargs):
            dir = os.path.join(kwargs['dir'], '{}{}{}'.format(
                kwargs.get('prefix', ''),
                uuid.uuid4(),
                kwargs.get('suffix', '')))
            self.dirs.append(dir)
            return dir
        return call_effect

    def open_side_effect(self):
        def call_effect(*args, **kwargs):
            for dir in self.dirs:
                if args[0].startswith(dir):
                    return self.open_mock_default_side_effect()
            raise FileNotFoundError(
                '[Errno 2] No such file or directory: {}'.format(args[0]))
        return call_effect

    def rmtree_side_effect(self):
        def call_effect(*args, **kwargs):
            if args[0] not in self.dirs:
                raise FileNotFoundError(
                    '[Errno 2] No such file or directory: {}'.format(args[0]))
            self.dirs.remove(args[0])
        return call_effect


class FakeLXD(fixtures.Fixture):
    '''...'''

    def __init__(self):
        self.status = None
        self.files = []
        self.kernel_arch = 'x86_64'
        self.devices = '{}'

    def _setUp(self):
        patcher = mock.patch('snapcraft.internal.lxd.check_call')
        self.check_call_mock = patcher.start()
        self.check_call_mock.side_effect = self.check_output_side_effect()
        self.addCleanup(patcher.stop)

        patcher = mock.patch('snapcraft.internal.lxd.check_output')
        self.check_output_mock = patcher.start()
        self.check_output_mock.side_effect = self.check_output_side_effect()
        self.addCleanup(patcher.stop)

        patcher = mock.patch('snapcraft.internal.lxd.Popen')
        self.popen_mock = patcher.start()
        self.popen_mock.side_effect = self.check_output_side_effect()
        self.addCleanup(patcher.stop)

        patcher = mock.patch('snapcraft.internal.lxd.sleep', lambda _: None)
        patcher.start()
        self.addCleanup(patcher.stop)

        patcher = mock.patch('platform.machine')
        self.machine_mock = patcher.start()
        self.machine_mock.return_value = 'x86_64'
        self.addCleanup(patcher.stop)
        patcher = mock.patch('platform.architecture')
        self.architecture_mock = patcher.start()
        self.architecture_mock.return_value = ('64bit', 'ELF')
        self.addCleanup(patcher.stop)

    def check_output_side_effect(self):
        def call_effect(*args, **kwargs):
            if args[0] == ['lxc', 'remote', 'get-default']:
                return 'local'.encode('utf-8')
            elif args[0][:2] == ['lxc', 'info']:
                return '''
                    environment:
                      kernel_architecture: {}
                    '''.format(self.kernel_arch).encode('utf-8')
            elif args[0][:3] == ['lxc', 'list', '--format=json']:
                if self.status and args[0][3] == self.name:
                    return string.Template('''
                        [{"name": "$NAME",
                          "status": "$STATUS",
                          "devices": $DEVICES}]
                        ''').substitute({
                            # Container name without remote prefix
                            'NAME': self.name.split(':')[-1],
                            'STATUS': self.status,
                            'DEVICES': self.devices,
                            }).encode('utf-8')
                return '[]'.encode('utf-8')
            elif (args[0][0] == 'lxc' and
                  args[0][1] in ['init', 'start', 'launch', 'stop']):
                return self._lxc_create_start_stop(args)
            elif args[0][:2] == ['lxc', 'exec']:
                return self._lxc_exec(args)
            elif '/usr/lib/sftp-server' in args[0]:
                return self._popen(args[0])
            else:
                return ''.encode('utf-8')
        return call_effect

    def _lxc_create_start_stop(self, args):
        if args[0][1] == 'init':
            self.name = args[0][3]
            self.status = 'Stopped'
        elif args[0][1] == 'launch':
            self.name = args[0][4]
            self.status = 'Running'
        elif args[0][1] == 'start' and self.name == args[0][2]:
            self.status = 'Running'
        elif args[0][1] == 'stop' and not self.status:
            # error: not found
            raise CalledProcessError(returncode=1, cmd=args[0])

    def _lxc_exec(self, args):
        if self.status and args[0][2] == self.name:
            cmd = args[0][4]
            if cmd == 'ls':
                return ' '.join(self.files).encode('utf-8')
            elif cmd == 'sshfs':
                self.files = ['foo', 'bar']
                return self._popen(args[0])

    def _popen(self, args):
        class Popen:
            def __init__(self, args):
                self.args = args

            def terminate(self):
                pass
        return Popen(args)


class FakeSnapd(fixtures.Fixture):
    '''...'''

    def __init__(self):
        self.snaps = {
            'core': {'confinement': 'strict',
                     'id': '2kkitQurgOkL3foImG4wDwn9CIANuHlt',
                     'revision': '123'},
            'snapcraft': {'confinement': 'classic',
                          'id': '3lljuRvshPlM4gpJnH5xExo0DJBOvImu',
                          'revision': '345'},
        }

    def _setUp(self):
        patcher = mock.patch('requests_unixsocket.Session.request')
        self.session_request_mock = patcher.start()
        self.session_request_mock.side_effect = self.request_side_effect()
        self.addCleanup(patcher.stop)

    def request_side_effect(self):
        def request_effect(*args, **kwargs):
            if args[0] == 'GET' and '/v2/snaps/' in args[1]:
                class Session:
                    def __init__(self, name, snaps):
                        self._name = name
                        self._snaps = snaps

                    def json(self):
                        if self._name not in self._snaps:
                            return {'status': 'Not Found',
                                    'result': {'message': 'not found'},
                                    'status-code': 404,
                                    'type': 'error'}
                        return {'status': 'OK',
                                'type': 'sync',
                                'result': self._snaps[self._name]}
                name = args[1].split('/')[-1]
                return Session(name, self.snaps)
        return request_effect


class GitRepo(fixtures.Fixture):
    '''Create a git repo in the current directory'''

    def setUp(self):
        super().setUp()
        name = 'git-source'  # must match what the tests expect

        def _add_and_commit_file(path, filename, contents=None, message=None):
            if not contents:
                contents = filename
            if not message:
                message = filename

            with open(os.path.join(path, filename), 'w') as fp:
                fp.write(contents)

            call(['git', '-C', name, 'add', filename])
            call(['git', '-C', name, 'commit', '-am', message])

        os.makedirs(name)
        call(['git', '-C', name, 'init'])
        call(['git', '-C', name, 'config',
              'user.name', 'Test User'])
        call(['git', '-C', name, 'config',
              'user.email', 'testuser@example.com'])

        _add_and_commit_file(name, 'testing')
        call(['git', '-C', name, 'branch', 'test-branch'])

        _add_and_commit_file(name, 'testing-2')
        call(['git', '-C', name, 'tag', 'feature-tag'])

        _add_and_commit_file(name, 'testing-3')

        self.commit = call_with_output(
            ['git', '-C', name, 'rev-parse', 'HEAD'])


@contextlib.contextmanager
def return_to_cwd():
    cwd = os.getcwd()
    try:
        yield
    finally:
        os.chdir(cwd)


class BzrRepo(fixtures.Fixture):

    def __init__(self, name):
        self.name = name

    def setUp(self):
        super().setUp()

        bzr_home = self.useFixture(fixtures.TempDir()).path
        self.useFixture(fixtures.EnvironmentVariable('BZR_HOME', bzr_home))
        self.useFixture(fixtures.EnvironmentVariable(
            'BZR_EMAIL',  'Test User <test.user@example.com>'))

        with return_to_cwd():
            os.makedirs(self.name)
            os.chdir(self.name)
            call(['bzr', 'init'])
            with open('testing', 'w') as fp:
                fp.write('testing')

            call(['bzr', 'add', 'testing'])
            call(['bzr', 'commit', '-m', 'testing'])
            call(['bzr', 'tag', 'feature-tag'])
            revno = call_with_output(['bzr', 'revno'])

            self.commit = revno


class SvnRepo(fixtures.Fixture):

    def __init__(self, name):
        self.name = name

    def setUp(self):
        super().setUp()

        working_tree = 'svn-repo'
        call(['svnadmin', 'create', self.name])
        call(['svn', 'checkout',
              'file://{}'.format(os.path.join(os.getcwd(), self.name)),
              working_tree])

        with return_to_cwd():
            os.chdir(working_tree)
            with open('testing', 'w') as fp:
                fp.write('testing')

            call(['svn', 'add', 'testing'])
            call(['svn', 'commit', '-m', 'svn testing'])
            revno = '1'

            self.commit = revno


class HgRepo(fixtures.Fixture):

    def __init__(self, name):
        self.name = name

    def setUp(self):
        super().setUp()

        with return_to_cwd():
            os.makedirs(self.name)
            os.chdir(self.name)
            call(['hg', 'init'])
            with open('testing', 'w') as fp:
                fp.write('testing')

            call(['hg', 'add', 'testing'])
            call(['hg', 'commit', '-m', 'testing',
                  '-u', 'Test User <test.user@example.com>'])
            call(['hg', 'tag', 'feature-tag',
                  '-u', 'Test User <test.user@example.com>'])
            revno = call_with_output(['hg', 'id']).split()[0]

            self.commit = revno


class FakeAptCache(fixtures.Fixture):

    class Cache():

        def __init__(self):
            super().__init__()
            self.packages = collections.OrderedDict()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def __setitem__(self, key, item):
            package_parts = key.split('=')
            package_name = package_parts[0]
            version = (
                package_parts[1] if len(package_parts) > 1 else item.version)
            if package_name in self.packages:
                self.packages[package_name].version = version
            else:
                if version and not item.version:
                    item.version = version
                self.packages[package_name] = item

        def __getitem__(self, key):
            if '=' in key:
                key = key.split('=')[0]
            return self.packages[key]

        def __contains__(self, key):
            return key in self.packages

        def __iter__(self):
            return iter(self.packages.values())

        def open(self):
            pass

        def close(self):
            pass

        def update(self, *args, **kwargs):
            pass

        def get_changes(self):
            return [self.packages[package] for package in self.packages
                    if self.packages[package].marked_install]

        def get_providing_packages(self, package_name):
            providing_packages = []
            for package in self.packages:
                if package_name in self.packages[package].provides:
                    providing_packages.append(self.packages[package])
            return providing_packages

        def is_virtual_package(self, package_name):
            is_virtual = False
            if package_name not in self.packages:
                for package in self.packages:
                    if package_name in self.packages[package].provides:
                        return True
            return is_virtual

    def __init__(self, packages=None):
        super().__init__()
        self.packages = packages if packages else []

    def setUp(self):
        super().setUp()
        temp_dir_fixture = fixtures.TempDir()
        self.useFixture(temp_dir_fixture)
        self.path = temp_dir_fixture.path
        patcher = mock.patch('snapcraft.repo._deb.apt.Cache')
        self.mock_apt_cache = patcher.start()
        self.addCleanup(patcher.stop)

        self.cache = self.Cache()
        self.mock_apt_cache.return_value = self.cache
        for package, version in self.packages:
            self.add_package(FakeAptCachePackage(package, version))

        # Add all the packages in the manifest.
        with open(os.path.abspath(
                os.path.join(
                    __file__, '..', '..',
                    'internal', 'repo', 'manifest.txt'))) as manifest_file:
            self.add_packages([line.strip() for line in manifest_file])

    def add_package(self, package):
        package.temp_dir = self.path
        self.cache[package.name] = package

    def add_packages(self, package_names):
        for name in package_names:
            self.cache[name] = FakeAptCachePackage(name)


class FakeAptCachePackage():

    def __init__(
            self, name, version=None, installed=None,
            temp_dir=None, provides=None,
            priority='non-essential'):
        super().__init__()
        self.temp_dir = temp_dir
        self.name = name
        self._version = None
        self.versions = {}
        self.version = version
        self.candidate = self
        self.provides = provides if provides else []
        if installed:
            # XXX The installed attribute requires some values that the fake
            # package also requires. The shortest path to do it that I found
            # was to get installed to return the same fake package.
            self.installed = self
        else:
            self.installed = None
        self.priority = priority
        self.marked_install = False

    def __str__(self):
        if '=' in self.name:
            return self.name
        else:
            return '{}={}'.format(self.name, self.version)

    @property
    def version(self):
        return self._version

    @version.setter
    def version(self, version):
        self._version = version
        if version is not None:
            self.versions.update({version: self})

    def mark_install(self):
        if not self.installed:
            self.marked_install = True

    def mark_keep(self):
        pass

    def fetch_binary(self, dir_, progress):
        path = os.path.join(self.temp_dir, self.name)
        open(path, 'w').close()
        return path

    def get_dependencies(self, _):
        return []


class WithoutSnapInstalled(fixtures.Fixture):
    """Assert that a snap is not installed and remove it on clean up.

    :raises: AssertionError: if the snap is installed when this fixture is
        set up.
    """

    def __init__(self, snap_name):
        super().__init__()
        self.snap_name = snap_name.split('/')[0]

    def setUp(self):
        super().setUp()
        if snapcraft.repo.snaps.SnapPackage.is_snap_installed(self.snap_name):
            raise AssertionError(
                "This test cannot run if you already have the {snap!r} snap "
                "installed. Please uninstall it by running "
                "'sudo snap remove {snap}'.".format(snap=self.snap_name))

        self.addCleanup(self._remove_snap)

    def _remove_snap(self):
        try:
            subprocess.check_output(
                ['sudo', 'snap', 'remove', self.snap_name],
                stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            RuntimeError("unable to remove {!r}: {}".format(
                self.snap_name, e.output))


class SnapcraftYaml(fixtures.Fixture):

    def __init__(
            self, path, name='test-snap', version='test-version',
            summary='test-summary', description='test-description'):
        super().__init__()
        self.path = path
        self.data = {
            'name': name,
            'version': version,
            'summary': summary,
            'description': description,
            'parts': {}
        }

    def update_part(self, name, data):
        part = {name: data}
        self.data['parts'].update(part)

    def setUp(self):
        super().setUp()
        with open(os.path.join(self.path, 'snapcraft.yaml'),
                  'w') as snapcraft_yaml_file:
            yaml.dump(self.data, snapcraft_yaml_file)


class ObjectSpy(fixtures.Fixture):

    def __init__(self, target, cls):
        super().__init__()

        self._target = target
        self._cls = cls

    def _setUp(self):
        patcher = mock.patch(self._target, wraps=self._cls)
        self.spy = patcher.start()
        self.addCleanup(patcher.stop)

        for member in inspect.getmembers(self._cls,
                                         predicate=inspect.isfunction):
            name = member[0]
            value = member[1]

            # Already wrapped __init__, skip it here
            if name == '__init__':
                continue

            def _spy(wrapped_method):
                spy = mock.MagicMock()

                def _wrapper(self, *args, **kwargs):
                    spy(*args, **kwargs)
                    return wrapped_method(self, *args, **kwargs)
                _wrapper.spy = spy
                return _wrapper

            spy = _spy(value)
            patcher = mock.patch.object(self._cls, name, spy)
            patcher.start()
            setattr(self.spy, name, spy.spy)
            self.addCleanup(patcher.stop)


class FakePip(ObjectSpy):

    def __init__(self):
        super().__init__(
            'snapcraft.plugins._python._pip.Pip',
            snapcraft.plugins._python._pip.Pip)

        self._original_run_output = snapcraft.internal.common.run_output
        self._subcommand_dispatcher = {
            'download': self._fake_download,
            'install': self._fake_install,
            'wheel': self._fake_wheel,
            'list': self._fake_list,
        }

        self._download_dir_template = os.path.join('{base_dir}', 'downloaded')
        self._install_dir_template = os.path.join('{base_dir}', 'installed')

        self.fake_list_return = None

    def _setUp(self):
        super()._setUp()

        patcher = mock.patch(
            'snapcraft.internal.common.run_output',
            side_effect=self._fake_run_output)
        self.run_output = patcher.start()
        self.addCleanup(patcher.stop)

    def _fake_run_output(self, *args, **kwargs):
        try:
            command = self._get_pip_command(args[0])
            if command:
                return self._subcommand_dispatcher[command[0]](
                    command[1:], **kwargs)
        except ValueError:
            return self._original_run_output(*args, **kwargs)

    def _get_pip_command(self, args):
        with contextlib.suppress(IndexError):
            if ('python' in args[0]) and (args[1:3] == ['-m', 'pip']):
                return args[3:]

        raise ValueError('not a pip command')

    def _fake_download(self, args, **kwargs):
        # We only care about the destination and package list here. Remove
        # everything else.
        flags = (
            '--disable-pip-version-check', '--process-dependency-links', '.')
        for flag in flags:
            with contextlib.suppress(ValueError):
                args.remove(flag)

        index = args.index('--dest')
        del args[index]
        destination = args.pop(index)

        useless_args = ('--requirement', '--constraint')
        for arg in useless_args:
            with contextlib.suppress(ValueError):
                index = args.index(arg)
                del args[index]
                del args[index]

        # Only package names should be left. Pretend they've been downloaded by
        # creating a "downloaded" subdirectory and creating a file for each
        # package containing its version.
        download_dir = self._download_dir_template.format(
            base_dir=destination)
        for package in args:
            version = '1.0'  # Pretend it's v1.0 unless given otherwise
            with contextlib.suppress(ValueError):
                package, version = package.split('==')

            file_path = os.path.join(download_dir, package)
            os.makedirs(download_dir, exist_ok=True)
            with open(file_path, 'w') as f:
                f.write(version)

        return ''

    def _fake_install(self, args, **kwargs):
        # We only care about the find-links and package list here. Remove
        # everything else.
        flags = (
            '--user', '--no-compile', '--no-index',
            '--process-dependency-links', '--ignore-installed', '--no-deps',
            '--upgrade', '.')
        for flag in flags:
            with contextlib.suppress(ValueError):
                args.remove(flag)

        index = args.index('--find-links')
        del args[index]
        links_dir = args.pop(index)

        useless_args = ('--requirement', '--constraint')
        for arg in useless_args:
            with contextlib.suppress(ValueError):
                # There can be multiple of these. Just keep removing until
                # they're gone.
                while True:
                    index = args.index(arg)
                    del args[index]
                    del args[index]

        # Only package names should be left. Assume they've been "downloaded",
        # and pretend they've been "installed" by moving the downloaded files
        # into a "installed" subdirectory of PYTHONUSERBASE.
        download_dir = self._download_dir_template.format(
            base_dir=links_dir)
        install_dir = self._install_dir_template.format(
            base_dir=kwargs['env']['PYTHONUSERBASE'])
        for package in args:
            with contextlib.suppress(ValueError):
                package, version = package.split('==')

            file_path = os.path.join(download_dir, package)
            os.makedirs(install_dir, exist_ok=True)
            shutil.copy(file_path, install_dir)
        return ''

    def _fake_wheel(self, args, **kwargs):
        return ''

    def _fake_list(self, args, **kwargs):
        if self.fake_list_return:
            return self.fake_list_return

        # Return json string of package: version pairs for the packages that
        # were installed in PYTHONUSERBASE
        install_dir = self._install_dir_template.format(
            base_dir=kwargs['env']['PYTHONUSERBASE'])
        package_list = []
        if os.path.exists(install_dir):
            for package_file in os.listdir(install_dir):
                package_info = {'name': package_file}
                with open(os.path.join(install_dir, package_file)) as f:
                    package_info['version'] = f.read()
                package_list.append(package_info)
        return json.dumps(package_list)
