consolidate-sage-repos
======================

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

Also, the Sage build system will be modified to work with the changes in
paths which this necessitates, or most likely to just copy the files
from the new consolidated repository into their old locations whenever
you run `sage -b`.
