from subprocess import call

class GitInterface(object):
    def __init__(self, UI, username, gitcmd='git'):
        self._gitcmd = gitcmd
        self._username = username
        self.UI = UI
        # Need to set unstable
        raise NotImplementedError

    def released_sage_ver(self):
        # should return a string with the most recent released version
        # of Sage (in this branch's past?)
        raise NotImplementedError

    def _clean_str(self, s):
        # for now, no error checking
        return str(s)

    def execute(self, cmd, *args, **kwds):
        s = self._gitcmd + " " + cmd
        dryrun = kwds.pop("dryrun", None)
        for k, v in kwds.iteritems():
            if len(k) == 1:
                k = ' -' + k
            else:
                k = ' --' + k
            if v is True:
                s += k
            else:
                s += k + " " + self._clean_str(v)
        if args:
            s += " " + " ".join([self._clean_str(a) for a in args])
        if dryrun:
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
        # Returns True if there are uncommitted changes or non-added files
        raise NotImplementedError

    def commit_all(self, *args, **kwds):
        # if files are non-tracked and user doesn't want to add any of
        # them, there might be no changes being committed here....
        kwds['a'] = True
        self.execute("commit", *args, **kwds)

    def exists(self, ticketnum):
        # Returns True if ticket exists
        raise NotImplementedError

    def stash(self):
        # Should stash changes
        raise NotImplementedError

    def files_added(self):
        # Should return a list of filenames of files that the user
        # might want to add
        raise NotImplementedError

    def add_file(self, F):
        # Should add the file with filename F
        raise NotImplementedError

    def save(self):
        diff = self.UI.confirm("Would you like to see a diff of the changes?",
                               default_yes=False)
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
            self.execute("branch", self._local_branchname(ticketnum),
                     self._local_branchname(None))
        else:
            self.execute("branch", self._local_branchname(ticketnum))

    def fetch_branch(self, ticketnum):
        # fetches a branch from remote, including dependencies if
        # necessary. Doesn't switch
        raise NotImplementedError

    def switch(self, ticketnum):
        # switches to another ticket
        raise NotImplementedError

    def move_uncommited_changes(self, ticketnum):
        # create temp branch, commit chanes, rebase, fast-forward....
        raise NotImplementedError

    def needs_update(self, ticketnum):
        # returns True if there are changes in the ticket on trac that
        # aren't included in the current ticket
        raise NotImplementedError

    def sync(self, ticketnum=None):
        # pulls in changes from trac and rebases the current branch to
        # them. ticketnum=None syncs unstable.
        raise NotImplementedError

    def vanilla(self, release=False):
        # switch to unstable branch in the past (release=False) or a
        # given named release
        raise NotImplementedError

    def review(self, ticketnum, user):
        # download a remote branch to review
        raise NotImplementedError

    def prune(self):
        # gets rid of branches that have been merged into unstable
        raise NotImplementedError

    def abandon(self, ticketnum):
        # deletes the branch
        raise NotImplementedError
