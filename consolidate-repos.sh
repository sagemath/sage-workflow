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
# - tarballs for the source files in outdir/$SAGE_TARBALLS/

. ${0%consolidate-repos.sh}configuration.sh

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

# move the base tarballs into $SAGE_TARBALLS
mkdir -p "$OUTDIR"/$SAGE_TARBALLS
mkdir "$TMPDIR"/spkg
for TARBALL in "$SAGEDIR"/spkg/base/*.tar* ; do
    PKGNAME=$(sed -e 's/.*\/\([^/]*\)-[0-9]\{1,\}.*$/\1/' <<<"$TARBALL")
    PKGVER=$(sed -e 's/^-\(.*\)\.tar.*$/\1/' <<<"${TARBALL#*${PKGNAME}}")
    tar x -p -C "$TMPDIR"/spkg -f $TARBALL
    tar c -f "$OUTDIR"/$SAGE_TARBALLS/$PKGNAME-$PKGVER.tar -C "$TMPDIR"/spkg/ $PKGNAME-$PKGVER
done

# get the SPKG repos converted to git and pull them into the consolidated repo
# also tarball the src/ directories of the SPKGs and put them into a $SAGE_TARBALLS/ directory
rm -f "$OUTDIR"/detracked-files.txt
mkdir "$TMPDIR"/spkg-git

fix-whitespace () {
    while read file
    do
        cat "$file" | git stripspace > "$TMPDIR"/nospacefile
        mv "$TMPDIR"/nospacefile "$file"
    done
}
export -f fix-whitespace

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
    # tarball the src/ directory and put it into our $SAGE_TARBALLS/ directory
    case $PKGNAME in
        sage_root)
            REPO=.
            BRANCH=base
        ;;
        sage)
            REPO=$SAGE_SRC
            BRANCH=library
        ;;
        sage_scripts)
            REPO=$SAGE_SCRIPTS_DIR
            BRANCH=devel/bin
        ;;
        extcode)
            REPO=$SAGE_EXTDIR
            BRANCH=devel/ext
        ;;
        *)
            REPO=$SAGE_PKGS/$PKGNAME
            BRANCH=packages/$PKGNAME
            mv -T "$TMPDIR"/spkg/$PKGNAME-$PKGVER/src "$TMPDIR"/spkg/$PKGNAME-$PKGVER/$PKGNAME-$PKGVER_UPSTREAM
            tar c -jf "$OUTDIR"/$SAGE_TARBALLS/$PKGNAME-$PKGVER_UPSTREAM.tar.bz2 -C "$TMPDIR"/spkg/$PKGNAME-$PKGVER/ $PKGNAME-$PKGVER_UPSTREAM
        ;;
    esac

    # convert the SPKG's hg repo to git
    git init --bare "$TMPDIR"/spkg-git/$PKGNAME
    pushd "$TMPDIR"/spkg-git/$PKGNAME > /dev/null
    hg -R "$TMPDIR"/spkg/$PKGNAME-$PKGVER push . ; # hg-git returns non-zero exit code upon warnings (!?)
        rm -rf "$TMPDIR"/spkg/$PKGNAME-$PKGVER

    # rewrite paths
    # (taken from `man git-filter-branch` and modified a bit)
    if [[ "$REPO" == "." ]]; then
        git filter-branch -f -d "$TMPDIR/filter-branch/$SPKG" --prune-empty --index-filter "
            git ls-files -s | sed \"s+\tspkg/bin+\t$SAGE_SCRIPTS_DIR+\" | sed \"s+\tspkg+\t$SAGE_BUILD+\" |
            GIT_INDEX_FILE=\$GIT_INDEX_FILE.new git update-index --index-info &&
            mv \"\$GIT_INDEX_FILE.new\" \"\$GIT_INDEX_FILE\"
        " --tree-filter '
            git diff-tree --name-only --diff-filter=AM -r --no-commit-id $GIT_COMMIT | fix-whitespace
        ' master
    elif [[ "$REPO" == "$SAGE_EXTDIR" ]]; then
        git filter-branch -f -d "$TMPDIR/filter-branch/$SPKG" --prune-empty --index-filter "
            git ls-files -s | sed \"s+\t+&$REPO/+\" | sed \"s+$REPO/sage/ext/mac-app+$SAGE_MACAPP+\" |
            GIT_INDEX_FILE=\$GIT_INDEX_FILE.new git update-index --index-info &&
            mv \"\$GIT_INDEX_FILE.new\" \"\$GIT_INDEX_FILE\"
            git rm -rf --cached --ignore-unmatch $REPO/src/ >> $OUTDIR/detracked-files.txt
        " --tree-filter '
            git diff-tree --name-only --diff-filter=AM -r --no-commit-id $GIT_COMMIT | fix-whitespace
        ' master
    else
        git filter-branch -f -d "$TMPDIR/filter-branch/$SPKG" --prune-empty --index-filter "
            git ls-files -s | sed \"s+\t+&$REPO/+\" | GIT_INDEX_FILE=\$GIT_INDEX_FILE.new git update-index --index-info &&
            mv \"\$GIT_INDEX_FILE.new\" \"\$GIT_INDEX_FILE\" &&
            git rm -rf --cached --ignore-unmatch $REPO/src/ >> $OUTDIR/detracked-files.txt
        " --tree-filter '
            git diff-tree --name-only --diff-filter=AM -r --no-commit-id $GIT_COMMIT | fix-whitespace
        ' master
    fi
    popd > /dev/null

    # pull it into the consolidated repo
    git fetch -n "$TMPDIR"/spkg-git/$PKGNAME master:$BRANCH &&
        rm -rf "$TMPDIR"/spkg-git/$PKGNAME/.git

    # save the package version for later
    echo "$PKGVER" > "$TMPDIR"/spkg-git/$PKGNAME/spkg-version.txt
}
export -f process-spkg

for SPKGPATH in "$SAGEDIR"/spkg/*/*.spkg ; do
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
            # We incrementally build a list of stuff in $SAGE_SRC/ ;
            # this $BRANCH will give us one of the subdirs' tree
            # objects. This will happen twice, once for devel/bin
            # and once for devel/ext.
            case "$BRANCH" in
                devel/ext) BRANCH_DIR="$SAGE_EXTDIR $SAGE_MACAPP" ;;
                devel/bin) BRANCH_DIR=$SAGE_SCRIPTS_DIR ;;
            esac
            DEV_ENTRY=$(git ls-tree -d $BRANCH $BRANCH_DIR)
            DEV_ENTRY=$(sed "s+$SAGE_SRC/++" <<<"$DEV_ENTRY")
            DEVOBJS="${DEVOBJS}${DEV_ENTRY}\n"
            ;;
        library)
            # We incrementally build a list of stuff in $SAGE_SRC/ ;
            # this $BRANCH will give us the rest of the entries in
            # $SAGE_SRC/ .
            DEV_ENTRIES=$(git ls-tree $BRANCH $SAGE_SRC/)
            DEV_ENTRIES=$(sed "s+$SAGE_SRC/++" <<<"$DEV_ENTRIES")
            DEVOBJS="${DEVOBJS}${DEV_ENTRIES}\n"
            ;;
        packages/*)
            # We incrementally build a list of stuff in $SAGE_PKGS/
            # ; this $BRANCH will give us one of the subdirs' tree
            # objects. This will happen many many times.
            BRANCH_DIR=$SAGE_PKGS${BRANCH#packages}
            PKG_ENTRY=$(git ls-tree -d $BRANCH $BRANCH_DIR)
            PKG_ENTRY=$(sed "s+$SAGE_PKGS/++" <<<"$PKG_ENTRY")
            PKGOBJS="${PKGOBJS}${PKG_ENTRY}\n"
            ;;
        *)
            # WTF?
            die "Something bizarre happened; branch name $BRANCH shouldn't exist!"
    esac
done

# Produce new directory listing objects for $SAGE_PKGS/ and $SAGE_SRC/
# from the information gathered above, then dump those objects
# into the listing of the root directory which we are building on
# stdout. --batch is used because there's an extra newline at the
# end of $DEVOBJS and $PKGOBJS.
flatten-tree () {
    TREE="$1"
    TREE_DIR="$2"
    while [[ "$TREE_DIR" == *"/"* ]]
    do
        TREE=$(echo -e "040000 tree $TREE\t${TREE_DIR##*/}" | git mktree --missing)
        TREE_DIR="${TREE_DIR%/*}"
    done
    echo -n "040000 tree $TREE\t$TREE_DIR"
}
export -f flatten-tree

DEVTREE=$(echo -e "$DEVOBJS" | git mktree --missing --batch)
PKGTREE=$(echo -e "$PKGOBJS" | git mktree --missing --batch)
MERGEOBJS="${MERGEOBJS}$(flatten-tree "$DEVTREE" "$SAGE_SRC")\n"
MERGEOBJS="${MERGEOBJS}$(flatten-tree "$PKGTREE" "$SAGE_PKGS")"

# Actually make the directory listing into a git object
MERGETREE=$(echo -e "$MERGEOBJS" | git mktree --missing)
# Commit the new fully consolidated file tree
MERGECOMMIT=$(
    {
        for BRANCH in $BRANCHES ; do
            echo '-p '$(git show-ref -s --heads $BRANCH)
        done
    } | xargs git commit-tree $MERGETREE -m "Consolidate Sage's Repositories"
)
# Set up a new master branch and delete the other branches, and we're
# done!
git checkout -b master $MERGECOMMIT
for BRANCH in $BRANCHES ; do
    git branch -d $BRANCH || die "The octomerge failed; $BRANCH is still unmerged!"
done

# Commit package-version.txt files to track package \.p[0-9]+ versions
# (i.e. local revisions)
for BRANCH in $BRANCHES ; do
    case $BRANCH in
        packages/*)
            PKGNAME=${BRANCH#packages/}
            mv "$TMPDIR"/spkg-git/$PKGNAME/spkg-version.txt -T $SAGE_PKGS/$PKGNAME/package-version.txt
            git add $SAGE_PKGS/$PKGNAME/package-version.txt
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
