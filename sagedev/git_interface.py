from subprocess import call, check_output, CalledProcessError
import types

class GitInterface(object):
    def __init__(self, UI, username, gitcmd='git'):
        self._gitcmd = gitcmd
        self._username = username
        self.UI = UI

    def released_sage_ver(self):
        # should return a string with the most recent released version
        # of Sage (in this branch's past?)
        raise NotImplementedError

    def _clean_str(self, s):
        # for now, no error checking
        return str(s)

    def _run_git(self, output_type, cmd, args, kwds):
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
            if output_type == 'retval':
                return call(s, shell=True)
            elif output_type == 'stdout':
                return check_output(s, shell=True)

    def execute(self, cmd, *args, **kwds):
        return self._run_git('retval', cmd, args, kwds)

    def execute_silent(self, cmd, *args, **kwds):
        return self._run_git('retval', cmd, args + ('>/dev/null',), kwds)

    def read_output(self, cmd, *args, **kwds):
        return self._run_git('stdout', cmd, args, kwds)


    def is_ancestor_of(self, a, b):
        revs = self.read_output('rev-list', '{}..{}'.format(b, a)).splitlines()
        return len(revs) == 0

    def has_uncommitted_changes(self):
        # Returns True if there are uncommitted changes
        return self.execute('diff', quiet=True) != 0

    def commit_all(self, *args, **kwds):
        # if files are non-tracked and user doesn't want to add any of
        # them, there might be no changes being committed here....
        kwds['a'] = True
        self.execute("commit", *args, **kwds)

    def unknown_files(self):
        # Should return a list of filenames of files that the user
        # might want to add
        status_output = self.read_output("status", porcelain=True)
        files = [line[3:] for line in status_output.splitlines()
                          if line[:2] == '??']
        return files

    def add_file(self, F):
        # Should add the file with filename F
        self.execute('add', "'{}'".format(F))

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

    def local_branches(self):
        raise NotImplementedError

    def current_branch(self):
        try:
            branch = self.read_output('symbolic-ref', 'HEAD').strip()
            if not branch.startswith('refs/heads/'):
                raise RuntimeError('HEAD is bizarre!')
            return branch[11:]
        except CalledProcessError:
            return None

    def _branch_printname(self, branchname):
        if branchname[:2] == 't/':
            return '#' + branchname[2:]
        else:
            return branchname

    def _local_to_remote_name(self, branchname):
        """
        me/12345 -> u/roed/t/12345
        ticket/12345 -> u/roed/t/12345
        padics/feature -> g/padics/feature
        localname -> u/roed/localname
        """
        self._validate_local_name(branchname)
        if '/' in branchname:
            x = branchname.split('/')
            group = x[0]
            branchname = '/'.join(x[1:])
            if group == 'me' or group == 'ticket':
                branchname = 't/' + branchname
            else:
                return 'g/' + group + '/' + branchname
        return 'u/' + self._username + '/' + branchname

    def _validate_remote_name(self, x):
        if len(x) == 0: raise ValueError("Empty list")
        if x[0] == 'ticket':
            if len(x) > 1: raise ValueError("Too many slashes in branch name")
            if not x[1].isdigit(): raise ValueError("Ticket branch not numeric")
        elif x[0] == 'u':
            if len(x) == 4:
                if x[2] != 't': raise ValueError("Improperly formatted branch name")
                if not x[3].isdigit(): raise ValueError("Ticket branch not numeric")
            elif len(x) == 3:
                self._validate_local_name([x[2]])
            else:
                raise ValueError("Wrong number of slashes in branch name")
        elif x[0] == 'g':
            if len(x) != 3: raise ValueError("Wrong number of slashes in branch name")
            self._validate_atomic_name(x[1])
            self._validate_atomic_name(x[2])
        else:
            raise ValueError("Unrecognized remote branch format")

    def _validate_atomic_name(self, name):
        if '/' in name: raise ValueError("No slashes allowed in atomic name")
        if name in ["t", "u", "g", "me", "ticket", "trash"]:
            raise ValueError("Invalid atomic name")

    def _validate_local_name(self, x):
        if len(x) == 0: raise ValueError("Empty list")
        if len(x) == 1:
            self._validate_atomic_name(x[0])
        elif x[0] in ['me', 'ticket']:
            if len(x) > 2: raise ValueError("Too many slashes in branch name")
            if not x[1].isdigit(): raise ValueError("Ticket branch not numeric")
        elif x[0] == 'u':
            if x[1] != self._username: raise ValueError("Local name should not include username")
            self._validate_remote_name(x)
        elif len(x) == 2:
            self._validate_atomic_name(x[0])
            self._validate_atomic_name(x[1])
        else:
            raise ValueError("Too many slashes in branch name")

    def _remote_to_local_name(self, branchname):
        """
        ticket/12345 -> ticket/12345
        u/roed/t/12345 -> me/12345
        u/saraedum/t/12345 -> u/saraedum/t/12345
        g/padics/feature -> padics/feature
        u/roed/localname -> localname
        """
        self._validate_remote_name(branchname)
        x = branchname.split('/')
        self._validate_remote_name(x)
        if x[0] == 'ticket':
            return '/'.join(x)
        elif x[0] == 'u':
            if x[1] == self._username:
                if x[2] == 't':
                    return 'me/%s'%(x[3])
                return x[2]
            return '/'.join(x)
        elif x[0] == 'g':
            return '/'.join(x[1:])
        else:
            raise RuntimeError # should never reach here

    def branch_exists(self, branch):
        """
        Returns the commit id of the local branch, or None if branch does not exist.
        """
        raise NotImplementedError

    def ref_exists(self, ref):
        raise NotImplementedError

    def create_branch(self, branchname, location=None):
        if branchname in ["t", "u", "me", "u/" + self._username, "ticket"]:
            raise ValueError("Bad branchname")
                                
        if location is None:
            self.execute("branch", branchname)
        elif self.ref_exists(location):
            self.execute("branch", branchname, location)
        else:
            self.UI.show("Branch not created: %s does not exist"%location)

    def rename_branch(self, oldname, newname):
        self._validate_local_name(newname)
        self.execute("branch", oldname, newname, m=True)

    def fetch_ticket(self, ticketnum, user=None):
        # fetches a branch from remote, including dependencies if
        # necessary. Doesn't switch
        raise NotImplementedError

    def fetch_project(self, group, branchname):
        raise NotImplementedError

    def switch_branch(self, branchname):
        if self.has_uncommitted_changes():
            curbranch = self.current_branch()
            if curbranch is None:
                options = ["new branch", "stash"]
            else:
                options = ["current branch", "new branch", "stash"]
            dest = self.UI.get_input("Where do you want to commit your changes?", options)
            if dest == "stash":
                self.stash()
            elif dest == "current branch":
                self.save()
        
        # switches to another ticket
        raise NotImplementedError

    def move_uncommited_changes(self, branchname):
        # create temp branch, commit chanes, rebase, fast-forward....
        raise NotImplementedError

    def vanilla(self, release=False):
        # switch to unstable branch in the past (release=False) or a
        # given named release
        raise NotImplementedError

    def abandon(self, branchname):
        """
        Move to trash/
        """
        trashname = "trash/" + branchname
        oldtrash = self.branch_exists(trashname)
        if oldtrash:
            self.UI.show("Overwriting %s in trash"(oldtrash))
        self.execute("branch", branchname, trashname, M=True)

def git_cmd_wrapper(git_cmd, interface):
    def f(self, *args, **kwds):
        return self.execute(git_cmd, *args, **kwds)
    return types.MethodType(f, interface, interface)

for git_cmd in ["add","bisect","branch","checkout",
               "clone","commit","diff","fetch",
               "grep","init","log","merge",
               "mv","pull","push","rebase",
               "reset","rm","show","stash",
               "status","tag"]:
    setattr(GitInterface, git_cmd, git_cmd_wrapper(git_cmd, GitInterface))
