#!/bin/bash

###################################################################
# cinder_suspend_fix.sh                                           #
#                                                                 #
# Simple script that will scan the environment using dmsetup for  #
# suspended LVM volumes and snapshots. If any are found, the      #
# script will attempt to resume them via lvchange. A list of      #
# impacted volumes is compiled and emailed to targeted recipients #
#                                                                 #
###################################################################

volume_list=''
volume_dir="/dev/cinder-volumes/"
for i in $(dmsetup info "$(echo $volume_dir)"* | egrep -B1 'SUSPEND' | awk '/Name/ {print substr($2,17)}' | tr -s -);do
   lvchange -ay $(echo $volume_dir)$i
   mylist="$mylist $i"
done

if [ "$mylist" != "" ];then
    output="The following volumes have been re-activated on host $(hostname):\n$mylist"
    echo -e $output | sed 's/ volume/\nvolume/g'
fi

echo "did we execute?" >> /tmp/myfile

exit 0
