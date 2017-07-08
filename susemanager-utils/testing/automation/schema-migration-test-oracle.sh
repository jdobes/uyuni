#! /bin/sh

HERE=`dirname $0`
. $HERE/VERSION
GITROOT=`readlink -f $HERE/../../../`

# we need a special (old) baseimage to migrate to current schema
docker pull $REGISTRY/$ORACLE_CONTAINER
docker run --privileged --rm=true -v "$GITROOT:/manager" $REGISTRY/$ORACLE_CONTAINER /manager/susemanager-utils/testing/docker/scripts/schema_migration_test_oracle-21to31.sh
