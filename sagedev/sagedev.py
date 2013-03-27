import os
import os.path
import shutil
import atexit
import re
import time
from datetime import datetime
from subprocess import call, check_call
from trac_interface import TracInterface
from git_interface import GitInterface
from user_interface import CmdLineInterface

DOT_SAGE = os.environ.get('DOT_SAGE',os.path.join(os.environ['HOME'], '.sage'))

# regular expressions to parse mercurial patches
HG_HEADER_REGEX = re.compile(r"^# HG changeset patch$")
HG_USER_REGEX = re.compile(r"^# User (.*)$")
HG_DATE_REGEX = re.compile(r"^# Date (\d+) (\d+)$")
HG_NODE_REGEX = re.compile(r"^# Node ID ([0-9a-f]+)$")
HG_PARENT_REGEX = re.compile(r"^# Parent  ([0-9a-f]+)$")
HG_DIFF_REGEX = re.compile(r"^diff -r \d+ -r \d+ (.*)$")

# regular expressions to parse git patches -- at least those created by us
GIT_FROM_REGEX = re.compile(r"^From: (.*)$")
GIT_SUBJECT_REGEX = re.compile(r"^Subject: (.*)$")
GIT_DATE_REGEX = re.compile(r"^Date: (.*)$")
GIT_DIFF_REGEX = re.compile(r"^diff --git a/(.*) b/(.*)$") # this regex should work for our patches since we do not have spaces in file names

# regular expressions to determine whether a path was written for the new git
# repository of for the old hg repository
HG_PATH_REGEX = re.compile(r"^(?=sage/)|(?=module_list.py)|(?=setup.py)|(?=c_lib/)") # TODO: add more patterns
GIT_PATH_REGEX = re.compile(r"^(?=src/)")

class SageDev(object):
    def __init__(self, devrc=os.path.join(DOT_SAGE, 'devrc'),
                 ticket_file=os.path.join(DOT_SAGE, 'branch_to_ticket'),
                 branch_file=os.path.join(DOT_SAGE, 'branch_to_ticket'),
                 gitcmd='git', realm='sage.math.washington.edu',
                 trac='http://boxen.math.washington.edu:8888/sage_trac/',
                 ssh_pubkey_file=None, ssh_passphrase="", ssh_comment=None):
        self.UI = CmdLineInterface(interactive)
        username, password, has_ssh_key = self._process_rc(devrc)
        self._username = username
        self.git = GitInterface(self.UI, username, ticket_file, branch_file, gitcmd)
        self.trac = TracInterface(self.UI, realm, trac, username, password)
        self.tmp_dir = None
        if not has_ssh_key:
            self._send_ssh_key(username, password, devrc, ssh_pubkey_file, ssh_passphrase, ssh_comment)

    def _get_tmp_dir(self):
        if self.tmp_dir is None:
            from tmpfile import mkdtemp
            self.tmp_dir = mkdtemp()
            atexit.register(lambda: shutil.rmtree(self.tmp_dir))

    def _get_user_info(self):
        username = self.UI.get_input("Please enter your trac username: ")
        # we should eventually use a password entering mechanism (ie *s or blanks when typing)
        passwd = self.UI.get_input("Please enter your trac password (stored in plaintext on your filesystem): ")
        return username, passwd

    def _send_ssh_key(self, username, passwd, devrc, ssh_pubkey_file, ssh_passphrase, comment):
        if self.UI.confirm("You have not yet uploaded an ssh key to the server." +
                           "Would you like to upload one now?"):
            if ssh_pubkey_file is None:
                ssh_pubkey_file = os.path.join(os.environ['HOME'], '.ssh', 'id_rsa.pub')
            if not os.path.exists(ssh_pubkey_file):
                self.UI.show("Generating ssh key....")
                if not ssh_pubkey_file.endswith(".pub"):
                    raise ValueError("public key filename must end with .pub")
                ssh_prikey_file = ssh_pubkey_file[:-4]
                cmd = ["ssh-keygen", "-q", "-t", "rsa", "-f", ssh_prikey_file, "-N", ssh_passphrase]
                if comment is not None:
                    cmd.extend(["-C", comment])
                success = call(cmd)
                if success == 0:
                    self.UI.show("Ssh key successfully generated")
                else:
                    raise RuntimeError("Ssh key generation failed.  Please create a key in %s and retry"%(ssh_pubkey_file))
            with open(devrc, "w") as F:
                F.write("v0\n%s\n%s\nssh_sent"%(username, passwd))
            os.chmod(devrc, 0600)
        else:
            with open(devrc, "w") as F:
                F.write("v0\n%s\n%s"%(username, passwd))
            os.chmod(devrc, 0600)

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
        self.git.switch("t/" + ticketnum)

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
            self.git.fetch_ticket(ticketnum, user)
            branch = "t/" + str(ticketnum)
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
            check_call("wget","-r","-O",ret)
            return ret
        elif ticketnum:
            if patchname:
                return self.download_patch(url = self.trac._tracsite+"/raw-attachment/ticket/%s/%s"%(ticketnum,patchname))
            else:
                attachments = self.trac.attachment_names()
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
        if not local_file:
            if ticketnum or patchname or url:
                raise ValueError("If `local_file` is specified, `ticketnum`, `patchname`, and `url` must not be specified.")
            return self.import_patch(local_file = self.download_patch(ticketnum = ticketnum, patchname = patchname, url = url), **kwargs)
        else:
            lines = open(local_file).read().splitlines()
            lines = self._rewrite_patch(lines, to_format="git", from_diff_format=diff_format, from_header_format=header_format, from_path_format=path_format)
            #TODO: strip whitespace
            raise NotImplementedError

    def _detect_patch_diff_format(self, lines):
        """
        Determine the format of the ``diff`` lines in ``lines``.

        INPUT:

        - ``lines`` -- a list of strings

        OUTPUT:

        Either ``git`` (for ``diff --git`` lines) or ``hg`` (for ``diff -r`` lines).

        EXAMPLES::

            sage: from sagedev import _detect_patch_diff_format as detect
            >>> detect(["diff -r 1492e39aff50 -r 5803166c5b11 sage/schemes/elliptic_curves/ell_rational_field.py"])
            "hg"
            >>> detect(["diff --git a/sage/rings/padics/FM_template.pxi b/sage/rings/padics/FM_template.pxi"])
            "git"

        TESTS::

            >>> detect(["# HG changeset patch"])
            >>> detect(["diff -r 1492e39aff50 -r 5803166c5b11 sage/schemes/elliptic_curves/ell_rational_field.py", "diff --git a/sage/rings/padics/FM_template.pxi b/sage/rings/padics/FM_template.pxi"])

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

    def _determine_path_format(self, lines, diff_format = None):
        if diff_format is None:
            diff_format = self._determine_diff_format(lines)

        path_format = None

        if diff_format == "git":
            regex = GIT_DIFF_REGEX
        elif diff_format == "hg":
            regex = HG_DIFF_REGEX
        else:
            raise NotImplementedError(diff_format)

        regexs = { "hg" : HG_PATH_REGEX, "git" : GIT_PATH_REGEX }

        for line in lines:
            match = regex.match(line)
            if match:
                for group in match.groups():
                    for name, regex in regexs:
                        if regex.match(line):
                            if path_format is None:
                                path_format = name
                            if path_format != name:
                                raise ValueError("File appears to have mixed path formats.")

        if path_format is None:
            raise NotImplementedError("Failed to detect path format.")
        else:
           return path_format

    def _rewrite_diff_paths(self, lines, to_format, from_format=None, diff_format=None):
        if diff_format is None:
            diff_format = self._determine_diff_format(lines)

        if from_format is None:
            from_format = self._determine_path_format(lines)

        if to_format == from_format:
            return lines

        def hg_path_to_git_path(path):
            if any([path.startswith(p) for p in "module_list.py","setup.py","c_lib/","sage/","doc/"]):
                return "src/%s"%path
            else:
                raise NotImplementedError("mapping hg path `%s`"%path)

        def git_path_to_hg_path(git_path):
            if any([path.startswith(p) for p in "src/module_list.py","src/setup.py","src/c_lib/","src/sage/","src/doc/"]):
                return path[4:]
            else:
                raise NotImplementedError("mapping git path `%s`"%path)

        def apply_replacements(lines, diff_regex, replacement):
            ret = []
            for line in lines:
                m = diff_regex.match(line)
                if m:
                    for path in m.groups():
                        line = line.replace(path,replacement(path))
                ret.append(line)

            return ret

        diff_regex = None
        if diff_format == "hg":
            diff_regex = HG_DIFF_REGEX
        elif diff_format == "git":
            diff_regex = GIT_DIFF_REGEX
        else:
            raise NotImplementedError(diff_format)

        if from_format == "hg":
            self._rewrite_diff_paths(self, apply_replacements(lines, diff_regex, hg_path_to_git_path), from_format="git", to_format=to_format, diff_format=diff_format)
        elif from_format == "git":
            if to_format == "hg":
                return apply_replacements(lines, diff_format, git_path_to_hg_path)
            else:
                raise NotImplementedError(to_format)
        else:
            raise NotImplementedError(from_format)

    def _determine_patch_header_format(self, lines):
        if not lines:
            raise ValueError

        if lines[0] == "# HG changeset patch":
            for line in lines:
                if line.startswith("diff -"):
                    if line.startswith("diff --git "):
                        return "hg-git"
                    else:
                        return "hg"
        elif lines[0].startswith("From: "):
            return "git"
        else:
            raise NotImplementedError

    def __parse_header(self, lines, regexs):
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

    def _rewrite_patch_header(self, lines, to_format, from_format = None):
        """
        Reformat the patch whose ``lines`` are given to apply to the
        repository.

        INPUT:

        - ``lines`` -- a list of strings, the lines of the patch file (without
          the trailing newline)

        - ``from_format`` -- one of ``None``, ``'hg'``, ``'diff'``, ``'git'``
          (default: ``None``), the format of the patch file.  The format is
          determined automatically if ``format`` is ``None``.

        - ``to_format`` -- one of ``'hg'``, ``'diff'``, ``'git'`` (default:
          ``git``), the format of the resulting patch file.

        OUTPUT:

        A list of lines, in the format specified by ``to_format``.

        """
        if not lines:
            raise ValueError("empty patch file")

        if from_format is None:
            from_format = self._determine_patch_format(lines)

        if from_format == to_fromat:
            return lines

        if from_format == "git":
            message, diff = self.__parse_header(lines, (GIT_FROM_REGEX, GIT_SUBJECT_REGEX, GIT_DATE_REGEX))

            if to_format == "hg":
                ret = []
                ret.append('# HG changeset')
                ret.append('# User %s'%GIT_FROM_REGEX.match(lines[0]).groups()[0])
                ret.append('# Date %s 00000'%datetime.strptime(GIT_DATE_REGEX.match(lines[2]).groups()[0], "%a %b %d %H:%M:%S %Z %Y").strftime("%s")) # this is not portable and the time zone is wrong
                ret.append('# Node ID 0000000000000000000000000000000000000000')
                ret.append('# Parent  0000000000000000000000000000000000000000')
                ret.append(GIT_SUBJECT_REGEX.match(lines[1]).groups()[0])
                ret.extend(message)
                ret.extend(diff)
            else:
                raise NotImplementedError(to_format)
        elif from_format == "diff":
            ret = []
            ret.append('From: "Unknown User" <unknown@sagemath.org>')
            ret.append('Subject: No Subject')
            ret.append('Date: %s'%datetime.today().ctime())
            ret.extend(lines)
            return self._rewrite_patch_header(ret, to_format=to_format, from_format="git")
        elif from_format == "hg":
            message, diff = self.__parse_header(lines, (HG_HEADER_REGEX, HG_USER_REGEX, HG_DATE_REGEX, HG_NODE_REGEX, HG_PARENT_REGEX))
            ret = []
            ret.append('From: %s'%HG_USER_REGEX.match(lines[1]).groups()[0])
            ret.append('Subject: %s'%("No Subject" if not message else message[0]))
            ret.append('Date: %s'%datetime.utcfromtimestamp(HG_DATE_REGEX.match(lines[2]).groups()[0].ctime()))
            ret.extend(message[1:])
            ret.extend(diff)
            return self._rewrite_patch_header(ret, to_format=to_format, from_format="git")
        else:
            raise NotImplementedError(from_format)

    def _rewrite_patch(self, lines, to_format, from_diff_format=None, from_path_format=None, from_header_format=None):
        return self._rewrite_diff_paths(self._rewrite_patch_header(lines, to_format=to_format, from_format=from_header_format), to_format=to_format, from_diff_format=from_diff_format, from_path_format=from_path_format)

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
