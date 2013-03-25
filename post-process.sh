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
  $SAGE_SRC/README.txt
  $SAGE_SRC/export
  $SAGE_SRC/install
  $SAGE_SRC/pull
  $SAGE_SRC/sage/misc/hg.py
  $SAGE_SCRIPTS_DIR/sage-sage
  $SAGE_SCRIPTS_DIR/sage-clone
  $SAGE_BUILD/root-spkg-install
  $SAGE_BUILD/gen_html
  $SAGE_BUILD/standard
FILES
)
do
    git rm -r $file
done
git commit -m "[CLEANUP] Unused files"

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

add_gitignore build
add_gitignore root
add_gitignore src
add_gitignore src-c_lib
add_gitignore src-doc
add_gitignore src-sage
add_gitignore src-sage-ext-interpreters

git add -f $(find -name '.gitignore')
git commit -m '[CLEANUP] Add gitignores'

# apply patchs
apply_patch () {
    cat_workflow_file post-process_files/$1.patch | git am
}

apply_patch sage-env1
cat_workflow_file post-process_files/sage-build > "$SAGE_SCRIPTS_DIR"/sage-build
chmod 755 "$SAGE_SCRIPTS_DIR"/sage-build
git add "$SAGE_SCRIPTS_DIR"/sage-build
git commit -m '(FIXUP) new sage-build script'
apply_patch install1
apply_patch prereq-install1
apply_patch deps1
apply_patch sage-spkg1
apply_patch sage-spkg2
apply_patch sage-starts1
apply_patch csage1
apply_patch sage1
apply_patch docbuild1
apply_patch sage_artifacts1
apply_patch ntl1
apply_patch singular1
apply_patch sagenb1
apply_patch hg1
apply_patch makefile1
apply_patch whitespace1
apply_patch devel_doctests1
apply_patch makefile2
apply_patch sage_data1
apply_patch sage-envpy1
apply_patch setup1
