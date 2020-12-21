import micropython
import xbee
import uio
import os
import uos
from umqtt.simple import MQTTClient
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
sub_Topic = pubTopic.SUB_TOPIC
temp_Topic = pubTopic.TEMP_PUB_TOPIC
precip_Topic = pubTopic.PRECIP_PUB_TOPIC
daily_Topic = pubTopic.DAILY_PUB_TOPIC
update_Topic = pubTopic.UPDATE_TOPIC
command_Topic = pubTopic.COMMAND_TOPIC
alert_Topic = pubTopic.ALERT_TOPIC
msg_payload = ""
payload_Topic = ""
publish_Success = False

topic_ToSend = [] 
msg_ToSend = [] 
obs_publishReady = 0
topic_File = "topic.log"
msg_File = "msg.log"
transfer_File = "software1.bin"
tF_size = 0
file_lineRef = 0
tfile_readComplete = False
mfile_readComplete = False
files_Exist = False

badSig_Cnt = 0
XBee_RSSI = 105

CLIENT_ID = pubTopic.clientID  # Should be unique for each device connected.
client = MQTTClient(CLIENT_ID, SERVER, keepalive=200)
minute = 0
year = 0
TZ = pubTopic.clientTZ
atOb_T = pubTopic.atOb_T
rssiUpdated = False
timeUpdated = False

'''
AI_DESC = {
    0x00: 'CONNECTED',
    0x22: 'REGISTERING_TO_NETWORK',
    0x23: 'CONNECTING_TO_INTERNET',
    0x24: 'RECOVERY_NEEDED',
    0x25: 'NETWORK_REG_FAILURE',
    0x2A: 'AIRPLANE_MODE',
    0x2B: 'USB_DIRECT',
    0x2C: 'PSM_DORMANT',
    0x2F: 'BYPASS_MODE_ACTIVE',
    0xFF: 'MODEM_INITIALIZING',
}
'''

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

def publish_Obs():
  global topic_ToSend
  global msg_ToSend
  global obs_publishReady
  global publish_Success
  global wdt
  global tfile_readComplete
  global mfile_readComplete
  global client

  publish_Success = False
  cnt = 0
  wdt.feed()
  while cnt < obs_publishReady:
    topic = topic_ToSend[cnt]
    msg = msg_ToSend[cnt]
    client.publish(topic, msg)  
    wdt.feed()
    cnt = cnt + 1
    wdt.feed()
    time.sleep(0.5)
  client.disconnect()
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
  else: ##client socket connection contained error to post to message que
    topic_ToSend.append(msg_Topic)
    msg_ToSend.append(issue)
    obs_publishReady = obs_publishReady + 1
    

def read_teensy():
  global msg_payload
  global payload_Topic
  global temp_Topic
  global precip_Topic
  global alert_Topic
  global daily_Topic
  global topic_ToSend
  global msg_ToSend
  global obs_publishReady
  
  msg_read = False
  temp_Inbound = False
  precip_Inbound = False
  alert_Inbound = False
  dailyUpdate = False
  tempUpdate = False
  t_d = [""] * 8
  var = ""
  msg_payload = ""
  payload_Topic = ""
  trim_String = ""
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
        elif (tempBuff[i][1] == 'A'):
          alert_Inbound = True
        else:
          pass
        trim_String = tempBuff[i]
        trim_String = trim_String[2:len(trim_String)-1]
        if (temp_Inbound == True) or (precip_Inbound == True) or (alert_Inbound == True):
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

          elif alert_Inbound == True:
            alertUpdate = True
            payload_Topic=alert_Topic
            topic_ToSend.append(msg_Topic)
            msg_ToSend.append("Alert Received")
            obs_publishReady = obs_publishReady + 1
            publish_Backup()
            
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

      elif (tempBuff[i].startswith('!') and tempBuff[i].endswith('\r')):
        read_transferFileSize()

      else:
        pass

      msg_read = False
      temp_Inbound = False
      precip_Inbound = False
      alert_Inbound = False
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
  global TZ
  global timeUpdated
  global topic_ToSend
  global msg_ToSend
  global obs_publishReady
  
  t1 = str(int(utime.localtime()[0]) - 2000) + "," + str(utime.localtime()[1]) + "," + str(utime.localtime()[2]) + "," + str(utime.localtime()[3]) + "," + str(utime.localtime()[4])  + "," + str(utime.localtime()[5])
  timeMsg = t1 + "," + TZ
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

xbee.atcmd("AN", "super")
xbee.atcmd("CP", 0)
xbee.atcmd("AM", 0)
xbee.atcmd("N#", 0)
xbee.atcmd("TM", 0x258)
xbee.atcmd("TS", 0x258)
xbee.atcmd("DO", 0x21)
xbee.atcmd("K1", 0x3C)
xbee.atcmd("K2", 0x3C)
xbee.atcmd("MO", 0x7)
xbee.atcmd("HM", 0x1)
xbee.atcmd("HF", 0x3C)
xbee.atcmd("DL", "0.0.0.0")
xbee.atcmd("DE", 0x0)
xbee.atcmd("C0", 0x0)
xbee.atcmd("DX", 0xA0000)


yearCheck = 2019
conn = network.Cellular()
while not conn.isconnected():
  read_teensy()
  time.sleep(2)
while (utime.localtime()[0]) < yearCheck:
  read_teensy()
  time.sleep(2)
time.sleep(1)
printLocalTime()
wdt = machine.WDT(timeout=60000, response=machine.SOFT_RESET)


status = client.connect()

while True:
  wdt.feed()
  read_teensy()
  wdt.feed()
  time.sleep(2)
  XBee_RSSI = xbee.atcmd('DB')
  if XBee_RSSI != None:
    if badSig_Cnt != 0:
      topic_ToSend.append(msg_Topic)
      msg_ToSend.append("RSSI Degraded: " + str(badSig_Cnt) + " Loops")
      obs_publishReady = obs_publishReady + 1
      badSig_Cnt = 0
    if (obs_publishReady > 0):
      xbeeConn = xbee.atcmd('AI')
      if xbeeConn == 0:
        status = client.connect()
        if status == 0:
          try:            
            publish_Obs()
          except:
            status = -1
            #print("Not connected to broker")
            gc.collect()
          else:
            pass 
        else:
          gc.collect()
          status = client.connect()
          if status == 0:
            try:            
              publish_Obs()
            except:
              status = -1
              #print("Not connected to broker")
              gc.collect()
            else:
              pass 
          else:
            gc.collect()
            topic_ToSend.append(msg_Topic)
            msg_ToSend.append(status)
            obs_publishReady = obs_publishReady + 1              
      else:
        pass
    else:
      pass
  else:
    badSig_Cnt = badSig_Cnt + 1 
  wdt.feed()
  if publish_Success == True and file_lineRef > 0:
    readFiles()  
  if ((utime.localtime()[4]%15) == 0) and timeUpdated == False:
    printLocalTime()
    timeUpdated = True
  wdt.feed()
  if (timeUpdated == True) and ((utime.localtime()[4]%15) != 0):
    timeUpdated = False
  if ((utime.localtime()[4]%10) == 0) and rssiUpdated == False:
    topic_ToSend.append(msg_Topic)
    msg_ToSend.append("RSSI: " + str(XBee_RSSI))
    obs_publishReady = obs_publishReady + 1
    rssiUpdated = True
  wdt.feed()
  if (rssiUpdated == True) and ((utime.localtime()[4]%10) != 0):
    rssiUpdated = False
  wdt.feed()
  time.sleep(0.200)
  
