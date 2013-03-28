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

class TracInterface(ServerProxy):
    def __init__(self, UI, config):
        self.UI = UI
        self._config = config
        transport = DigestTransport(config['realm'], config['server'], config['username'], config['password'])
        ServerProxy.__init__(self, config['server'] + 'login/xmlrpc', transport=transport)

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

    def dependencies(self, ticketnum, all=False):
        # returns the list of all ticket dependencies, sorted by ticket number
        data = self._get_attributes(ticketnum)
        dependencies = [int(a.strip(" #\n")) for a in data['dependencies'].split(',')]
        if not all or not dependencies:
            return sorted(dependencies)
        L = []
        for a in dependencies:
            L.extend(self.dependencies(a, all=True))
        return sorted(list(set(L)))

    def attachment_names(self, ticketnum):
        ticketnum = int(ticketnum)
        attachments = self.ticket.listAttachments(ticketnum)
        return [a[0] for a in attachments]
