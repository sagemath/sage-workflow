#!/usr/bin/env bash

# consolidate-repos.sh
#
# Requires git, hg, and hg-git, as well as a copy of Sage. hg-git must
# contain revision e58a6d0b80e2, to avoid getting corrupt git repos.
# As of 2012-03-19 this means it needs to be directly pulled from the
# repo at http://bitbucket.org/durin42/hg-git/ .
#
# Usage:
#
#   consolidate-repos.sh -i sagedir -o outdir -t tmpdir
#
# Output:
#
# - A consolidated repo in outdir
# - tarballs for the source files in outdir/dist/

CMD="$0"

usage() {
  echo "usage: $CMD -i sagedir -o outdir -t tmpdir"
}

# parse command line options
while getopts "i:o:t:" opt;
do
    case $opt in
        i) SAGEDIR="$OPTARG";;
        o) OUTDIR="$OPTARG";;
        t) TMPDIR="$OPTARG";;
    esac
done
shift $((OPTIND-1))

# read options if not explicitly specified
if [ -z "$SAGEDIR" ]; then
    [ $# -ge 1 ] || { usage; exit 1; }
    SAGEDIR="$1"
    shift
fi
if [ -z "$OUTDIR" ]; then
    [ $# -ge 1 ] || { usage; exit 1; }
    OUTDIR="$1"
    shift
fi
[ -z "$TMPDIR" ] && TMPDIR="/tmp/consolidate-repos"

mkdir -p "$TMPDIR" && cd "$TMPDIR" && rm -rf *

# initiate repo
git init "$TMPDIR"/sage-repo && cd "$TMPDIR"/sage-repo

# move the base tarballs into dist
mkdir -p "$OUTDIR"/dist
mkdir "$TMPDIR"/spkg
for TARBALL in "$SAGEDIR"/spkg/base/*.tar*; do
    PKGNAME=$(sed -e 's/.*\/\([^/-]*\)-\([^/]*\)\.tar.*$/\1/' <<<"$TARBALL")
    PKGVER=$(sed -e 's/.*\/\([^/-]*\)-\([^/]*\)\.tar.*$/\2/' <<<"$TARBALL")
    tar x -p -C "$TMPDIR"/spkg -f $TARBALL
    tar c -f "$OUTDIR"/dist/$PKGNAME-$PKGVER.tar -C "$TMPDIR"/spkg/ $PKGNAME-$PKGVER
done

# get the SPKG repos converted to git and pull them into the consolidated repo
# also tarball the src/ directories of the SPKGs and put them into a dist/ directory
rm -f "$OUTDIR"/unknown.txt
mkdir "$TMPDIR"/spkg-git
for SPKG in $(find "$SAGEDIR"/spkg/standard -regex '.*/[^/]*\.spkg' -type f)
do
    # figure out what the spkg is
    PKGNAME=$(sed -e 's/.*\/\([^/-]*\)-\([^/]*\)\.spkg$/\1/' <<<"$SPKG")
    PKGVER=$(sed -e 's/.*\/\([^/-]*\)-\([^/]*\)\.spkg$/\2/' <<<"$SPKG")
    echo Found SPKG: $PKGNAME version $PKGVER
    tar x -p -C "$TMPDIR"/spkg -f $SPKG
    case $PKGNAME in
        extcode) REPO=sageext ;;
        sage) REPO=sagelib ;;
        sage_root) REPO=sagebin ;;
        sage_scripts) REPO=sagebase ;;
        *)
            # tarball the src/ directory and put it into our dist/ directory
            mv -T "$TMPDIR"/spkg/$PKGNAME-$PKGVER/src "$TMPDIR"/spkg/$PKGNAME-$PKGVER/$PKGNAME-$PKGVER
            tar c -f "$OUTDIR"/dist/$PKGNAME-$PKGVER.tar -C "$TMPDIR"/spkg/$PKGNAME-$PKGVER/ $PKGNAME-$PKGVER
            REPO=spkg/$PKGNAME
        ;;
    esac

    # convert the SPKG's hg repo to git
    git init --bare "$TMPDIR"/spkg-git/$PKGNAME
    hg -R "$TMPDIR"/spkg/$PKGNAME-$PKGVER push "$TMPDIR"/spkg-git/$PKGNAME ; # hg-git returns non-zero exit code upon warnings (!?)
        rm -rf "$TMPDIR"/spkg/$PKGNAME-$PKGVER
    rm -rf "$TMPDIR"/spkg/$PKGNAME-$PKGVER

    # pull it into the consolidated repo
    git fetch -n "$TMPDIR"/spkg-git/$PKGNAME master:$REPO &&
        rm -rf "$TMPDIR"/spkg-git/$PKGNAME
done
rmdir "$TMPDIR"/spkg "$TMPDIR"/spkg-git

# rewrite paths
BRANCHES=$(git branch)
git checkout sagebase -b master # filter-branch fails without a checked out branch for some reason
for BRANCH in $BRANCHES
do
    # taken from `man git-filter-branch` and modified a bit
    git filter-branch -f -d /tmp/filter-branch --index-filter "git ls-files -s | sed \"s+\t\\\"*+&$BRANCH/+\" | GIT_INDEX_FILE=\$GIT_INDEX_FILE.new git update-index --index-info && mv \"\$GIT_INDEX_FILE.new\" \"\$GIT_INDEX_FILE\"" $BRANCH
done
git reset --hard sagebase # lose the last old pre- path-rewriting branch

# humongous octomerge (TODO)
for BRANCH in $BRANCHES;
do
    git merge "$BRANCH" || { echo "There was an error merging in $BRANCH, please inspect"; exit 1; }
    git branch -d "$BRANCH"
done

cp -r sagebase/* "$OUTDIR"/
cd .. && mv sage_repo sage && tar c -f "$OUTDIR"/devel/sage.tar sage
