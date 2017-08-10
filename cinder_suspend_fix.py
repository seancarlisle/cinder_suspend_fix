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
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
import sys
from threading import Timer
import json
import requests

class cinderSuspendFix:
   def __init__(self, checkInterval=None, debug=None, logDestination=None, email=None):
      self.suspendedVolumeList = list()

      try:
         if logDestination is None:
            self.logHandle = sys.stdout
         else:
            self.logHandle = open(logDestination, 'a')
      except Exception as exception:
         self.logHandle = sys.stdout
         self._logging(exception.message)
         self._logging("Unable to open %s for logging, reverting to stdout" % logDestination)

      try:
         if checkInterval is None:
            self.checkInterval = 10.0
         else:
            self.checkInterval = float(checkInterval)
      except Exception as exception:
         self._logging(exception.message)
         self._logging("Invalid check interval, defaulting to 10 seconds")
         self.checkInterval = 10.0

      self.debug = debug

      try:
         if email is None:
            self.email = "root@localhost"
         else:
            print "item: %s self.email: %s" % (item,self.email)
            self.email = email
      except Exception as exception:
         self._logging(exception.message)
         self._logging("Invalid email, reverting to root@localhost")
         self.email = "root@localhost"

      if self.debug:
         self._logging("check Interval %s, logDestination: %s, email: %s" % (self.checkInterval,self.logHandle.name, self.email))

  # Uses dmsetup to find volumes in a suspended state
   def _getSuspendedVols(self):
      try:
         myoutput = subprocess.check_output(['dmsetup','info','-c','--noheadings','-o','name,suspended'])
         if self.debug:
            self._logging("Checking output:\n %s" % myoutput)

         mysearch = re.compile('^cinder--volumes-[a-z0-9-_]*:Suspended', re.MULTILINE)
         mymatch = re.findall(mysearch,myoutput)

         volumeList=list()
         for i in mymatch:
            delim = i.index(':')
            volumeList.append(i[0:delim])
         return volumeList

      except subprocess.CalledProcessError as procError:
         self._logging(procError.output)
      except Exception as exception:
         self._logging(exception.message)

   # Uses dmsetup to resume a suspended volume.
   # seancarlisle: This method originally used lvchange, but I somehow managed to suspend a *-real device
   # and lvchange doesn't know about those, so I opted for dmsetup resume instead.
   def _setAvailable(self,volume):
      try:
         self._logging("Attempting to resume %s ..." % volume)
         returnCode = subprocess.call(['dmsetup', 'resume', '-y', volume])
         self._logging("%s resumed successfully" % volume)
         return returnCode
      except subprocess.CalledProcessError as procError:
         self._logging(procError.output)
         return 1
      except Exception as exception:
         self._logging(exception.message)
         return 1

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
   #def _sendEmail(self, fixedVolumes, failedVolumes):
   #   message = self._buildMessage(fixedVolumes, failedVolumes)
   #   try:
   #      self._logging("Attempting to send email...")
   #      msg = MIMEText(message)
   #      hostname = subprocess.check_output(['hostname'])
   #      msg['Subject'] = 'Suspended Cinder Volumes on %s' % hostname
   #      msg['From'] = 'mail@%s' % hostname
   #      self.email
   #
   #      s = smtplib.SMTP('localhost')
   #      s.sendmail(msg['From'], self.email, msg.as_string())
   #      s.quit()
   #      self._logging("Email sent to the following recipients: " + msg['To'])
   #   except Exception as exception:
   #      self._logging(exception.message)

   # Sends slack message to slack channel
   def _slackNotify(self, fixedVolumes, failedVolumes):
      message = self._buildMessage(fixedVolumes, failedVolumes)
      try:
         self._logging("Sending message to slack")
         url = 'localhost'
         payload = {'channel':'#channel','username':'user','text':message}
         r = requests.post(url,data=json.dumps(payload))
         if self.debug:
            self._logging("sent the following payload: %s and got the following response: %s:%s" % (json.dumps(payload),r,r.text))
         if r > 300:
            self._logging("Failed to post to Slack. Reason: %s" % r.text)
      except Exception as exception:
         self._logging(exception.message)
 
   # Creates the message for emailing the peoples
   def _buildMessage(self, fixedVolumes, failedVolumes):
      message = ''
      if len(fixedVolumes) > 0:
         message += "The following volumes were found to have been suspended and have been resumed:\n\n"
         for volume in fixedVolumes:
            message += volume + "\n"
         message += "\n"
      if len(failedVolumes) > 0:
         message += "The following volumes failed to resume and require investigation:\n\n"
         for volume in failedVolumes:
            message += volume + "\n"

      return message

   # Sends email about tgtd issue
   def _tgtdEmail(self, tgtdError):
      try:
         ###### seancarlisle: Converted to use slack notification ############
         #self._logging("Attempting to send email...")
         #msg = MIMEText(tgtdError)
         #hostname = subprocess.check_output(['hostname'])
         #msg['Subject'] = 'Daemon tgtd unresponsive on host %s' % hostname
         #msg['From'] = 'mail@%s' % hostname
         #msg['To'] = self.email
         #
         #s = smtplib.SMTP('localhost')
         #s.sendmail(msg['From'], msg['To'], msg.as_string())
         #s.quit()
         #self._logging("Email sent to the following recipients: " + msg['To'])
         
         hostname = subprocess.check_output(['hostname'])
         self._logging("Sending message to slack")
         url = 'localhost'
         payload = {'channel':'#channel','username':'user','text':tgtdError}
         r = requests.post(url,data=json.dumps(payload))
         if self.debug:
            self._logging("sent the following payload: %s and got the following response: %s:%s" % (json.dumps(payload),r,r.text))
         if r > 300:
            self._logging("Failed to post to Slack. Reason: %s" % r.text)
         ###### seancarlisle: Converted to use slack notification ############
      except Exception as exception:
         self._logging(str(exception))

   def _tgtdTest(self, timeout_sec):
      FNULL = open(os.devnull, 'w')
      cmd = ['tgtadm', '-C', '0', '--op', 'show', '--mode', 'target']
      proc = subprocess.Popen(cmd, stdout=FNULL, stderr=FNULL)
      timer = Timer(timeout_sec, proc.kill)
      timer.start()
      output, err = proc.communicate()
      if timer.is_alive():
          # Process completed naturally - cancel timer and return exit code
          timer.cancel()
          return proc.returncode, output
      # Process killed by timer - raise exception
      raise SubprocessTimeoutError('Command `tgt-admin` (pid #%d) killed after %i seconds. Daemon `tgtd` may be dead.' % (proc.pid, timeout_sec))

   # Basic logging method
   def _logging(self, message):
      messageLines = message.split('\n')
      formattedMessage = ''
      # Append the timestamp to each line to make the logging more "official"
      for line in messageLines:
         formattedMessage += str(datetime.utcnow().isoformat(' '))[:-3] + " " + line + "\n"

      self.logHandle.write(formattedMessage)
      self.logHandle.flush()

   # Main program loop
   def do_run(self):
      fixedVolumeList = list()
      failedVolumeList = list()

      while True:
         ########## BEGIN CAMP4034 ##########
         # Test tgtd
         tgtd_timeout = 5
         try:
            tgtadm_status, tgtadm_output = self._tgtdTest(tgtd_timeout)
            if tgtadm_status != 0:
               raise SubprocessError("Command `tgt-admin -s` returned non-zero exit status.  Is tgtd running?")
            else:
               self._logging("Command `tgt-admin -s` executed successfully, tgtd assumed responsive.")
         except (SubprocessError, SubprocessTimeoutError) as error:
            self._logging(str(error))
            self._tgtdEmail(str(error))
         ########## END CAMP4034 ##########

         currentSuspended = self._getSuspendedVols()
         if currentSuspended is None:
            self._logging("Unable to retreive volume list...")
         elif len(currentSuspended) > 0:
            self._logging("Found the following suspended volumes: \n %s" % currentSuspended)

            # scarlisle: Sort the list prior to attempting resume. This will put *-real and *-cow first
            # which is what we want, otherwise dmsetup will hang indefinitely.
            currentSuspended.sort(key=len, reverse=True)
            for volume in currentSuspended:
               # If the volume is in our list already, attempt to resume it
               if self._checkForExisting(volume) > 0:
                  if self._setAvailable(volume) == 0:
                     self._removeVolumeFromGlobalList(volume)
                     fixedVolumeList.append(volume[16:].replace('--','-'))
                  else:
                     failedVolumeList.append(volume[16:].replace('--','-'))

               # Else add it to the list for the next go-around
               else:
                  self._logging("Adding %s to the list for the next run" % volume)
                  self._addVolumeToGlobalList(volume)
            if len(fixedVolumeList) > 0 or len(failedVolumeList) > 0:
               self._logging("Sending email")
               #self._sendEmail(fixedVolumeList, failedVolumeList)
               self._slackNotify(fixedVolumeList, failedVolumeList)
               # Clear the lists for the next round
               for i in range(1, len(fixedVolumeList)):
                  fixedVolumeList.pop()

               for i in range(1, len(failedVolumeList)):
                  failedVolumeList.pop()

         self._logging("sleeping for %s seconds..." % self.checkInterval)
         time.sleep(self.checkInterval)

class SubprocessTimeoutError(Exception):
   pass

class SubprocessError(Exception):
   pass

if __name__ == '__main__':
   parser = argparse.ArgumentParser()
   parser.add_argument('--interval', help='Interval to check for suspended volumes. Defaults to 10 seconds.')
   parser.add_argument('--debug', default=False, action='store_true', help='Provide debug logging')
   parser.add_argument('--log', help='Logging destination. Defaults to stdout')
   #parser.add_argument('--email', help='List of recipients to send email alerts to. Defaults to root@localhost', nargs=argparse.REMAINDER)
   args = parser.parse_args()

   #suspendFixer = cinderSuspendFix(args.interval, args.debug, args.log, args.email)
   suspendFixer = cinderSuspendFix(args.interval, args.debug, args.log)

   suspendFixer.do_run()
