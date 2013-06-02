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
rm -rf "$OUTDIR"
mkdir -p "$OUTDIR"/$SAGE_TARBALLS
mkdir -p "$TMPDIR"/spkg
cp "$SAGEDIR"/spkg/base/*.tar* "$OUTDIR"/$SAGE_TARBALLS

# get the SPKG repos converted to git and pull them into the consolidated repo
# also tarball the src/ directories of the SPKGs and put them into a $SAGE_TARBALLS/ directory
mkdir -p "$TMPDIR"/spkg-git

process-spkg () {
    # figure out what the spkg is
    SPKGPATH=$1
    SPKG="${SPKGPATH#$SAGEDIR/spkg/*/}"
    SPKG="${SPKG%.spkg}"
    PKGNAME=$(sed -e 's/\([^-_]*\)[-_][0-9].*$/\1/' <<< "$SPKG")
    PKGVER=$(sed -e 's/^[-_]\+\(.*\)$/\1/' -e 's/[-_]/\./g' <<< "${SPKG#"$PKGNAME"}")
    PKGVER_UPSTREAM=$(sed -e 's/\.p[0-9][0-9]*$//' <<<"$PKGVER")
    echo
    echo "*** Found SPKG: $PKGNAME version $PKGVER"
    tar x -p -C "$TMPDIR"/spkg -f "$SPKGPATH"

    # determine eventual subtree of the spkg's repo
    # tarball the src/ directory and put it into our $SAGE_TARBALLS/ directory
    # apply any WIP mecurial patches
    pushd "$TMPDIR"/spkg/$SPKG > /dev/null
    if [ ! -d .hg ]; then
        popd > /dev/null
        rm -rf "$TMPDIR"/spkg/$SPKG
        echo "${SPKGPATH#$SAGEDIR/spkg/}" >> "$OUTDIR"/failed-spkgs.txt
        return 0
    fi
    
    TAGS_SWITCH=''
    case $PKGNAME in
        sage_root)
            REPO=.
            BRANCH=base
        ;;
        sage)
            REPO=$SAGE_SRC
            BRANCH=library
            TAGS_SWITCH='--tag-name-filter cat'
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

            rm -f .hgignore # hg add doesn't really add things if the file is supposed to be ignored
            case "$PKGNAME" in
                # some packages need a bit of special processing
                atlas)
                    mv lapack-*.tar src
                ;;
                mpfr)
                    hg add patches/upstream
                    hg commit -m 'mpfr: add upstream patches to the repository'
                ;;
                cliquer)
                    hg add patches
                    hg commit -m 'cliquer: add patches to the repository'
                ;;
                ntl)
                    mv libtool src
                ;;
                singular)
                    mv shared src
                ;;
            esac

            if tar --test-label < "$SPKGPATH" 2>/dev/null; then
                TAROPTS=
                TAREXT=.tar
            elif gzip -t "$SPKGPATH" 2>/dev/null; then
                TAROPTS=z
                TAREXT=.tar.gz
            else # assume everything else is bzip2
                TAROPTS=j
                TAREXT=.tar.bz2
            fi
            mv -T "$TMPDIR"/spkg/$SPKG/src "$TMPDIR"/spkg/$SPKG/$PKGNAME-$PKGVER_UPSTREAM
            tar c -${TAROPTS}f "$OUTDIR"/$SAGE_TARBALLS/$PKGNAME-${PKGVER_UPSTREAM}${TAREXT} -C "$TMPDIR"/spkg/$SPKG/ $PKGNAME-$PKGVER_UPSTREAM
            rm -rf "$TMPDIR"/spkg/$SPKG/$PKGNAME-$PKGVER_UPSTREAM
        ;;
    esac
    popd > /dev/null

    # convert the SPKG's hg repo to git
    git init --bare "$TMPDIR"/spkg-git/$PKGNAME
    pushd "$TMPDIR"/spkg-git/$PKGNAME > /dev/null
    $WORKFLOW_DIR/fast-export/hg-fast-export.sh -r "$TMPDIR"/spkg/$SPKG -M master
    rm -rf "$TMPDIR"/spkg/$SPKG

    # rewrite paths
    # hacked into git-filter-branch so that we can use a bash array across
    # commits (bash does not support exporting arrays)
    export REPO SAGE_BUILD SAGE_MACAPP SAGE_SCRIPTS_DIR SAGE_EXTDIR
    $WORKFLOW_DIR/git-filter-branch -f -d "$TMPDIR/filter-branch/$SPKG" --prune-empty --index-filter '' $TAGS_SWITCH master
    popd > /dev/null

    if [ -n "$TAGS_SWITCH" ]; then
        TAGS_SWITCH=''
    else
        TAGS_SWITCH='-n'
    fi
    # pull it into the consolidated repo
    git fetch $TAGS_SWITCH "$TMPDIR"/spkg-git/$PKGNAME master:$BRANCH &&
        rm -rf "$TMPDIR"/spkg-git/$PKGNAME

    # save the package version for later
    mkdir -p "$TMPDIR"/spkg-git/$PKGNAME
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
BRANCHES=$(git branch | sed 's+^\**\s*++')
DEVOBJS=""
PKGOBJS=""
# Collect directory entries from the various branches
for BRANCH in $BRANCHES ; do
    case "$BRANCH" in
        base)
            # Skip for now, we will merge this with the other
            # trees later
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
    while true
    do
        TREE=$(echo -e "040000 tree $TREE\t${TREE_DIR##*/}" | git mktree --missing)
        if [[ "${TREE_DIR}" != *"/"* ]]; then
            echo -n "$TREE"
            return 0
        fi
        TREE_DIR="${TREE_DIR%/*}"
    done
}
export -f flatten-tree

get-object () {
    git ls-tree $1 $2 | cut -f3 -d' ' | cut -f1
}
export -f get-object

merge-tree () {
    local TREE_ONE=$1
    local TREE_TWO=$2
    local LS_ONE LS_TWO LS_NEW ITEM
    LS_ONE="$(git ls-tree --name-only $TREE_ONE)"
    LS_TWO="$(git ls-tree --name-only $TREE_TWO)"
    LS_NEW="$(printf '%s\n%s\n' "$LS_ONE" "$LS_TWO"| sort -u)"

    # all duplicates are assumed to be trees
    for ITEM in $LS_NEW; do
        if echo "$LS_ONE" | egrep "^$ITEM$" >/dev/null; then
            if echo "$LS_TWO" | egrep "^$ITEM$" >/dev/null; then
                echo -e "040000 tree $(merge-tree $(get-object $TREE_ONE "$ITEM") $(get-object $TREE_TWO "$ITEM"))\t$ITEM"
            else
                git ls-tree $TREE_ONE "$ITEM"
            fi
        else
            git ls-tree $TREE_TWO "$ITEM"
        fi
    done | git mktree --missing
}
export -f merge-tree

DEVTREE=$(echo -e "$DEVOBJS" | git mktree --missing --batch)
PKGTREE=$(echo -e "$PKGOBJS" | git mktree --missing --batch)
DEVTREE=$(flatten-tree $DEVTREE "$SAGE_SRC")
PKGTREE=$(flatten-tree $PKGTREE "$SAGE_PKGS")

MERGETREE=$(merge-tree base $DEVTREE)
MERGETREE=$(merge-tree $MERGETREE $PKGTREE)

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
[[ -z $MADETMP ]] || rm -rf "$TMPDIR"
