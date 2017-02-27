#!/bin/bash
#
# Start file for all-in-one
set -eo pipefail

. /environment/bin/activate
commctl $@
