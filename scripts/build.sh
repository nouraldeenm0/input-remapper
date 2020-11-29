#!/usr/bin/env bash

build_deb() {
  # https://github.com/phusion/debian-packaging-for-the-modern-developer/tree/master/tutorial-1
  dist=dist
  name=key-mapper-0.1.0

  python3 setup.py sdist --dist-dir $dist
  tar -C $dist -xzf $dist/$name.tar.gz
  rm $dist/$name.tar.gz
  cp DEBIAN $dist/$name -r
  dpkg-deb -b $dist/$name $dist/$name.deb
  rm $dist/$name -r
  echo "created $dist/$name.deb"
}

build_deb &
# add more build targets here

wait