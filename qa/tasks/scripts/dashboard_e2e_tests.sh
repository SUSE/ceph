# dashboard_e2e_tests.sh
#
# Assumes that "ceph-dashboard-e2e" RPM has already been installed

set -ex

useradd -m farm
echo "farm ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers
su - farm -c '/usr/lib/ceph/dashboard-e2e/dashboard_e2e_tests.sh'
