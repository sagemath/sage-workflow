#!/usr/bin/env bash

WORKFLOW_DIR=$(readlink -f "$0")
WORKFLOW_DIR=${WORKFLOW_DIR%/*}

SAGE_BUILD=build
SAGE_MACAPP=mac-app
SAGE_PKGS=build
SAGE_SCRIPTS=bin
SAGE_SRC=src
SAGE_TARBALLS=upstream
