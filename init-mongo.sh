#!/bin/bash

mongo_bin_dir=$(dirname $(which mongo))
service_name=mongo-logs
root_dir=$(pwd)
ip=`ip addr show eth0|grep inet|sed -nr 's/.*inet ([0-9\.]+)\/.*/\1/p'`
first_shard=shard1

mongo_shard1_dir="$root_dir"/shards/"$first_shard"
mongo_config_dir="$root_dir"/config
mongo_mongos_dir="$root_dir"/mongos

mkdir -p "$mongo_shard1_dir"/data
mkdir -p "$mongo_config_dir"/data
mkdir -p "$mongo_mongos_dir"

cat > "$mongo_shard1_dir"/mongod.conf <<EOF
systemLog:
  destination: file
  path: "$mongo_shard1_dir/mongod.log"
processManagement:
  fork: true
  pidFilePath: "$mongo_shard1_dir/mongod.pid"
net:
  port: 27017
  bindIp: $ip
storage:
  dbPath: "$mongo_shard1_dir/data"
replication:
  replSetName: $first_shard
sharding:
  clusterRole: shardsvr
EOF

cat > "$mongo_config_dir"/mongod.conf <<EOF
systemLog:
  destination: file
  path: "$mongo_config_dir/mongod.log"
processManagement:
  fork: true
  pidFilePath: "$mongo_config_dir/mongod.pid"
net:
  port: 27018
  bindIp: $ip
storage:
  dbPath: "$mongo_config_dir/data"
replication:
  replSetName: configs
sharding:
  clusterRole: configsvr
EOF

cat > "$mongo_mongos_dir"/mongos.conf <<EOF
systemLog:
  destination: file
  path: "$mongo_mongos_dir/mongos.log"
processManagement:
  fork: true
  pidFilePath: "$mongo_mongos_dir/mongos.pid"
net:
  port: 27019
  bindIp: $ip
sharding:
  configDB: configs/$ip:27018
EOF

cat > /tmp/init-$first_shard-replica.js <<EOF
rs.initiate( {
   _id: "$first_shard",
   members: [
      { _id: 0, host: "$ip:27017" }
   ]
} )
EOF

cat > /tmp/init-config-replica.js <<EOF
rs.initiate( {
   _id: "configs",
   members: [
      { _id: 0, host: "$ip:27018" }
   ]
} )
EOF

cat > /tmp/init-shards.js <<EOF
sh.addShard("$first_shard/$ip:27017")
sh.addShardToZone("$first_shard", "Zone.$first_shard")
EOF

cat > "$root_dir"/setup.sh <<EOF
#!/bin/bash
$mongo_bin_dir/mongod -f $mongo_shard1_dir/mongod.conf
wait
$mongo_bin_dir/mongo $ip:27017 /tmp/init-shard1-replica.js
wait
$mongo_bin_dir/mongod -f $mongo_config_dir/mongod.conf
wait
$mongo_bin_dir/mongo $ip:27018 /tmp/init-config-replica.js
wait
$mongo_bin_dir/mongos -f $mongo_mongos_dir/mongos.conf
wait
$mongo_bin_dir/mongo $ip:27019 /tmp/init-shards.js
echo "$service_name init finished."
EOF


cat > "$root_dir"/start.sh <<EOF
#!/bin/bash
$mongo_bin_dir/mongod -f $mongo_config_dir/mongod.conf
wait
$mongo_bin_dir/mongod -f $mongo_shard1_dir/mongod.conf
wait
$mongo_bin_dir/mongos -f $mongo_mongos_dir/mongos.conf
wait
echo "$service_name start finished."
EOF

cat > "$root_dir"/stop.sh <<EOF
#!/bin/bash
kill -TERM \$(cat $mongo_shard1_dir/mongod.pid)
wait
kill -TERM \$(cat $mongo_config_dir/mongod.pid)
wait
kill -TERM \$(cat $mongo_mongos_dir/mongos.pid)
wait
echo "$service_name stop finished."
EOF

cat > /usr/lib/systemd/system/"$service_name".service <<EOF
[Unit]
Description=$service_name.service

[Service]
ExecStart=/bin/sh $root_dir/start.sh
ExecStop=/bin/sh $root_dir/stop.sh

[Install]
WantedBy=multi-user.target
EOF

/bin/sh "$root_dir/setup.sh"

systemctl enable "$service_name".service
#systemctl start "$service_name".service
