import os, tempfile
from xmlrpclib import Transport, ServerProxy
import urllib2

REALM = 'sage.math.washington.edu'
TRAC_SERVER_URI = 'https://trac.tangentspace.org/sage_trac'

class DigestTransport(Transport):
    """Handles an HTTP transaction to an XML-RPC server."""

    def __init__(self, realm, url, username=None, password=None, **kwds):
        Transport.__init__(self, **kwds)

        if username and password:
            authhandler = urllib2.HTTPDigestAuthHandler()
            authhandler.add_password(realm, url, username, password)
        else:
            raise NotImplementedError

        self.opener = urllib2.build_opener(authhandler)

    def request(self, host, handler, request_body, verbose=0):
        # issue XML-RPC request

        self.verbose = verbose

        headers = {'Content-type': 'text/xml'}
        data = request_body
        req = urllib2.Request('http://' + host + handler, data, headers)

        response = self.opener.open(req)

        return self.parse_response(response)

class TracInterface(object):
    def __init__(self, UI, config):
        self._UI = UI
        self._config = config
        # Caches for the analogous single-underscore properties
        self.__anonymous_server_proxy = None
        self.__authenticated_server_proxy = None

    @property
    def _anonymous_server_proxy(self):
        if self.__anonymous_server_proxy is None:
            realm = REALM
            if "realm" in self._config:
                realm = self._config["realm"]
            server = TRAC_SERVER_URI
            if "server" in self._config:
                server = self._config["server"]
            if server[-1] != '/': server += '/'

            transport = DigestTransport(realm, server)
            self.__anonymous_server_proxy = ServerProxy.__init__(self, server + 'xmlrpc', transport=transport)
        return self.__anonymous_server_proxy

    @property
    def _authenticated_server_proxy(self):
        """
        Get an XML-RPC proxy object that is authenticated using the users
        username and password.

        EXAMPLES::

            sage: SageDev()._trac._authenticated_server_proxy # optional: trac

        For convenient doctesting, this is replaced with a fake object for the user ``'doctest'``::

            sage: SageDev(config=Config._doctest_config(authenticated=False))._trac._authenticated_server_proxy

            sage: SageDev(config=Config._doctest_config(authenticated=True))._trac._authenticated_server_proxy

        """
        config = self._config

        if self.__authenticated_server_proxy is None:
            realm = REALM
            if "realm" in self._config:
                realm = self._config["realm"]
            server = TRAC_SERVER_URI
            if "server" in self._config:
                server = self._config["server"]
            if server[-1] != '/': server += '/'

            username = self._username
            if username == "doctest":
                return DoctestServerProxy()
            else:
                transport = DigestTransport(realm, server, username, self._password)
                self.__authenticated_server_proxy = ServerProxy.__init__(self, server + 'login/xmlrpc', transport=transport)

        return self.__authenticated_server_proxy


    @property
    def _username(self):
        if 'username' not in self._config:
            self._config['username'] = self._UI.get_input("Please enter your trac username: ")
            self._config._write_config()
        return self._config['username']

    @property
    def _password(self):
        if 'password' in self._config:
            return self._config['password']
        else:
            while True:
                password = self._UI.get_password("Please enter your trac password: ")
                password2 = self._UI.get_password("Please confirm your trac password: ")
                if password != password2:
                    self._UI.show("Passwords do not agree.")
                else: break
            if self._UI.confirm("Do you want your password to be stored on your local system? (your password will be stored in plaintext in a file only readable by you)", defaultYes=False):
                self._config['password'] = password
                self._config._write_confi()
            return password

    @property
    def sshkeys(self):
        return self._authenticated_server_proxy.sshkeys

    def __repr__(self):
        return "TracInterface()"

    def create_ticket(self, summary, description, type, component,
                      attributes={}, notify=False):
        """
        Create a ticket on trac and return the new ticket number.

        EXAMPLES::

            sage: SD = SageDev()
            sage: SD.trac_create_ticket(
            ... "Creating a trac ticket is not doctested",
            ... "There seems to be no way to doctest the automated"
            ... " creation of trac tickets in the SageDev class",
            ... "defect", "scripts"
            ... )
        """
        tnum = self.ticket.create(summary, description,
                                  attributes, notify)
        return tnum

    def create_ticket_interactive(self):
        proceed = self.UI.confirm("create a new ticket")
        if proceed:
            if os.environ.has_key('EDITOR'):
                editor = os.environ['EDITOR']
            else:
                editor = 'nano'
            while True:
                F = tempfile.NamedTemporaryFile(delete=False)
                filename = F.name
                F.write("Summary (one line): \n")
                F.write("Description (multiple lines, trac markup allowed):"
                        " \n\n\n\n")
                F.write("Type (defect/enhancement): \n")
                F.write("Component: \n")
                F.close()
                parsed = self.parse(filename)
                os.unlink(filename)
                if any([a is None for a in parsed]):
                    if not self.UI.confirm("Error in entering ticket data."
                                           " Would you like to try again?"):
                        break
                else:
                    summary, description, ticket_type, component = parsed
                    return self.create_ticket(summary, description, ticket_type,
                                              component)

    def add_dependency(self, new_ticket, old_ticket):
        # makes the trac ticket for new_ticket depend on the old_ticket
        raise NotImplementedError

    def _get_attributes(self, ticketnum):
        ticketnum = int(ticketnum)
        return self.ticket.get(ticketnum)[3]

    def dependencies(self, ticketnum, all=False, _seen=None):
        # returns the list of all ticket dependencies, sorted by ticket number
        if _seen is None:
            seen = []
        elif ticketnum in _seen:
            return
        else:
            seen = _seen
        seen.append(ticketnum)
        data = self._get_attributes(ticketnum)
        dependencies = data['dependencies']
        if dependencies.strip() == '': return []
        dependencies = [a.strip(" ,;+-\nabcdefghijklmnopqrstuvwxyz") for a in data['dependencies'].split('#')]
        dependencies = [a for a in dependencies if a]
        dependencies = [int(a) if a.isdigit() else a for a in dependencies]
        if not all:
            return dependencies
        for a in dependencies:
            if isinstance(a, int):
                self.dependencies(a, True, seen)
            else:
                seen.append(a)
        if _seen is None:
            return seen[1:]

    def attachment_names(self, ticketnum):
        ticketnum = int(ticketnum)
        attachments = self.ticket.listAttachments(ticketnum)
        return [a[0] for a in attachments]
