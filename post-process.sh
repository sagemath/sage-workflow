#!/usr/bin/env bash

. ${0%post-process.sh}configuration.sh

if [ $# -gt 1 ]; then
    SAGE_ROOT="$1"
else
    SAGE_ROOT="$(pwd)"
fi
SAGE_ROOT=$(readlink -f "$SAGE_ROOT")

cd "$SAGE_ROOT"

# remove .hg* files
git rm $(find -name '.hg*')
git commit -m "[CLEANUP] Mercurial-related data"

# final fix of file locations
git mv $SAGE_BUILD/standard/deps $SAGE_BUILD/deps
git commit -m "[REORG] Final fix of file locations"

# remove unused scripts
git rm $(find -name sage-push)
git rm $(find -name sage-pull)
git rm $(find $SAGE_SRC -name spkg-install)
git rm $(find $SAGE_SRC -name spkg-dist)
git rm $(find $SAGE_SRC -name spkg-delauto)
for file in $(cat <<FILES
  $SAGE_SRC/bundle
  $SAGE_SRC/export
  $SAGE_SRC/install
  $SAGE_SRC/pull
  $SAGE_SCRIPTS_DIR/sage-sage
  $SAGE_BUILD/root-spkg-install
  $SAGE_BUILD/gen_html
  $SAGE_BUILD/standard
FILES
)
do
    git rm -r $file
done
git commit -m "[CLEANUP] Old unused scripts"

# add gitignores
add_gitignore() {
    FILE=$1
    case $FILE in
        root) OUTDIR="." ;;
        build*) OUTDIR="$(sed -e "s+\$build+$SAGE_BUILD+" <<<$FILE)" ;;
        src*) OUTDIR="$(sed -e "s+\$src+$SAGE_SRC+" <<<$FILE)" ;;
        *) OUTDIR="$FILE" ;;
    esac
    OUTDIR="$(sed 's+-+/+g' <<<$OUTDIR)"

    cat_workflow_file post-process_files/gitignore-$FILE | sort > $OUTDIR/.gitignore
}

add_gitignore root
add_gitignore build
add_gitignore src-sage
add_gitignore src-c_lib

git add $(find -name '.gitignore')
git commit -m '[CLEANUP] Add gitignores'

# apply patchs
apply_patch () {
    cat_workflow_file post-process_files/$1.patch | git am
}

apply_patch sage-env1
apply_patch install1
apply_patch prereq-install1
apply_patch deps1
apply_patch sage-spkg1
apply_patch sage-starts1
apply_patch csage1
apply_patch sage1
