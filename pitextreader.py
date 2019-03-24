import RPi.GPIO as GPIO
import os, sys
import logging
import subprocess
import threading
import time
import datetime as dt
import shutil

#Ito yung unique number based sa time and
fileNameNya = dt.datetime.now().isoformat()

##### USER VARIABLES
DEBUG   = 0 # Debug 0/1 off/on (writes to debug.log)
SPEED   = 0.8   # Speech speed, 0.5 - 2.0 
VOLUME  = 100    # Audio volume

# GPIO BUTTONS
BTN1    = 24    # The button!
LED     = 18    # The button's LED!

def doesFileExist(filePathAndName):
    return os.path.exists(filePathAndName)

### FUNCTIONS
# Thread controls for background processing
class RaspberryThread(threading.Thread):
    def __init__(self, function):
        self.running = False
        self.function = function
        super(RaspberryThread, self).__init__()

    def start(self):
        self.running = True
        super(RaspberryThread, self).start()

    def run(self):
        while self.running:
            self.function()

    def stop(self):
        self.running = False 

# LED ON/OFF
def led(val):   
    logger.info('led('+str(val)+')') 
    if val:
       GPIO.output(LED,GPIO.HIGH)
    else:
       GPIO.output(LED,GPIO.LOW)
    
# PLAY SOUND
def sound(val): # Play a sound
    logger.info('sound()') 
    time.sleep(0.2)
    cmd = "/usr/bin/aplay -q "+str(val)
    logger.info(cmd) 
    os.system(cmd)
    return
 
# SPEAK STATUS
def speak(val): # TTS Speak
    logger.info('speak()') 
    cmd = "/usr/bin/flite -voice slt --setf duration_stretch="+str(SPEED)+" -t \""+str(val)+"\""
    logger.info(cmd) 
    os.system(cmd)
    return 

# SET VOLUME
def volume(val): # Set Volume for Launch
    logger.info('volume('+str(val)+')') 
    vol = int(val)
    cmd = "sudo amixer -q sset PCM,0 "+str(vol)+"%"
    logger.info(cmd) 
    os.system(cmd)
    return 

# TEXT CLEANUP
def cleanText():
    logger.info('cleanText()')
    #cmd = "sed -e 's/\([0-9]\)/& /g' -e 's/[[:punct:]]/ /g' -e 'G' -i /tmp/text.txt"
    cmd = "sed -e 's/\([0-9]\)/& /g' -e 's/[[:punct:]]/ /g' -e 'G' -i /tmp/" + fileNameNya + ".txt"
    logger.info(cmd) 
    os.system(cmd)
    return
    
# Play TTS (Allow Interrupt)
def playTTS():
    logger.info('playTTS()') 
    global current_tts
    #current_tts=subprocess.Popen(['/usr/bin/flite','-voice','slt','-f', '/tmp/text.txt'],
    current_tts=subprocess.Popen(['/usr/bin/flite','-voice','slt','-f', '/tmp/' + fileNameNya + '.txt'],
        stdin=subprocess.PIPE,stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,close_fds=True)
    # Kick off stop audio thread 
    rt.start()
    # Wait until finished speaking (unless interrupted)
    current_tts.communicate()
    return


# Stop TTS (with Interrupt)
def stopTTS():
    global current_tts
    # If button pressed, then stop audio
    if GPIO.input(BTN1) == GPIO.LOW:
        logger.info('stopTTS()') 
        #current_tts.terminate()
        current_tts.kill()
        time.sleep(0.5)
    return 

# GRAB IMAGE AND CONVERT
def getData():
    logger.info('getData()') 
    #led(1) # Turn off Button LED

    # Take photo
    sound(SOUNDS+"camera-shutter.wav")
    cmd = CAMERA
    logger.info(cmd) 
    os.system(cmd)

    # OCR to text
    speak("Now Reading. Please, be Patient.")
    led(0)
    #cmd = "/usr/bin/tesseract /tmp/image.jpg /tmp/text"
    cmd = "/usr/bin/tesseract /tmp/" + fileNameNya + ".jpg /tmp/" + fileNameNya
    logger.info(cmd) 
    os.system(cmd)
    
    # Cleanup text
    cleanText()
    led(0)
    # Start reading text
    playTTS()
    return


######
# MAIN
######
try:
    global rt
    # Setup Logging
    logger = logging.getLogger()
    handler = logging.FileHandler('debug.log')
    if DEBUG:
        logger.setLevel(logging.INFO)
        handler.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.ERROR)
        handler.setLevel(logging.ERROR)
    log_format = '%(asctime)-6s: %(name)s - %(levelname)s - %(message)s'
    handler.setFormatter(logging.Formatter(log_format))
    logger.addHandler(handler)
    logger.info('Starting') 
    
    # Setup GPIO buttons
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings (False)
     
    GPIO.setup(BTN1, GPIO.IN, pull_up_down=GPIO.PUD_UP) 
    GPIO.setup(LED, GPIO.OUT) 
    
    # Threaded audio player
    #rt = RaspberryThread( function = repeatTTS ) # Repeat Speak text
    rt = RaspberryThread( function = stopTTS ) # Stop Speaking text
    
    volume(VOLUME)
    speak("The Device is Ready to use")
    
    
    while True:
        if GPIO.input(BTN1) == GPIO.LOW:
            led(1)
            # OTHER SETTINGS
            SOUNDS  = "/home/pi/PiTextReader/sounds/" # Directory for sound effect(s)
            #CAMERA  = "raspistill -cfx 128:128 --awb auto -rot 180 -t 500 -o /tmp/image.jpg"
            CAMERA  = "raspistill -cfx 128:128 --awb auto -rot 180 -t 500 -o /tmp/" + fileNameNya + ".jpg"
            flashDrive = "/media/usb/PiTextReader/"
            
            # Btn 1
            getData()
            rt.stop()
            rt = RaspberryThread( function = stopTTS ) # Stop Speaking text
            #led(0)
            
            time.sleep(1.0)
                
            if doesFileExist(flashDrive):
                picSource = "/tmp/%s.jpg" % fileNameNya
                textSource = "/tmp/%s.txt" % fileNameNya
                
                
                #picDestination = "/media/pi/TOPIX/%s.jpg" % fileNameNya
                #textDestination = "/media/pi/TOPIX/%s.txt" % fileNameNya
                a1 = "/media/usb/PiTextReader/%s.jpg" % fileNameNya
                a2 = "/media/usb/PiTextReader/%s.txt" % fileNameNya
                
                b1 = a1.replace(':','')
                c1 = b1.replace('-','')
                
                b2 = a2.replace(':','')
                c2 = b2.replace('-','')
                
                try:
                    # Copy file to destination
                    shutil.copy2(picSource, c1)
                    shutil.copy2(textSource, c2)
                    # E.g. source and destination is the same location
                except shutil.Error as e:
                    print("Error: %s" % e)
                    # E.g. source or destination does not exist
                except IOError as e:
                    print("Error: %s" % e.strerror)
                    
                fileNameNya = dt.datetime.now().isoformat()
                speak("Finish Reading, and Finish Saving to USB. The Device is Ready to use again")
                time.sleep(0.2)
            else:
                fileNameNya = dt.datetime.now().isoformat()
                speak("Finish Reading. The Device is Ready to use again")
                time.sleep(0.2)
    
except KeyboardInterrupt:
    logger.info("exiting")

GPIO.cleanup() #Reset GPIOs
sys.exit(0)
