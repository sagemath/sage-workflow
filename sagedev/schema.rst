Branches
--------

Local branches
==============

  - ticket/12345 - my branch for working on ticket #12345
  - groupname/feature - groupname's branch for feature "feature"


* local branches are named freeform, dev scripts will set them up with remote
  tracking on boxen by default. Autodetect preferred push target based on
  branch name in the case of a branch that doesn't have tracking information:

  * foo -> u/username/foo
  * t-12345 -> u/username/t-12345 and prompt for attaching to ticket #12345
  * foo/bar -> g/foo/bar on boxen

* the dev scripts keep some local state containing what tickets we think have
  which of our local branches attached to them; when starting to work on ticket
  42, this will be checked against boxen

Hooks?
------

* if a branch is deleted and it is attached to any ticket, we should copy the
  branch to g/abandoned/something
