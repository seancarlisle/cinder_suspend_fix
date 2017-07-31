#!/bin/bash

###################################################################
# cinder_suspend_fix.sh                                           #
#                                                                 #
# Simple script that will scan the environment using dmsetup for  #
# suspended LVM volumes and snapshots. If any are found, the      #
# script will attempt to resume them via lvchange. A list of      #
# impacted volumes is compiled and emailed to targeted recipients #
#                                                                 #
#                                                                 #
###################################################################
