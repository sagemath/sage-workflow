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

# TODO: incorporate the following into consolidate repos
git mv $SAGE_SRC/ext/sage/ext/mac-app $SAGE_MACAPP
rm -r $SAGE_SRC/ext/sage
git commit -m '[REORG] Rewrite mac app directory'

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
FILES
)
do
  git rm $file
done
git rm -r $SAGE_BUILD/standard
git commit -m "[CLEANUP] Old unused scripts"

# add gitignores
cat_workflow_file post-process_files/gitignore-root | sort > .gitignore
git add $(find -name '.gitignore')
git commit -m '[CLEANUP] Add gitignores'
