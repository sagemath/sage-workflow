import os, tempfile
from xmlrpclib import Transport, ServerProxy
import urllib2

REALM = 'sage.math.washington.edu'
TRAC_SERVER_URI = 'https://trac.tangentspace.org/sage_trac'

class DigestTransport(object, Transport):
    """
    Handles an HTTP transaction to an XML-RPC server.

    EXAMPLES::

        sage: from trac_interface import REALM, TRAC_SERVER_URI, DigestTransport
        sage: DigestTransport(REALM, TRAC_SERVER_URI+"/xmlrpc")
        <trac_interface.DigestTransport at ...>

    """
    def __init__(self, realm, url, username=None, password=None, **kwds):
        """
        Initialization.

        EXAMPLES::

            sage: from trac_interface import REALM, TRAC_SERVER_URI, DigestTransport
            sage: type(DigestTransport(REALM, TRAC_SERVER_URI+"/xmlrpc"))
            trac_interface.DigestTransport

        """
        Transport.__init__(self, **kwds)

        authhandler = urllib2.HTTPDigestAuthHandler()
        if username and password:
            authhandler.add_password(realm, url, username, password)

        self.opener = urllib2.build_opener(authhandler)

    def request(self, host, handler, request_body, verbose=0):
        """
        Issue an XML-RPC request.

        EXAMPLES::

            sage: from trac_interface import REALM, TRAC_SERVER_URI, DigestTransport
            sage: d = DigestTransport(REALM, TRAC_SERVER_URI+"/xmlrpc")
            sage: d.request # not tested

        """
        self.verbose = verbose

        headers = {'Content-type': 'text/xml'}
        data = request_body
        req = urllib2.Request('http://' + host + handler, data, headers)

        response = self.opener.open(req)

        return self.parse_response(response)

class DoctestServerProxy(object):
    """
    A fake trac proxy for doctesting the functionality in this file which would require authentication by trac.

    EXAMPLES::

        sage: from trac_interface import DoctestServerProxy
        sage: DoctestServerProxy(None)
        <trac_interface.DoctestServerProxy at ...>

    """
    def __init__(self, trac):
        self._trac = trac
        self._sshkeys = {}

    @property
    def sshkeys(self):
        class SshKeys(object):
            def setkeys(this, keys):
                if self._trac._username not in self._sshkeys:
                    self._sshkeys[self._trac._username] = set()
                self._sshkeys[self._trac._username] = self._sshkeys[self._trac._username].union(set(keys))
                return 0
            def getkeys(this):
                if self._trac._username not in self._sshkeys: return []
                return list(self._sshkeys[self._trac._username])
            def listusers(this):
                return self._sshkeys.keys()

        self._sshkeys_impl = SshKeys()
        return self._sshkeys_impl

    @property
    def ticket(self):
        class Ticket(object):
            def create(self, summary, description, attributes, notify):
                return 14366
        return Ticket()

class TracInterface(object):
    """
    Wrapper around the XML-RPC interface of trac.

    EXAMPLES::

        sage: from sagedev import SageDev, Config
        sage: SageDev(Config._doctest_config()).trac
        <trac_interface.TracInterface at ...>

    """
    def __init__(self, sagedev):
        """
        Initialization.

        EXAMPLES::

            sage: from sagedev import SageDev, Config
            sage: from trac_interface import TracInterface
            sage: type(TracInterface(SageDev(Config._doctest_config())))
            trac_interface.TracInterface

        """
        self._sagedev = sagedev
        self._UI = sagedev._UI
        if 'trac' not in sagedev._config:
            sagedev._config['trac'] = {}
        self._config = sagedev._config['trac']
        # Caches for the analogous single-underscore properties
        self.__anonymous_server_proxy = None
        self.__authenticated_server_proxy = None

    @property
    def _anonymous_server_proxy(self):
        """
        Lazy wrapper around a non-authenticated XML-RPC interface to trac.

        .. NOTE::

            Unlike the authenticated server proxy, this is not replaced with a
            fake proxy for doctesting. All doctests using it should therefore
            be labeled as optional ``online``

        EXAMPLES::

            sage: from sagedev import SageDev, Config
            sage: SageDev(Config._doctest_config()).trac._anonymous_server_proxy
            <ServerProxy for trac.tangentspace.org/sage_trac/xmlrpc>

        """
        if self.__anonymous_server_proxy is None:
            realm = REALM
            if "realm" in self._config:
                realm = self._config["realm"]
            server = TRAC_SERVER_URI
            if "server" in self._config:
                server = self._config["server"]
            if server[-1] != '/': server += '/'

            transport = DigestTransport(realm, server)
            self.__anonymous_server_proxy = ServerProxy(server + 'xmlrpc', transport=transport)
        return self.__anonymous_server_proxy

    @property
    def _authenticated_server_proxy(self):
        """
        Get an XML-RPC proxy object that is authenticated using the users
        username and password.

        EXAMPLES::

            sage: from sagedev import SageDev, Config
            sage: SageDev().trac._authenticated_server_proxy # not tested
            <ServerProxy for trac.tangentspace.org/sage_trac/login/xmlrpc>

        For convenient doctesting, this is replaced with a fake object for the user ``'doctest'``::

            sage: from sagedev import SageDev, Config
            sage: SageDev(config=Config._doctest_config()).trac._authenticated_server_proxy
            <trac_interface.DoctestServerProxy at ...>

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
                return DoctestServerProxy(self)
            else:
                transport = DigestTransport(realm, server, username, self._password)
                self.__authenticated_server_proxy = ServerProxy(server + 'login/xmlrpc', transport=transport)

        return self.__authenticated_server_proxy


    @property
    def _username(self):
        """
        A lazy property to get the username on trac.

        EXAMPLES::

            sage: from sagedev import SageDev, Config
            sage: import tempfile
            sage: devrc = tempfile.NamedTemporaryFile().name
            sage: s = SageDev(Config(devrc))
            sage: s._UI._answer_stack = ["user"]
            sage: s.trac._username
            Please enter your trac username: user
            'user'
            sage: s.trac._username
            'user'
            sage: s = SageDev(Config(devrc))
            sage: s.trac._username
            'user'

        """
        if 'username' not in self._config:
            self._config['username'] = self._UI.get_input("Please enter your trac username: ")
            self._config._write_config()
        return self._config['username']

    @property
    def _password(self):
        """
        A lazy property to get the username of trac.

        EXAMPLES::

            sage: import tempfile
            sage: from sagedev import SageDev, Config
            sage: s = SageDev(Config(tempfile.NamedTemporaryFile().name))
            sage: s._UI._answer_stack = [ "", "pass", "pass" ]
            sage: s.trac._password
            Please enter your trac password:
            Please confirm your trac password:
            Do you want your password to be stored on your local system? (your password will be stored in plaintext in a file only readable by you) [yes/No]
            'pass'
            sage: s._UI._answer_stack = [ "yes", "passwd", "passwd" ]
            sage: s.trac._password
            Please enter your trac password:
            Please confirm your trac password:
            Do you want your password to be stored on your local system? (your password will be stored in plaintext in a file only readable by you) [yes/No] yes
            'passwd'
            sage: s.trac._password
            'passwd'

        """
        if 'password' in self._config:
            return self._config['password']
        else:
            while True:
                password = self._UI.get_password("Please enter your trac password: ")
                password2 = self._UI.get_password("Please confirm your trac password: ")
                if password != password2:
                    self._UI.show("Passwords do not agree.")
                else: break
            if self._UI.confirm("Do you want your password to be stored on your local system? (your password will be stored in plaintext in a file only readable by you)", default_yes=False):
                self._config['password'] = password
                self._config._write_config()
            return password

    @property
    def sshkeys(self):
        """
        Retrieve the interface to the ssh keys stored for the user.

        EXAMPLES::

            sage: from sagedev import SageDev, Config
            sage: sshkeys = SageDev().trac.sshkeys # not tested
            sage: type(sshkeys) # not tested
            instance
            sage: sshkeys.listusers() # not tested
            ['rohana', 'saraedum', 'roed', 'kini', 'nthiery', 'anonymous']
            sage: sshkeys.getkeys() # not tested
            []
            sage: sshkeys.setkeys(["foo","bar"]) # not tested
            0
            sage: sshkeys.getkeys() # not tested
            ['foo', 'bar']

            sage: sshkeys = SageDev(Config._doctest_config()).trac.sshkeys
            sage: type(sshkeys)
            trac_interface.SshKeys
            sage: sshkeys.listusers()
            []
            sage: sshkeys.getkeys()
            []
            sage: sshkeys.setkeys(["foo","bar"])
            0
            sage: sshkeys.getkeys()
            ['foo', 'bar']

        """
        return self._authenticated_server_proxy.sshkeys

    def create_ticket(self, summary, description, attributes={}, notify=False):
        """
        Create a ticket on trac and return the new ticket number.

        EXAMPLES::

            sage: from sagedev import SageDev, Config
            sage: SageDev().trac.create_ticket("Summary","Description",{'type':'defect','component':'algebra'}) # not tested
            14366

            sage: SageDev(Config._doctest_config()).trac.create_ticket("Summary","Description",{'type':'defect','component':'algebra'})
            14366

        """
        return self._authenticated_server_proxy.ticket.create(summary, description, attributes, notify)

    def create_ticket_interactive(self):
        proceed = self._UI.confirm("create a new ticket")
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
                    if not self._UI.confirm("Error in entering ticket data."
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
        """
        Retrieve the properties of ticket ``ticketnum``.

        EXAMPLES::

            sage: from sagedev import SageDev, Config
            sage: SageDev(Config._doctest_config()).trac._get_attributes(1000) # optional: online
            {'_ts': '1199953720000000',
             'cc': '',
             'changetime': <DateTime '20080110T08:28:40' at ...>,
             'component': 'distribution',
             'description': '',
             'keywords': '',
             'milestone': 'sage-2.10',
             'owner': 'was',
             'priority': 'major',
             'reporter': 'was',
             'resolution': 'fixed',
             'status': 'closed',
             'summary': 'Sage does not have 10000 users yet.',
             'time': <DateTime '20071025T16:48:05' at ...>,
             'type': 'defect'}

        """
        ticketnum = int(ticketnum)
        return self._anonymous_server_proxy.ticket.get(ticketnum)[3]

    def dependencies(self, ticketnum, all=False, _seen=None):
        """
        Retrieve the dependencies of ticket ``ticketnum``.

        INPUT:

        - ``ticketnum`` -- an integer, the number of a ticket

        - ``all`` -- a boolean (default: ``False``), whether to get indirect
          dependencies of ``ticketnum``

        - ``_seen`` -- (default: ``None``), used internally in recursive calls

        EXAMPLES::

            sage: from sagedev import SageDev, Config
            sage: SageDev(Config._doctest_config()).trac.dependencies(1000) # optional: online (an old ticket with no dependency field)
            []
            sage: SageDev(Config._doctest_config()).trac.dependencies(13147) # optional: online
            [13579, 13681]
            sage: SageDev(Config._doctest_config()).trac.dependencies(13147,all=True) # long time optional: online
            [13579, 13681, 13631]

        """
        # returns the list of all ticket dependencies, sorted by ticket number
        if _seen is None:
            seen = []
        elif ticketnum in _seen:
            return
        else:
            seen = _seen
        seen.append(ticketnum)
        data = self._get_attributes(ticketnum)
        if 'dependencies' not in data: return []
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
        """
        Retrieve the names of the attachments for ticket ``ticketnum``.

        EXAMPLES::

            sage: from sagedev import SageDev, Config
            sage: SageDev(Config._doctest_config()).trac.attachment_names(1000) # optional: online
            []
            sage: SageDev(Config._doctest_config()).trac.attachment_names(13147) # optional: online
            ['13147_move.patch', '13147_lazy.patch', '13147_lazy_spkg.patch', '13147_new.patch', '13147_over_13579.patch', 'trac_13147-ref.patch', 'trac_13147-rebased-to-13681.patch', 'trac_13681_root.patch']

        """
        ticketnum = int(ticketnum)
        attachments = self._anonymous_server_proxy.ticket.listAttachments(ticketnum)
        return [a[0] for a in attachments]

    def _set_branch(self, ticketnum, remote_branch, commit_id):
        ticketnum = int(ticketnum)
        tid, time0, time1, attributes = self._anonymous_server_proxy.ticket.get(ticketnum)
        self._authenticated_server_proxy.ticket.update(tid, 'Set by SageDev: commit %s'%(commit_id), {'branch':remote_branch})
