set -ex

REPO=$1
BRANCH=$2
if [ -n "$REPO" ]
then
	if [ ! -n "$BRANCH" ]
	then
		BRANCH="master"
	fi
	cd /root
	git clone $REPO
	cd ceph-salt
	zypper -n install autoconf gcc python3-devel python3-pip python3-curses
	git checkout $BRANCH
	pip install .
	cp -r ceph-salt-formula/salt/* /srv/salt/
	chown -R salt:salt /srv
else
	zypper -n install ceph-salt
fi
