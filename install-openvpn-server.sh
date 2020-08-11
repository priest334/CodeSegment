#!/bin/bash

version=2.4.9
easyrsa_version=3.0.7
cwd=$(pwd)
yum install -y automake libtool openssl-devel lz4-devel lzo-devel pam-devel
wget https://github.com/OpenVPN/openvpn/archive/v$version.tar.gz -O -|tar -xzf -
wget https://github.com/OpenVPN/easy-rsa/archive/v$easyrsa_version.tar.gz -O -|tar -xzf -

cd $cwd/openvpn-$version
autoreconf -i -v -f
./configure
make && make install

varsfile=vars
confdir=/etc/openvpn
mkdir -p $confdir/keys
mkdir -p $confdir/clients
mkdir -p $confdir/ccd
cd $cwd/easy-rsa-$easyrsa_version/easyrsa3
cp vars.example $varsfile
sed -i -r '/EASYRSA_REQ_COUNTRY/cset_var EASYRSA_REQ_COUNTRY "CN"' $varsfile
sed -i -r '/EASYRSA_REQ_PROVINCE/cset_var EASYRSA_REQ_PROVINCE "BJ"/' $varsfile
sed -i -r '/EASYRSA_REQ_CITY/cset_var EASYRSA_REQ_CITY "BJ"/' $varsfile
sed -i -r '/EASYRSA_REQ_ORG/cset_var EASYRSA_REQ_ORG "wthmox"/' $varsfile
sed -i -r '/EASYRSA_REQ_EMAIL/cset_var EASYRSA_REQ_EMAIL "admin@wthmox.cn"/' $varsfile
sed -i -r '/EASYRSA_REQ_OU/cset_var EASYRSA_REQ_OU "DEV"/' $varsfile

rm -rf ./pki
./easyrsa init-pki
./easyrsa gen-dh
./easyrsa build-ca nopass <<EOF

EOF
./easyrsa build-server-full server nopass
openvpn --genkey --secret pki/ta.key

find ./pki -regextype posix-extended -regex ".*\.(key|crt)|.*dh\.pem" -type f -exec cp {} $confdir/keys \;

ip_forward_enabled=$(sysctl -n net.ipv4.ip_forward)
if [ "x$ip_forward_enabled" == "x0" ]; then
	ip_forward_exist=$(grep "net.ipv4.ip_forward" /etc/sysctl.conf)
	if [ "x$ip_forward_exist" == "x" ]; then
		echo "net.ipv4.ip_forward = 1" >> /etc/sysctl.conf
	else	
		sed -ir "/net.ipv4.ip_forward/cnet.ipv4.ip_forward = 1" /etc/sysctl.conf 
	fi
	sysctl -p
fi

cat > $confdir/server.conf << EOF
port 334
proto tcp
dev tun
ca $confdir/keys/ca.crt
cert $confdir/keys/server.crt
key $confdir/keys/server.key
dh $confdir/keys/dh.pem
server 10.7.14.0 255.255.255.0
ifconfig-pool-persist $confdir/ipp.txt
;client-config-dir $confdir/ccd
client-to-client
ccd-exclusive
keepalive 10 120
;tls-auth $confdir/keys/ta.key 0
cipher AES-256-CBC
persist-key
persist-tun
status status.log
log-append openvpn.log
verb 3
;explicit-exit-notify 1
EOF




