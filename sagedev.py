import os
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
        devrc = os.path.expanduser(devrc)
        username, password = self.process_rc(devrc)
        self._gitcmd = gitcmd
        if trac[-1] != '/':
            trac += '/'
        trac += 'login/xmlrpc'
        transport = DigestTransport(realm, trac, username, password)
        self._tracserver = ServerProxy(trac, transport=transport)

    def process_rc(self, devrc):
        with open(devrc) as F:
            L = list(F)
            username = L[0].strip()
            passwd = L[1].strip()
            return username, passwd

    #########################################################
    # Git interface
    #########################################################

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

    #########################################################
    # Trac interface
    #########################################################

    def trac_create_ticket(self, summary, description, attributes={}, notify=False):
        """
        Creates a ticket on trac and returns the new ticket number.

        EXAMPLES::

            sage: SD = SageDev()
            sage: SD.trac_create_ticket("Creating a trac ticket is not doctested", "There seems to be no way to doctest the automated creation of trac tickets in the SageDev class")
        """
        tnum = self._tracserver.ticket.create(summary, description, attributes, notify)

    #########################################################
    # User input
    #########################################################

    def get_input(self, prompt, options=None, default=None, testing=False):
        """
        Get input from the developer.

        INPUT:

        - ``promt`` -- a string
        - ``options`` -- a list of strings or None
        - ``default`` -- a string or None
        - ``testing`` -- boolean

        EXAMPLES::

            sage: SD = SageDev()
            sage: SD.get_input("Should I delete your home directory?", ["yes","no"], default="y", testing=True)
            'Should I delete your home directory? [Yes/no] '
        """
        if default is not None:
            for i, opt in enumerate(options):
                if opt.startswith(default):
                    default = i
                    break
            else:
                default = None
        if options is not None:
            options = list(options)
            if len(options) > 0:
                for i in range(len(options)):
                    if i == default:
                        options[i] = str(options[i]).capitalize()
                    else:
                        options[i] = str(options[i]).lower()
                prompt += " [" + "/".join(options) + "] "
                options[default] = options[default].lower()
            else:
                options = None
        if testing:
            return prompt
        while True:
            s = raw_input(prompt)
            if options is None:
                return s
            found = -1
            for i, opt in enumerate(options):
                if opt.startswith(s):
                    if found == -1:
                        found = i
                    else:
                        break
            else:
                if found != -1:
                    return options[found]
            if found == -1:
                print "Please specify an allowable option"
            else:
                print "Please disambiguate between options"
