#!/usr/bin/env bash
# Dev helper: run Maven from Git Bash / MinGW on Windows.
#
# The upstream `mvn` shell script does not convert the boot classpath to a
# Windows path for MinGW (see the `# TODO classpath?` branch in its source), so
# `java -classpath <posix-path>` fails with
# "ClassNotFoundException: org.codehaus.plexus.classworlds.launcher.Launcher".
# This wrapper launches the launcher jar with an explicit Windows-format path.
#
# Usage: scripts/mvn.sh [maven args...]     e.g.  scripts/mvn.sh -q test
set -euo pipefail

MAVEN_ROOT_POSIX="${MAVEN_ROOT_POSIX:-/c/Users/18414/scoop/apps/maven/current}"
MAVEN_ROOT_WIN="$(cygpath -w "${MAVEN_ROOT_POSIX}")"
CLASSWORLDS_JAR_WIN="$(cygpath -w "$(ls "${MAVEN_ROOT_POSIX}/boot/plexus-classworlds-"*.jar | head -n1)")"
PROJECT_DIR_WIN="$(cygpath -w "$(pwd)")"

exec java \
  -classpath "${CLASSWORLDS_JAR_WIN}" \
  "-Dclassworlds.conf=${MAVEN_ROOT_WIN}\\bin\\m2.conf" \
  "-Dmaven.home=${MAVEN_ROOT_WIN}" \
  "-Dmaven.multiModuleProjectDirectory=${PROJECT_DIR_WIN}" \
  org.codehaus.plexus.classworlds.launcher.Launcher "$@"
