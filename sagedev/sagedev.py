import os
from subprocess import call
from trac_interface import TracInterface
from git_interface import GitInterface
from user_interface import CmdLineInterface

class SageDev(object):
    def __init__(self, devrc='~/.sage/devrc', gitcmd='git',
                 realm='sage.math.washington.edu',
                 trac='http://trac.sagemath.org/experimental/'):
        devrc = os.path.expanduser(devrc)
        username, password = self.process_rc(devrc)
        self.UI = CmdLineInterface()
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
                if self.UI.confirm("Should the new ticket depend on #%s?"%(curticket)):
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

    def upload(self, ticketnum=None):
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
