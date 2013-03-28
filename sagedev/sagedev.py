import os
import os.path
import shutil
import atexit
import re
import time
import tempfile
import email.utils
import ConfigParser as configparser
from datetime import datetime
from subprocess import call, check_call
from trac_interface import TracInterface
from git_interface import GitInterface
from user_interface import CmdLineInterface

def switch_ticket(ticket, branchname=None, offline=False):
    """
    Switch to a branch associated to ``ticket``.

    INPUT:

    - ``ticket`` -- an integer or a string. If a string, then switch to the
      branch ``ticket`` (``branchname`` must be ``None`` in this case).  If an
      integer, it must be the number of a ticket. If ``branchname`` is
      ``None``, then a new name for a ``branch`` is chosen. If ``branchname``
      is the name of a branch that exists locally, then associate this branch
      to ``ticket``. Otherwise, switch to a new branch ``branchname``. If
      ``offline`` is False, download the branch mentioned on the trac ticket
      (if there is such a branch) to that branch.

    - ``branchname`` -- a string or ``None`` (default: ``None``)

    - ``offline`` -- a boolean (default: ``False``)

    """
    raise NotImplementedError

def create_ticket(branchname=None, remote_branch=None):
    """
    Create a new ticket on trac.

    INPUT:

    - ``branchname`` -- a string of ``None`` (default: ``None``), the name of
      the local branch that will used for the new ticket; if ``None``, a name
      will be chosen automatically.

    - ``remote_branch`` -- a string or ``Neon`` (default: ``None``), if a
      string, the name of the remote branch this branch should be tracking.

    """
    raise NotImplementedError

def commit(message=None, interactive=False):
    """
    Create a commit from the pending changes on the current branch.

    INPUT:

    - ``message`` -- a string or ``None`` (default: ``None``), the message of
      the commit; if ``None``, prompt for a message.

    - ``interactive`` -- a boolean (default: ``False``), interactively select
      which part of the changes should be part of the commit. Prompts for the
      addition of untracked files even if ``interactive`` is ``False``.

    """
    raise NotImplementedError

def upload(ticket=None, remote_branch=None, force=False):
    """
    Upload the current branch to the sage repository.

    INPUT:

    - ``ticket`` -- an integer or ``None`` (default: ``None``), if an integer
      or if this branch is associated to a ticket, set the trac ticket to point
      to this branch.

    - ``remote_branch`` -- a string or ``None`` (default: ``None``), the remote
      branch to upload to; if ``None``, then a default is chosen (how?)

    - ``force`` -- a boolean (default: ``False``), whether to upload if this is
      not a fast-forward.

    """
    raise NotImplementedError

def download(ticket=None, force=False):
    """
    Download the changes made to a remote branch into the current branch.

    INPUT:

    - ``ticket`` -- an integer or ``None`` (default: ``None``), if ``None`` 


    force - dont merge, just take the upstream version
    """

def remote_status(ticket=None):
    """
    Show the remote status of a ticket or a branch.

    If ``ticket`` is ``None`` and we're currently on a branch associated to a
    ticket, then show the log and difference of the upstream ticket.

    ... Show the log of ``tickets`` or of the current ticket if ``None``. + Possibly some more info
    ... If not a ticket, then the remote tracking branch.
    ... Of all your tickets if ``'all'``.
    ... patchbot status
    """

def diff(base="master/dependencies/'commit default'/..."):
    """

    """

def prune_closed_tickets():
    """
    Remove tickets that have already been merged...
    """

def abandon_ticket(ticket=None):
    """
    Move to abandoned
    """

def gather(tickets, branchname):
    """
    Create a new brach with all tickets applied.
    """

def show_dependencies(ticket=None, all=False): # all = recursive
    """
    Show the dependencies of the given ticket.

    INPUT:

    - ``ticket`` -- string, int or None (default ``None``), the ticket
      for which dependencies are desired.  An int indicates a ticket
      number while a string indicates a branch name; ``None`` asks for
      the dependencies of the current ticket.

    - ``all`` -- boolean (default ``True``), whether to recursively
      list all tickets on which this ticket depends (in depth-first
      order).

    .. NOTE::

        Ticket dependencies are stored locally and only updated with
        respect to the remote server during :meth:`upload` and
        :meth:`download`.
    """

def merge(self, ticket="master", create_dependency=True, download=False):
    """
    Merge changes from another branch into the current branch.

    INPUT:

    - ``ticket`` -- string or int (default ``"master"``), a branch,
      ticket number or the current set of dependencies (indicated by
      the string ``"dependencies"``): the source of the changes to be
      merged.  If ``ticket = "dependencies"`` then each updated
      dependency is merged in one by one, starting with the one listed
      first in the dependencies field on trac.  An int indicates a
      ticket number while a string indicates a branch name.

    - ``create_dependency`` -- boolean (default ``True``), whether to
      append the other ticket to the list of dependencies.  Listing
      the other ticket as a dependency has the following consequences:

      - the other ticket must be positively reviewed and merged before
        this ticket may be merged into master.  The commits included
        from a dependency don't need to be reviewed in this ticket,
        whereas commits reviewed in this ticket from a non-dependency
        may make reviewing the other ticket easier.

      - you can more easily merge in future changes to depdencies.  So
        if you need a feature from another ticket it may be
        appropriate to create a dependency to that you may more easily
        benefit from others' work on that ticket.

      - if you depend on another ticket then you need to worry about
        the progress on that ticket.  If that ticket is still being
        actively developed then you may need to make many merges to
        keep up.

      Note that dependencies are stored locally and only updated with
      respect to the remote server during :meth:`upload` and
      :meth:`download`.

    - ``download`` -- boolean (default ``False``), whether to download
      the most recent version of the other ticket(s) before merging.

    .. SEEALSO::

    - :meth:`show_dependencies` -- see the current dependencies.

    - :meth:`GitInterface.merge` -- git's merge command has more
      options and can merge multiple branches at once.
    """

def local_tickets(self, abandoned=False):
    """
    Print the tickets currently being worked on in your local
    repository.

    This function will show the branch names as well as the ticket
    numbers for all active tickets.  It will also show local branches
    that are not associated to ticket numbers.

    INPUT:

    - ``abandoned`` -- boolean (default ``False), whether to show abandoned branches.

    .. SEEALSO::

    - :meth:`abandon_ticket` -- hide tickets from this method.

    - :meth:`remote_status` -- also show status compared to the trac
      server.
    """

##
## Everything below this line should probably not be part of the public interface.
##

DOT_SAGE = os.environ.get('DOT_SAGE',os.path.join(os.environ['HOME'], '.sage'))

# regular expressions to parse mercurial patches
HG_HEADER_REGEX = re.compile(r"^# HG changeset patch$")
HG_USER_REGEX = re.compile(r"^# User (.*)$")
HG_DATE_REGEX = re.compile(r"^# Date (\d+) (-?\d+)$")
HG_NODE_REGEX = re.compile(r"^# Node ID ([0-9a-f]+)$")
HG_PARENT_REGEX = re.compile(r"^# Parent +([0-9a-f]+)$")
HG_DIFF_REGEX = re.compile(r"^diff -r [0-9a-f]+ -r [0-9a-f]+ (.*)$")
PM_DIFF_REGEX = re.compile(r"^(?:(?:\+\+\+)|(?:---)) [ab]/([^ ]*)(?: .*)?$")

# regular expressions to parse git patches -- at least those created by us
GIT_FROM_REGEX = re.compile(r"^From: (.*)$")
GIT_SUBJECT_REGEX = re.compile(r"^Subject: (.*)$")
GIT_DATE_REGEX = re.compile(r"^Date: (.*)$")
GIT_DIFF_REGEX = re.compile(r"^diff --git a/(.*) b/(.*)$") # this regex should work for our patches since we do not have spaces in file names

# regular expressions to determine whether a path was written for the new git
# repository of for the old hg repository
HG_PATH_REGEX = re.compile(r"^(?=sage/)|(?=module_list\.py)|(?=setup\.py)|(?=c_lib/)")
GIT_PATH_REGEX = re.compile(r"^(?=src/)")

# a wrapper to be able to index the configparser as a dictionary of dictionaries,
# like in the python3 api.
class ConfigParser(configparser.ConfigParser):
    def keys(self):
        return self.sections()

    def values(self):
        return [self[key] for key in self.keys()]

    def __getitem__(self, section):
        class IndexableForSection(object):
            def __init__(this, section):
                this._section = section
            def __getitem__(this, option):
                return self.get(this._section, option)
            def __setitem__(this, option, value):
                self.set(this._section, option, value)
            def getboolean(this, option):
                return self.getboolean(this._section, option)

        return IndexableForSection(section)

    def __setitem__(self, section, dictionary):
        if self.has_section(section):
            self.remove_section(section)
        self.add_section(section)
        for option, value in dictionary.iteritems():
            self.set(section, option, value)

REALM = 'sage.math.washington.edu'
TRAC_SERVER_URI = 'https://trac.tangentspace.org/sage_trac'

class SageDev(object):
    def __init__(self, devrc=os.path.join(DOT_SAGE, 'devrc'),
                 ssh_pubkey_file=None, ssh_passphrase="", ssh_comment=None):
        self.UI = CmdLineInterface()
        self._devrc = devrc
        self._config = cfg = ConfigParser()
        self._read_config()

        if not cfg.has_option('trac','realm'):
            cfg.set('trac','realm',REALM)
        if not cfg.has_option('trac','server'):
            cfg.set('trac','server',TRAC_SERVER_URI)
        if cfg['trac']['server'][-1] != '/':
            cfg['trac']['server'] += '/'

        if not cfg.has_option('git','ticketfile'):
            cfg.set('git','ticketfile',os.path.join(DOT_SAGE, 'branch_to_ticket'))
        if not cfg.has_option('git','branchfile'):
            cfg.set('git','branchfile',os.path.join(DOT_SAGE, 'ticket_to_branch'))
        if not cfg.has_option('git','dot_git'):
            dot_git = os.environ.get("SAGE_DOT_GIT", ".git")
            if not os.path.exists(dot_git):
                raise ValueError("`%s` does not point to an existing directory."%dot_git)
            cfg.set('git','dot_git',dot_git)
        cfg.set('git','username',cfg['trac']['username'])
        if not cfg.has_option('git', 'sshkeyfile'):
            cfg.set('git','sshkeyfile',os.path.join(os.environ['HOME'], '.ssh', 'id_rsa'))
        keyfile = cfg['git']['sshkeyfile']
        try:
            with open(keyfile, 'r') as F:
                pass
            with open(keyfile + '.pub', 'r') as F:
                pubkey = F.read()
        except IOError:
            self.UI.show("Generating ssh key....")
            success = call(["ssh-keygen", "-q", "-N", '""', "-f", keyfile])
            if success == 0:
                self.UI.show("Ssh key successfully generated")
                with open(keyfile + '.pub', 'r') as F:
                    pubkey = F.read().strip()
            else:
                raise RuntimeError("Ssh key generation failed.  Please create a key in %s and retry"%(keyfile))
        if not cfg.has_option('git','gitcmd'):
            cfg.set('git','gitcmd','git')
        self.trac = TracInterface(self.UI, cfg['trac'])
        if not cfg.has_option('trac', 'sshkey_set'):
            if self.UI.confirm("You have not yet uploaded an ssh key to the server." +
                               "Would you like to upload one now?"):
                self.trac.sshkeys.addkey(pubkey)
                cfg.set('trac','sshkey_set')
        self.git = GitInterface(self.UI, cfg['git'])
        self.tmp_dir = None
        self._write_config()

    def _get_tmp_dir(self):
        if self.tmp_dir is None:
            self.tmp_dir = tempfile.mkdtemp()
            atexit.register(lambda: shutil.rmtree(self.tmp_dir))
        return self.tmp_dir

    def _get_user_info(self):
        username = self.UI.get_input("Please enter your trac username: ")
        # we should eventually use a password entering mechanism (ie *s or blanks when typing)
        passwd, confirm = 0, 1
        while passwd != confirm:
            msg = "Please enter your trac password" + (" (stored in plaintext on your filesystem)" if passwd == 0 else "") + ": "
            passwd = self.UI.get_password(msg)
            confirm = self.UI.get_password("Please confirm your trac password: ")
            if passwd != confirm:
                self.UI.show("Passwords do not agree")
        return username, passwd

    def _read_config(self):
        cfg = self._config
        if os.path.exists(self._devrc):
            cfg.read(self._devrc)
        if not cfg.has_section('trac'): cfg.add_section('trac')
        if not cfg.has_section('git'): cfg.add_section('git')
        if not (cfg.has_option('trac', 'username') and cfg.has_option('trac', 'password')):
            username, password = self._get_user_info()
            cfg.set('trac','username',username)
            cfg.set('trac','password',password)

    def _write_config(self):
        with open(self._devrc, 'w') as F:
            self._config.write(F)
        # set the configuration file to read only by this user,
        # because it may contain the trac password
        os.chmod(self._devrc, 0600)

    def current_ticket(self, error=False):
        curbranch = self.git.current_branch()
        if curbranch is not None and curbranch in self.git._ticket:
            return self.git._ticket[curbranch]
        if error: raise ValueError("You must specify a ticket")

    def start(self, ticketnum = None, branchname = None, remote_branch=True):
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
        self.git.switch_branch("t/" + ticketnum)

    def save(self):
        curticket = self.git.current_ticket()
        if self.UI.confirm("Are you sure you want to save your changes to ticket #%s?"%(curticket)):
            self.git.save()
            if self.UI.confirm("Would you like to upload the changes?"):
                self.git.upload()
        else:
            self.UI.show("If you want to commit these changes to another ticket use the start() method")

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
        # pulls in changes from trac and rebases the current branch to
        # them. ticketnum=None syncs unstable.
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
            self.git.fetch_ticket(ticketnum, user, switch=True)
            if self.UI.confirm("Would you like to rebuild Sage?"):
                call("sage -b", shell=True)

    #def status(self):
    #    self.git.execute("status")

    #def list(self):
    #    self.git.execute("branch")

    def diff(self, vs_dependencies=False):
        if vs_dependencies:
            self.git.execute("diff", self.dependency_join())
        else:
            self.git.execute("diff")

    def prune_merged(self):
        # gets rid of branches that have been merged into unstable
        # Do we need this confirmation?  This is pretty harmless....
        if self.UI.confirm("Are you sure you want to abandon all branches that have been merged into master?"):
            for branch in self.git.local_branches():
                if self.git.is_ancestor_of(branch, "master"):
                    self.UI.show("Abandoning %s"%branch)
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
        if ticketnum is None:
            ticketnum = self.current_ticket(error=True)
        self.UI.show("Ticket %s depends on %s"%(ticketnum, ", ".join(["#%s"%(a) for a in self.trac.dependencies(ticketnum, all)])))

    def update_dependencies(self, ticketnum=None, dependencynum=None, all=False):
        # Merge in most recent changes from dependency(ies)
        raise NotImplementedError

    def add_dependency(self, ticketnum=None, dependencynum=None):
        # Do we want to do this?
        raise NotImplementedError

    def download_patch(self, ticketnum=None, patchname=None, url=None):
        """
        Download a patch to a temporary directory.

        If only ``ticketnum`` is specified and the ticket has only one attachment, download the patch attached to ``ticketnum``.

        If ``ticketnum`` and ``patchname`` are specified, download the patch ``patchname`` attached to ``ticketnum``.

        If ``url`` is specified, download ``url``.

        Raise an error on any other combination of parameters.

        INPUT:

        - ``ticketnum`` -- an int or an Integer or ``None`` (default: ``None``)

        - ``patchname`` -- a string or ``None`` (default: ``None``)

        - ``url`` -- a string or ``None`` (default: ``None``)

        OUTPUT:

        Returns the absolute file name of the returned file.

        """
        if url:
            if ticketnum or patchname:
                raise ValueError("If `url` is specifed, `ticketnum` and `patchname` must not be specified.")
            tmp_dir = self._get_tmp_dir()
            ret = os.path.join(tmp_dir,"patch")
            check_call(["wget","-r","-O",ret,url])
            return ret
        elif ticketnum:
            if patchname:
                return self.download_patch(url = self._config['trac']['server']+"raw-attachment/ticket/%s/%s"%(ticketnum,patchname))
            else:
                attachments = self.trac.attachment_names(ticketnum)
                if len(attachments) == 0:
                    raise ValueError("Ticket #%s has no attachments."%ticketnum)
                if len(attachments) == 1:
                    return self.download_patch(ticketnum = ticketnum, patchname = attachments[0])
                else:
                    raise ValueError("Ticket #%s has more than one attachment but parameter `patchname` is not present."%ticketnum)
        else:
            raise ValueError("If `url` is not specified, `ticketnum` must be specified")

    def import_patch(self, ticketnum=None, patchname=None, url=None, local_file=None, diff_format=None, header_format=None, path_format=None):
        """
        Import a patch to your working copy.

        If ``local_file`` is specified, apply the file it points to.

        Otherwise, apply the patch using :meth:`download_patch` and apply it.

        INPUT:

        - ``ticketnum`` -- an int or an Integer or ``None`` (default: ``None``)

        - ``patchname`` -- a string or ``None`` (default: ``None``)

        - ``url`` -- a string or ``None`` (default: ``None``)

        - ``local_file`` -- a string or ``None`` (default: ``None``)
        """
        if not self.git.reset_to_clean_state(): return
        if not self.git.reset_to_clean_working_directory(): return

        if not local_file:
            return self.import_patch(local_file = self.download_patch(ticketnum = ticketnum, patchname = patchname, url = url), diff_format=diff_format, header_format=header_format, path_format=path_format)
        else:
            if patchname or url:
                raise ValueError("If `local_file` is specified, `patchname`, and `url` must not be specified.")
            if ticketnum:
                self.git.branch("t/%s"%ticketnum)
                self.git.checkout("t/%s"%ticketnum)
            lines = open(local_file).read().splitlines()
            lines = self._rewrite_patch(lines, to_header_format="git", to_path_format="new", from_diff_format=diff_format, from_header_format=header_format, from_path_format=path_format)
            outfile = os.path.join(self._get_tmp_dir(), "patch_new")
            open(outfile, 'w').writelines("\n".join(lines)+"\n")
            print "Trying to apply reformatted patch `%s` ..."%outfile
            shared_args = ["--ignore-whitespace",outfile]
            am_args = shared_args+["--resolvemsg=''"]
            am = self.git.am(*am_args)
            if am: # apply failed
                if not self.UI.confirm("The patch does not apply cleanly. Would you like to apply it anyway and create reject files for the parts that do not apply?", default_yes=False):
                    print "Not applying patch."
                    self.git.reset_to_clean_state(interactive=False)
                    return

                apply_args = shared_args + ["--reject"]
                apply = self.git.apply(*apply_args)
                if apply: # apply failed
                    if self.UI.get_input("The patch did not apply cleanly. Please integrate the `.rej` files that were created and resolve conflicts. When you did, type `resolved`. If you want to abort this process, type `abort`.",["resolved","abort"]) == "abort":
                        self.git.reset_to_clean_state(interactive=False)
                        self.git.reset_to_clean_working_directory(interactive=False)
                        return
                else:
                    print "It seemed that the patch would not apply, but in fact it did."

                self.git.add("--update")
                self.git.am("--resolved")

    def _detect_patch_diff_format(self, lines):
        """
        Determine the format of the ``diff`` lines in ``lines``.

        INPUT:

        - ``lines`` -- a list of strings

        OUTPUT:

        Either ``git`` (for ``diff --git`` lines) or ``hg`` (for ``diff -r`` lines).

        EXAMPLES::

            sage: s = SageDev()
            sage: s._detect_patch_diff_format(["diff -r 1492e39aff50 -r 5803166c5b11 sage/schemes/elliptic_curves/ell_rational_field.py"])
            'hg'
            sage: s._detect_patch_diff_format(["diff --git a/sage/rings/padics/FM_template.pxi b/sage/rings/padics/FM_template.pxi"])
            'git'

        TESTS::

            sage: s._detect_patch_diff_format(["# HG changeset patch"])
            Traceback (most recent call last):
            ...
            NotImplementedError: Failed to detect diff format.
            sage: s._detect_patch_diff_format(["diff -r 1492e39aff50 -r 5803166c5b11 sage/schemes/elliptic_curves/ell_rational_field.py", "diff --git a/sage/rings/padics/FM_template.pxi b/sage/rings/padics/FM_template.pxi"])
            Traceback (most recent call last):
            ...
            ValueError: File appears to have mixed diff formats.

        """
        format = None
        regexs = { "hg" : HG_DIFF_REGEX, "git" : GIT_DIFF_REGEX }

        for line in lines:
            for name,regex in regexs.items():
                if regex.match(line):
                    if format is None:
                        format = name
                    if format != name:
                        raise ValueError("File appears to have mixed diff formats.")

        if format is None:
            raise NotImplementedError("Failed to detect diff format.")
        else:
            return format

    def _detect_patch_path_format(self, lines, diff_format = None):
        """
        Determine the format of the paths in the patch given in ``lines``.

        INPUT:

        - ``lines`` -- a list of strings

        - ``diff_format`` -- ``'hg'``,``'git'``, or ``None`` (default:
          ``None``), the format of the ``diff`` lines in the patch. If
          ``None``, the format will be determined by
          :meth:`_detect_patch_diff_format`.

        OUTPUT:

        A string, ``'new'`` (new repository layout) or ``'old'`` (old
        repository layout).

        EXAMPLES::

            sage: s = SageDev()
            sage: s._detect_patch_path_format(["diff -r 1492e39aff50 -r 5803166c5b11 sage/schemes/elliptic_curves/ell_rational_field.py"])
            'old'
            sage: s._detect_patch_path_format(["diff -r 1492e39aff50 -r 5803166c5b11 sage/schemes/elliptic_curves/ell_rational_field.py"], diff_format="git")
            Traceback (most recent call last):
            ...
            NotImplementedError: Failed to detect path format.
            sage: s._detect_patch_path_format(["diff --git a/sage/rings/padics/FM_template.pxi b/sage/rings/padics/FM_template.pxi"])
            'old'
            sage: s._detect_patch_path_format(["diff --git a/src/sage/rings/padics/FM_template.pxi b/src/sage/rings/padics/FM_template.pxi"])
            'new'

        """
        if diff_format is None:
            diff_format = self._detect_patch_diff_format(lines)

        path_format = None

        if diff_format == "git":
            diff_regexs = (GIT_DIFF_REGEX, PM_DIFF_REGEX)
        elif diff_format == "hg":
            diff_regexs = (HG_DIFF_REGEX, PM_DIFF_REGEX)
        else:
            raise NotImplementedError(diff_format)

        regexs = { "old" : HG_PATH_REGEX, "new" : GIT_PATH_REGEX }

        for line in lines:
            for regex in diff_regexs:
                match = regex.match(line)
                if match:
                    for group in match.groups():
                        for name, regex in regexs.items():
                            if regex.match(group):
                                if path_format is None:
                                    path_format = name
                                if path_format != name:
                                    raise ValueError("File appears to have mixed path formats.")

        if path_format is None:
            raise NotImplementedError("Failed to detect path format.")
        else:
           return path_format

    def _rewrite_patch_diff_paths(self, lines, to_format, from_format=None, diff_format=None):
        """
        Rewrite the ``diff`` lines in ``lines`` to use ``to_format``.

        INPUT:

        - ``lines`` -- a list of strings

        - ``to_format`` -- ``'old'`` or ``'new'``

        - ``from_format`` -- ``'old'``, ``'new'``, or ``None`` (default:
          ``None``), the current formatting of the paths; detected
          automatically if ``None``

        - ``diff_format`` -- ``'git'``, ``'hg'``, or ``None`` (default:
          ``None``), the format of the ``diff`` lines; detected automatically
          if ``None``

        OUTPUT:

        A list of string, ``lines`` rewritten to conform to ``lines``.

        EXAMPLES:

        Paths in the old format::


            sage: s = SageDev()
            sage: s._rewrite_patch_diff_paths(['diff -r 1492e39aff50 -r 5803166c5b11 sage/schemes/elliptic_curves/ell_rational_field.py'], to_format="old")
            ['diff -r 1492e39aff50 -r 5803166c5b11 sage/schemes/elliptic_curves/ell_rational_field.py']
            sage: s._rewrite_patch_diff_paths(['diff --git a/sage/rings/padics/FM_template.pxi b/sage/rings/padics/FM_template.pxi'], to_format="old")
            ['diff --git a/sage/rings/padics/FM_template.pxi b/sage/rings/padics/FM_template.pxi']
            sage: s._rewrite_patch_diff_paths(['--- a/sage/rings/padics/pow_computer_ext.pxd','+++ b/sage/rings/padics/pow_computer_ext.pxd'], to_format="old", diff_format="git")
            ['--- a/sage/rings/padics/pow_computer_ext.pxd',
             '+++ b/sage/rings/padics/pow_computer_ext.pxd']
            sage: s._rewrite_patch_diff_paths(['diff -r 1492e39aff50 -r 5803166c5b11 sage/schemes/elliptic_curves/ell_rational_field.py'], to_format="new")
            ['diff -r 1492e39aff50 -r 5803166c5b11 src/sage/schemes/elliptic_curves/ell_rational_field.py']
            sage: s._rewrite_patch_diff_paths(['diff --git a/sage/rings/padics/FM_template.pxi b/sage/rings/padics/FM_template.pxi'], to_format="new")
            ['diff --git a/src/sage/rings/padics/FM_template.pxi b/src/sage/rings/padics/FM_template.pxi']
            sage: s._rewrite_patch_diff_paths(['--- a/sage/rings/padics/pow_computer_ext.pxd','+++ b/sage/rings/padics/pow_computer_ext.pxd'], to_format="new", diff_format="git")
            ['--- a/src/sage/rings/padics/pow_computer_ext.pxd',
             '+++ b/src/sage/rings/padics/pow_computer_ext.pxd']

        Paths in the new format::

            sage: s._rewrite_patch_diff_paths(['diff -r 1492e39aff50 -r 5803166c5b11 src/sage/schemes/elliptic_curves/ell_rational_field.py'], to_format="old")
            ['diff -r 1492e39aff50 -r 5803166c5b11 sage/schemes/elliptic_curves/ell_rational_field.py']
            sage: s._rewrite_patch_diff_paths(['diff --git a/src/sage/rings/padics/FM_template.pxi b/src/sage/rings/padics/FM_template.pxi'], to_format="old")
            ['diff --git a/sage/rings/padics/FM_template.pxi b/sage/rings/padics/FM_template.pxi']
            sage: s._rewrite_patch_diff_paths(['--- a/src/sage/rings/padics/pow_computer_ext.pxd','+++ b/src/sage/rings/padics/pow_computer_ext.pxd'], to_format="old", diff_format="git")
            ['--- a/sage/rings/padics/pow_computer_ext.pxd',
             '+++ b/sage/rings/padics/pow_computer_ext.pxd']
            sage: s._rewrite_patch_diff_paths(['diff -r 1492e39aff50 -r 5803166c5b11 src/sage/schemes/elliptic_curves/ell_rational_field.py'], to_format="new")
            ['diff -r 1492e39aff50 -r 5803166c5b11 src/sage/schemes/elliptic_curves/ell_rational_field.py']
            sage: s._rewrite_patch_diff_paths(['diff --git a/src/sage/rings/padics/FM_template.pxi b/src/sage/rings/padics/FM_template.pxi'], to_format="new")
            ['diff --git a/src/sage/rings/padics/FM_template.pxi b/src/sage/rings/padics/FM_template.pxi']
            sage: s._rewrite_patch_diff_paths(['--- a/src/sage/rings/padics/pow_computer_ext.pxd','+++ b/src/sage/rings/padics/pow_computer_ext.pxd'], to_format="new", diff_format="git")
            ['--- a/src/sage/rings/padics/pow_computer_ext.pxd',
             '+++ b/src/sage/rings/padics/pow_computer_ext.pxd']

        """
        if diff_format is None:
            diff_format = self._detect_patch_diff_format(lines)

        if from_format is None:
            from_format = self._detect_patch_path_format(lines, diff_format=diff_format)

        if to_format == from_format:
            return lines

        def hg_path_to_git_path(path):
            if any([path.startswith(p) for p in "module_list.py","setup.py","c_lib/","sage/","doc/"]):
                return "src/%s"%path
            else:
                raise NotImplementedError("mapping hg path `%s`"%path)

        def git_path_to_hg_path(path):
            if any([path.startswith(p) for p in "src/module_list.py","src/setup.py","src/c_lib/","src/sage/","src/doc/"]):
                return path[4:]
            else:
                raise NotImplementedError("mapping git path `%s`"%path)

        def apply_replacements(lines, diff_regexs, replacement):
            ret = []
            for line in lines:
                for diff_regex in diff_regexs:
                    m = diff_regex.match(line)
                    if m:
                        line = line[:m.start(1)] + ("".join([ line[m.end(i-1):m.start(i)]+replacement(m.group(i)) for i in range(1,m.lastindex+1) ])) + line[m.end(m.lastindex):]
                ret.append(line)
            return ret

        diff_regex = None
        if diff_format == "hg":
            diff_regex = (HG_DIFF_REGEX, PM_DIFF_REGEX)
        elif diff_format == "git":
            diff_regex = (GIT_DIFF_REGEX, PM_DIFF_REGEX)
        else:
            raise NotImplementedError(diff_format)

        if from_format == "old":
            return self._rewrite_patch_diff_paths(apply_replacements(lines, diff_regex, hg_path_to_git_path), from_format="new", to_format=to_format, diff_format=diff_format)
        elif from_format == "new":
            if to_format == "old":
                return apply_replacements(lines, diff_regex, git_path_to_hg_path)
            else:
                raise NotImplementedError(to_format)
        else:
            raise NotImplementedError(from_format)

    def _detect_patch_header_format(self, lines):
        """
        Detect the format of the patch header in ``lines``.

        INPUT:

        - ``lines`` -- a list of strings

        OUTPUT:

        A string, ``'hg-export'`` (mercurial export header), ``'hg'``
        (mercurial header), ``'git'`` (git mailbox header), ``'diff'`` (no
        header)

        EXAMPLES::

            sage: s = SageDev()
            sage: s._detect_patch_header_format(['# HG changeset patch','# Parent 05fca316b08fe56c8eec85151d9a6dde6f435d46'])
            'hg'
            sage: s._detect_patch_header_format(['# HG changeset patch','# User foo@bar.com'])
            'hg-export'
            sage: s._detect_patch_header_format(['From: foo@bar'])
            'git'

        """
        if not lines:
            raise ValueError("patch is empty")

        if HG_HEADER_REGEX.match(lines[0]):
            if HG_USER_REGEX.match(lines[1]):
                return "hg-export"
            elif HG_PARENT_REGEX.match(lines[1]):
                return "hg"
        elif GIT_FROM_REGEX.match(lines[0]):
            return "git"
        elif lines[0].startswith("diff -"):
            return "diff"

        raise NotImplementedError("Failed to determine patch header format.")

    def _detect_patch_modified_files(self, lines, diff_format = None):
        if diff_format is None:
            diff_format = self._detect_patch_diff_format(lines)

        if diff_format == "hg":
            regex = HG_DIFF_REGEX
        elif diff_format == "git":
            regex = GIT_DIFF_REGEX
        else:
            raise NotImplementedError(diff_format)

        ret = set()
        for line in lines:
            m = regex.match(line)
            if m:
                for group in m.groups():
                    split = group.split('/')
                    if split:
                        ret.add(split[-1])
        return list(ret)

    def _rewrite_patch_header(self, lines, to_format, from_format = None, diff_format = None):
        """
        Rewrite ``lines`` to match ``to_format``.

        INPUT:

        - ``lines`` -- a list of strings, the lines of the patch file

        - ``to_format`` -- one of ``'hg'``, ``'hg-export'``, ``'diff'``,
          ``'git'``, the format of the resulting patch file.

        - ``from_format`` -- one of ``None``, ``'hg'``, ``'diff'``, ``'git'``
          (default: ``None``), the format of the patch file.  The format is
          determined automatically if ``format`` is ``None``.

        OUTPUT:

        A list of lines, in the format specified by ``to_format``.

        EXAMPLES::

            sage: s = SageDev()
            sage: lines = r'''# HG changeset patch
            ....: # User David Roe <roed@math.harvard.edu>
            ....: # Date 1330837723 28800
            ....: # Node ID 264dcd0442d217ff8762bcc068fbb6fc12cf5367
            ....: # Parent  05fca316b08fe56c8eec85151d9a6dde6f435d46
            ....: #12555: fixed modulus templates
            ....:
            ....: diff --git a/sage/rings/padics/FM_template.pxi b/sage/rings/padics/FM_template.pxi'''.splitlines()
            sage: s._rewrite_patch_header(lines, 'hg-export') == lines
            True
            sage: lines = s._rewrite_patch_header(lines, 'git'); lines
            ['From: David Roe <roed@math.harvard.edu>',
             'Subject: #12555: fixed modulus templates',
             'Date: Sun, 04 Mar 2012 05:08:43 -0000',
             '',
             'diff --git a/sage/rings/padics/FM_template.pxi b/sage/rings/padics/FM_template.pxi']
            sage: s._rewrite_patch_header(lines, 'git') == lines
            True
            sage: s._rewrite_patch_header(lines, 'hg-export')

        """
        if not lines:
            raise ValueError("empty patch file")

        if from_format is None:
            from_format = self._detect_patch_header_format(lines)

        if from_format == to_format:
            return lines

        def parse_header(lines, regexs):
            if len(lines) < len(regexs):
                raise ValueError("patch files must have at least %s lines"%len(regexs))

            for i,regex in enumerate(regexs):
                if not regex.match(lines[i]):
                    raise ValueError("Malformatted patch. Line `%s` does not match regular expression `%s`."%(lines[i],regex.pattern))

            message = []
            for i in range(len(regexs),len(lines)):
                if not lines[i].startswith("diff -"):
                    message.append(lines[i])
                else: break

            return message, lines[i:]

        if from_format == "git":
            message, diff = parse_header(lines, (GIT_FROM_REGEX, GIT_SUBJECT_REGEX, GIT_DATE_REGEX))

            if to_format == "hg-export":
                ret = []
                ret.append('# HG changeset')
                ret.append('# User %s'%GIT_FROM_REGEX.match(lines[0]).groups()[0])
                ret.append('# Date %s 00000'%time.mktime(email.utils.parsedate(GIT_DATE_REGEX.match(lines[2]).groups()[0]))) # this is not portable and the time zone is wrong
                ret.append('# Node ID 0000000000000000000000000000000000000000')
                ret.append('# Parent  0000000000000000000000000000000000000000')
                ret.append(GIT_SUBJECT_REGEX.match(lines[1]).groups()[0])
                ret.extend(message)
                ret.extend(diff)
                return ret
            else:
                raise NotImplementedError(to_format)
        elif from_format == "diff":
            ret = []
            ret.append('From: "Unknown User" <unknown@sagemath.org>')
            ret.append('Subject: No Subject. Modified: %s'%(", ".join(self._detect_patch_modified_files(lines))))
            ret.append('Date: %s'%email.utils.formatdate(time.time()))
            ret.extend(lines)
            return self._rewrite_patch_header(ret, to_format=to_format, from_format="git", diff_format=diff_format)
        elif from_format == "hg":
            message, diff = parse_header(lines, (HG_HEADER_REGEX, HG_PARENT_REGEX))
            if message:
                subject = message[0]
                message = message[1:]
            else:
                subject = 'No Subject. Modified: %s'%(", ".join(self._detect_patch_modified_files(lines)))

            ret = []
            ret.append('From: "Unknown User" <unknown@sagemath.org>')
            ret.append('Subject: %s'%subject)
            ret.append('Date: %s'%email.utils.formatdate(time.time()))
            ret.extend(message)
            ret.extend(diff)
            return self._rewrite_patch_header(ret, to_format=to_format, from_format="git", diff_format=diff_format)
        elif from_format == "hg-export":
            message, diff = parse_header(lines, (HG_HEADER_REGEX, HG_USER_REGEX, HG_DATE_REGEX, HG_NODE_REGEX, HG_PARENT_REGEX))
            ret = []
            ret.append('From: %s'%HG_USER_REGEX.match(lines[1]).groups()[0])
            ret.append('Subject: %s'%("No Subject" if not message else message[0]))
            ret.append('Date: %s'%email.utils.formatdate(int(HG_DATE_REGEX.match(lines[2]).groups()[0])))
            ret.extend(message[1:])
            ret.extend(diff)
            return self._rewrite_patch_header(ret, to_format=to_format, from_format="git", diff_format=diff_format)
        else:
            raise NotImplementedError(from_format)

    def _rewrite_patch(self, lines, to_path_format, to_header_format, from_diff_format=None, from_path_format=None, from_header_format=None):
        return self._rewrite_patch_diff_paths(self._rewrite_patch_header(lines, to_format=to_header_format, from_format=from_header_format, diff_format=from_diff_format), to_format=to_path_format, diff_format=from_diff_format, from_format=from_path_format)

    def dependency_join(self, ticketnum=None):
        if ticketnum is None:
            ticketnum = self.current_ticket(error=True)
        for d in self.trac.dependencies(ticketnum):
            pass
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
        return "%s/%s"(self._config['trac']['username'], ticketnum)

    def needs_update(self, ticketnum):
        # returns True if there are changes in the ticket on trac that
        # aren't included in the current ticket
        raise NotImplementedError

