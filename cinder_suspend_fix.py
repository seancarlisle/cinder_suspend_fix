#!/usr/bin/python2.7

###################################################################
# cinder_suspend_fix.py                                           #
#                                                                 #
# Simple script that will scan the environment using dmsetup for  #
# suspended LVM volumes and snapshots. If any are found, the      #
# script will attempt to resume them via lvchange. A list of      #
# impacted volumes is compiled and emailed to targeted recipients #
#                                                                 #
###################################################################

import os
import subprocess
import re
import argparse
import time
import smtplib
from email.mime.text import MIMEText
import sys

class cinderSuspendFix:
   def __init__(self,checkInterval=None,debug=None,logDestination=None):
      self.suspendedVolumeList = list()
      if checkInterval is None:
         self.checkInterval = 10.0
      else:
         self.checkInterval = float(checkInterval)
      if debug is None:
         self.debug = False
      else:
         self.debug = debug
      if logDestination is None:
         self.logHandle = sys.stdout
      else:
         self.logHandle = open(logDestination, 'a')

   # Uses dmsetup to find volumes in a suspended state
   def _getSuspendedVols(self):
      try:
         myoutput = subprocess.check_output(['dmsetup','info'])
         if self.debug:
            self._logging("Checking output:\n %s" % myoutput)
         
         mysearch = re.compile('^Name: *cinder--volumes-volume--[0-9a-z]{8}--[0-9a-z-]{18}[0-9a-z]{12}[0-9a-z-]{0,5}\n^State: *SUSPENDED$', re.MULTILINE)
 
         mymatch = re.findall(mysearch,myoutput)

         volumeList=list()
         for i in mymatch:
            newLinePos = i.index('\n')
            volumeList.append(i[19:newLinePos])
         return volumeList

      except subprocess.CalledProcessError as procError:
         self._logging(procError.output)
      except Exception as exception:
         self._logging(exception)

   # Uses dmsetup to resume a suspended volume.
   # seancarlisle: This method originally used lvchange, but I somehow managed to suspend a *-real device
   # and lvchange doesn't know about those, so I opted for dmsetup resume instead.
   def _setAvailable(self,volume):
      try:
         self._logging("Attempting to resume %s ..." % volume)
         subprocess.call(['dmsetup', 'resume', volume])
         self._logging("%s resumed successfully" % volume)
      except subprocess.CalledProcessError as procError:
         self._logging(procError.output)
      except Exception as exception:
         self._logging(exception)
   # Check if we already know about the suspended volume from the previous run
   def _checkForExisting(self, volume):
      return self.suspendedVolumeList.count(volume) 

   # Adds the specific volume to the list to resume on the next loop
   def _addVolumeToGlobalList(self, volume):
      self.suspendedVolumeList.append(volume)

   # Remove the specific volume from the list after doing things to it
   def _removeVolumeFromGlobalList(self, volume):
      self.suspendedVolumeList.remove(volume)    

   # Emails the list of fixed volumes
   def _sendEmail(self, fixedVolumes):
      message = self._buildMessage(fixedVolumes)
      try:      
         self._logging("Attempting to send email...")
         msg = MIMEText(message)
         msg['Subject'] = 'Suspended Cinder Volumes on %s' % subprocess.check_output(['hostname'])
         msg['From'] = 'mail@%s' % subprocess.check_output(['hostname'])
         msg['To'] = 'root@localhost'

         s = smtplib.SMTP('localhost')
         s.sendmail(msg['From'], msg['To'], msg.as_string())
         s.quit()
         self._logging("Email sent to the following recipients: " + msg['To'])
      except Exception as exception:
         self._logging(exception)

   # Creates the message for emailing the peoples
   def _buildMessage(self, fixedVolumes):
      message = "The following volumes were found to have been suspended and have been re-enabled:\n\n"
      for volume in fixedVolumes:
         message += volume + "\n"

      return message

   # Debug logging 
   def _logging(self, message):
      formattedMessage = time.strftime("%Y-%m-%d %H:%M:%S",time.localtime()) + " " + message + "\n"
      #if isinstance(self.logHandle, file): 
      #   print "hello inside isinstance"
      self.logHandle.write(formattedMessage)
      self.logHandle.flush()
      #else:
      #   print formattedMessage
      
   # Main program loop
   def do_run(self):
      while True:
         currentSuspended = self._getSuspendedVols()
         if currentSuspended is None:
            self._logging("Unable to retreive volume list...")
         else:
            if self.debug:
               self._logging("got the following suspended volumes: %s" % currentSuspended)
            elif len(currentSuspended) > 0:
               self._logging("Found the following suspended volumes: \n %s" % currentSuspended)
            fixedVolumeList = list()
            failedVolumeList = list()

            for volume in currentSuspended:
               # If the volume is in our list already, attempt to resume it
               if self._checkForExisting(volume) > 0:
                  self._setAvailable(volume)
                  self._removeVolumeFromGlobalList(volume)
                  fixedVolumeList.append(volume[16:].replace('--','-'))
               # Else add it to the list for the next go-around
               else:
                  self._logging("Adding %s to the list for the next run" % volume)
                  self._addVolumeToGlobalList(volume)
            if len(fixedVolumeList) > 0:
               self._logging("Sending email")
               self._sendEmail(fixedVolumeList)
         self._logging("sleeping for %s seconds..." % self.checkInterval)
         time.sleep(self.checkInterval)
  
 

#parser = argparse.ArgumentParser()
#parser.add_argument('--interval', help='Interval to check for suspended volumes')
#parser.add_argument('--debug', help='Provide debug logging')
#parser.add_argument('--log', help='Logging destination (leave blank for stdout)')
#args = parser.parse_args()
#
#suspendFixer = cinderSuspendFix(args.interval, args.debug, args.log)
#
#suspendFixer.do_run()

if __name__ == '__main__':
   parser = argparse.ArgumentParser()
   parser.add_argument('--interval', help='Interval to check for suspended volumes')
   parser.add_argument('--debug', help='Provide debug logging')
   parser.add_argument('--log', help='Logging destination (leave blank for stdout)')
   args = parser.parse_args()

   suspendFixer = cinderSuspendFix(args.interval, args.debug, args.log)

   suspendFixer.do_run()


