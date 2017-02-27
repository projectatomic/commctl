FROM fedora:25
MAINTAINER Red Hat, Inc. <container-tools@redhat.com>

# Install required dependencies and commissaire
RUN dnf -y update && \
dnf -y install --setopt=tsflags=nodocs redhat-rpm-config openssh-clients python3-pip python3-virtualenv git gcc libffi-devel; dnf clean all && \
git clone https://github.com/projectatomic/commctl.git && \
virtualenv-3 /environment && \
. /environment/bin/activate && \
cd commctl && \
pip install -U pip && \
pip install -r requirements.txt && \
pip install . && \
pip freeze > /installed-python-deps.txt && \
dnf remove -y gcc git redhat-rpm-config libffi-devel && \
dnf clean all && \
mkdir -p /etc/commissaire /data/{redis,etcd}

# Configuration directory. Use --volume=/pathtoyour/.commissaire.json:/root/.commissaire.json
VOLUME /root/.commissaire.json

# Run everything from /commissaire
WORKDIR /commissaire
# Execute the all-in-one-script
ENTRYPOINT /commctl/tools/run.sh
