#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Link-Tap Domoticz plugin
#
# API Documentation 1.2: https://www.link-tap.com/#!/api-for-developers
#
# Author: DebugBill June 2021
#
"""
<plugin key="linktap" name="Link-Tap Watering System plugin" author="DebugBill" version="0.1" wikilink="http://www.domoticz.com/wiki/plugins/plugin.html" externallink="https://github.com/DebugBill/Link-Tap">
    <description>
        <h2>Link-Tap watering system</h2><br/>
        This plugin will allow Domoticz to read data from the Link-Tap cloud API. <br/>
        API key from LinkTap is required.<br/>
        More info on Link-Tap hardware can be found at https://link-tap.com<br/><br/>
        <h3>Features</h3>
        Several devices are created
        <ul style="list-style-type:square">
            <li>Reads waterflow counters and stores data</li>
            <li>Sets watering modes using preconfigures settings in Watertap</li>
            <li>Turns watering On and Off</li>
            <li>Displays alerts if any</li>
        </ul>
        <h3>Devices</h3>
        <ul style="list-style-type:square">
            <li>Device Type - What it does...</li>
        </ul>
        <h3>Configuration</h3>
    </description>
    <params>
        <param field="Address" label="Link-Tap API URL" width="300px" required="true" default="https://www.link-tap.com/"/>
        <param field="Username" label="User" width="300px" required="true"/>
        <param field="Password" label="Key" width="300px" required="true"/>
        <param field="Mode1" label="Return to previous wateting mode after manual mode" width="50px">
            <options>
                <option label="True" value=true default="true"/>
                <option label="False" value=false/>
            </options>
        </param>
        <param field="Mode6" label="Debug Level" width="300px">
            <options>
                <option label="None" value="0"  default="true"/>
                <option label="Plugin Verbose" value="2"/>
                <option label="Domoticz Plugin" value="4"/>
                <option label="Domoticz Devices" value="8"/>
                <option label="Domoticz Connections" value="16"/>
                <option label="Verbose+Plugin+Devices" value="14"/>
                <option label="Verbose+Plugin+Devices+Connections" value="30"/>
                <option label="Domoticz Framework - All (useless but in case)" value="1"/>
            </options>
	</param>
    </params>
</plugin>
"""
import Domoticz
import json
import requests

class BasePlugin:
    enabled = False
    def __init__(self):
        self.timer = 0
        self.token = ''
        self.url = ''
        self.taplinkers = dict() # All taplinkers by id
        self.devices = dict()
        self.gateways = dict()
        self.types  = {'counters':'-243-30','modes':'-244-62'}
        self.images = {'counters':'1','modes':'20'}
        self.headers = {'Content-type': 'application/json', 'Accept': 'text/plain'} 
        self.getAllDevices = dict()

    def onStart(self):
        # Rate limiting is in place at Link-Tap, highest freq is 15 sec
        Domoticz.Heartbeat(15)
        self.token = {'username':Parameters["Username"],'apiKey':Parameters['Password']}
        self.url = Parameters['Address']
        if self.url[-1] == '/':
            self.url += 'api/'
        else:
            self.url += '/api/'
        Domoticz.Debugging(int(Parameters["Mode6"]))
        Domoticz.Debug("onStart called")
        self.CreateDevices()

    def onStop(self):
        Domoticz.Log("onStop called")

    def onConnect(self, Connection, Status, Description):
        Domoticz.Log("onConnect called")

    def onMessage(self, Connection, Data):
        Domoticz.Log("onMessage called")

    def onCommand(self, Unit, Command, Level, Hue):
        Domoticz.Log("onCommand called for Unit " + str(Unit) + ": Parameter '" + str(Command) + "', Level: " + str(Level))
        if Level == 10: method = "activateIntervalMode"
        elif Level == 20: method = "activateOddEvenMode"
        elif Level == 30: method = "activateSevenDayMode"
        elif Levle == 40: method = "activateMonthMode"
        else: 
            Domoticz.Error("Unknown level received (" + str(Level) + "for device id " + str(Unit))
            return
        taplinkerId = Devices[Unit].DeviceID
        token = {'username':Parameters["Username"],'apiKey':Parameters['Password'], 'gatewayId':self.gateways[taplinkerId], 'taplinkerId':taplinkerId}
        post = requests.post(self.url + method, json=token, headers=self.headers)
        status = json.loads(post.text)
        if status['result'] == 'ok':
            Domoticz.Log('Command sent successfully to Taplinker ' + taplinkerId)
        elif status['result'] == 'error':
            Domoticz.Error('Error sending command to taplinker ' + taplinkerId + ': ' + status['message'])
        else:
            Domoticz.Error('Error while retreiving datafor Taplinker ' + taplinkerId + ', result code is: ' + status['result'])

    def onNotification(self, Name, Subject, Text, Status, Priority, Sound, ImageFile):
        Domoticz.Log("Notification: " + Name + "," + Subject + "," + Text + "," + Status + "," + str(Priority) + "," + Sound + "," + ImageFile)

    def onDisconnect(self, Connection):
        Domoticz.Log("onDisconnect called")

    def onHeartbeat(self):
        self.timer += 1
        Domoticz.Debug("onHeartbeat called ")
        if self.timer %  2 == 0: # Rate limiting is 30 seconds
            self.CreateDevices() # Call just in case hardware is added or devices are removed
            for gateway in self.getAllDevices['devices']:
                for taplinker in gateway['taplinker']:
                    taplinkerId = taplinker['taplinkerId']
                    if taplinkerId + self.types['counters'] in self.devices:
                        token = {'username':Parameters["Username"],'apiKey':Parameters['Password'],'taplinkerId':taplinkerId}
                        post = requests.post(self.url + 'getWateringStatus', json=token, headers=self.headers)
                        status = json.loads(post.text)
                        vel = 0
                        if status['result'] == 'ok':
                            if status['status'] is not None:
                                vel=round(int(status['status']['vel'])/1000,1)
                        elif status['result'] == 'error':
                            Domoticz.Error('Error while retreiving data: ' + status['message'])
                        else:
                            Domoticz.Error('Error while retreiving data, result is: ' + status['result'])
                        Devices[self.devices[taplinkerId + self.types['counters']]].Update(nValue=int(round(vel,0)), sValue=str(vel), SignalLevel=int(taplinker['signal']), BatteryLevel=int(taplinker['batteryStatus'][:-1]))
                        Domoticz.Log("Updated device: " + taplinker['taplinkerName'] + " with ID " + taplinkerId + ". Vel is " + str(vel))

    # Function to create devices from LinkTap and refresh plugin's internal structures
    # Rate limiting is in place at LinkTap, minimum interval is 5 minutes
    def CreateDevices(self):
        if self.timer % 300 != 0: # Rate limiting is 5 minutes
            Domoticz.Debug("CreateDevices function called to early, rate limiting is 5mn")
            return
        self.devices = dict()
        # Build list of current devices in Domoticz
        for device in Devices:
            Domoticz.Debug("Current device:" + str(device) + " " + str(Devices[device].DeviceID) + " " + str(Devices[device].Type)+ " " + str(Devices[device].SubType) + " " + str(Devices[device].SwitchType)+ " - " + str(Devices[device]))
            self.devices[Devices[device].DeviceID + '-' + str(Devices[device].Type) + '-' + str(Devices[device].SubType)] = device
    
        # Build list of devices on API and create missing ones
        post = requests.post(self.url + 'getAllDevices', json=self.token, headers=self.headers)
        self.getAllDevices = json.loads(post.text)
        for gateway in self.getAllDevices['devices']:
            gatewayName = gateway['name']
            for taplinker in gateway['taplinker']:
                taplinkerId = taplinker['taplinkerId']
                self.gateways[taplinkerId] = gateway['gatewayId']
                self.taplinkers[taplinkerId] = taplinker['taplinkerName']
                for type in self.types:
                    if not taplinkerId + self.types[type] in self.devices:
                        # Find a hole in the device IDs
                        hole = 1
                        if len(Devices) > 0:
                            sortedIDs = sorted(self.devices.values())
                            previous = 0
                            for id in sortedIDs:
                                if id != previous+1:
                                    hole = previous+1
                                    break
                                else:
                                    previous = id
                                    hole = id + 1
                        if hole > 255:
                            Domoticz.Error("Maximum of 255 devices per hardware has been reached, can't create any more devices")
                            return
                        if type == 'counters':
                            Domoticz.Device(Name=gatewayName + " - " + taplinker['taplinkerName'] + ' Counters',  Unit=hole, TypeName='Waterflow',  DeviceID=taplinkerId).Create()
                        elif type == 'modes':
                            Option1 = {"Scenes": "||||", "LevelActions": "||||", "LevelNames": "0|Intervals|Odd-Even|Seven days|Months", "LevelOffHidden": "true", "SelectorStyle": "1"}
                            Domoticz.Device(Name = gatewayName + " - " + taplinker['taplinkerName'] + " Watering Modes",  DeviceID=taplinkerId, Image = 20, Unit=hole, Type=244, Subtype=62 , Switchtype=18, Options = Option1, Used=1).Create()
                        else :
                            Domoticz.Error("Device type " + type + " not implemented")
                            return
                        self.devices[taplinkerId + self.types[type]] = hole
                        Domoticz.Log("Device " + taplinker['taplinkerName'] + " of type '" + type + "' with ID " +taplinkerId + " created")


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

def onMessage(Connection, Data):
    global _plugin
    _plugin.onMessage(Connection, Data)

def onCommand(Unit, Command, Level, Hue):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Hue)

def onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile):
    global _plugin
    _plugin.onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile)

def onDisconnect(Connection):
    global _plugin
    _plugin.onDisconnect(Connection)

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()


    # Generic helper functions
def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug( "'" + x + "':'" + str(Parameters[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device:           " + str(x) + " - " + str(Devices[x]))
        Domoticz.Debug("Device ID:       '" + str(Devices[x].ID) + "'")
        Domoticz.Debug("Device Name:     '" + Devices[x].Name + "'")
        Domoticz.Debug("Device nValue:    " + str(Devices[x].nValue))
        Domoticz.Debug("Device sValue:   '" + Devices[x].sValue + "'")
        Domoticz.Debug("Device LastLevel: " + str(Devices[x].LastLevel))
    return


def DumpDevicesToLog():
    # Show devices
    Domoticz.Debug("Device count.........: {}".format(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device...............: {} - {}".format(x, Devices[x]))
        Domoticz.Debug("Device Idx...........: {}".format(Devices[x].ID))
        Domoticz.Debug(
            "Device Type..........: {} / {}".format(Devices[x].Type, Devices[x].SubType)
        )
        Domoticz.Debug("Device Name..........: '{}'".format(Devices[x].Name))
        Domoticz.Debug("Device nValue........: {}".format(Devices[x].nValue))
        Domoticz.Debug("Device sValue........: '{}'".format(Devices[x].sValue))
        Domoticz.Debug("Device Options.......: '{}'".format(Devices[x].Options))
        Domoticz.Debug("Device Used..........: {}".format(Devices[x].Used))
        Domoticz.Debug("Device ID............: '{}'".format(Devices[x].DeviceID))
        Domoticz.Debug("Device LastLevel.....: {}".format(Devices[x].LastLevel))
        Domoticz.Debug("Device Image.........: {}".format(Devices[x].Image))


def DumpImagesToLog():
    # Show images
    Domoticz.Debug("Image count..........: {}".format((len(Images))))
    for x in Images:
        Domoticz.Debug("Image '{}'...: '{}'".format(x, Images[x]))


def DumpParametersToLog():
    # Show parameters
    Domoticz.Debug("Parameters count.....: {}".format(len(Parameters)))
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug("Parameter '{}'...: '{}'".format(x, Parameters[x]))


def DumpSettingsToLog():
    # Show settings
    Domoticz.Debug("Settings count.......: {}".format(len(Settings)))
    for x in Settings:
        Domoticz.Debug("Setting '{}'...: '{}'".format(x, Settings[x]))


def DumpAllToLog():
    DumpDevicesToLog()
    DumpImagesToLog()
    DumpParametersToLog()
    DumpSettingsToLog()
    return


