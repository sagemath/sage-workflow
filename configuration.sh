#!/usr/bin/env bash

WORKFLOW_DIR=$(readlink -f "$0")
WORKFLOW_DIR=${WORKFLOW_DIR%post-process.sh}

SAGE_SRC=src
SAGE_BUILD=build
