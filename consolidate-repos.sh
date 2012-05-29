#!/usr/bin/env bash

# consolidate-repos.sh
#
# Requires git, hg, and hg-git, as well as a copy of Sage. hg-git must
# contain revision e58a6d0b80e2, to avoid getting corrupt git repos.
# As of 2012-03-19 this means it needs to be directly pulled from the
# repo at http://bitbucket.org/durin42/hg-git/ .
#
# If GNU parallel is present, certain operations will be parallelized.
# If notify-send is present, the script will send notifications that
# certain long segments of the operation have been completed.
#
# Usage:
#
#   consolidate-repos.sh -i sagedir -o outdir -t tmpdir
#
# Output:
#
# - A consolidated repo in outdir
# - tarballs for the source files in outdir/upstream/

CMD="${0##*/}"

die () {
    echo $@ 1>&2
    exit 1
}

usage () {
    echo "usage: $CMD -i sagedir -o outdir -t tmpdir"
}

# parse command line options
while getopts "i:o:t:" opt ; do
    case $opt in
        i) SAGEDIR=$(readlink -f "$OPTARG") ;;
        o) OUTDIR=$(readlink -f "$OPTARG") ;;
        t) TMPDIR=$(readlink -f "$OPTARG") ;;
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

export SAGEDIR OUTDIR TMPDIR

mkdir -p "$TMPDIR" && cd "$TMPDIR" && rm -rf *

# initialize output repo
git init "$TMPDIR"/sage-repo && cd "$TMPDIR"/sage-repo

# move the base tarballs into upstream
mkdir -p "$OUTDIR"/upstream
mkdir "$TMPDIR"/spkg
for TARBALL in "$SAGEDIR"/spkg/base/*.tar* ; do
    PKGNAME=$(sed -e 's/.*\/\([^/]*\)-[0-9]\{1,\}.*$/\1/' <<<"$TARBALL")
    PKGVER=$(sed -e 's/^-\(.*\)\.tar.*$/\1/' <<<"${TARBALL#*${PKGNAME}}")
    tar x -p -C "$TMPDIR"/spkg -f $TARBALL
    tar c -f "$OUTDIR"/upstream/$PKGNAME-$PKGVER.tar -C "$TMPDIR"/spkg/ $PKGNAME-$PKGVER
done

# get the SPKG repos converted to git and pull them into the consolidated repo
# also tarball the src/ directories of the SPKGs and put them into a upstream/ directory
rm -f "$OUTDIR"/detracked-files.txt
mkdir "$TMPDIR"/spkg-git

process-spkg () {
    # figure out what the spkg is
    SPKGPATH=$1
    SPKG="${SPKGPATH#$SAGEDIR/spkg/standard/}"
    PKGNAME=$(sed -e 's/\([^-]*\)-[0-9].*.spkg$/\1/' <<< "$SPKG")
    PKGVER=$(sed -e 's/^-\(.*\)\.spkg$/\1/' <<< "${SPKG#"$PKGNAME"}")
    PKGVER_UPSTREAM=$(sed -e 's/\.p[0-9][0-9]*$//' <<<"$PKGVER")
    echo
    echo "*** Found SPKG: $PKGNAME version $PKGVER"
    tar x -p -C "$TMPDIR"/spkg -f "$SPKGPATH"

    # determine eventual subtree of the spkg's repo
    # tarball the src/ directory and put it into our upstream/ directory
    case $PKGNAME in
        sage_root) REPO=. ;;
        sage) REPO=devel ;;
        sage_scripts) REPO=devel/bin ;;
        extcode) REPO=devel/ext ;;
        *)  REPO=packages/$PKGNAME
            mv -T "$TMPDIR"/spkg/$PKGNAME-$PKGVER/src "$TMPDIR"/spkg/$PKGNAME-$PKGVER/$PKGNAME-$PKGVER_UPSTREAM
            tar c -jf "$OUTDIR"/upstream/$PKGNAME-$PKGVER_UPSTREAM.tar.bz2 -C "$TMPDIR"/spkg/$PKGNAME-$PKGVER/ $PKGNAME-$PKGVER_UPSTREAM
        ;;
    esac

    # convert the SPKG's hg repo to git
    git init --bare "$TMPDIR"/spkg-git/$PKGNAME
    pushd "$TMPDIR"/spkg-git/$PKGNAME > /dev/null
    hg -R "$TMPDIR"/spkg/$PKGNAME-$PKGVER push . ; # hg-git returns non-zero exit code upon warnings (!?)
        rm -rf "$TMPDIR"/spkg/$PKGNAME-$PKGVER

    # rewrite paths
    # (taken from `man git-filter-branch` and modified a bit)
    if [[ "$REPO" != "." ]]; then
        git filter-branch -f -d "$TMPDIR/filter-branch/$SPKG" --prune-empty --index-filter "
            git ls-files -s | sed \"s+\t\\\"*+&$REPO/+\" | GIT_INDEX_FILE=\$GIT_INDEX_FILE.new git update-index --index-info &&
            mv \"\$GIT_INDEX_FILE.new\" \"\$GIT_INDEX_FILE\" &&
            git rm -rf --cached --ignore-unmatch $REPO/src/ >> $OUTDIR/detracked-files.txt
        " master
    else
        # Incidentally this should do nothing in the case of the base
        # repo in particular, since there is no ./src
        git filter-branch -f -d "$TMPDIR/filter-branch/$SPKG" --prune-empty --index-filter "
            git rm -rf --cached --ignore-unmatch ./src/ >> $OUTDIR/detracked-files.txt
        " master
    fi
    popd > /dev/null

    # pull it into the consolidated repo
    if [[ "$REPO" == '.' ]]; then
        BRANCH=base
    elif [[ "$REPO" == 'devel' ]]; then
        # you can't have branches named devel and devel/foo at the same time
        BRANCH=library
    else
        BRANCH=$REPO
    fi
    git fetch -n "$TMPDIR"/spkg-git/$PKGNAME master:$BRANCH &&
        rm -rf "$TMPDIR"/spkg-git/$PKGNAME/.git

    # save the package version for later
    echo "$PKGVER" > "$TMPDIR"/spkg-git/$PKGNAME/spkg-version.txt
}
export -f process-spkg

for SPKGPATH in "$SAGEDIR"/spkg/standard/*.spkg ; do
    process-spkg "$SPKGPATH"
done

if [[ $(command -v notify-send) ]] ; then
    notify-send "$CMD: finished parsing SPKGs"
fi


# Humongous octomerge

# Put together a directory listing for the repo to commit in the merge
BRANCHES=$(git branch)
DEVOBJS=""
PKGOBJS=""
MERGEOBJS=""
# Collect directory entries from the various branches
for BRANCH in $BRANCHES ; do
    case "$BRANCH" in
        base)
            # Base entries are in the current directory, so we
            # output them into $MERGEOBJS immediately.
            MERGEOBJS="${MERGEOBJS}$(git ls-tree $BRANCH .)\n"
            ;;
        devel/*)
            # We incrementally build a list of stuff in devel/ ;
            # this $BRANCH will give us one of the subdirs' tree
            # objects. This will happen twice, once for devel/bin
            # and once for devel/ext.
            DEV_ENTRY=$(git ls-tree -d $BRANCH $BRANCH)
            DEV_ENTRY=$(sed "s+devel/++" <<<"$DEV_ENTRY")
            DEVOBJS="${DEVOBJS}${DEV_ENTRY}\n"
            ;;
        library)
            # We incrementally build a list of stuff in devel/ ;
            # this $BRANCH will give us the rest of the entries in
            # devel/ .
            DEV_ENTRIES=$(git ls-tree $BRANCH devel/)
            DEV_ENTRIES=$(sed "s+devel/++" <<<"$DEV_ENTRIES")
            DEVOBJS="${DEVOBJS}${DEV_ENTRIES}\n"
            ;;
        packages/*)
            # We incrementally build a list of stuff in packages/
            # ; this $BRANCH will give us one of the subdirs' tree
            # objects. This will happen many many times.
            PKG_ENTRY=$(git ls-tree -d $BRANCH $BRANCH)
            PKG_ENTRY=$(sed "s+packages/++" <<<"$PKG_ENTRY")
            PKGOBJS="${PKGOBJS}${PKG_ENTRY}\n"
            ;;
        *)
            # WTF?
            die "Something bizarre happened; branch name $BRANCH shouldn't exist!"
    esac
done

# Produce new directory listing objects for packages/ and devel/
# from the information gathered above, then dump those objects
# into the listing of the root directory which we are building on
# stdout. --batch is used because there's an extra newline at the
# end of $DEVOBJS and $PKGOBJS.
DEVTREE=$(echo -e "$DEVOBJS" | git mktree --missing --batch)
PKGTREE=$(echo -e "$PKGOBJS" | git mktree --missing --batch)
MERGEOBJS="${MERGEOBJS}040000 tree $DEVTREE\tdevel\n"
MERGEOBJS="${MERGEOBJS}040000 tree $PKGTREE\tpackages"

# Actually make the directory listing into a git object
MERGETREE=$(echo -e "$MERGEOBJS" | git mktree --missing)
# Commit the new fully consolidated file tree
MERGECOMMIT=$(
    {
        for BRANCH in $BRANCHES ; do
            echo '-p '$(git show-ref -s --heads $BRANCH)
        done
    } | xargs git commit-tree $MERGETREE -m "ePiC oCtOmErGe"
)
# Set up a new master branch and delete the other branches, and we're
# done!
git checkout -b master $MERGECOMMIT
for BRANCH in $BRANCHES ; do
    git branch -d $BRANCH || die "The octomerge failed; $BRANCH is still unmerged!"
done

# Clean up or adapt .hg* files (Mercurial-related data)
for REPO in $BRANCHES ; do
    [[ "$REPO" == 'base' ]] && REPO=.
    [[ "$REPO" == 'library' ]] && REPO=devel
    git rm --ignore-unmatch "$REPO"/.hgtags
    if [ -f "$REPO"/.hgignore ]; then
        git mv "$REPO"/.hgignore "$REPO"/.gitignore
    fi
done
git commit -m "[CLEANUP] Mercurial-related data"

# Commit package-version.txt files to track package \.p[0-9]+ versions
# (i.e. local revisions)
for BRANCH in $BRANCHES ; do
    case $BRANCH in
        packages/*)
            PKGNAME=${BRANCH#packages/}
            mv "$TMPDIR"/spkg-git/$PKGNAME/spkg-version.txt -T packages/$PKGNAME/package-version.txt
            git add packages/$PKGNAME/package-version.txt
            ;;
    esac
done
git commit -m "[CLEANUP] Add package-version.txt files"

# Optimize the repo
git gc --aggressive --prune=0

# Move the consolidated repo into place, and check out the package
# installation scripts so that Sage can start building
mv "$TMPDIR"/sage-repo/.git "$OUTDIR"
cd "$OUTDIR"
git checkout master .

# Clean up $TMPDIR
cd "$OUTDIR"
[[ -z $MADETMP ]] || rm -rf "$TMPDIR"
