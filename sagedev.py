from subprocess import call
from xmlrpclib import Transport, ServerProxy
import urllib2

class DigestTransport(Transport):
    """Handles an HTTP transaction to an XML-RPC server."""

    def __init__(self, realm, url, username, password, **kwds):
        Transport.__init__(self, **kwds)

        authhandler = urllib2.HTTPDigestAuthHandler()
        authhandler.add_password(realm, url, username, password)
        self.opener = urllib2.build_opener(authhandler)

    def request(self, host, handler, request_body, verbose=0):
        # issue XML-RPC request

        self.verbose = verbose

        headers = {'Content-type': 'text/xml'}
        data = request_body
        req = urllib2.Request('http://' + host + handler, data, headers)

        response = self.opener.open(req)

        return self.parse_response(response)

class SageDev(object):
    def __init__(self, devrc = '~/.sage/devrc', gitcmd = 'git', realm = 'sage.math.washington.edu', trac='http://trac.sagemath.org/experimental/'):
        username, password = self.process_rc(devrc)
        self._gitcmd = gitcmd
        if trac[-1] != '/':
            trac += '/'
        trac += 'login/xmlrpc'
        transport = DigestTransport(realm, trac, username, password)
        self._tracserver = ServerProxy(trac, transport=transport)

    def process_rc(self, devrc):
        return "roed","nopadicbugs"

    def _clean_str(self, s):
        # for now, no error checking
        return str(s)

    def git(self, cmd, *args, **kwds):
        s = self._gitcmd + " " + cmd
        testing = kwds.pop("testing",None)
        for k, v in kwds:
            if len(k) == 1:
                k = ' -' + k
            else:
                k = ' --' + k
            if v is True:
                s += k
            else:
                s += k + " " + self._clean_str(v)
        if args:
            s += " " + "".join([self._clean_str(a) for a in args])
        if testing:
            return s
        else:
            call(s, shell=True)

    def trac_create_ticket(self, summary, description, attributes={}, notify=False):
        """
        Creates a ticket on trac and returns the new ticket number.

        EXAMPLES::

            sage: SD = SageDev()
            sage: SD.trac_create_ticket("Creating a trac ticket is not doctested", "There seems to be no way to doctest the automated creation of trac tickets in the SageDev class")
        """
        return self._tracserver.ticket.create(summary, description, attributes, notify)

