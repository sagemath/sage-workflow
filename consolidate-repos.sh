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

CMD="${0##*/}"

die () {
    echo $@ 1>&2
    exit 1
}

usage () {
    echo "usage: $CMD -i sagedir -o outdir -t tmpdir"
}

# parse command line options
while getopts "i:o:t:" opt;
do
    case $opt in
        i) SAGEDIR=$(readlink -f "$OPTARG");;
        o) OUTDIR=$(readlink -f "$OPTARG");;
        t) TMPDIR=$(readlink -f "$OPTARG");;
    esac
done
shift $((OPTIND-1))

# read options if not explicitly specified
if [ -z "$SAGEDIR" ]; then
    [ -d "$1" ] || die $(usage)
    SAGEDIR="$1"
    shift
fi
if [ -z "$OUTDIR" ]; then
    [ -d "$1" ] || die $(usage)
    OUTDIR="$1"
    shift
fi
[ -z "$TMPDIR" ] && TMPDIR="$(mktemp -d /tmp/consolidate-repos.XXXX)" &&
        MADETMP=yes && echo "Created directory $TMPDIR"

mkdir -p "$TMPDIR" && cd "$TMPDIR" && rm -rf *

# initiate repo
git init "$TMPDIR"/sage-repo && cd "$TMPDIR"/sage-repo

# move the base tarballs into dist
mkdir -p "$OUTDIR"/dist
mkdir "$TMPDIR"/spkg
for TARBALL in "$SAGEDIR"/spkg/base/*.tar*; do
    PKGNAME=$(sed -e 's/.*\/\([^/]*\)-[0-9]\{1,\}.*$/\1/' <<<"$TARBALL")
    PKGVER=$(sed -e 's/^-\(.*\)\.tar.*$/\1/' <<<"${TARBALL#*${PKGNAME}}")
    tar x -p -C "$TMPDIR"/spkg -f $TARBALL
    tar c -f "$OUTDIR"/dist/$PKGNAME-$PKGVER.tar -C "$TMPDIR"/spkg/ $PKGNAME-$PKGVER
done

# get the SPKG repos converted to git and pull them into the consolidated repo
# also tarball the src/ directories of the SPKGs and put them into a dist/ directory
rm -f "$OUTDIR"/unknown.txt
mkdir "$TMPDIR"/spkg-git
for SPKG in "$SAGEDIR"/spkg/standard/*.spkg; do
    # figure out what the spkg is
    PKGNAME=$(sed -e 's/.*\/\([^/]*\)-[0-9]\{1,\}.*$/\1/' <<<"$SPKG")
    PKGVER=$(sed -e 's/^-\(.*\)\.spkg$/\1/' <<<"${SPKG#*${PKGNAME}}")
    PKGVER_UPSTREAM=$(sed -e 's/\.p[0-9][0-9]*$//' <<<"$PKGVER")
    echo "Found SPKG: $PKGNAME version $PKGVER"
    tar x -p -C "$TMPDIR"/spkg -f $SPKG

    # determine eventual subtree of the spkg's repo
    # tarball the src/ directory and put it into our dist/ directory
    case $PKGNAME in
        extcode) REPO=ext ;;
        sage) REPO=library ;;
        sage_root) REPO=base ;;
        sage_scripts) REPO=bin ;;
        *)
            mv -T "$TMPDIR"/spkg/$PKGNAME-$PKGVER/src "$TMPDIR"/spkg/$PKGNAME-$PKGVER/$PKGNAME-$PKGVER
            tar c -jf "$OUTDIR"/dist/$PKGNAME-$PKGVER_UPSTREAM.tar.bz2 -C "$TMPDIR"/spkg/$PKGNAME-$PKGVER/ $PKGNAME-$PKGVER
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
        rm -rf "$TMPDIR"/spkg-git/$PKGNAME/.git

    # save the package version for later
    echo "$PKGVER" > "$TMPDIR"/spkg-git/$PKGNAME/spkg-version.txt
done

# rewrite paths
BRANCHES=$(git branch)
git checkout -b dummy base # filter-branch fails without a checked out branch for some reason
for BRANCH in $BRANCHES
do
    # taken from `man git-filter-branch` and modified a bit
    git filter-branch -f -d "$TMPDIR"/filter-branch --index-filter "git ls-files -s | sed \"s+\t\\\"*+&$BRANCH/+\" | GIT_INDEX_FILE=\$GIT_INDEX_FILE.new git update-index --index-info && mv \"\$GIT_INDEX_FILE.new\" \"\$GIT_INDEX_FILE\"" $BRANCH
done


# Humongous octomerge

# Put together a directory listing for the repo to commit in the merge
MERGEOBJS=$(
    for BRANCH in $BRANCHES
    do
        ENTRY=$(git ls-tree $BRANCH) # an object-filename association
        if [ $(cut -f2 <<<"$ENTRY") == "spkg" ]; then
            # In this case, $BRANCH associates a subdirectory listing
            # to spkg containing a single dir. We ignore this
            # association and instead collect all the dirs that the
            # various branches insist are sole occupants of spkg/ ,
            # and produce a combined listing for spkg/ .
            PKGDIR_ENTRY=$(git ls-tree $(git ls-tree $BRANCH spkg | cut -d' ' -f3 | cut -f1))
            PKGOBJS="${PKGOBJS}${PKGDIR_ENTRY}\n"
        else
            # At the same time, we continue producing a listing of the
            # root dir on stdout. (This case should only happen four
            # times, when $BRANCH is one of the four special cases.)
            echo "$ENTRY"
        fi
    done

    # Produce a new directory listing object for spkg/ from the
    # information gathered above, then dump that object into the
    # listing of the root directory which we are building on
    # stdout. --batch is used because there's an extra newline at the
    # end of $PKGOBJS.
    PKGTREE=$(echo -e "$PKGOBJS" | git mktree --missing --batch)
    echo -e "040000 tree $PKGTREE\tspkg"
)
# Actually make the directory listing into a git object
MERGETREE=$(echo -e "$MERGEOBJS" | git mktree --missing)
# Commit the new fully consolidated file tree
MERGECOMMIT=$(
    {
        for BRANCH in $BRANCHES
        do
            echo '-p '$(git show-ref -s --heads $BRANCH)
        done
    } | xargs git commit-tree $MERGETREE -m "ePiC oCtOmErGe"
)
# Set up a new master branch and delete the other branches, and we're
# done!
git checkout -b master $MERGECOMMIT
git branch -D dummy
for BRANCH in $BRANCHES;
do
    git branch -d $BRANCH || die "The octomerge failed; $BRANCH is still unmerged!"
done

# Clean up or adapt .hg* files (Mercurial-related data)
for BRANCH in $BRANCHES;
do
    git rm --ignore-unmatch "$BRANCH"/.hgtags
    if [ -f "$BRANCH"/.hgignore ]; then
        sed "s+^[^#]+$BRANCH/+" "$BRANCH"/.hgignore >> .gitignore
        git rm "$BRANCH"/.hgignore
    fi
done
git add .gitignore
git commit -m "[CLEANUP] Mercurial-related data"

# Commit spkg-version.txt files to track package \.p[0-9]+ versions
# (i.e. local revisions)
for BRANCH in $BRANCHES
do
    if [[ $BRANCH == '*spkg/*' ]]; then
        PKGNAME=${BRANCH#spkg/}
        mv "$TMPDIR"/spkg-git/$PKGNAME/spkg-version.txt spkg/$PKGNAME/
        git add spkg/$PKGNAME/spkg-version.txt
    fi
done
git commit -m "[CLEANUP] Add spkg-version.txt files"

# Optimize the repo
git gc --aggressive

# Unpack the root layout of the consolidated Sage installation
cp -r base/* "$OUTDIR"/

# Move the consolidated repo into place, and check out the package
# installation scripts so that Sage can start building
mkdir -p "$OUTDIR"/devel/sage && mv "$TMPDIR"/sage-repo/.git "$OUTDIR"/devel/sage/
cd "$OUTDIR"/devel/sage
git checkout master -- spkg/

# Clean up $TMPDIR
cd "$OUTDIR"
[[ -z $MADETMP ]] || rm -rf "$TMPDIR"
