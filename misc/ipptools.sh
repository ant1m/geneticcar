#!/bin/sh

### VARIABLES ###

BINARY_NAME="ceo-be-config-server"
TARGET_DIR="target"
PACKAGING_DIR=${TARGET_DIR}/package
CURRENT_VERSION=`cat misc/version.properties`
SNAPSHOT_TIMESTAMP=`date +%Y%m%d%H%M%S`

### TOOLS ###

function build_ipp_version {
  declare ippversion=$CURRENT_VERSION
  [[ $ippversion == *SNAPSHOT* ]] && ippversion=$ippversion-$SNAPSHOT_TIMESTAMP
  echo $ippversion
}

function build_archive_name {
  declare version=$(build_ipp_version)
  [[ $version == *SNAPSHOT* ]] || version="V$version"
  echo "$BINARY_NAME-batch-$version.tgz"
}

function ipp_deploy {
  declare ippversion=$1
  declare archive_name=$2  
  declare environment_key=$3
  declare module_name="$BINARY_NAME-batch"
  declare key=$DEPLOY_IPP93_KEY
  declare user=$DEPLOY_IPP_USER

  echo "--> deploying $module_name on IPP..."

  python misc/deploy.py --user=$user --env=${environment_key} -tbatch --baseurl=http://deploy.ipp93.cvf/ --key=$key $module_name deliver $PACKAGING_DIR/$archive_name && \
  python misc/deploy.py -u$user -e${environment_key} -tbatch --baseurl=http://deploy.ipp93.cvf/ -k$key $module_name install $ippversion && \
  python misc/deploy.py -u$user -e${environment_key} -tbatch --baseurl=http://deploy.ipp93.cvf/ -k$key $module_name batch stop && \
  python misc/deploy.py -u$user -e${environment_key} -tbatch --baseurl=http://deploy.ipp93.cvf/ -k$key $module_name batch start
  return $?
}

function upgrade_version {

  version=$CURRENT_VERSION
  if [ `echo -n $version | grep -c "SNAPSHOT"` -eq '1' ]
    then
    version=`echo -n $version | sed -e 's/-SNAPSHOT//'`
  fi

  MAJOR=`echo $version | sed -e 's/\([0-9]*\)\..*/\1/'`
  MINOR=`echo $version | sed -e 's/.*\.\([0-9]*\)\..*/\1/'`
  PATCH=`expr \`echo $version | sed -e 's/.*\.[0-9]*\.\([0-9]*\)/\1/'\` + 1`

  echo "Updating version... "

  new_version="$MAJOR.$MINOR.$PATCH-SNAPSHOT"
  read -p "New version [$new_version]: "
  if [ ! -z "$REPLY" ]
    then
    new_version=$REPLY
  fi
  
  echo $MAJOR.$MINOR.$PATCH-SNAPSHOT > misc/version.properties
  git commit -m "Update version.properties file" -a ; git push origin master
}

### GLOBAL COMMANDS ###

function package {
  rm -rf $PACKAGING_DIR
  mkdir -p $PACKAGING_DIR/common/bin && \
  cp -R bin/$BINARY_NAME $PACKAGING_DIR/common/bin && cp bin/${BINARY_NAME}_D $PACKAGING_DIR/common/bin && \
  mkdir -p $PACKAGING_DIR/common && \
  cp -R doc/ $PACKAGING_DIR/common && \
  cp -R env/ $PACKAGING_DIR/env && \
  echo "VERSION: $CURRENT_VERSION" > $PACKAGING_DIR/package.properties && \
  tar czvf $PACKAGING_DIR/$(build_archive_name) -C $PACKAGING_DIR `ls $PACKAGING_DIR` > /dev/null
  rm -rf $(find $PACKAGING_DIR | tail -n +2 | grep -v ".*tgz")
}

function deploy {
  declare ippversion=$(build_ipp_version)
  declare archive_name=$(build_archive_name)
  package $archive_name && \
  ipp_deploy $ippversion $archive_name $1
  result=$?
  if [ $result -ne 0 ] 
    then 
    echo "Deploy $module_to_deploy project on IPP failed"
    return $result
  fi
  echo "Deploy $module_to_deploy project on IPP with success"
}



function release {
  if [ "`git status | grep "Changes not staged for commit" | wc -l`" != "0" ]
    then
    echo "KO - You have local modifications, run git status first"
    return 1
  fi

  release_version=$CURRENT_VERSION
  if [ `echo -n $release_version | grep -c "SNAPSHOT"` -eq '1' ]
    then
    release_version=`echo -n $release_version | sed -e 's/-SNAPSHOT//'`
  fi
  
  read -p "Version [$release_version]: "
  if [ ! -z "$REPLY" ]
    then
    release_version=$REPLY
  fi

  CURRENT_VERSION=$release_version

  deploy "itg"
  result=$?
  if [ $result -ne 0 ] 
   then 
   echo "Deploy $module_to_deploy project on IPP failed"
   return $result
 fi
 echo "Deploy $module_to_deploy project on IPP with success"


 echo -n "Tagging GIT...  "
 git tag "RELEASE-$CURRENT_VERSION"
 if [ $? != 0 ]
  then
  echo "KO - The version $VERSION has already been tagged"
  return 1
fi

git push origin --tags	

upgrade_version

}



#### MAIN & USAGE ####

function usage {

  echo "
  Usage: $0 target

  Available targets : 
  package
  - Create an IPP compliant package (tarball)
  deploy [environment]
  - Create package and deploy a snapshot on [environment] IPP
  release [environment]
  - Create package and deploy a release on [environment] IPP
  "
  exit 1;
}

function main {

  if [ -z "$*" ] 
    then
    usage
    exit 1;
  fi

  eval set -- "$*"
  while [ -n "$*" ] 
  do
    case "$1" in 
    package) package || exit 1 ; shift ;;
    release) release || exit 1 ; shift ;;
    deploy)  shift ; deploy "$@" || exit 1; shift ;;
esac
done

}

main $*

