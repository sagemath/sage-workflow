sage-workflow
=============

This is a repository for various stuff we're working on for the
Workflow SEP (Sage Enhancement Proposal).


consolidate-repos.sh
--------------------

This is a script which will ultimately take a (sufficiently recent)
Sage release source tarball and convert it into another tarball. The
new tarball will be similar to the original, i.e. it will be a source
tarball which you will extract, enter the extracted directory, do
``make``, wait a long time, and then end up with a working copy of
Sage.

The difference will be that now there will be a single, consolidated
git repo sitting in the top level directory. The repo will contain
within it the Sage library, the Sage scripts, the Sage root scripts
(i.e. the stuff other than SPKGs which you usually see when you
extract a source tarball), the Sage external system code (i.e. what is
currently in ``data/extcode``).

There will also be no SPKGs in the new tarball. The script will have
disassembled each SPKG ``foo-x.y.z.spkg``, repacking the src/
directory into a new tarball ``upstream/foo-x.y.z.tar.bz2`` and
merging the internal Mercurial repository into the single consolidated
git repo, moving it into the subdirectory ``packages/``, specifically
so that its files appear in ``packages/foo/``.

Thus, in this variant of Sage, when installing a package, instead of
extracting an SPKG file into a build directory for building, the
spkg-install script / patches / etc. and the source tarball will be
separately copied (resp. extracted) into the build directory.
Installation of actual SPKG files will be emulated - when you run
``sage -i foo.spkg``, the script will disassemble the SPKG as
described above, and then install it in its new way.

Besides this, Sage will be generally modified to work with the new
paths which all the above necessitate, or, in simple cases, to just
copy the files from the new consolidated repository into their old
locations whenever you run ``sage -b``.


sagedev.py
----------

There used to be a sagedev development tool in this repository. Work on this
has been moved to http://trac.sagemath.org/ticket/14482.


issue_export.py
---------------

A file to assist in moving tickets from trac to GitHub.
Run it with ``./run issue_export.py`` -- the ``run`` file
constructs a ``virtualenv`` directory so that it can
install some dependencies.


directory structure
-------------------

The proposed directory structure of sage root is::

    sage_root/
        sage          # the binary
        Makefile      # top level Makefile
        (configure)   # perhaps, eventually
        ...           # other standard top level files (README, etc.)
        build/
            core/     # sage's build system
            pkgs/     # install, patch, and metadata from spkgs
            ...
        src/
            sage/     # sage library, i.e. devel/sage-main/sage
            ext/      # sage_extcode
            (macapp/) # would no longer have to awkwardly be in extcode
            scripts/  # sage_scripts
            ...
        upstream/     # (stripped) tarballs of upstream sources (not tracked)
        local/        # installed binaries and compile artifacts (not tracked)
