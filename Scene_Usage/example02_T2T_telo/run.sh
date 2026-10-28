#!/bin/sh
#$ -S /bin/sh
#Version1.0	hewm@genomics.org.cn	2020-11-09
echo Start Time : 
date
##  track_shift_y=-20                   #上移 和  track 1 叠在一起 ##
perl ../../bin/RectChr	-InConf	in1.conf	-OutPut	OUT1

perl ../../bin/RectChr	-InConf	in2.conf	-OutPut	OUT2


echo End Time : 
date
