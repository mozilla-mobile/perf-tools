import sys, getopt
import subprocess
import time
import os
import signal

def main(argv):
    recording_name = ''
    try:
      opts, args = getopt.getopt(argv,"hi:n:",["n="])
    except getopt.GetoptError:
      print('record_adb.py -n <recording_name>')
      sys.exit(2)
    for opt, arg in opts:
      if opt == '-h':
         print('record_adb.py -n <recording_name>')
         sys.exit()
      elif opt in ("-n", "--name"):
          print(arg)
          recording_name = './sdcard/' + arg
    record_process = subprocess.Popen(['adb', 'shell','screenrecord'] + [recording_name])
    time.sleep(3)
    activity_start = subprocess.Popen(['adb', 'shell', 'am', 'start-activity', 'org.mozilla.fenix.nightly/org.mozilla.fenix.HomeActivity', '--ez finishonboarding true'])
    time.sleep(3)
    proc = subprocess.Popen(['adb', 'pull'] + [recording_name])
    proc.wait()

    

    

if __name__ == "__main__":
    main(sys.argv[1:])