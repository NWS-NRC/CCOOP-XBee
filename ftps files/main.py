import micropython
import xbee
import uio
import os
import uos
from umqtt.simple import MQTTClient
from uftp.uftp import FTP
from sys import stdin, stdout
import network
import machine
import json
import time
import utime
import sys
import gc
from sites.siteFile import pubTopic



SERVER = pubTopic.server_Address
msg_Topic = pubTopic.MESSAGE_TOPIC  
temp_Topic = pubTopic.TEMP_PUB_TOPIC
precip_Topic = pubTopic.PRECIP_PUB_TOPIC
daily_Topic = pubTopic.DAILY_PUB_TOPIC
update_Topic = pubTopic.UPDATE_TOPIC
command_Topic = pubTopic.COMMAND_TOPIC
msg_payload = ""
payload_Topic = ""
publish_Success = False

topic_ToSend = [] 
msg_ToSend = [] 
obs_publishReady = 0
topic_File = "topic.log"
msg_File = "msg.log"
transfer_File = "software.bin"
tF_size = 0
file_lineRef = 0
tfile_readComplete = False
mfile_readComplete = False
files_Exist = False

CLIENT_ID = pubTopic.clientID  # Should be unique for each device connected.
client = MQTTClient(CLIENT_ID, SERVER, keepalive=200)
minute = 0
year = 0
TZ = pubTopic.clientTZ
atOb_T = pubTopic.atOb_T
rssiUpdated = False
timeUpdated = False

# FTPS Variables
version_File = "xbee_versionInfo.txt"
current_FS_Version = ""
site_infoFile = "siteFile_" + CLIENT_ID + ".py"
temp_File = "temp.txt"
quit_Command = "QUIT"
retrieve_Command = "RETR "
temp_Path = "/flash/temp"
root_Path = "/flash"
empty_Text = ""
file_szRcvd = 0
file_Required = []
file_Path = []
file_Action = []
files_toProcess = 0
files_Processed = 0
read_updateFile = False
updating_Logger = False
ftps_Checked = False
site_Checked = False
logger_Update = False
reboot = False

wdt = machine.WDT(timeout=60000, response=machine.HARD_RESET)

def ftps_Conn(check = True, site = False):
  global version_File
  global site_infoFile
  global transfer_File
  global temp_File
  global temp_Path
  global file_Required
  global file_Path
  global file_Action
  global reboot
  global files_toProcess
  global files_Processed
  global wdt
  global logger_Update
  global empty_Text
  global quit_Command
  global retrieve_Command
  global file_szRcvd
  global read_updateFile
  global ftps_Checked
  global site_Checked
  
  file_Size = 0
  file_szRcvd = 0
  uos.chdir(temp_Path)
  filename = empty_Text
  try:
    ftp_conn = FTP(port=990, timeout=20)
  except Exception as ex:
    eMsg = str(ex)
    return eMsg
  else:
    stat = ftp_conn.sendcmd("PASV")
    if not stat.startswith('227'):
      return
    try:
      left = stat.find('(')
      if left < 0:
        pass
      right = stat.find(')', left + 1)
      if right < 0:
        pass
      numbers = tuple(int(i) for i in stat[left+1:right].split(',', 6))
      h_port = int(numbers[4] << 8)
      l_port = int(numbers[5] & 255)
      f_port2 = int(h_port | l_port)
        
    except Exception as exc:
      eMsg =("Error parsing response '%s': %s" % (stat, exc))
      return eMsg

    else:
      if check == True:
        try:
          log = uio.open(temp_File)
          log.close()
        except OSError:
          pass
        else:
          try:
            uos.remove(temp_File)
          except OSError:
            pass
          else:
            pass
        if site == False:
          filename = version_File
        else:
          filename = site_infoFile
        file_Size = int(ftp_conn.size(filename))
        file_cmd = retrieve_Command + filename
        time.sleep(1.0)
        ftp_conn.sendcmd(file_cmd, re=False)
        wdt.feed()
        ftps_downloadFile(fileport = f_port2,sz = file_Size)
        ftp_conn.sendcmd(quit_Command, re=False)
      else:
        uos.chdir(temp_Path)
        try:
          log = uio.open(temp_File)
          log.close()
        except OSError:
          pass
        else:
          try:
            uos.remove(temp_File)
          except OSError:
            pass
          else:
            pass
        filename = file_Required[files_Processed]
        file_Size = int(ftp_conn.size(filename))
        file_cmd = retrieve_Command + filename
        ftp_conn.sendcmd(file_cmd, re=False)
        wdt.feed()
        if file_Required[files_Processed] == transfer_File:
          ftps_downloadFile(fileport = f_port2,sz = file_Size,df_chunk=2048)
        else:
          ftps_downloadFile(fileport = f_port2,sz = file_Size)
        ftp_conn.sendcmd(cmd=quit_Command, re=False)
    uos.chdir(temp_Path)
    if file_Size == file_szRcvd:
      if check == True and site == False:
        ftps_Checked = True
        read_updateFile = True
      elif check == True and site == True:
        site_Checked = True
        uos.rename(temp_File, "siteFile.py")
        time.sleep(0.5)
        uos.replace("siteFile.py","/flash/lib/sites/siteFile.py")
      else:
        if file_Action[files_Processed] == "1" or file_Action[files_Processed] == "2":
          try:
            uos.rename(temp_File,file_Required[files_Processed])
            time.sleep(0.5)
            if file_Required[files_Processed] == transfer_File:
              logger_Update = True
          except OSError:
            pass
          else:
            pass
        elif file_Action[files_Processed] == "3":
          try:
            uos.mkdir(file_Path[files_Processed])
            time.sleep(0.5)
          except OSError:
            time.sleep(0.5)
            uos.rename(temp_File,file_Required[files_Processed])
          else:
            uos.rename(temp_File,file_Required[files_Processed])
        else:
          pass
        files_Processed = files_Processed + 1
    else:
      pass
        
def ftps_downloadFile(fileport = 0,sz = 0,df_chunk=1000):
  global temp_File
  global topic_ToSend
  global msg_ToSend
  global msg_Topic
  global obs_publishReady
  global wdt
  global temp_Path
  global file_szRcvd  
  
  file_Size = sz
  data_Received = 0
  uos.chdir(temp_Path)
  log = uio.open(temp_File, mode="w")
  try:    
    ftp_conn2 = FTP(port=fileport,user=None,passwd=None, timeout=20)
    ftp_conn2.download(port=fileport)
    time.sleep(5)
  except:
    log.close()
    topic_ToSend.append(msg_Topic)
    msg_ToSend.append("Could not Access FTPS for download")
    obs_publishReady = obs_publishReady + 1
  else:
    excess_Data = file_Size % df_chunk
    while (data_Received < file_Size):
      if ((file_Size - data_Received) > df_chunk):
        try:
          data = ftp_conn2.rcv(df_chunk)
        except OSError:
          pass
        else:
          data_Received = data_Received + len(data)
          wdt.feed()
          if len(data) > 0:
            log.write(data)
            time.sleep(0.5)
          else:
            pass
      else:
        try:
          data = ftp_conn2.rcv(excess_Data)
        except OSError:
          pass
        else:
          data_Received = data_Received + len(data)
          wdt.feed()
          if len(data) > 0:
            log.write(data)
            time.sleep(0.5)
          else:
            pass
  log.close()
  file_szRcvd = data_Received

def move_Files():
  global file_Required
  global file_Path
  global file_Action
  global files_toProcess
  global files_Processed
  global temp_Path
  global reboot

  i = 0
  uos.chdir(temp_Path)
  while i < files_Processed:
    if file_Action[i] == "1":
      try:
        uos.replace(file_Required[i],file_Path[i] + "/" + file_Required[i])
        time.sleep(0.5)
      except OSError:
        uos.rename(file_Required[i],file_Path[i] + "/" + file_Required[i])
        i = i + 1
        pass
      else:
        i = i + 1
    elif file_Action[i] == "2" or file_Action[i] == "3":
      try:
        uos.rename(file_Required[i],file_Path[i] + "/" + file_Required[i])
        time.sleep(0.5)
      except OSError:
        uos.replace(file_Required[i],file_Path[i] + "/" + file_Required[i])
        i = i + 1
        pass
      else:
        i = i + 1
    else:
      pass
  file_Required.clear()
  file_Path.clear()
  file_Action.clear()
  files_toProcess = 0
  files_Processed = 0
  reboot = True
            
def read_Version():
  global current_FS_Version
  global version_File
  global temp_Path
  global empty_Text

  uos.chdir(temp_Path)
  info = empty_Text
  with uio.open(version_File, mode="r") as log:
    info = log.readlines()
    log.close()
  ver = info[0]
  current_FS_Version = ver.rstrip()
  
def read_Update():
  global files_Required
  global file_Path
  global files_toProcess
  global read_updateFile
  global topic_ToSend
  global msg_ToSend
  global msg_Topic
  global obs_publishReady
  global current_FS_Version
  global version_File
  global temp_File
  global temp_Path
  global empty_Text
  global read_updateFile

  info = empty_Text
  uos.chdir(temp_Path)
  with uio.open(temp_File, mode="r") as log:
    info = log.readlines()
    log.close()
  num = len(info)
  update_ver = info[0]
  compare = update_ver.rstrip()
  if (compare == current_FS_Version):
    topic_ToSend.append(msg_Topic)
    msg_ToSend.append("No updates required")
    obs_publishReady = obs_publishReady + 1
  else:
    x = 1 #position 0 is the version number so thissets up start of file info
    while x < num: #parse the files and paths for action
      temp_String = info[x]
      temp_String = temp_String.rstrip()
      tempBuff = temp_String.split(',')
      file_Required.append(tempBuff[0]) #add file to buffer
      file_Path.append(tempBuff[1]) #add file path to buffer
      file_Action.append(tempBuff[2]) #add action to buffer
      files_toProcess = files_toProcess + 1
      x = x + 1
    uos.replace(temp_File, version_File)
  read_updateFile = False

def read_transferFile():
  global transfer_File
  global wdt
  global root_Path

  uos.chdir(root_Path)
  fileBuff = [0x00] * 200
  f_Size = 0
  count = 0
  with uio.open(transfer_File, mode="r") as log:
    log.seek(0, 2)
    f_Size = log.tell()
    log.seek(0)
    log.close
  stdout.buffer.write("#F" + str(f_Size))
  c = None
  done = False
  complete = False
  cancel_Transfer = False
  while done == False:
    while c is None and count < 5:
      c = stdin.buffer.read() # reads byte and returns first byte in buffer or None
      time.sleep(2)
      count = count + 1
    if count < 5:
      temp_String = str(c.decode())
      tempBuff = temp_String.split('\n')
      i = 0
      new = True
      while done == False:
        if (tempBuff[i].startswith('!') and tempBuff[i].endswith('\r')):
          if (tempBuff[i][1] == 'S'):
            with uio.open(transfer_File, mode="r") as log1:
              cnt = 0
              buff_Index = 0
              while cnt < f_Size and cancel_Transfer == False:
                wdt.feed()
                #if the first transmission or okay to proceed with file transfer
                if new == True:
                  for x in range(0,200):
                    if cnt < f_Size:
                      a = log1.read(1)
                      fileBuff[x]=(a)
                      cnt = cnt + 1
                    else:
                      buff_Index = x
                      break        
                  if cnt % 200 == 0:
                    for x in range(0,200):
                      stdout.buffer.write(fileBuff[x])
                    time.sleep(0.1)
                  else:
                    for x in range(0,buff_Index):
                      stdout.buffer.write(fileBuff[x])
                    done = True
                    time.sleep(2)
                #if file transfer had issues and needs last transmission to be resent
                else:
                  if cnt % 200 == 0:
                    for x in range(0,200):
                      stdout.buffer.write(fileBuff[x])
                    time.sleep(0.1)
                  else:
                    for x in range(0,buff_Index):
                      stdout.buffer.write(fileBuff[x])
                    done = True
                    time.sleep(2)                
                y = None
                count = 0
                while y is None and count < 5:
                  y = stdin.buffer.read() # reads byte and returns first byte in buffer or None
                  time.sleep(2)
                  count = count + 1
                if count < 5:
                  temp_String2 = str(y.decode())
                  tempBuff2 = temp_String2.split('\n')
                  if (tempBuff2[i].startswith('!') and tempBuff2[i].endswith('\r')):
                    #print("Good Teensy Read")
                    if (tempBuff2[i][1] == 'S'):
                      new = True
                      #print("new = True")
                    elif (tempBuff2[i][1] == 'R'):
                      new = False
                      #print("new = False")
                    elif (tempBuff2[i][1] == 'X'):
                      if (done == True):
                        complete = True
                      else:
                        done = True
                        cancel_Transfer = True
                        #print("Cancel")
                    else:
                      done = True
                      cancel_Transfer = True
                  else:
                    done = True
                    cancel_Transfer = True
                else:
                  done = True
                  cancel_Transfer = True
            log1.close()
          else:
            done = True
            cancel_Transfer = True
        else:
          done = True
          cancel_Transfer = True
    else:
      done = True
      cancel_Transfer = True
  if done == True and cancel_Transfer == False and complete == True:
    uos.remove(transfer_File)
    logger_Update = False
    
def publish_Backup():
  global msg_payload
  global payload_Topic
  global daily_Topic
  global precip_Topic
  global topic_ToSend
  global msg_ToSend
  global obs_publishReady
  global topic_File
  global msg_File
  global root_Path

  uos.chdir(root_Path)	
  topic_ToSend.append(payload_Topic)
  msg_ToSend.append(msg_payload)
  obs_publishReady = obs_publishReady + 1
  
  if (payload_Topic == daily_Topic or payload_Topic == precip_Topic):    
    log = uio.open(topic_File, mode="a")
    log.write(payload_Topic + "\n")
    time.sleep(0.5)
    log.close()
    log1 = uio.open(msg_File, mode="a")
    log1.write(msg_payload + "\n")
    time.sleep(0.5)
    log1.close()
    
  msg_payload = ""
  payload_Topic = ""  

def publish_Obs(client_id=CLIENT_ID, hostname=SERVER, keepalive=60):
  global topic_ToSend
  global msg_ToSend
  global msg_Topic
  global obs_publishReady
  global publish_Success
  global wdt
  global tfile_readComplete
  global mfile_readComplete
  global client

  publish_Success = False
  cnt = 0
  wdt.feed()
  try:
    while cnt < obs_publishReady:
      topic = topic_ToSend[cnt]
      msg = msg_ToSend[cnt]
      client.publish(topic, msg)  
      wdt.feed()
      cnt = cnt + 1
      wdt.feed()
      time.sleep(0.5)
    if cnt == obs_publishReady:
      publish_Success = True
      obs_publishReady = 0
      topic_ToSend.clear()
      msg_ToSend.clear()
      
      if files_Exist == True and tfile_readComplete == True and mfile_readComplete == True:
        wdt.feed()
        deleteFiles()
        time.sleep(1)
        createFiles()
      else:
        wdt.feed()
  except: ##client socket connection contained error to post to message que
    fail = -1
    return fail
  else:
    success = 0
    return success
    

def read_teensy():
  global msg_payload
  global payload_Topic
  global temp_Topic
  global precip_Topic
  global daily_Topic
  global msg_Topic
  global topic_ToSend
  global msg_ToSend
  global obs_publishReady
  global empty_Text
  
  msg_read = False
  temp_Inbound = False
  precip_Inbound = False
  dailyUpdate = False
  tempUpdate = False
  t_d = [empty_Text] * 8
  var = empty_Text
  msg_payload = empty_Text
  payload_Topic = empty_Text
  trim_String = empty_Text
  empty_Read = False

  time.sleep(3)
  c = stdin.buffer.read() # reads byte and returns first byte in buffer or None
  if c is None: #buffer is empty, move on
    empty_Read = True
  if empty_Read == False:
    temp_String = str(c.decode())
    tempBuff = temp_String.split('\n')
    pubCnt = len(tempBuff)
    i = 0
    while i < pubCnt:
      if (tempBuff[i].startswith('#') and tempBuff[i].endswith('\r')):
        if (tempBuff[i][1] == 'T'):
          temp_Inbound = True
        elif (tempBuff[i][1] == 'F'):
          precip_Inbound = True
        else:
          pass
        trim_String = tempBuff[i]
        trim_String = trim_String[2:len(trim_String)-1]
        if (temp_Inbound == True) or (precip_Inbound == True):
          msg_payload = trim_String
          msg_read = True
          
          if precip_Inbound == True:
            payload_Topic=precip_Topic
            topic_ToSend.append(msg_Topic)
            msg_ToSend.append("RR8 Precip Received")
            obs_publishReady = obs_publishReady + 1
            publish_Backup()
            
          elif temp_Inbound == True:
            if msg_payload.count(",") == 7: # daily has the pp value so there will be 7 "," delimiters
              t_d = msg_payload.split(",")
              dailyUpdate = True
              topic_ToSend.append(msg_Topic)
              msg_ToSend.append("RR3 Received")
              obs_publishReady = obs_publishReady + 1
            elif msg_payload.count(",") == 6:
              t_d = msg_payload.split(",")
              tempUpdate = True
              topic_ToSend.append(msg_Topic)
              msg_ToSend.append("RR8 Temp Received")
              obs_publishReady = obs_publishReady + 1
            else:
              msg_payload = ""
              payload_Topic = ""
            
          else:
            pass          
             
          if dailyUpdate == True:
            msg_payload = pubTopic.clientID + ',' + t_d[0] + ',' + t_d[1] + ',' + t_d[2] + ',' + t_d[3] + ',' + t_d[4] + ',' + t_d[5] + ',' + t_d[6] + ',' + t_d[7]
            payload_Topic=daily_Topic
            publish_Backup()
          
          if tempUpdate == True:
            msg_payload = pubTopic.clientID + ',' + t_d[0] + ",,,,," + t_d[5] + ',' + t_d[6]
            payload_Topic=temp_Topic
            publish_Backup()

        else:
          pass

      else:
        pass

      msg_read = False
      temp_Inbound = False
      precip_Inbound = False
      dailyUpdate = False
      tempUpdate = False
      t_d = [""] * 8
      var = ""
      msg_payload = ""
      payload_Topic = ""
      trim_String = ""
      i = i + 1

def xbee_debug(desig = "", msgToTeensy = ""):
  if desig == "#T":
    xbee_msg = desig + msgToTeensy + "\r\n"
  else:
    xbee_msg = desig + "\r\n"
  stdout.buffer.write(xbee_msg)
  
def printLocalTime():
  global atOb_T
  global timeUpdated
  global topic_ToSend
  global msg_ToSend
  global obs_publishReady
  
  t1 = str(int(utime.localtime()[0]) - 2000) + "," + str(utime.localtime()[1]) + "," + str(utime.localtime()[2]) + "," + str(utime.localtime()[3]) + "," + str(utime.localtime()[4])  + "," + str(utime.localtime()[5])
  timeMsg = t1 + "," + atOb_T
  xbee_debug("#T",timeMsg + "\r\n")
  topic_ToSend.append(msg_Topic)
  msg_ToSend.append("Time Sync: " + timeMsg)
  obs_publishReady = obs_publishReady + 1
  timeUpdated = True

def readFiles():
  global obs_publishReady
  global topic_ToSend
  global msg_ToSend
  global topic_File
  global msg_File
  global file_lineRef
  global tfile_readComplete
  global mfile_readComplete
  global root_Path

  uos.chdir(root_Path)
  obs_ToAdd = 0
  temp_Line = file_lineRef
  start_Read = temp_Line
  currentNum = obs_publishReady
  with uio.open(topic_File, mode="r") as log:
    topics_pending = log.readlines()
    num = len(topics_pending)
    if num > 0:
      i = 0
      incr_Read = start_Read
      while i < 50 - currentNum:
        t = topics_pending[incr_Read]
        topic_ToSend.append(t[:len(t)-1])
        incr_Read = incr_Read + 1
        if incr_Read == num:
          i = 50 - currentNum
          tfile_readComplete = True
          file_lineRef = 0
        else:
          i = i + 1
          obs_ToAdd = obs_ToAdd + 1
      log.close()
      with uio.open(msg_File, mode="r") as log1:
        msg_pending = log1.readlines()
        num = len(msg_pending)
        i = 0
        incr_Read = start_Read
        while i < 50 - currentNum:
          m = msg_pending[incr_Read]
          msg_ToSend.append(m[:len(m)-1])
          incr_Read = incr_Read + 1
          if incr_Read == num:
            i = 50 - currentNum
            mfile_readComplete = True
            file_lineRef = 0
          else:
            i = i + 1
        log1.close()
      obs_publishReady = obs_publishReady + obs_ToAdd
      if tfile_readComplete == False:
        file_lineRef = file_lineRef + obs_ToAdd
      else:
        pass

    else:
      log.close()
      tfile_readComplete = True
      mfile_readComplete = True
      file_lineRef = 0

def createFiles():
  global topic_File
  global msg_File
  global file_lineRef
  global tfile_readComplete
  global mfile_readComplete
  global root_Path

  uos.chdir(root_Path)
  log = uio.open(topic_File, mode="x")
  log.close()
  log1 = uio.open(msg_File, mode="x")
  log1.close()
  tfile_readComplete = True
  mfile_readComplete = True
  file_lineRef = 0

def deleteFiles():
  global topic_File
  global msg_File
  global root_Path

  uos.chdir(root_Path)
  try:
    log = uio.open(topic_File)
    log.close()
    uos.remove(topic_File)
  except OSError:
    pass
  try:
    log1 = uio.open(msg_File)
    log1.close()
    uos.remove(msg_File)
  except OSError:
    pass
  

topic_ToSend.append(msg_Topic)
msg_ToSend.append(pubTopic.clientID + " Cellular and MQTT Connected, v0.9")

bootMsg = str(machine.reset_cause())
topic_ToSend.append(msg_Topic)
msg_ToSend.append(bootMsg)
obs_publishReady = 2

#Pull pending topic/msg from log files
try:
  log = uio.open(topic_File)
  log.close()
  files_Exist = True
except OSError:
  files_Exist = False
  pass
  
if files_Exist == True:
  readFiles()
else:
  createFiles()

try:
  log = uio.open(transfer_File)
  log.close()
  logger_Update = True
except OSError:
  pass

yearCheck = 2019
conn = network.Cellular()
while not conn.isconnected():
  read_teensy()
  time.sleep(2)
while (utime.localtime()[0]) < yearCheck:
  read_teensy()
  time.sleep(2)
time.sleep(1)
try: # validate we have a /temp folder to handle file operations.
  uos.chdir(temp_Path)
except OSError: #if no /temp folder, create it.  
  uos.mkdir(temp_Path)
  pass
else: # we validated or created, move on
  pass
uos.chdir(root_Path) #return to root directory (/flash)
updateString = "Update: "
update_hr = machine.rng() % 24 #Hour to check for updates each day
updateString = updateString + str(update_hr)
updateString = updateString + ":"
update_min = machine.rng() % 60 #Minute to check for updates each day
updateString = updateString + str(update_min)
updateString = updateString + ", Site: "                               
update_siteHr = machine.rng() % 6 #Hour to pull siteFile each day
updateString = updateString + str(update_siteHr)
updateString = updateString + ":"
update_siteMin = machine.rng() % 60 #Minute to pull siteFile each day
updateString = updateString + str(update_siteMin)
topic_ToSend.append(msg_Topic)
msg_ToSend.append(updateString) 
obs_publishReady = obs_publishReady + 1
printLocalTime()
read_Version()
  
status = client.connect()

while True:
  wdt.feed()
  read_teensy()
  wdt.feed()
  time.sleep(2)
  xbeeConn = xbee.atcmd('AI')
  XBee_RSSI = xbee.atcmd('DB')
  if XBee_RSSI != None and xbeeConn == 0:
    if (obs_publishReady > 0):
      if status == 0:
        status = publish_Obs()
        if status == -1:
            gc.collect()
        if reboot == True:
          machine.reset() 
      else:
        gc.collect()
        status = client.connect()
        if status == 0:
          status = publish_Obs()
          if status == -1:
            gc.collect()
          else:
            pass 
        else:
          gc.collect()             
    else:
      pass
    wdt.feed()
    if utime.localtime()[3] == 9 and utime.localtime()[4] == 2:
      reboot = True
    if (ftps_Checked == False) and (utime.localtime()[3] == update_hr) and (utime.localtime()[4] >= update_min):
      if status == 0:
        status = -1
        try:
          client.disconnect()
        except OSError:
          pass
        else:          
          gc.collect()
          time.sleep(2.0)
      gc.collect()
      time.sleep(1.0)
      topic_ToSend.append(msg_Topic)
      msg_ToSend.append("Accessing FTPS Server")
      obs_publishReady = obs_publishReady + 1
      ftps_Conn()
      if read_updateFile == True:
        read_Update()
    wdt.feed()
    if (files_toProcess == 0) and (site_Checked == False) and (utime.localtime()[3] == update_siteHr) and (utime.localtime()[4] >= update_siteMin):
      if status == 0:
        status = -1
        try:
          client.disconnect()
        except OSError:
          pass
        else:          
          gc.collect()
          time.sleep(2.0)
      gc.collect()
      topic_ToSend.append(msg_Topic)
      msg_ToSend.append("FTPS Site File Check")
      obs_publishReady = obs_publishReady + 1
      ftps_Conn(site=True)
      wdt.feed()
    if files_toProcess > 0 and files_Processed < files_toProcess:
      gc.collect()
      time.sleep(1.0)
      wdt.feed()
      ftps_Conn(check = False)
    if files_toProcess > 0 and files_Processed == files_toProcess: #all files have been downloaded and need to be moved
      move_Files()
      wdt.feed()
  else:
    pass  
  if publish_Success == True and file_lineRef > 0:
    wdt.feed()
    readFiles()
  if ((utime.localtime()[4]%10) == 0) and rssiUpdated == False:
    topic_ToSend.append(msg_Topic)
    msg_ToSend.append("RSSI: " + str(XBee_RSSI))
    obs_publishReady = obs_publishReady + 1
    rssiUpdated = True
  if (rssiUpdated == True) and ((utime.localtime()[4]%10) != 0):
    rssiUpdated = False
  if ((utime.localtime()[4]%15) == 0) and timeUpdated == False:
    printLocalTime()
    timeUpdated = True
    if xbeeConn == 1 or (XBee_RSSI == None and xbeeConn == 0):
      reboot = True
  if (timeUpdated == True) and ((utime.localtime()[4]%15) != 0):
    timeUpdated = False
  if (logger_Update == True) and (updating_Logger == False) and ((utime.localtime()[4]%15) == 1):
    wdt.feed()
    updating_Logger = True
    read_transferFile()
  if (updating_Logger == True) and ((utime.localtime()[4]%15) != 1):
    updating_Logger = False  
  wdt.feed()
  if utime.localtime()[3] == 0 and utime.localtime()[4] == 0:
    ftps_Checked = False
    site_Checked = False
  time.sleep(2.0)
  
