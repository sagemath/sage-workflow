import os, tempfile
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

class TracInterface(object):
    def __init__(self, UI, realm, trac, username, password):
        self.UI = UI
        if trac[-1] != '/':
            trac += '/'
        trac += 'login/xmlrpc'
        transport = DigestTransport(realm, trac, username, password)
        self._tracserver = ServerProxy(trac, transport=transport)

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
        tnum = self._tracserver.ticket.create(summary, description,
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

    def dependencies(self, curticket):
        # returns the list of all ticket dependencies that have not
        # been merged into unstable. Earlier elements should be
        # 'older'.
        raise NotImplementedError
