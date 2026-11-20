# PostgreSQL 18.6 built on a given Ubuntu release, with that release's glibc and locale data.
# Round 5 real-upgrade experiment (dbms/r5_real_upgrade.py). Build context: dbms/.
ARG BASE=ubuntu:20.04
FROM ${BASE}
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update -q && apt-get install -y -q --no-install-recommends build-essential perl bison flex locales bzip2 ca-certificates \
    && localedef -i en_US -f UTF-8 en_US.UTF-8 && rm -rf /var/lib/apt/lists/*
COPY src/postgresql-18.6.tar.bz2 /tmp/
# the tarball checksum is verified on the host against src/postgresql-18.6.tar.bz2.sha256 before the build
RUN cd /tmp && tar -xjf postgresql-18.6.tar.bz2 && cd postgresql-18.6 \
    && ./configure -q --prefix=/opt/pg --without-icu --without-readline --without-zlib \
    && make -s -j32 && make -s install && make -s -C contrib/amcheck install \
    && cd / && rm -rf /tmp/postgresql-18.6*
RUN useradd -u 4242 -m pg
USER pg
