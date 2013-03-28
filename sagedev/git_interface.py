import functools
import os.path
from subprocess import call, check_output, CalledProcessError
import types
import cPickle
from cStringIO import StringIO
import random
import os

class SavingDict(dict):
    def __init__(self, filename, **kwds):
        self._filename = filename
        dict.__init__(self, **kwds)

    def __setitem__(self, key, value):
        dict.__setitem__(self, key, value)
        tmpfile = self._filename + '%016x'%(random.randrange(256**8))
        s = cPickle.dumps(self, protocol=2)
        with open(tmpfile, 'wb') as F:
            F.write(s)
        # This move is atomic
        os.rename(tmpfile, self._filename)
        os.unlink(tmpfile)

class GitInterface(object):
    def __init__(self, UI, config):
        self._config = config
        self._dot_git = config['dot_git']
        self.UI = UI
        ssh_git = 'ssh -i "%s"' % config['sshkeyfile']
        ssh_git = 'GIT_SSH="%s" ' % ssh_git
        self._gitcmd = ssh_git + config['gitcmd']
        self._ticket, self._branch = self._load_ticket_branches(config['ticketfile'], config['branchfile'])

    def _load_ticket_branches(self, ticket_file, branch_file):
        if os.path.exists(ticket_file):
            with open(ticket_file) as F:
                s = F.read()
                unpickler = cPickle.Unpickler(StringIO(s))
                ticket_dict = unpickle.load()
        else:
            ticket_dict = {}
        if os.path.exists(branch_file):
            with open(branch_file) as F:
                s = F.read()
                unpickler = cPickle.Unpickler(StringIO(s))
                branch_dict = unpickle.load()
        else:
            branch_dict = {}
        return SavingDict(ticket_file, **ticket_dict), SavingDict(branch_file, **branch_dict)

    def released_sage_ver(self):
        # should return a string with the most recent released version
        # of Sage (in this branch's past?)
        raise NotImplementedError

    def get_state(self):
        ret = []
        if os.path.exists(os.path.join(self._dot_git,"rebase-apply")):
            ret.append("am")
        return ret

    def reset_to_clean_state(self, interactive=True):
        state = self.get_state()
        if not state:
            return True
        if state:
            state = state[0]
        if state == "am":
            if interactive and not self.UI.confirm("Your repository is in an unclean state. It seems you are in the middle of a merge of some sort. To run this command you have to reset your respository to a clean state. Do you want me to reset your respository? (This will discard any changes which are not commited.)"):
                return False

            self.am("--abort")
            return self.reset_to_clean_state(interactive=interactive)
        else:
            raise NotImplementedError(state)

    def reset_to_clean_working_directory(self, interactive=True):
        if not self.has_uncommitted_changes():
            return True

        if interactive and not self.UI.confirm("You have uncommited changes in your working directory. To run this command you have to discard your changes. Do you want me to discard any changes which are not commited?"):
            return False

        self.reset("--hard")

        return True

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
        if diff:
            self.execute("diff")
        added = self.files_added()
        for F in added:
            toadd = self.UI.confirm("Would you like to start tracking %s?"%F)
            if toadd:
                self.add_file(F)
        msg = self.UI.get_input("Please enter a commit message:")
        self.commit_all(m=msg)

    def local_branches(self):
        """
        Return the list of the local branches

        EXAMPLES::

            sage: git.local_branches()
            ['master', 't/13624', 't/13838']
        """
        result = self._run_git("stdout", "show-ref", ["--heads"], {}).split()
        result = [result[2*i+1][11:] for i in range(len(result)/2)]
        return result

    def current_branch(self):
        try:
            branch = self.read_output('symbolic-ref', 'HEAD').strip()
            if not branch.startswith('refs/heads/'):
                raise RuntimeError('HEAD is bizarre!')
            return branch[11:]
        except CalledProcessError:
            return None

    def _branch_to_ticketnum(self, branchname):
        x = branchname.split('/')
        self._validate_local_name(x)
        if x[0] == 'me' or x[0] == 'ticket':
            return x[1]
        else:
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
        return 'u/' + self._config['username'] + '/' + branchname

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
            if x[1] != self._config['username']: raise ValueError("Local name should not include username")
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
            if x[1] == self._config['username']:
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

        EXAMPLES::

            sage: import sagedev
            sage: cd ..
            sage: git = sagedev.SageDev().git
            sage: git.branch_exists("master")    # random
            'c4512c860a162c962073a83fd08e984674dd4f44'
            sage: type(git.branch_exists("master"))
            str
            sage: len(git.branch_exists("master"))
            40
            sage: git.branch_exists("asdlkfjasdlf")
        """
        # TODO: optimize and make this atomic :-)
        ref = "refs/heads/%s"%branch
        if self.execute("show-ref", "--quiet", "--verify", ref):
            return None
        else:
            return self.read_output("show-ref", "--verify", ref).split()[0]

    def ref_exists(self, ref):
        raise NotImplementedError

    def create_branch(self, branchname, location=None):
        if branchname in ["t", "u", "me", "u/" + self._config['username'], "ticket"]:
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
        # create temp branch, commit changes, rebase, fast-forward....
        raise NotImplementedError

    def vanilla(self, release=False):
        # switch to unstable branch in the past (release=False) or a
        # given named release
        if release is False:
            self.switch_branch("master")
        elif release is True:
            raise NotImplementedError
        else:
            release = self._validate_release_name(release)
            if not self.branch_exists(release):
                self.fetch_release(release)
            self.switch_branch(release)

    def abandon(self, branchname):
        """
        Move to trash/
        """
        remotename = self._local_to_remote_name(branchname)
        trashname = "trash/" + branchname
        oldtrash = self.branch_exists(trashname)
        if oldtrash:
            self.UI.show("Overwriting %s in trash"(oldtrash))
        self.execute("branch", branchname, trashname, M=True)
        # Need to delete remote branch (and have a hook move it to /g/abandoned/ and update the trac symlink)

def git_cmd_wrapper(git_cmd):
    def f(self, *args, **kwds):
        return self.execute(git_cmd, *args, **kwds)
    return f

for git_cmd in ["add","am","apply","bisect","branch","checkout",
               "clone","commit","diff","fetch",
               "grep","init","log","merge",
               "mv","pull","push","rebase",
               "reset","rm","show","stash",
               "status","tag"]:
    setattr(GitInterface, git_cmd, git_cmd_wrapper(git_cmd))
