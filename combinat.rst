.. Original authors: Florent Hivert and Nicolas Thiéry

What is this Sage-Combinat queue madness about???
=================================================

Sage-Combinat is a software project whose mission is: "to improve the
open source mathematical system Sage as an extensible toolbox for
computer exploration in (algebraic) combinatorics, and foster code
sharing between researchers in this area".

In practice it's a community of a dozen regular contributers, 20
occasional ones and, maybe, 30 users. They collaborate together on a
collection of experimental patches (i.e. extensions) on top of
Sage. Each one describes a relatively atomic modification which may
span several files; it may fix a bug, implement a new feature, improve
some documentation. The intent is that most of those extensions get
integrated into Sage as soon as they are mature enough, with a typical
life-cycle ranging from a few days to a couple months. In average 20
extensions are merged in each version of Sage (42 in Sage 5.0!), and
more than 200 are under development.


Why do we want to share our experimental code
=============================================

Here are our goals in using the Sage-Combinat queue for sharing patches:

- Preintegration
   It is very common that an advanced feature needs some infrastructure
   support. For example, advanced Hopf algebras or representation theory
   features needs basic linear algebra stuff (eg: tensor product) which them
   self needs support from categories which them self may need support for
   optimized dynamic classes. Having a central repository for experimental
   code allows us for sharing several layer of dependant patch. In our
   (Nicolas and Florent) experience it is fairly common that during research,
   we end up improving dependant patches with more than four layers of
   dependencies.

- Pair programming (or more than pair!)
   Many Sage-Combinat patches have several authors. We need an easy way to
   exchange patches (note that this is not specific to the Sage-Combinat
   project).

- Easy review even with many dependencies
   As said in preintegration, we can have several layer of dependant
   patches. We need some tool to apply a bunch of patches (not necessarily in
   a stable/needs-review status), experiment with the code and launch the
   tests.

- Maturation
   Due to the kind of computation we need (gluing algebra and combinatorics
   together), we have to be extra careful on the interface. Therefore, it is
   very common that we wait for a feature to be used several time before
   entering Sage. This is particularly true for infrastructure stuff.

- Overview of what's developed by who
   Having a centralized place where all de development is seen is a good tool
   for team coordination and code management. It also helps early detection of
   patch conflicts.

- Sharing code with beginner colleagues
   The queue is also an easy way to distribute experimental code to non
   developer colleagues. The two commands::

       sage -combinat install / sage -combinat update

   need no mercurial or developer skills



What are our constraints
========================

- Vital necessity of supporting several versions of Sage at once
    For the convenience of the user, it is usually possible to use the
    sage-combinat patches with older versions of sage. The intent is only
    to temporarily support one or two older versions of sage (that is
    about one month old). Typical use case: a developer urgently needs the
    latest version of a patch for a software demonstration at a
    conference, but can't instantly upgrade because of a slow internet
    connection. There is no guarantee whatsoever; on occasion we do not
    support this when this causes technical difficulties.

- By nature, our calculations are transversal. Thus it would be hard
  to split Sage-Combinat in smaller chunks by subareas.



Some random questions
=====================

- linear order versus DAG (directed acyclic graph) of dependencies: what's
  easier to maintain ?



Foreseeable future
==================

- More contributers
- Less overlap between patches as development goes from core to
  peripheral features
