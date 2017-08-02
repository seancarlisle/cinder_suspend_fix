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

# Generate the list of suspended volumes and store 
for i in $(/sbin/dmsetup info "$(echo $volume_dir)"* | egrep -B1 'SUSPEND' | awk '/Name/ {print substr($2,17)}' | tr -s -);do
   
   # Check if the volume is already in the file. If it is, attempt to resume it, else add it to the file
   if [ $(grep $i /tmp/suspendedvols) -eq 0 ]; then         
#     /sbin/lvchange -ay $(echo $volume_dir)$i
      sed -i "/$i/ d" /tmp/suspendedvols
      mylist="$mylist $i"
   else
      echo "$i" >> /tmp/suspendedvols
   fi
done

if [ "$mylist" != "" ];then
    output="The following volumes have been re-activated on host $(hostname):\n$mylist" | mail -s "Suspended Volumes Resumed"
    echo -e $output | sed 's/ volume/\nvolume/g'
fi

exit 0
