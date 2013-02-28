#!/usr/bin/env bash

WORKFLOW_DIR=$(readlink -f "$0")
WORKFLOW_DIR=${WORKFLOW_DIR%/*}

SAGE_BUILD=build
SAGE_SRC=src
SAGE_TARBALLS=upstream
SAGE_PKGS=$SAGE_BUILD
SAGE_SCRIPTS_DIR=$SAGE_SRC/bin
SAGE_MACAPP=$SAGE_SRC/mac-app

SAGE_CONSTANTS=$(cat <<EOF
  SAGE_BUILD
  SAGE_SRC
  SAGE_TARBALLS
  SAGE_SCRIPTS_DIR
  SAGE_MACAPP
  SAGE_PKGS
EOF
)

SED_ARGS=""
for constant in $SAGE_CONSTANTS
do
  constant_value=$(eval echo \$$constant)
  SED_ARGS="$SED_ARGS -e s+__${constant}__+$constant_value+g"
done

cat_workflow_file () {
  sed $SED_ARGS $WORKFLOW_DIR/$1
}
