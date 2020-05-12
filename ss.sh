#!/bin/bash

action=$1
service=$2
shift 2

ROOTDIR=$ROOTDIR
if [ -z "$ROOTDIR" ]; then
	ROOTDIR="."
fi

PARAMS="-Xms256m -Xmx512m"

set -- $(getopt d:p: "$@")
while getopts d:p: opt; do
case $opt in
d) ROOTDIR=$OPTARG ;;
p) PARAMS=$OPTARG ;;
*) echo "$opt=$OPTARG" ;;
esac
done


declare -A named_services
named_services["eureka"]="eureka.jar"
named_services["config"]="config.jar"

names=`echo ${!named_services[@]}|sed -n 's/ /|/gp'`

usages() {
    echo "Usages: $0 [start|stop|status] [$names]"
    exit 1
}

service_pid() {
	name=$1;
	echo `ps -C java --no-heading -opid,cmd|grep $name|awk '{print $1}'`
}

service_status() {
	name=$1
	pid=$(service_pid $name)
	if [ $pid"x" != "x" ]; then
		echo "$name is running with pid=$pid"
	else
		echo "$name is not running"
	fi
}

start_service() {
	name=$1
	pid=$(service_pid $name)
	if [ $pid"x" != "x" ]; then
		echo "$name is running with pid=$pid"
		exit 0
	fi
	shift 1
	jar_path="$ROOTDIR"/${named_services[$name]}
	java $PARAMS -jar $jar_path >> nohup.$name&
}

stop_service() {
	name=$1
	pid=$(service_pid $name)
	if [ $pid"x" != "x" ]; then
		kill -9 $pid
		exit 0
	fi
	echo "$name is not running"
}

case "$action" in
  "start")
	start_service $service
  ;;
  "stop")
	stop_service $service
  ;;
  "status")
	service_status $service
  ;;
  *)
	usages
  ;;
esac

