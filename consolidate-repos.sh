#!/usr/bin/env bash

# consolidate-repos.sh
#
# Requires git, hg, and hg-git, as well as a copy of Sage. hg-git must
# contain revision e58a6d0b80e2, to avoid getting corrupt git repos.
# As of 2012-03-19 this means it needs to be directly pulled from the
# repo at http://bitbucket.org/durin42/hg-git/ .
#
# If GNU parallel is present, certain operations will be parallelized.
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

export SAGEDIR OUTDIR TMPDIR

mkdir -p "$TMPDIR" && cd "$TMPDIR" && rm -rf *

# initialize output repo
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
rm -f "$OUTDIR"/detracked-files.txt
mkdir "$TMPDIR"/spkg-git

process-spkg () {
    # figure out what the spkg is
    SPKGPATH=$1
    SPKG="${SPKGPATH#$SAGEDIR/spkg/standard/}"
    PKGNAME=$(sed -e 's/\([^-]*\)-[0-9].*.spkg$/\1/' <<< "$SPKG")
    PKGVER=$(sed -e 's/^-\(.*\)\.spkg$/\1/' <<< "${SPKG#"$PKGNAME"}")
    PKGVER_UPSTREAM=$(sed -e 's/\.p[0-9][0-9]*$//' <<<"$PKGVER")
    echo "Found SPKG: $PKGNAME version $PKGVER"
    tar x -p -C "$TMPDIR"/spkg -f "$SPKGPATH"

    # determine eventual subtree of the spkg's repo
    # tarball the src/ directory and put it into our dist/ directory
    case $PKGNAME in
        extcode) REPO=ext ;;
        sage) REPO=library ;;
        sage_root) REPO=base ;;
        sage_scripts) REPO=bin ;;
        *)
            mv -T "$TMPDIR"/spkg/$PKGNAME-$PKGVER/src "$TMPDIR"/spkg/$PKGNAME-$PKGVER/$PKGNAME-$PKGVER_UPSTREAM
            tar c -jf "$OUTDIR"/dist/$PKGNAME-$PKGVER_UPSTREAM.tar.bz2 -C "$TMPDIR"/spkg/$PKGNAME-$PKGVER/ $PKGNAME-$PKGVER_UPSTREAM
            REPO=spkg/$PKGNAME
        ;;
    esac

    # convert the SPKG's hg repo to git
    git init --bare "$TMPDIR"/spkg-git/$PKGNAME
    pushd "$TMPDIR"/spkg-git/$PKGNAME
    hg -R "$TMPDIR"/spkg/$PKGNAME-$PKGVER push . ; # hg-git returns non-zero exit code upon warnings (!?)
        rm -rf "$TMPDIR"/spkg/$PKGNAME-$PKGVER

    # rewrite paths
    # (taken from `man git-filter-branch` and modified a bit)
    git filter-branch -f -d "$TMPDIR/filter-branch/$SPKG" --prune-empty --index-filter "
        git ls-files -s | sed \"s+\t\\\"*+&$REPO/+\" | GIT_INDEX_FILE=\$GIT_INDEX_FILE.new git update-index --index-info &&
        mv \"\$GIT_INDEX_FILE.new\" \"\$GIT_INDEX_FILE\" &&
        git rm -rf --cached --ignore-unmatch $REPO/src/ >> $OUTDIR/detracked-files.txt
    " master
    popd

    # pull it into the consolidated repo
    git fetch -n "$TMPDIR"/spkg-git/$PKGNAME master:$REPO &&
        rm -rf "$TMPDIR"/spkg-git/$PKGNAME/.git

    # save the package version for later
    echo "$PKGVER" > "$TMPDIR"/spkg-git/$PKGNAME/spkg-version.txt
}
export -f process-spkg

if [[ $(command -v parallel) ]]; then
    find "$SAGEDIR/spkg/standard" -name '*.spkg' |
        parallel 'process-spkg {}'
else
    for SPKGPATH in "$SAGEDIR"/spkg/standard/*.spkg; do
        process-spkg "$SPKGPATH"
    done
fi

if [[ $(command -v notify-send) ]]; then
    notify-send "$CMD: finished parsing SPKGs"
fi


# Humongous octomerge

# Put together a directory listing for the repo to commit in the merge
BRANCHES=$(git branch)
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
for BRANCH in $BRANCHES;
do
    git branch -d $BRANCH || die "The octomerge failed; $BRANCH is still unmerged!"
done

# Clean up or adapt .hg* files (Mercurial-related data)
for BRANCH in $BRANCHES;
do
    git rm --ignore-unmatch "$BRANCH"/.hgtags
    if [ -f "$BRANCH"/.hgignore ]; then
        sed "s+^[^#]+$BRANCH/&+" "$BRANCH"/.hgignore >> .gitignore
        echo >> .gitignore
        git rm "$BRANCH"/.hgignore
    fi
done
git add .gitignore
git commit -m "[CLEANUP] Mercurial-related data"

# Commit spkg-version.txt files to track package \.p[0-9]+ versions
# (i.e. local revisions)
for BRANCH in $BRANCHES
do
    PKGNAME=${BRANCH#spkg/}
    if [ "$BRANCH" != "$PKGNAME" ]; then
        mv "$TMPDIR"/spkg-git/$PKGNAME/spkg-version.txt spkg/$PKGNAME/
        git add spkg/$PKGNAME/spkg-version.txt
    fi
done
git commit -m "[CLEANUP] Add spkg-version.txt files"

# Optimize the repo
git gc --aggressive --prune=0

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
