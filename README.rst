sage-workflow
=============

This is a repository for various stuff we're working on for the Workflow
SEP (Sage Enhancement Proposal).


consolidate-repos.sh
--------------------

This is a script which will ultimately take a (sufficiently recent) Sage
release source tarball and convert it into another tarball. The new
tarball will be similar to the original, i.e. it will be a source
tarball which you will extract, enter the extracted directory, do
`make`, wait a long time, and then end up with a working copy of Sage.

The difference will be that now there will be a single, consolidated git
repo sitting in the top level directory. The repo will contain within it the
Sage library, the Sage scripts, the Sage root scripts (i.e. the stuff other
than SPKGs which you usually see when you extract a source tarball), the
Sage external system code (i.e. what is currently in ``data/extcode``).

There will also be no SPKGs in the new tarball. The script will have
disassembled each SPKG ``foo-x.y.z.spkg``, repacking the src/ directory
into a new tarball ``dist/foo-x.y.z.tar.bz2`` and merging the internal
Mercurial repository into the single consolidated git repo in
``packages/``, specifically so that its files appear in
``packages/foo/``.

Thus, in this variant of Sage, when installing a package, instead of
extracting an SPKG file into a build directory for building, the
spkg-install script / patches / etc. and the source tarball will be
separately copied (resp. extracted) into the build directory.
Installation of actual SPKG files will be emulated - when you run ``sage
-i foo.spkg``, the script will disassemble the SPKG as described above,
and then install it in its new way.

Besides this, Sage will be generally modified to work with the new paths
which all the above necessitate, or, in simple cases, to just copy the
files from the new consolidated repository into their old locations
whenever you run `sage -b`.


sagedev.py
----------

This is a Python module which implements development tools for Sage. It
provides an interface to our `Trac server`_, an interface to git, and an
interface to gathering input from the user, all of which come together

Functionality includes:

- **start**: Start or continue working on a given ticket.

- **save**: Add/commit changes.

- **upload**: Show your latest changes on the trac ticket.

- **sync**: Merge changes from the latest Sage or from the latest work
  on another given ticket into your current code.

- ...?

.. _Trac server: http://trac.sagemath.org/sage_trac/


directory structure
-------------------

The directory structure of sage root will be

sage_root/
    sage          # the binary
    Makefile      # top level Makefile
    (configure)   # perhaps, eventually
    devel/        # all the non-spkg sources will here
        sage/     # sage library, i.e. devel/sage-main/sage
        extcode/  # sage-extcode
        bin/      # sage-scripts
        ...
    packages/     # install, patch, and metadata from spkgs
    upstream/     # (stripped) tarballs of upstream sources (not in git)
    local/        # installed binaries and compile artifacts (not in git)
