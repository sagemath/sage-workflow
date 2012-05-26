import os, tempfile
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

class GitInterface(object):
    def __init__(self, UI, gitcmd = 'git'):
        self._gitcmd = gitcmd
        self.UI = UI

    def _clean_str(self, s):
        # for now, no error checking
        return str(s)

    def execute(self, cmd, *args, **kwds):
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
            return call(s, shell=True)

    def has_uncommitted_changes(self):
        return False

    def commit_all(self, *args, **kwds):
        kwds['a'] = True
        self.execute("commit", *args, **kwds)

    def exists(self, ticketnum, branchname):
        return False

    def stash(self):
        self.execute("stash")

    def files_added(self):
        raise NotImplementedError("Should return a list of filenames of files that the user might want to add")

    def add_file(self, F):
        raise NotImplementedError("Should add the file with filename F")

    def save(self):
        diff = self.UI.get_input("Would you like to see a diff of the changes?",["yes","no"],"no")
        if diff == "yes":
            self.execute("diff")
        added = self.files_added()
        for F in added:
            toadd = self.UI.get_input("Would you like to start tracking %s?"%F,["yes","no"],"yes")
            if toadd == "yes":
                self.add_file(F)
        msg = self.UI.get_input("Please enter a commit message:")
        self.commit_all(m=msg)

class TracInterface(object):
    def __init__(self, UI, realm, trac, username, password):
        self.UI = UI
        if trac[-1] != '/':
            trac += '/'
        trac += 'login/xmlrpc'
        transport = DigestTransport(realm, trac, username, password)
        self._tracserver = ServerProxy(trac, transport=transport)

    def create_ticket(self, summary, description, type, component, attributes={}, notify=False):
        """
        Creates a ticket on trac and returns the new ticket number.

        EXAMPLES::

            sage: SD = SageDev()
            sage: SD.trac_create_ticket("Creating a trac ticket is not doctested", "There seems to be no way to doctest the automated creation of trac tickets in the SageDev class", "defect", "scripts")
        """
        tnum = self._tracserver.ticket.create(summary, description, attributes, notify)
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
                F.write("Description (multiple lines, trac markup allowed): \n\n\n\n")
                F.write("Type (defect/enhancement): \n")
                F.write("Component: \n")
                F.close()
                parsed = self.parse(filename)
                os.unlink(filename)
                if any([a is None for a in parsed]):
                    tryagain = self.UI.get_input("Error in entering ticket data. Would you like to try again?", ["yes","no"],default="y")
                    if tryagain == "no": break
                else:
                    summary, description, type, component = parsed
                    return self.create_ticket(summary, description, type, component)

class UserInterface(object):
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
                prompt += " "
                options = None
        if testing:
            return prompt
        while True:
            s = raw_input(prompt)
            if options is None:
                return s
            if len(s.strip()) == 0:
                if default is None:
                    print "Please enter an option"
                    continue
                else:
                    return options[default]
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

    def confirm(self, action, default_yes=True):
        ok = self.get_input("Are you sure you want to " + action + "?", ["yes","no"], "yes" if default_yes else "no")
        return ok == "yes"



class SageDev(object):
    def __init__(self, devrc = '~/.sage/devrc', gitcmd = 'git', realm = 'sage.math.washington.edu', trac='http://trac.sagemath.org/experimental/'):
        devrc = os.path.expanduser(devrc)
        username, password = self.process_rc(devrc)
        self.UI = UserInterface()
        self.git = GitInterface(self.UI, gitcmd)
        self.trac = TracInterface(self.UI, realm, trac, username, password)

    def process_rc(self, devrc):
        with open(devrc) as F:
            L = list(F)
            username = L[0].strip()
            passwd = L[1].strip()
            return username, passwd

    def start(self, ticketnum = None, branchname = None):
        if ticketnum is None:
            # User wants to create a ticket
            ticketnum = self.trac.create_ticket_interactive()
            if ticketnum is None:
                return
        if self.git.has_uncommitted_changes():
            curticket = self.git.current_ticket()
            if curticket is None:
                options = [ticketnum, "stash"]
            else:
                options = [ticketnum, curticket, "stash"]
            dest = self.UI.get_input("Where do you want to commit your changes?", options)
            if dest == "stash":
                self.git.stash()
            elif dest == str(curticket):
                self.git.save()
            if self.git.exists(ticketnum, branchname):
                

            self.git.commit_all()
