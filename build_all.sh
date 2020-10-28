#!/usr/bin/env bash
# usage {{{1 ------------------------------------------------------------------
#/ Usage: 
#/
#/  ./build_all.sh [OPTIONS] --tag <version tag number>
#/
#/    this script will build all of the related images
#/
#/    -t|--tag)
#/       provide a version tag for the builds
#/    -h|-?|--help)
#/       show this help and exit
#/    -v|--verbose)
#/       make the script chatty
#/
# 1}}} ------------------------------------------------------------------------
# environment {{{1 ------------------------------------------------------------
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
# 1}}} ------------------------------------------------------------------------
# functions {{{1 --------------------------------------------------------------
banner() { # {{{2 -------------------------------------------------------------
  echo -e "\\e[31m Some Project Banner\\e[39m"
} # 2}}} ----------------------------------------------------------------------
die() { # {{{2 ----------------------------------------------------------------
  echo -e "\\e[31mFAILURE:\\e[39m $1"
  exit 1
} # 2}}} ----------------------------------------------------------------------
warn() { # {{{2 ---------------------------------------------------------------
  echo -e "\\e[33mWARNING:\\e[39m $1"
} # 2}}} ----------------------------------------------------------------------
show_help() { # {{{2 ----------------------------------------------------------
  grep '^#/' "${BASH_SOURCE[0]}" | cut -c4- || \
    die "Failed to display usage information"
} # 2}}} ----------------------------------------------------------------------
# 1}}} ------------------------------------------------------------------------
# arguments {{{1 --------------------------------------------------------------
while :; do
  case $1 in # check arguments {{{2 -------------------------------------------
		-t|--tag) # tag {{{3 ------------------------------------------------------
			BUILD_TAG=$2
			shift 2
			;; # 3}}} ---------------------------------------------------------------
    -h|-\?|--help) # help {{{3 ------------------------------------------------
      banner
      show_help
      exit
      ;; # 3}}} ---------------------------------------------------------------
    -?*) # unknown argument {{{3 ----------------------------------------------
      warn "Unknown option (ignored): $1"
      shift
      ;; # 3}}} ---------------------------------------------------------------
    *) # default {{{3 ---------------------------------------------------------
      break # 3}}} ------------------------------------------------------------
  esac # 2}}} -----------------------------------------------------------------
done
# 1}}} ------------------------------------------------------------------------
# logic {{{1 ------------------------------------------------------------------
if [ "$BUILD_TAG" == "" ]; then
	die "a tag must be supplied in order to build the images"
fi
$DIR/rasterpy/build.sh $BUILD_TAG
docker pull code.ornl.gov:4567/6ng/choppy-lite/rasterpy:latest
$DIR/build.sh $BUILD_TAG
# 1}}} ------------------------------------------------------------------------
