Branches
--------

* local branches are named freeform, dev scripts will set them up with remote
  tracking on boxen by default. Autodetect preferred push target based on
  branch name in the case of a branch that doesn't have tracking information:

  * foo -> u/username/foo
  * t-12345 -> u/username/t-12345 and prompt for attaching to ticket #12345
  * foo/bar -> g/foo/bar on boxen

* remote branches are named in the following ways:

  * u/johndoe/foobar = John Doe's branch called "foobar"
  * g/FBI/barbaz = the FBI's shared branch barbaz (writeable by everyone by
    default)
  * t/12345 = a symbolic link to whatever user or group branch has been
    specified on the trac ticket #12345

* the dev scripts keep some local state containing what tickets we think have
  which of our local branches attached to them; when starting to work on ticket
  42, this will be checked against boxen

Hooks on Trac
-------------

* if a branch is deleted and it is attached to any ticket, we should copy the
  branch to g/abandoned/something

* if a branch is attached to any ticket, we should symlink t/<ticketnum> to the
  ref for the branch that was attached
