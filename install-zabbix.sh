#!/bin/bash

#set -x

version="5.0.1"
name="zabbix"
dbhost="127.0.0.1"
dbport="5432"
dbname="$name"
dbuser="$name"
dbpass="123456"
zdir="zabbix-$version"

if [ ! -d "$zdir" ]; then
        #wget https://cdn.zabbix.com/zabbix/sources/stable/5.0/zabbix-$version.tar.gz -O -|tar -xzf -
        if [ ! -f "$zdir.tar.gz" ]; then
                wget https://cdn.zabbix.com/zabbix/sources/stable/5.0/$zdir.tar.gz
        fi
        tar -xzf "$zdir.tar.gz"
fi
cd "$zdir"

groupadd --system --force $name
if [ "$(awk -F':' '/zabbix/{print $1}' /etc/passwd)" != "zabbix" ]; then
        useradd --system -g $name -d /usr/lib/$name -s /sbin/nologin -c "Zabbix Monitoring System" $name
fi

createuser -h $dbhost -p $dbport -U postgres $dbuser<<EOF
$dbpass
$dbpass
EOF
createdb -h $dbhost -p $dbport -U postgres -O $dbuser -E Unicode -T template0 $dbname

yum install centos-release-scl
yum -y install zlib-devel libevent-devel pcre-devel
yum install rh-php73-php-fpm rh-php73-php-pgsql rh-php73-php-gd rh-php73-php-xml rh-php73-php-bcmath rh-php73-php-mbstring
./configure --enable-server --with-postgresql
make install
#yum -y install postgresql96-devel
#./configure --enable-server --with-postgresql=/usr/pgsql-9.6/bin/pg_config

cd database/postgresql
psql -h $dbhost -p $dbport -U $dbuser $dbname -f schema.sql
psql -h $dbhost -p $dbport -U $dbuser $dbname -f images.sql
psql -h $dbhost -p $dbport -U $dbuser $dbname -f data.sql

mkdir -p /var/run/zabbix
chown $name:$name /var/run/zabbix
cat > /etc/zabbix/zabbix-server.conf <<EOF
LogFile=/var/log/zabbix/zabbix_server.log
LogFileSize=128
PidFile=/var/run/zabbix/zabbix_server.pid
SocketDir=/var/run/zabbix
DBHost=$dbhost
DBName=$dbname
DBUser=$dbuser
DBPassword=$dbpass
DBPort=$dbport
SNMPTrapperFile=/var/log/snmptrap/snmptrap.log
Timeout=4
AlertScriptsPath=/usr/lib/zabbix/alertscripts
ExternalScripts=/usr/lib/zabbix/externalscripts
LogSlowQueries=3000
StatsAllowedIP=127.0.0.1
EOF

systemctl enable zabbix-server.service
#systemctl start zabbix-server

