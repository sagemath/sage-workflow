from subprocess import call, check_output, CalledProcessError
import types

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

    def branch_exists(self, branch):
        return NotImplementedError

    def create_branch(self, branchname, at_unstable=False):
        if at_unstable:
            self.execute("branch", branchname, self._get_unstable())
        else:
            self.execute("branch", branchname)

    def fetch_branch(self, branchname):
        # fetches a branch from remote, including dependencies if
        # necessary. Doesn't switch
        raise NotImplementedError

    def switch_branch(self, branchname):
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
        # deletes the branch
        raise NotImplementedError

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
