#!/bin/bash
#-S switch 与case不同列,case缩进
#-K 缩进case下面的语句
#-p 只在操作符两边加空格
#-n 不备份格式化之前的文件
#-k1 指针或引用运算符*/&/^号靠近类型名
#-s4 TAB键替换为4个空格
#-f  空行分隔没有关系的块，类，标签(不包括代码快)
#-U  删除括号内外额外空格
#-H  关键字后插入空格（关键字类似if、for、while等等
#apt-get install astyle
for f in $(find ./ -name '*.cpp' -or -name '*.h' -type f|grep -v thirdparty)
do
    #astyle -pnfUHk1s4 --style=ansi   *.cpp
    astyle -SKpnfUHk1s4 --style=ansi   ${f}
done
