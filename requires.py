from charmhelpers.core import hookenv
from charms.reactive import RelationBase
from charms.reactive import hook
from charms.reactive import scopes


class MySQLSharedRequires(RelationBase):
    scope = scopes.GLOBAL

    # These remote data fields will be automatically mapped to accessors
    # with a basic documentation string provided.
    auto_accessors = ['access-network', 'db_host',
                      'ssl_ca', 'ssl_cert', 'ssl_key']

    @hook('{requires:mysql-shared}-relation-joined')
    def joined(self):
        self.set_state('{relation_name}.connected')

    @hook('{requires:mysql-shared}-relation-changed')
    def changed(self):
        if self.base_data_complete():
            self.set_state('{relation_name}.available')
        if self.access_network_data_complete():
            self.set_state('{relation_name}.available.access_network')
        if self.ssl_data_complete():
            self.set_state('{relation_name}.available.ssl')

    @hook('{requires:mysql-shared}-relation-{broken,departed}')
    def departed(self):
        self.remove_state('{relation_name}.connected')
        self.remove_state('{relation_name}.available')
        self.remove_state('{relation_name}.available.access_network')
        self.remove_state('{relation_name}.available.ssl')

    def configure(self, database, username, hostname=None, prefix=None):
        """
        Called by charm layer that uses this interface to configure a database.
        """
        if not hostname:
            conversation = self.conversation()
            try:
                hostname = hookenv.network_get_primary_address(
                    conversation.relation_name
                )
            except NotImplementedError:
                hostname = hookenv.unit_private_ip()

        if prefix:
            relation_info = {
                prefix + '_database': database,
                prefix + '_username': username,
                prefix + '_hostname': hostname,
            }
            self.set_prefix(prefix)
        else:
            relation_info = {
                'database': database,
                'username': username,
                'hostname': hostname,
            }
        self.set_remote(**relation_info)
        self.set_local(**relation_info)

    def set_prefix(self, prefix):
        """
        Store all of the database prefixes in a list.
        """
        prefixes = self.get_local('prefixes')
        if prefixes:
            if prefix not in prefixes:
                self.set_local('prefixes', prefixes + [prefix])
        else:
            self.set_local('prefixes', [prefix])

    def get_prefixes(self):
        """
        Return the list of saved prefixes.
        """
        return self.get_local('prefixes')

    def database(self, prefix=None):
        """
        Return a configured database name.
        """
        if prefix:
            return self.get_local(prefix + '_database')
        return self.get_local('database')

    def username(self, prefix=None):
        """
        Return a configured username.
        """
        if prefix:
            return self.get_local(prefix + '_username')
        return self.get_local('username')

    def hostname(self, prefix=None):
        """
        Return a configured hostname.
        """
        if prefix:
            return self.get_local(prefix + '_hostname')
        return self.get_local('hostname')

    def password(self, prefix=None):
        """
        Return a database password.
        """
        if prefix:
            return self.get_remote(prefix + '_password')
        return self.get_remote('password')

    def allowed_units(self, prefix=None):
        """
        Return a database's allowed_units.
        """
        if prefix:
            return self.get_remote(prefix + '_allowed_units')
        return self.get_remote('allowed_units')

    def base_data_complete(self):
        """
        Check if required base data is complete.
        """
        data = {
            'db_host': self.db_host(),
        }
        if self.get_prefixes():
            suffixes = ['_password', '_allowed_units']
            for prefix in self.get_prefixes():
                for suffix in suffixes:
                    key = prefix + suffix
                    data[key] = self.get_remote(key)
        else:
            data['password'] = self.get_remote('password')
            data['allowed_units'] = self.get_remote('allowed_units')
        if all(data.values()):
            return True
        return False

    def access_network_data_complete(self):
        """
        Check if optional access network data provided by mysql is complete.
        """
        data = {
            'access-network': self.access_network(),
        }
        if all(data.values()):
            return True
        return False

    def ssl_data_complete(self):
        """
        Check if optional ssl data provided by mysql is complete.
        """
        # Note: ssl_ca can also be set but isn't required
        data = {
            'ssl_cert': self.ssl_cert(),
            'ssl_key': self.ssl_key(),
        }
        if all(data.values()):
            return True
        return False
