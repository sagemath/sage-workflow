import os
from subprocess import call
from trac_interface import TracInterface
from git_interface import GitInterface
from user_interface import CmdLineInterface

DOT_SAGE = os.environ.get('DOT_SAGE',os.path.join(os.environ['HOME'], '.sage'))

class SageDev(object):
    def __init__(self, devrc=os.path.join(DOT_SAGE, 'devrc'), gitcmd='git',
                 realm='sage.math.washington.edu',
                 trac='http://boxen.math.washington.edu:8888/sage_trac/',
                 ssh_pubkey_file=None,
                 ssh_passphrase="",
                 ssh_comment=None):
        self.UI = CmdLineInterface()
        username, password, has_ssh_key = self._process_rc(devrc)
        self._username = username
        self.git = GitInterface(self.UI, username, gitcmd)
        self.trac = TracInterface(self.UI, realm, trac, username, password)
        if not has_ssh_key:
            self._send_ssh_key(username, passwd, devrc, ssh_pubkey_file, ssh_passphrase)

    def _get_user_info(self):
        username = self.UI.get_input("Please enter your trac username: ")
        # we should eventually use a password entering mechanism (ie *s or blanks when typing)
        passwd = self.UI.get_input("Please enter your trac password (stored in plaintext on your filesystem): ")
        return username, passwd

    def _send_ssh_key(self, username, passwd, devrc, ssh_pubkey_file, ssh_passphrase, comment):
        if ssh_pubkey_file is None:
            ssh_pubkey_file = os.path.join(os.environ['HOME'], '.ssh', 'id_rsa.pub')
        if not os.path.exists(ssh_pubkey_file):
            if not ssh_pubkey_file.endswith(".pub"):
                raise ValueError("public key filename must end with .pub")
            ssh_prikey_file = ssh_pubkey_file[:-4]
            cmd = ["ssh-keygen", "-q", "-t", "rsa", "-f", ssh_prikey_file, "-N", ssh_passphrase]
            if comment is not None:
                cmd.extend(["-C", comment])
            call(cmd)
        with open(devrc, "w") as F:
            F.write("v0\n%s\n%s\nssh_sent"%(username, passwd))

    def _process_rc(self, devrc):
        if not os.path.exists(devrc):
            username, passwd = self._get_user_info()
            has_ssh_key = False
        else:
            with open(devrc) as F:
                L = list(F)
                if len(L) < 3:
                    username, passwd = self._get_user_info()
                else:
                    username, passwd = L[1].strip(), L[2].strip()
                has_ssh_key = len(L) >= 4
        return username, passwd, has_ssh_key

    def current_ticket(self):
        curbranch = self.git.current_branch()
        if curbranch is not None and curbranch.startswith("t/"):
            return curbranch[2:]
        else:
            return None

    def start(self, ticketnum = None):
        curticket = self.current_ticket()
        if ticketnum is None:
            # User wants to create a ticket
            ticketnum = self.trac.create_ticket_interactive()
            if ticketnum is None:
                # They didn't succeed.
                return
            if curticket is not None:
                if self.UI.confirm("Should the new ticket depend on #%s?"%(curticket)):
                    self.git.create_branch(self, ticketnum)
                    self.trac.add_dependency(self, ticketnum, curticket)
                else:
                    self.git.create_branch(self, ticketnum, at_master=True)
        if not self.exists(ticketnum):
            self.git.fetch_ticket(ticketnum)
        self.git.switch(ticketnum)

    def save(self):
        curticket = self.git.current_ticket()
        if self.UI.confirm("Are you sure you want to save your changes to ticket #%s?"%(curticket)):
            self.git.save()
            if self.UI.confirm("Would you like to upload the changes?"):
                self.git.upload()

    def upload(self, ticketnum=None):
        oldticket = self.git.current_ticket()
        if ticketnum is None or ticketnum == oldticket:
            oldticket = None
            ticketnum = self.git.current_ticket()
            if not self.UI.confirm("Are you sure you want to upload your changes to ticket #%s?"%(ticketnum)):
                return
        elif not self.exists(ticketnum):
            self.UI.show("You don't have a branch for ticket %s"%(ticketnum))
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
            raise NotImplementedError
            if self.UI.confirm("Would you like to rebuild Sage?"):
                call("sage -b", shell=True)

    #def status(self):
    #    self.git.execute("status")

    #def list(self):
    #    self.git.execute("branch")

    def diff(self, vs_unstable=False):
        if vs_unstable:
            self.git.execute("diff", self.git._unstable)
        else:
            self.git.execute("diff")

    def prune_merged(self):
        # gets rid of branches that have been merged into unstable
        # Do we need this confirmation?  This is pretty harmless....
        if self.UI.confirm("Are you sure you want to abandon all branches that have been merged into master?"):
            for branch in self.git.local_branches():
                if self.git.is_ancestor_of(branch, "master"):
                    self.UI.show("Abandoning %s"("#%s"%(branch[2:]) if branch.startswith("t/") else branch))
                    self.git.abandon(branch)

    def abandon(self, ticketnum):
        if self.UI.confirm("Are you sure you want to delete your work on #%s?"%(ticketnum), default_yes=False):
            self.git.abandon(ticketnum)

    def help(self):
        raise NotImplementedError

    def gather(self, branchname, *inputs):
        # Creates a join of inputs and stores that in a branch, switching to it.
        if len(inputs) == 0:
            self.UI.show("Please include at least one input branch")
            return
        if self.git.branch_exists(branchname):
            if not self.UI.confirm("The %s branch already exists; do you want to merge into it?", default_yes=False):
                return
        else:
            self.git.execute_silent("branch", branchname, inputs[0])
            inputs = inputs[1:]
        # The following will deal with outstanding changes
        self.git.switch_branch(branchname)
        if len(inputs) > 1:
            self.git.execute("merge", *inputs, q=True, m="Gathering %s into branch %s"%(", ".join(inputs), branchname))

    def show_dependencies(self, ticketnum=None, all=True):
        raise NotImplementedError

    def update_dependencies(self, ticketnum=None, dependencynum=None, all=False):
        # Merge in most recent changes from dependency(ies)
        raise NotImplementedError

    def add_dependency(self, ticketnum=None, dependencynum=None):
        # Do we want to do this?
        raise NotImplementedError

    def import_patch(self, ticketnum, patchname=None, url=None):
        # Import a patch from trac, in either new or old repo structure
        raise NotImplementedError

    def dependency_join(self, ticketnum=None):
        raise NotImplementedError

    def exists(self, ticketnum):
        # Determines whether ticket exists locally
        return self.git.branch_exists("t/" + str(ticketnum))

    def _local_branchname(self, ticketnum):
        if ticketnum is None:
            return "master"
        return "t/" + str(ticketnum)

    def _remote_branchname(self, ticketnum):
        if ticketnum is None:
            return "master"
        return "%s/%s"(self._username, ticketnum)

    def needs_update(self, ticketnum):
        # returns True if there are changes in the ticket on trac that
        # aren't included in the current ticket
        raise NotImplementedError

    def sync(self, ticketnum=None):
        # pulls in changes from trac and rebases the current branch to
        # them. ticketnum=None syncs unstable.
        raise NotImplementedError
