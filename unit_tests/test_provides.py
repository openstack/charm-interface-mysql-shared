# Copyright 2019 Canonical Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import charms_openstack.test_utils as test_utils
import mock
import provides


class TestRegisteredHooks(test_utils.TestRegisteredHooks):

    def test_hooks(self):
        defaults = []
        hook_set = {
            "when": {
                "joined": (
                    "endpoint.{endpoint_name}.joined",),

                "changed": (
                    "endpoint.{endpoint_name}.changed",),
                "departed": ("endpoint.{endpoint_name}.broken",
                             "endpoint.{endpoint_name}.departed",),
            },
        }
        # test that the hooks were registered
        self.registered_hooks_test_helper(provides, hook_set, defaults)


class TestMySQLSharedProvides(test_utils.PatchHelper):

    def setUp(self):
        super().setUp()
        self._patches = {}
        self._patches_start = {}
        self.patch_object(provides.reactive, "clear_flag")
        self.patch_object(provides.reactive, "set_flag")

        self.fake_unit = mock.MagicMock()
        self.fake_unit.unit_name = "myunit/4"
        self.fake_unit.received = {"username": None}

        self.fake_relation_id = "shared-db:19"
        self.fake_relation = mock.MagicMock()
        self.fake_relation.relation_id = self.fake_relation_id
        self.fake_relation.units = [self.fake_unit]

        self.ep_name = "ep"
        self.ep = provides.MySQLSharedProvides(
            self.ep_name, [self.fake_relation_id])
        self.ep.ingress_address = "10.10.10.10"
        self.ep.relations[0] = self.fake_relation

    def tearDown(self):
        self.ep = None
        for k, v in self._patches.items():
            v.stop()
            setattr(self, k, None)
        self._patches = None
        self._patches_start = None

    def test_joined(self):
        self.ep.set_ingress_address = mock.MagicMock()
        self.ep.joined()
        self.clear_flag.assert_called_once_with(
            "{}.available".format(self.ep_name))
        self.set_flag.assert_called_once_with(
            "{}.connected".format(self.ep_name))
        self.ep.set_ingress_address.assert_called_once()

    def test_changed_not_available(self):
        self.ep.available = mock.MagicMock()
        self.ep.available.return_value = False
        self.ep.changed()

        _calls = [
            mock.call("{}.available".format(self.ep_name)),
            mock.call("endpoint.{}.changed.database".format(self.ep_name)),
            mock.call("endpoint.{}.changed.username".format(self.ep_name)),
            mock.call("endpoint.{}.changed.hostname".format(self.ep_name))]
        self.clear_flag.assert_has_calls(_calls, any_order=True)
        self.set_flag.assert_not_called()

    def test_changed_available(self):
        self.ep.available = mock.MagicMock()
        self.ep.available.return_value = True
        self.ep.changed()

        _calls = [
            mock.call("endpoint.{}.changed.database".format(self.ep_name)),
            mock.call("endpoint.{}.changed.username".format(self.ep_name)),
            mock.call("endpoint.{}.changed.hostname".format(self.ep_name))]
        self.clear_flag.assert_has_calls(_calls, any_order=True)
        self.set_flag.assert_called_once_with(
            "{}.available".format(self.ep_name))

    def test_departed(self):
        self.ep.departed()
        _calls = [
            mock.call("{}.available".format(self.ep_name)),
            mock.call("{}.connected".format(self.ep_name))]
        self.clear_flag.assert_has_calls(_calls, any_order=True)

    def test_relation_ids(self):
        self.assertEqual([self.fake_relation_id], self.ep.relation_ids())

    def test_set_ingress_address(self):
        _calls = [
            mock.call("ingress-address", self.ep.ingress_address),
            mock.call("private-address", self.ep.ingress_address)]
        self.ep.set_ingress_address()
        self.fake_relation.to_publish_raw.__setitem__.assert_has_calls(_calls)

    def test_available_not_available(self):
        self.assertFalse(self.ep.available())

    def test_available_simple_available(self):
        self.fake_unit.received = {"username": "user"}
        self.assertTrue(self.ep.available())

    def test_available_prefixed_available(self):
        self.fake_unit.received["prefix_username"] = "user"
        self.assertTrue(self.ep.available())

    def test_set_db_connection_info_no_prefix(self):
        _pw = "fakepassword"
        self.ep.set_db_connection_info(
            self.fake_relation_id,
            self.ep.ingress_address,
            _pw,
            allowed_units=self.fake_unit.unit_name)
        _calls = [
            mock.call("db_host", self.ep.ingress_address),
            mock.call("password", _pw),
            mock.call("allowed_units", self.fake_unit.unit_name)]
        self.fake_relation.to_publish_raw.__setitem__.assert_has_calls(_calls)

    def test_set_db_connection_info_prefixed(self):
        _p = "prefix"
        _pw = "fakepassword"
        self.ep.set_db_connection_info(
            self.fake_relation_id,
            self.ep.ingress_address,
            _pw,
            allowed_units=self.fake_unit.unit_name,
            prefix=_p)
        _calls = [
            mock.call("db_host", self.ep.ingress_address),
            mock.call("{}_password".format(_p), _pw),
            mock.call("{}_allowed_units".format(_p), self.fake_unit.unit_name)]
        self.fake_relation.to_publish_raw.__setitem__.assert_has_calls(_calls)

    def test_set_db_connection_info_wait_timeout(self):
        _wto = 90
        _p = "prefix"
        _pw = "fakepassword"
        self.ep.set_db_connection_info(
            self.fake_relation_id,
            self.ep.ingress_address,
            _pw,
            allowed_units=self.fake_unit.unit_name,
            prefix=_p, wait_timeout=_wto)
        _calls = [
            mock.call("db_host", self.ep.ingress_address),
            mock.call("wait_timeout", _wto),
            mock.call("{}_password".format(_p), _pw),
            mock.call("{}_allowed_units".format(_p), self.fake_unit.unit_name)]
        self.fake_relation.to_publish_raw.__setitem__.assert_has_calls(_calls)
