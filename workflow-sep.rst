.. warning:: This is a work in progress!

============
Workflow SEP
============

We propose to improve the workflow of Sage development by moving away
from using patch files to communicate changes to the Sage library and
ancillary structures, and instead start to use the modern DVCS
(distributed version control system) method of lightweight branching
and merging. We also propose various other improvements of developers'
situation when writing code for Sage.

Primary goals:

* Switch from patches to branches

  - Consolidate *all* Sage repositories into a single repository,
    including SPKG installer/patches repositories for all standard and
    optional SPKGs

    + The src/ directory of current SPKGs will be separated from the
      rest of the SPKG (which is under version control) and placed in
      a different location.

  - Switch to git for version control

  - Implement and use something similar to ccache for Cython, so that
    building will be faster when switching branches

* Implement a better review system on Trac

  - Make Trac aware of users' personal repositories and read new commits
    from them into its own overarching repository on demand

  - Implement "attaching" of branches to a ticket

  - Make it easy to view source code, commits, changesets, and hopefully
    even diffs between arbitrary pairs of commits on Trac

  - Customize Trac to allow for line-by-line comments on changesets

    + Also allow for line-by-line comments on patch files that currently
      exist on Trac

* Make a script, ``sage dev``, which completely wraps some limited git
  functionality necessary to allow developers to use our new workflow
  without being git experts

  - It will know about Trac, and handle any branching or merging
    required

  - User is hand-held through everything they need to do - i.e. a
    wizard for development

* Implement "live development" from sagenb.org or other public
  notebook servers

  - TODO

See also our `brainstorming page`_ on the wiki page for Review Days 2,
which was where most of these ideas came together.

.. _brainstorming page:
    http://wiki.sagemath.org/review2/Projects/SystemProposals
