sage-workflow
=============

This is a repository for various stuff we're working on for the
Workflow SEP (Sage Enhancement Proposal).


consolidate-repos.sh
--------------------

This is a script which will ultimately take a (sufficiently recent) Sage
release source tarball and convert it into another tarball. The new
tarball will be similar to the original, i.e. it will be a source
tarball which you will extract, enter the extracted directory, do
`make`, wait a long time, and then end up with a working copy of Sage.

The difference will be that now there will be a single, consolidated git
repo sitting in ``devel/sage/`` from the moment you extract the tarball
(not a symlink, and not even the same thing as what is currently in
``devel/sage-main/``!). The repo will contain within it the Sage
library, the Sage scripts, the Sage root scripts (i.e. the stuff other
than SPKGs which you usually see when you extract a source tarball), the
Sage external system code (i.e. what is currently in ``data/extcode``).

There will also be no SPKGs in the new tarball. The script will have
disassembled each SPKG ``foo-x.y.z.spkg``, repacking the src/ directory
into a new tarball ``dist/foo-x.y.z.tar.bz2`` and merging the internal
Mercurial repository into the single consolidated git repo in
``devel/sage/``, specifically so that its files appear in
``devel/sage/spkg/foo/``.

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
