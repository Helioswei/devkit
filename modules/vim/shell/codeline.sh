#!/bin/bash
find . -name "*.h" -or -name "*.cpp" |grep -v thirdparty|grep -v build |grep -v cmdline.h|xargs  wc -l
