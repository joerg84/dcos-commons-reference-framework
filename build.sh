#!/bin/bash

# This script does a full build/upload of Reference artifacts.
# This script is invoked by Jenkins CI, as well as by build-docker.sh.

# Prevent jenkins from immediately killing the script when a step fails, allowing us to notify github:
set +e

REPO_ROOT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $REPO_ROOT_DIR

if [ -z "$AWS_ACCESS_KEY_ID" -o -z "$AWS_SECRET_ACCESS_KEY" ]; then
    echo "Missing required AWS access info: AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY"
    exit 1
fi

# Grab dcos-commons build/release tools:
rm -rf dcos-commons-tools/ && curl https://infinity-artifacts.s3.amazonaws.com/dcos-commons-tools.tgz | tar xz

# GitHub notifier config
_notify_github() {
    $REPO_ROOT_DIR/dcos-commons-tools/github_update.py $1 build $2
}

_notify_github pending "Build running"

# Scheduler/Executor (Java):

./gradlew --refresh-dependencies distZip
if [ $? -ne 0 ]; then
  _notify_github failure "Gradle build failed"
  exit 1
fi

./gradlew check
if [ $? -ne 0 ]; then
  _notify_github failure "Unit tests failed"
  exit 1
fi

cd $REPO_ROOT_DIR

_notify_github success "Build succeeded"


./dcos-commons-tools/ci_upload.py \
  reference-framework \
  universe/ \
  reference-scheduler/build/distributions/*.zip \
