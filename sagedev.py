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
    def __init__(self, UI, username, gitcmd = 'git'):
        self._gitcmd = gitcmd
        self._username = username
        self.UI = UI
        raise NotImplementedError("Need to set unstable")

    def released_sage_ver(self):
        raise NotImplementedError("should return a string with the most recent released version of Sage (in this branch's past?)")

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

    def _local_branchname(self, ticketnum):
        if ticketnum is None:
            return self._unstable
        return str(ticketnum)

    def _remote_branchname(self, ticketnum):
        if ticketnum is None:
            return self._unstable
        return "%s/%s"(self._username, ticketnum)

    def has_uncommitted_changes(self):
        raise NotImplementedError("Returns True if there are uncommitted changes or non-added files")

    def commit_all(self, *args, **kwds):
        # if files are non-tracked and user doesn't want to add any of
        # them, there might be no changes being committed here....
        kwds['a'] = True
        self.execute("commit", *args, **kwds)

    def exists(self, ticketnum):
        raise NotImplementedError("Returns True if ticket exists")

    def stash(self):
        raise NotImplementedError("Should stash changes")

    def files_added(self):
        raise NotImplementedError("Should return a list of filenames of files that the user might want to add")

    def add_file(self, F):
        raise NotImplementedError("Should add the file with filename F")

    def save(self):
        diff = self.UI.confirm("Would you like to see a diff of the changes?",default_yes=False)
        if diff == "yes":
            self.execute("diff")
        added = self.files_added()
        for F in added:
            toadd = self.UI.confirm("Would you like to start tracking %s?"%F)
            if toadd == "yes":
                self.add_file(F)
        msg = self.UI.get_input("Please enter a commit message:")
        self.commit_all(m=msg)

    def create_branch(self, ticketnum, at_unstable=False):
        if at_unstable:
            self.git("branch", self._local_branchname(ticketnum), self._local_branchname(None))
        else:
            self.git("branch", self._local_branchname(ticketnum))

    def fetch_branch(self, ticketnum):
        raise NotImplementedError("fetches a branch from remote, including dependencies if necessary.  Doesn't switch")

    def switch(self, ticketnum):
        raise NotImplementedError("switches to another ticket")

    def move_uncommited_changes(self, ticketnum):
        raise NotImplementedError("create temp branch, commit changes, rebase, fast-forward....")

    def needs_update(self, ticketnum):
        raise NotImplementedError("returns True if there are changes in the ticket on trac that aren't included in the current ticket")

    def sync(self, ticketnum=None):
        raise NotImplementedError("pulls in changes from trac and rebases the current branch to them.  ticketnum=None syncs unstable.")

    def vanilla(self, release=False):
        raise NotImplementedError("switch to unstable branch in the past (release=False) or a given named release")

    def review(self, ticketnum, user):
        raise NotImplementedError("download a remote branch to review")

    def prune(self):
        raise NotImplementedError("gets rid of branches that have been merged into unstable")

    def abandon(self, ticketnum):
        raise NotImplementedError("deletes the branch")

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
                    if not self.UI.confirm("Error in entering ticket data. Would you like to try again?"):
                        break
                else:
                    summary, description, type, component = parsed
                    return self.create_ticket(summary, description, type, component)

    def add_dependency(self, new_ticket, old_ticket):
        raise NotImplementedError("makes the trac ticket for new_ticket depend on the old_ticket")

    def dependencies(self, curticket):
        raise NotImplementedError("returns the list of all ticket dependencies that have not been merged into unstable.  Earlier elements should be 'older'.")

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

    def confirm(self, question, default_yes=True):
        ok = self.get_input(question, ["yes","no"], "yes" if default_yes else "no")
        return ok == "yes"



class SageDev(object):
    def __init__(self, devrc = '~/.sage/devrc', gitcmd = 'git', realm = 'sage.math.washington.edu', trac='http://trac.sagemath.org/experimental/'):
        devrc = os.path.expanduser(devrc)
        username, password = self.process_rc(devrc)
        self.UI = UserInterface()
        self.git = GitInterface(self.UI, username, gitcmd)
        self.trac = TracInterface(self.UI, realm, trac, username, password)

    def process_rc(self, devrc):
        with open(devrc) as F:
            L = list(F)
            username = L[0].strip()
            passwd = L[1].strip()
            return username, passwd

    def start(self, ticketnum = None):
        curticket = self.git.current_ticket()
        if ticketnum is None:
            # User wants to create a ticket
            ticketnum = self.trac.create_ticket_interactive()
            if ticketnum is None:
                # They didn't succeed.
                return
            if curticket is not None:
                if self.UI.confirm("Should the new ticket depend on #%s?"%(curticket))
                    self.git.create_branch(self, ticketnum)
                    self.trac.add_dependency(self, ticketnum, curticket)
                else:
                    self.git.create_branch(self, ticketnum, at_unstable=True)
        dest = None
        if self.git.has_uncommitted_changes():
            if curticket is None:
                options = ["#%s"%ticketnum, "stash"]
            else:
                options = ["#%s"%ticketnum, "#%s"%curticket, "stash"]
            dest = self.UI.get_input("Where do you want to commit your changes?", options)
            if dest == "stash":
                self.git.stash()
            elif dest == str(curticket):
                self.git.save()
        if self.git.exists(ticketnum):
            if dest == str(ticketnum):
                self.git.move_uncommited_changes(ticketnum)
            else:
                self.git.switch(ticketnum)
        else:
            self.git.fetch_branch(self, ticketnum)
            self.git.switch(ticketnum)

    def save(self):
        curticket = self.git.current_ticket()
        if self.UI.confirm("Are you sure you want to save your changes to ticket #%s?"%(curticket)):
            self.git.save()
            if self.UI.confirm("Would you like to upload the changes?"):
                self.git.upload()

    def upload(self, ticketnum = None):
        oldticket = self.git.current_ticket()
        if ticketnum is None or ticketnum == oldticket:
            oldticket = None
            ticketnum = self.git.current_ticket()
            if not self.UI.confirm("Are you sure you want to upload your changes to ticket #%s?"%(ticketnum)):
                return
        elif not self.git.exists(ticketnum):
            print "You don't have a branch for ticket %s"%(ticketnum)
            return
        elif not self.UI.confirm("Are you sure you want to upload your changes to ticket #%s?"%(ticketnum)):
            return
        else:
            self.start(ticketnum)
        self.git.upload()
        if oldticket is not None:
            self.git.switch(oldticket)

    def sync(self):
        curticket = self.git.current_ticket()
        if self.UI.confirm("Are you sure you want to save your changes and sync to the most recent development version of Sage?"):
            self.git.save()
            self.git.sync()
        if curticket is not None and curticket.isdigit():
            dependencies = self.trac.dependencies(curticket)
            for dep in dependencies:
                if self.git.needs_update(dep) and self.UI.confirm("Do you want to sync to the latest version of #%s"%(dep)):
                    self.git.sync(dep)

    def vanilla(self, release=False):
        if self.UI.confirm("Are you sure you want to revert to %s?"%(self.git.released_sage_ver() if release else "a plain development version")):
            if self.git.has_uncommitted_changes():
                dest = self.UI.get_input("Where would you like to save your changes?",["current branch","stash"],"current branch")
                if dest == "stash":
                    self.git.stash()
                else:
                    self.git.save()
            self.git.vanilla(release)

    def review(self, ticketnum, user=None):
        if self.UI.confirm("Are you sure you want to download and review #%s"%(ticketnum)):
            self.git.review(ticketnum, user)
            if self.UI.confirm("Would you like to rebuild Sage?"):
                call("sage -b", shell=True)

    def status(self):
        self.git.execute("status")

    def list(self):
        self.git.execute("branch")

    def diff(self, vs_unstable=False):
        if vs_unstable:
            self.git.execute("diff", self.git._unstable)
        else:
            self.git.execute("diff")

    def prune(self):
        if self.UI.confirm("Are you sure you want to delete all branches that have been merged into unstable?"):
            self.git.prune()

    def abandon(self, ticketnum):
        if self.UI.confirm("Are you sure you want to delete your work on #%s?"%(ticketnum), default_yes=False):
            self.git.abandon(ticketnum)

    def help(self):
        raise NotImplementedError
