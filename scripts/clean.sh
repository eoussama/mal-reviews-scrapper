#! /bin/sh
set -eu

find out -mindepth 1 ! -name .gitkeep -exec rm -rf {} +
