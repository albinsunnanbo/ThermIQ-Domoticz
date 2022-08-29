"""
<plugin key="ThermIQPlugin" name="ThermIQ MQTT Plugin" author="Jack Fagner" version="0.1.0">
    <description>
      <h2>ThermIQ MQTT Plugin</h2><br/>
      <h3>by Jack Fagner</h3>
      
    </description>
    <params>
        <param field="Address" label="MQTT Server address" width="300px" required="true" default="127.0.0.1"/>
        <param field="Port" label="Port" width="300px" required="true" default="1883"/>
        <param field="Username" label="Username" width="300px"/>
        <param field="Password" label="Password" width="300px" default="" password="true"/>
		<param field="Mode1" label="Topic" width="125px" default="ThermIQ/ThermIQ-room-bb" />
        <param field="Mode6" label="Debug" width="150px">
            <options>
                <option label="None" value="0"  default="true" />
                <option label="Python Only" value="2"/>
                <option label="Basic Debugging" value="62"/>
                <option label="Basic+Messages" value="126"/>
                <option label="Connections Only" value="16"/>
                <option label="Connections+Queue" value="144"/>
                <option label="All" value="-1"/>
            </options>
        </param>
    </params>
</plugin>
"""
errmsg = ""
try:
 import Domoticz
except Exception as e:
 errmsg += "Domoticz core start error: "+str(e)
try:
 import json
except Exception as e:
 errmsg += " Json import error: "+str(e)
try:
 import time
except Exception as e:
 errmsg += " time import error: "+str(e)
try:
 import re
except Exception as e:
 errmsg += " re import error: "+str(e)
try:
 from mqtt import MqttClientSH2
except Exception as e:
 errmsg += " MQTT client import error: "+str(e)

try:
    from datetime import datetime
except Exception as e:
    errmsg += "  datetime import error: "+str(e)

class BasePlugin:
    mqttClient = None

    def __init__(self):
     return

    def onStart(self):
     global errmsg
     if errmsg =="":
      try:
        Domoticz.Heartbeat(10)
        if Parameters["Mode6"] != "0":
            Domoticz.Debugging(int(Parameters["Mode6"]))
        self.base_topic = Parameters["Mode1"].strip()
        self.mqttserveraddress = Parameters["Address"].strip()
        self.mqttserverport = Parameters["Port"].strip()
        self.mqttClient = MqttClientSH2(self.mqttserveraddress, self.mqttserverport, "", self.onMQTTConnected, self.onMQTTDisconnected, self.onMQTTPublish, self.onMQTTSubscribed)
      except Exception as e:
        Domoticz.Error("MQTT client start error: "+str(e))
        self.mqttClient = None
     else:
        Domoticz.Error("Your Domoticz Python environment is not functional! "+errmsg)
        self.mqttClient = None
     #if str(Settings["AcceptNewHardware"])!="0":
     # Domoticz.Log("New hardware creation enabled ")
     #else:
     # Domoticz.Log("--> New hardware creation disabled! <-- ")

    def checkDevices(self):
        Domoticz.Debug("checkDevices called")

    def onStop(self):
        Domoticz.Debug("onStop called")

    def onCommand(self, Unit, Command, Level, Color):  # react to commands arrived from Domoticz
        if self.mqttClient is None:
         return False
        Domoticz.Debug("onCommand called for Unit " + str(Unit) + ": Parameter '" + str(Command) + "', Level: " + str(Level)+", DeviceID: "+Devices[Unit].DeviceID )
        #Domoticz.Debug("Command: " + Command + " (" + str(Level) + ") Color:" + Color)
        # Publish to MQTT using message: Devices[Unit].Description.replace("$sValue$",Devices[Unit].sValue)
        writeTopic = self.base_topic + "/WRITE"
        if( Unit==151 and str(Command)=="Set Level" ):
          newMode = int(int(Level) / 10)
          if (self.mqttClient.isConnected):
            try:
              self.mqttClient.publish(writeTopic, '{"d51":'+str(newMode)+'}')
              Devices[Unit].Update(0, str(Level))
            except Exception as e:
              Domoticz.Debug(str(e))
        if( Unit==150 and str(Command)=="Set Level" ):
          newTemp = str(int(Level))
          if (self.mqttClient.isConnected):
            try:
              self.mqttClient.publish(writeTopic, '{"d50":'+newTemp+'}')
              Devices[Unit].Update(0, newTemp)
            except Exception as e:
              Domoticz.Debug(str(e))
        if( Unit==158 and str(Command)=="Set Level" ):
          newTemp = str(int(Level))
          if (self.mqttClient.isConnected):
            try:
              self.mqttClient.publish(writeTopic, '{"d58":'+newTemp+'}')
              Devices[Unit].Update(0, newTemp)
            except Exception as e:
              Domoticz.Debug(str(e))
        if( Unit==101 and str(Command)=="Set Level" ):
          setTopic = self.base_topic + "/SET"
          newTempStr = str(Level)
          if (self.mqttClient.isConnected):
            try:
              self.mqttClient.publish(setTopic, '{"INDR_T":'+newTempStr+'}')
              Devices[Unit].Update(0, newTempStr)
            except Exception as e:
              Domoticz.Debug(str(e))
          
          

    def onConnect(self, Connection, Status, Description):
       if self.mqttClient is not None:
        self.mqttClient.onConnect(Connection, Status, Description)

    def onDisconnect(self, Connection):
       if self.mqttClient is not None:
        self.mqttClient.onDisconnect(Connection)

    def onMessage(self, Connection, Data):
       if self.mqttClient is not None:
        self.mqttClient.onMessage(Connection, Data)

    def onHeartbeat(self):
      Domoticz.Debug("Heartbeating...")
      if self.mqttClient is not None:
       try:
        # Reconnect if connection has dropped
        if (self.mqttClient._connection is None) or (not self.mqttClient.isConnected):
            Domoticz.Debug("Reconnecting")
            self.mqttClient._open()
        else:
            self.mqttClient.ping()
       except Exception as e:
        Domoticz.Error(str(e))

    def onMQTTConnected(self):
       if self.mqttClient is not None:
        self.mqttClient.subscribe([self.base_topic + '/data'])
        #self.mqttClient.subscribe([self.base_topic + '/#'])

    def onMQTTDisconnected(self):
        Domoticz.Debug("onMQTTDisconnected")

    def onMQTTSubscribed(self):
        Domoticz.Debug("onMQTTSubscribed")
        
    def onMQTTPublish(self, topic, message): # process incoming MQTT statuses
    
        def addOrUpdateDevice( nValue, sValue, **kwargs ):
            iUnit = kwargs["Unit"]
            if iUnit not in Devices:
              if str(Settings["AcceptNewHardware"])!="0":
                Domoticz.Log( "Adding device: " + str(kwargs))
                Domoticz.Device( **kwargs ).Create()
              else:
                return -1
            if( Devices[iUnit].sValue != sValue ): #Update if changed. Check nValue as well?
              Devices[iUnit].Update(nValue, sValue)
            return iUnit
    
        if "/announce" in topic: # announce did not contain any information for us
         return False
        try:
         topic = str(topic)
         message = str(message)
        except:
         Domoticz.Debug("MQTT message is not a valid string!") #if message is not a real string, drop it
         return False
        Domoticz.Debug("MQTT message: " + topic + " " + str(message))
        if(str(message)=="connected"):
            Domoticz.Error("mqtt connected")
        elif(str(message)=="disconnected"):         
            Domoticz.Error("mqtt disconnected")
        else:
            payload =  json.loads( message.replace("'",'"').lower() )
            if( "rssi" in payload ):
              Domoticz.Debug("rssi: " + str( payload["rssi"] ) )
              devparams = { "Name" : "RSSI", "DeviceID" : "rssi", "Unit": 231, "Type": 243, "Subtype": 31, "Options" : { "Custom" : "1;dBm"} }
              addOrUpdateDevice(0, str( payload["rssi"] ), **devparams)
            if( "d51" in payload ):
              Domoticz.Debug("mode (d51): " + str( payload["d51"] ) )
              options = { "LevelActions": "||||", "LevelNames": "Off|Auto|Heatpump|Aux|Hotwater",
                          "LevelOffHidden": "false", "SelectorStyle": "0" }
              devparams = { "Name" : "Mode", "DeviceID" : "mode", "Unit": 151, "TypeName" : "Selector Switch", "Image": 15, "Options" : options }
              nValue = int( payload["d51"] ) * 10
              addOrUpdateDevice(0, str( nValue ), **devparams)
            if( "d50" in payload ):
              Domoticz.Debug("indoor target temp (d50): " + str( payload["d50"] ) )
              devparams = { "Name" : "Indoor target temp", "DeviceID" : "targettemp", "Unit": 150, "Type": 242, "Subtype": 1 }
              addOrUpdateDevice(0, str( payload["d50"] ), **devparams)
            if( "d58" in payload ):
              Domoticz.Debug("heatstop (d58): " + str( payload["d58"] ) )
              devparams = { "Name" : "Heatstop", "DeviceID" : "heatstop", "Unit": 158, "Type": 242, "Subtype": 1 }
              addOrUpdateDevice(0, str( payload["d58"] ), **devparams)
            if( "d7" in payload ):
              Domoticz.Debug("hotwater temp (d7): " + str( payload["d7"] ) )
              devparams = { "Name" : "Hotwater temp", "DeviceID" : "watertemp", "Unit": 107, "TypeName": "Temperature" }
              addOrUpdateDevice(0, str( payload["d7"] ), **devparams)
            if( "d0" in payload ):
              Domoticz.Debug("outdoor temp (d0): " + str( payload["d0"] ) )
              devparams = { "Name" : "Outdoor temp", "DeviceID" : "outtemp", "Unit": 100, "TypeName": "Temperature" }
              addOrUpdateDevice(0, str( payload["d0"] ), **devparams)
            if( "d12" in payload ):
              Domoticz.Debug("electrical current (d12): " + str( payload["d12"] ) )
              devparams = { "Name" : "Electrical Current", "DeviceID" : "current", "Unit": 112, "Type": 243, "Subtype": 23 }
              addOrUpdateDevice(0, str( payload["d12"] ), **devparams)
            if( "d1" in payload and "d2" in payload ):
              indoorTempStr = str( payload["d1"] ) + "." + str( payload["d2"] )
              Domoticz.Debug("indoor temp (d1/d2): " + indoorTempStr )
              devparams = { "Name" : "Indoor temp", "DeviceID" : "indoortemp", "Unit": 101, "Type": 242, "Subtype": 1 }
              addOrUpdateDevice(0, indoorTempStr, **devparams)
              
        return True
    

global _plugin
_plugin = BasePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onStop():
    global _plugin
    _plugin.onStop()

def onConnect(Connection, Status, Description):
    global _plugin
    _plugin.onConnect(Connection, Status, Description)

def onDeviceModified(Unit):
    global _plugin
    return

def onDisconnect(Connection):
    global _plugin
    _plugin.onDisconnect(Connection)

def onMessage(Connection, Data):
    global _plugin
    _plugin.onMessage(Connection, Data)

def onCommand(Unit, Command, Level, Color):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Color)

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()
