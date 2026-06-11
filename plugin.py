#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Link-Tap Domoticz plugin
#
# API Documentation 1.2: https://www.link-tap.com/#!/api-for-developers
#
# Author:  DebugBill <DebugBill@thauvin.org>
# License: GNU General Public License v3.0 (GPL-3.0)
#          https://www.gnu.org/licenses/gpl-3.0.html
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------
# 2.00  2026  - Bug fixes:
#                 * Boolean condition always True in onHeartbeat (or vs in)
#                 * Dead code after return in onHeartbeat (unreachable alert block)
#                 * return inside taplinker loop was aborting all remaining devices
#                 * nValue passed as bool instead of int; sValue="Test" placeholder
#                 * autoBack sent as string instead of real boolean to the API
#                 * type builtin shadowed as loop variable (renamed dtype)
#                 * Double json.loads() call in CheckVersion
#               - Robustness:
#                 * All HTTP calls centralised in _api_post() with try/except
#                 * self.getAllDevices initialised to safe default in __init__
#                 * hole-finding algorithm simplified and corrected
#                 * onStop() added
#                 * Unused self.images attribute removed
#               - Internationalisation:
#                 * All user-visible strings externalised in STRINGS dict (EN/FR)
#                 * Language auto-detected from Settings["Language"] with EN fallback
#                 * New languages can be added by copying the 'en' block
#               - Version check:
#                 * Numeric tuple comparison replaces string equality check
#                 * Local version ahead of GitHub release logs an info, not an alert
# 0.2   2024-05 - Better handling of status device updates
# 0.1   2021-06 - Initial release
# ---------------------------------------------------------------------------
"""
<plugin key="linktap" name="Link-Tap Watering System" author="DebugBill" version="2.00" wikilink="http://www.domoticz.com/wiki/plugins/plugin.html" externallink="https://github.com/DebugBill/Link-Tap">
    <description>
        <h2>Link-Tap watering system</h2><br/>
        This plugin will allow Domoticz to read data from the Link-Tap cloud API. <br/>
        API key from LinkTap is required.<br/>
        More info on Link-Tap hardware can be found at https://link-tap.com<br/><br/>
        <h3>Features</h3>
        Several devices are created
        <ul style="list-style-type:square">
            <li>Reads waterflow counters and stores data</li>
            <li>Sets watering modes using preconfigured settings in WaterTap</li>
            <li>Turns watering On and Off</li>
            <li>Displays alerts if any</li>
        </ul>
        <h3>Devices</h3>
        Five devices are created for each Link-Tap box
        <ul style="list-style-type:square">
            <li>Mode: allows for selecting the watering mode</li>
            <li>Status: Displays alerts collected by Link-Tap</li>
            <li>Flow: Instant flow in l/mn</li>
            <li>Volume: Total volume of last watering cycle</li>
            <li>On/Off: Immediate On or Off in instant mode</li>
        </ul>
        <h3>Configuration</h3>
    </description>
    <params>
        <param field="Username" label="User" width="300px" required="true"/>
        <param field="Password" label="Key" width="300px" required="true"/>
        <param field="Mode1" label="Return to previous watering mode after manual mode" width="50px">
            <options>
                <option label="True" value="true" default="true"/>
                <option label="False" value="false"/>
            </options>
        </param>
        <param field="Mode2" label="Maximum watering duration before automatic turn off (1 - 1439 sec)" width="40px" required="true" default="1439"/>
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

# ---------------------------------------------------------------------------
# Internationalisation
# ---------------------------------------------------------------------------
# To add a new language, add a new top-level key (ISO 639-1 code) and provide
# translations for every key present in 'en'. Missing keys automatically fall
# back to English.
# ---------------------------------------------------------------------------
STRINGS = {
    'en': {
        # onStart / general
        'onstart':              "onStart called",
        'version_ok':           "Current version ({ver}) of Link-Tap plugin is up to date",
        'version_new':          "A newer version of Link-Tap plugin is available: {ver}. Current version is: {cur}",
        'version_ahead':        "Local version ({cur}) is ahead of the latest GitHub release ({ver}) — development build",
        'version_check_fail':   "Could not contact GitHub to check for latest version",
        'max_devices':          "Maximum of 255 devices per hardware has been reached, can't create any more devices",
        'device_created':       "Device '{name}' of type '{dtype}' with ID {tid} created",
        'device_type_unknown':  "Device type '{dtype}' not implemented",
        # onHeartbeat
        'heartbeat':            "onHeartbeat called",
        'updated_counters':     "Updated counters: {name} (ID {tid}) — flow: {vel} l/min, volume: {vol} l, signal: {sig}",
        'updated_status':       "Updated status: {name} (ID {tid}) — {status}",
        # onCommand
        'command_received':     "onCommand called for device {unit}: command='{cmd}', level={lvl}",
        'command_ok':           "Command sent successfully to Taplinker {tid}",
        'level_unknown':        "Unknown level received ({lvl}) for device id {unit}",
        'command_unknown':      "Unknown command received ('{cmd}') for device id {unit}",
        # Watering status
        'watering':             "Watering",
        'idle':                 "Idle",
        # Work modes
        'mode_manual':          " - Manual mode",
        'mode_interval':        " - Intervals mode",
        'mode_oddeven':         " - Odd/Even mode",
        'mode_sevenday':        " - Seven Days mode",
        'mode_month':           " - Month mode",
        'mode_unknown':         " - Unknown mode {mode}",
        # Alert labels
        'alert_prefix':         " — Alert(s):",
        'alert_fall':           " fall",
        'alert_nowater':        " no water",
        'alert_leak':           " leak",
        'alert_clog':           " clog",
        'alert_valve':          " valve broken",
        # Errors
        'err_api_error':        "API error for Taplinker {tid}: {msg}",
        'err_api_unexpected':   "Unexpected API result for Taplinker {tid}: {res}",
        'err_http':             "HTTP error calling '{method}': {err}",
    },
    'fr': {
        # onStart / general
        'onstart':              "onStart appelé",
        'version_ok':           "La version actuelle ({ver}) du plugin Link-Tap est à jour",
        'version_new':          "Une nouvelle version du plugin Link-Tap est disponible : {ver}. Version actuelle : {cur}",
        'version_ahead':        "La version locale ({cur}) est en avance sur la dernière release GitHub ({ver}) — version de développement",
        'version_check_fail':   "Impossible de contacter GitHub pour vérifier la dernière version",
        'max_devices':          "Le maximum de 255 dispositifs par matériel est atteint, impossible d'en créer davantage",
        'device_created':       "Dispositif '{name}' de type '{dtype}' avec l'ID {tid} créé",
        'device_type_unknown':  "Type de dispositif '{dtype}' non implémenté",
        # onHeartbeat
        'heartbeat':            "onHeartbeat appelé",
        'updated_counters':     "Compteurs mis à jour : {name} (ID {tid}) — débit : {vel} l/min, volume : {vol} l, signal : {sig}",
        'updated_status':       "Statut mis à jour : {name} (ID {tid}) — {status}",
        # onCommand
        'command_received':     "onCommand appelé pour le dispositif {unit} : commande='{cmd}', niveau={lvl}",
        'command_ok':           "Commande envoyée avec succès au Taplinker {tid}",
        'level_unknown':        "Niveau inconnu reçu ({lvl}) pour le dispositif id {unit}",
        'command_unknown':      "Commande inconnue reçue ('{cmd}') pour le dispositif id {unit}",
        # Watering status
        'watering':             "Arrosage",
        'idle':                 "Inactif",
        # Work modes
        'mode_manual':          " - Mode manuel",
        'mode_interval':        " - Mode intervalles",
        'mode_oddeven':         " - Mode pair/impair",
        'mode_sevenday':        " - Mode 7 jours",
        'mode_month':           " - Mode mensuel",
        'mode_unknown':         " - Mode inconnu {mode}",
        # Alert labels
        'alert_prefix':         " — Alerte(s) :",
        'alert_fall':           " chute",
        'alert_nowater':        " manque d'eau",
        'alert_leak':           " fuite",
        'alert_clog':           " obstruction",
        'alert_valve':          " valve défectueuse",
        # Errors
        'err_api_error':        "Erreur API pour le Taplinker {tid} : {msg}",
        'err_api_unexpected':   "Résultat API inattendu pour le Taplinker {tid} : {res}",
        'err_http':             "Erreur HTTP lors de l'appel '{method}' : {err}",
    },
}

def _get_lang():
    """Return the two-letter language code from Domoticz settings, defaulting to 'en'."""
    try:
        lang = Settings["Language"].lower()[:2]
    except Exception:
        lang = 'en'
    return lang if lang in STRINGS else 'en'

def _(key, **kwargs):
    """Translate *key* for the current Domoticz language, falling back to English."""
    lang = _get_lang()
    template = STRINGS[lang].get(key) or STRINGS['en'].get(key, key)
    return template.format(**kwargs) if kwargs else template


# ---------------------------------------------------------------------------
# Plugin
# ---------------------------------------------------------------------------

class BasePlugin:
    enabled = False

    def __init__(self):
        self.version = '2.00'
        self.timer = 0
        self.token = {}
        self.url = 'https://www.link-tap.com/api/'
        self.taplinkers = {}        # All taplinkers by id
        self.devices = {}           # Cross-reference between Link-Tap IDs and Domoticz unit numbers
        self.gateways = {}          # Gateway each taplinker is attached to
        self.updateNeeded = {}      # Taplinkers that need a status update
        self.types = {
            'flow':   '-243-30',
            'volume': '-243-33',
            'modes':  '-244-62',
            'status': '-243-22',
            'on-off': '-244-73',
        }
        self.headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        self.getAllDevices = {'devices': []}  # Safe default before first API call

    # ------------------------------------------------------------------
    # Domoticz callbacks
    # ------------------------------------------------------------------

    def onStart(self):
        # Rate limiting is in place at Link-Tap; highest allowed frequency is 15 s
        Domoticz.Heartbeat(15)
        self.token = {
            'username': Parameters["Username"],
            'apiKey':   Parameters['Password'],
        }
        Domoticz.Debugging(int(Parameters["Mode6"]))
        Domoticz.Debug(_('onstart'))
        self.CreateDevices()
        self.CheckVersion()

    def onStop(self):
        Domoticz.Debug("onStop called")

    def onCommand(self, Unit, Command, Level, Hue):
        dtype = '-' + str(Devices[Unit].Type) + '-' + str(Devices[Unit].SubType)
        taplinkerId = Devices[Unit].DeviceID
        Domoticz.Debug(_('command_received', unit=Unit, cmd=Command, lvl=Level))

        if dtype == self.types['modes']:
            mode_map = {10: "activateIntervalMode", 20: "activateOddEvenMode",
                        30: "activateSevenDayMode", 40: "activateMonthMode"}
            if Level not in mode_map:
                Domoticz.Error(_('level_unknown', lvl=Level, unit=Unit))
                return
            method = mode_map[Level]
            payload = {**self.token, 'gatewayId': self.gateways[taplinkerId], 'taplinkerId': taplinkerId}
            result = self._api_post(method, payload)
            if result is None:
                return
            if result.get('result') == 'ok':
                Domoticz.Log(_('command_ok', tid=taplinkerId))
                self.updateNeeded[taplinkerId] = True
            elif result.get('result') == 'error':
                Domoticz.Error(_('err_api_error', tid=taplinkerId, msg=result.get('message', '')))
            else:
                Domoticz.Error(_('err_api_unexpected', tid=taplinkerId, res=result.get('result', '')))

        elif dtype == self.types['on-off']:
            if Command == 'On':
                switch = True
            elif Command == 'Off':
                switch = False
            else:
                Domoticz.Error(_('command_unknown', cmd=Command, unit=Unit))
                return
            duration = int(Parameters["Mode2"])
            if not (1 <= duration <= 1439):
                duration = 1439
            payload = {
                **self.token,
                'gatewayId':   self.gateways[taplinkerId],
                'taplinkerId': taplinkerId,
                'action':      switch,
                'duration':    duration,
                'autoBack':    Parameters["Mode1"] == "true",   # API expects a real boolean
            }
            result = self._api_post("activateInstantMode", payload)
            if result is None:
                return
            if result.get('result') == 'ok':
                Domoticz.Log(_('command_ok', tid=taplinkerId))
                Devices[Unit].Update(nValue=int(switch), sValue='On' if switch else 'Off')
                self.updateNeeded[taplinkerId] = True
            elif result.get('result') == 'error':
                Domoticz.Error(_('err_api_error', tid=taplinkerId, msg=result.get('message', '')))
            else:
                Domoticz.Error(_('err_api_unexpected', tid=taplinkerId, res=result.get('result', '')))

    def onHeartbeat(self):
        self.timer += 1
        Domoticz.Debug(_('heartbeat'))

        if self.timer % 480 == 0:
            self.CheckVersion()  # Every 2 hours

        if self.timer % 20 == 0:
            # Rate limit: 5-minute minimum on getAllDevices
            self.CreateDevices()

        if self.timer % 2 == 0:
            # Rate limit: 30-second minimum on getWateringStatus (during active watering)
            for gateway in self.getAllDevices.get('devices', []):
                for taplinker in gateway.get('taplinker', []):
                    taplinkerId = taplinker['taplinkerId']

                    # Only poll taplinkers that have at least one device in Domoticz
                    if not (taplinkerId + self.types['flow']   in self.devices or
                            taplinkerId + self.types['volume'] in self.devices or
                            taplinkerId + self.types['status'] in self.devices):
                        continue

                    result = self._api_post('getWateringStatus',
                                            {**self.token, 'taplinkerId': taplinkerId})
                    if result is None:
                        continue  # HTTP error already logged; try next taplinker

                    if result.get('result') == 'error':
                        Domoticz.Error(_('err_api_error', tid=taplinkerId, msg=result.get('message', '')))
                        continue
                    elif result.get('result') != 'ok':
                        Domoticz.Error(_('err_api_unexpected', tid=taplinkerId, res=result.get('result', '')))
                        continue

                    # Parse watering data
                    vel = 0
                    vol = 0
                    if result.get('status') is not None:
                        vel = round(int(result['status']['vel']) / 1000)
                        vol = round(int(result['status']['vol']) / 1000)
                        currentStatus = _('watering')
                        # Sync On/Off switch if it's out of date
                        onoff_unit = self.devices.get(taplinkerId + self.types['on-off'])
                        if onoff_unit and Devices[onoff_unit].nValue == 0:
                            self.updateNeeded[taplinkerId] = True
                            Devices[onoff_unit].Update(nValue=1, sValue='On')
                    else:
                        currentStatus = _('idle')
                        onoff_unit = self.devices.get(taplinkerId + self.types['on-off'])
                        if onoff_unit and Devices[onoff_unit].nValue == 1:
                            self.updateNeeded[taplinkerId] = True
                            Devices[onoff_unit].Update(nValue=0, sValue='Off')

                    battery = int(taplinker['batteryStatus'][:-1])
                    signal  = int((int(taplinker['signal']) + 5) / 10)

                    flow_unit = self.devices.get(taplinkerId + self.types['flow'])
                    if flow_unit:
                        Devices[flow_unit].Update(nValue=0, sValue=str(vel),
                                                  BatteryLevel=battery, SignalLevel=signal)

                    vol_unit = self.devices.get(taplinkerId + self.types['volume'])
                    if vol_unit and currentStatus == _('watering'):
                        # Don't reset volume counter when idle
                        Devices[vol_unit].Update(nValue=0, sValue=str(vol),
                                                 BatteryLevel=battery, SignalLevel=signal)

                    Domoticz.Log(_('updated_counters', name=taplinker['taplinkerName'],
                                   tid=taplinkerId, vel=vel, vol=vol, sig=taplinker['signal']))

                    if self.updateNeeded.get(taplinkerId):
                        self.UpdateStatus(taplinker, currentStatus)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _api_post(self, method, payload):
        """POST to the Link-Tap API. Returns parsed JSON dict or None on error."""
        try:
            response = requests.post(self.url + method, json=payload,
                                     headers=self.headers, timeout=5)
            response.raise_for_status()
            return json.loads(response.text)
        except Exception as err:
            Domoticz.Error(_('err_http', method=method, err=str(err)))
            return None

    def CreateDevices(self):
        """Synchronise Domoticz devices with the Link-Tap API device list.

        Rate limiting at Link-Tap: minimum 5-minute interval on getAllDevices.
        """
        # Rebuild the local cross-reference from scratch
        self.devices = {}
        for unit in Devices:
            dev = Devices[unit]
            key = dev.DeviceID + '-' + str(dev.Type) + '-' + str(dev.SubType)
            self.devices[key] = unit
            Domoticz.Debug("Existing device: unit={} id={} type={} subtype={} switchtype={}".format(
                unit, dev.DeviceID, dev.Type, dev.SubType, dev.SwitchType))

        # Fetch current topology from the API
        data = self._api_post('getAllDevices', self.token)
        if data is None:
            return
        self.getAllDevices = data

        for gateway in self.getAllDevices.get('devices', []):
            gatewayName = gateway['name']
            for taplinker in gateway['taplinker']:
                taplinkerId = taplinker['taplinkerId']
                self.updateNeeded[taplinkerId] = True
                self.gateways[taplinkerId] = gateway['gatewayId']
                self.taplinkers[taplinkerId] = taplinker['taplinkerName']

                for dtype in self.types:
                    key = taplinkerId + self.types[dtype]
                    if key in self.devices:
                        continue  # Device already exists in Domoticz

                    # Find the lowest available unit number (1-255)
                    used = set(self.devices.values())
                    hole = next((n for n in range(1, 256) if n not in used), None)
                    if hole is None:
                        Domoticz.Error(_('max_devices'))
                        return

                    base_name = gatewayName + " - " + taplinker['taplinkerName']
                    if dtype == 'flow':
                        Domoticz.Device(Name=base_name + ' - Flow',
                                        Unit=hole, Type=243, Subtype=30,
                                        DeviceID=taplinkerId).Create()
                    elif dtype == 'volume':
                        Domoticz.Device(Name=base_name + ' - Volume',
                                        Unit=hole, Type=243, Subtype=33, Switchtype=2,
                                        DeviceID=taplinkerId).Create()
                    elif dtype == 'modes':
                        Options = {
                            "Scenes": "||||",
                            "LevelActions": "||||",
                            "LevelNames": "0|Intervals|Odd-Even|Seven days|Months",
                            "LevelOffHidden": "true",
                            "SelectorStyle": "1",
                        }
                        Domoticz.Device(Name=base_name + " - Watering Modes",
                                        DeviceID=taplinkerId, Image=20,
                                        Unit=hole, Type=244, Subtype=62, Switchtype=18,
                                        Options=Options).Create()
                    elif dtype == 'status':
                        Domoticz.Device(Name=base_name + " - Status",
                                        DeviceID=taplinkerId, Unit=hole,
                                        TypeName='Alert').Create()
                    elif dtype == 'on-off':
                        Domoticz.Device(Name=base_name + " - On/Off",
                                        DeviceID=taplinkerId, Unit=hole,
                                        Type=244, Subtype=73, Switchtype=0, Image=20).Create()
                    else:
                        Domoticz.Error(_('device_type_unknown', dtype=dtype))
                        return

                    self.devices[key] = hole
                    Domoticz.Log(_('device_created', name=base_name,
                                   dtype=dtype, tid=taplinkerId))

    def UpdateStatus(self, taplinker, currentStatus):
        """Update the Status (Alert) device for one taplinker."""
        taplinkerId = taplinker['taplinkerId']
        alert = 1   # 0=Grey 1=Green 2=Greenish-Yellow 3=Orange 4=Red
        alertText = _('alert_prefix')

        if taplinker.get('fall'):
            alert = 4
            alertText += _('alert_fall')
        if taplinker.get('noWater'):
            alert = 4
            alertText += _('alert_nowater')
        if taplinker.get('leakFlag'):
            alert = 4
            alertText += _('alert_leak')
        if taplinker.get('clogFlag'):
            alert = 4
            alertText += _('alert_clog')
        if taplinker.get('valveBroken'):
            alert = 4
            alertText += _('alert_valve')

        mode_labels = {
            'M': _('mode_manual'),
            'I': _('mode_interval'),
            'O': _('mode_oddeven'),
            'T': _('mode_sevenday'),
            'N': _('mode_month'),
        }
        workMode = taplinker.get('workMode', '')
        currentStatus += mode_labels.get(workMode, _('mode_unknown', mode=workMode))

        if alert == 4:
            currentStatus += alertText

        status_unit = self.devices.get(taplinkerId + self.types['status'])
        if status_unit:
            battery = int(taplinker['batteryStatus'][:-1])
            signal  = int((int(taplinker['signal']) + 5) / 10)
            Devices[status_unit].Update(nValue=alert, sValue=currentStatus,
                                        SignalLevel=signal, BatteryLevel=battery)
            Domoticz.Log(_('updated_status', name=taplinker['taplinkerName'],
                           tid=taplinkerId, status=currentStatus))

        self.updateNeeded[taplinkerId] = False

    @staticmethod
    def _parse_version(v):
        """Convert a version string like '2.00' or '0.2' to a comparable tuple of ints.
        Non-numeric segments are treated as 0 so that malformed tags don't raise."""
        try:
            return tuple(int(x) for x in str(v).strip().lstrip('v').split('.'))
        except ValueError:
            return (0,)

    def CheckVersion(self):
        """Check GitHub releases for a newer version of the plugin.

        Uses numeric version comparison so that a local development build that is
        ahead of the latest published release does not trigger a spurious update alert.
        """
        try:
            response = requests.get(
                'https://api.github.com/repos/DebugBill/Link-Tap/releases/latest',
                headers={'Accept': 'application/vnd.github.v3+json'},
                timeout=5,
            )
            data = json.loads(response.text)
        except Exception:
            Domoticz.Log(_('version_check_fail'))
            return

        if 'tag_name' not in data:
            Domoticz.Log(_('version_check_fail'))
            return

        remote_str = str(data['tag_name'])
        remote = self._parse_version(remote_str)
        local  = self._parse_version(self.version)

        if remote > local:
            Domoticz.Error(_('version_new', ver=remote_str, cur=self.version))
        elif local > remote:
            Domoticz.Log(_('version_ahead', ver=remote_str, cur=self.version))
        else:
            Domoticz.Log(_('version_ok', ver=self.version))


# ---------------------------------------------------------------------------
# Domoticz plugin entry points
# ---------------------------------------------------------------------------

global _plugin
_plugin = BasePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onStop():
    global _plugin
    _plugin.onStop()

def onCommand(Unit, Command, Level, Hue):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Hue)

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()
