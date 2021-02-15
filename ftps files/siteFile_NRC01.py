import time
import sys

class pubTopic:
  #-----topics
  #test
  
  SUB_TOPIC = "NWS/#"
  COMMAND_TOPIC = "NWS/CRH/NRC/COOP/NRC01/COMMAND"
  TEMP_PUB_TOPIC = "NWS/CRH/NRC/COOP/NRC01/TEMP"
  PRECIP_PUB_TOPIC = "NWS/CRH/NRC/COOP/NRC01/PRECIP"
  DAILY_PUB_TOPIC = "NWS/CRH/NRC/COOP/NRC01/DAILY"
  MESSAGE_TOPIC = "NWS/CRH/NRC/COOP/NRC01/MSG"
  UPDATE_TOPIC = "NWS/CRH/NRC/COOP/NRC01/UPDATE"
  ALERT_TOPIC = "NWS/CRH/NRC/COOP/NRC01/UPDATE"
  clientID = "NRC01"
  clientTZ = "-6"
  atOb_T = "7"
  server_Address = "sftp.crh.noaa.gov"
