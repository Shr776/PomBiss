# -*- coding: utf-8 -*-
"""
SatfinderScan.py - Satfinder with PomBiss integration
بر اساس الگوی pli.py
"""

from enigma import eDVBResourceManager, eDVBFrontendParametersSatellite
from Screens.ScanSetup import ScanSetup, buildTerTransponder
from Screens.ServiceScan import ServiceScan
from Screens.MessageBox import MessageBox
from Components.Sources.FrontendStatus import FrontendStatus
from Components.ActionMap import ActionMap
from Components.NimManager import nimmanager, getConfigSatlist
from Components.config import config, ConfigSelection, getConfigListEntry
from Components.TuneTest import Tuner
from Components.SystemInfo import SystemInfo
from Tools.BoundFunction import boundFunction
from Plugins.Plugin import PluginDescriptor

nim = nimmanager.getNimListOfType('DVB-S')


class PomBissScan(ScanSetup, ServiceScan):
    """Inherits StaticText [key_red] and [key_green] properties from ScanSetup"""
    
    def __init__(self, session, **kwargs):
        self.initcomplete = False
        service = session and session.nav.getCurrentService()
        feinfo = service and service.frontendInfo()
        self.frontendData = feinfo and feinfo.getAll(True)
        del feinfo
        del service
        
        self.typeOfTuningEntry = None
        self.raw_channel = None
        self.systemEntry = None
        self.satfinderTunerEntry = None
        self.satEntry = None
        self.typeOfInputEntry = None
        self.DVB_TypeEntry = None
        self.systemEntryTerr = None
        self.frontend = None
        self.is_id_boolEntry = None
        self.t2mi_plp_id_boolEntry = None
        
        ScanSetup.__init__(self, session)
        self.setTitle(_('PomBiss Scan'))
        self['Frontend'] = FrontendStatus(
            frontend_source=lambda: self.frontend,
            update_interval=100
        )
        self['actions'] = ActionMap(
            ['SetupActions', 'ColorActions'],
            {
                'save': self.keyGoScan,
                'ok': self.keyGoScan,
                'cancel': self.keyCancel
            },
            -3
        )
        self.initcomplete = True
        
        try:
            self.session.postScanService = self.session.nav.getCurrentlyPlayingServiceOrGroup()
        except:
            self.session.postScanService = self.session.nav.getCurrentlyPlayingServiceReference()
        
        self.onClose.append(self.__onClose)
        self.onShow.append(self.prepareFrontend)
    
    def openFrontend(self):
        res_mgr = eDVBResourceManager.getInstance()
        if res_mgr:
            self.raw_channel = res_mgr.allocateRawChannel(self.feid)
            if self.raw_channel:
                self.frontend = self.raw_channel.getFrontend()
                if self.frontend:
                    return True
        return False
    
    def prepareFrontend(self):
        self.frontend = None
        if not self.openFrontend():
            self.session.nav.stopService()
            if not self.openFrontend():
                if self.session.pipshown:
                    from Screens.InfoBar import InfoBar
                    if InfoBar.instance:
                        if hasattr(InfoBar.instance, 'showPiP'):
                            InfoBar.instance.showPiP()
                    if not self.openFrontend():
                        self.frontend = None
        self.tuner = Tuner(self.frontend)
        self.retune()
    
    def __onClose(self):
        self.session.nav.playService(self.session.postScanService)
    
    def newConfig(self):
        cur = self['config'].getCurrent()
        if cur in (self.typeOfTuningEntry, self.systemEntry, self.typeOfInputEntry,
                   self.DVB_TypeEntry, self.satEntry):
            self.createSetup()
            self.retune()
        elif cur == self.satfinderTunerEntry:
            self.feid = int(config.plugins.PomBiss.nimnum.value)
            self.createSetup()
            self.prepareFrontend()
            if self.frontend is None:
                msg = _('Tuner not available.')
                if self.session.nav.RecordTimer.isRecording():
                    msg += _('\nRecording in progress.')
                self.session.open(MessageBox, msg, MessageBox.TYPE_ERROR)
    
    def createSetup(self):
        self.list = []
        self.satfinderTunerEntry = getConfigListEntry(
            _('Tuner'), config.plugins.PomBiss.nimnum
        )
        self.list.append(self.satfinderTunerEntry)
        
        index_to_scan = int(config.plugins.PomBiss.nimnum.value)
        
        try:
        self.DVB_type = self.nim_type_dict[index_to_scan]["selection"]
except:
    # fallback: از nimmanager استفاده کن
    nim = nimmanager.nim_slots[index_to_scan]
    if nim.isCompatible('DVB-S'):
        self.DVB_type = type('obj', (object,), {'value': 'DVB-S'})()
    else:
        self.DVB_type = type('obj', (object,), {'value': 'DVB-S'})()
        
        if self.DVB_type.value == 'DVB-S':
            self.tuning_sat = self.scan_satselection[self.getSelectedSatIndex(self.feid)]
            self.satEntry = getConfigListEntry(_('Satellite'), self.tuning_sat)
            self.list.append(self.satEntry)
            
            self.typeOfTuningEntry = getConfigListEntry(_('Tune'), self.tuning_type)
            self.list.append(self.typeOfTuningEntry)
            self.tuning_type.value = 'single_transponder'
            
            nim = nimmanager.nim_slots[self.feid]
            
            if self.tuning_type.value == 'single_transponder':
                if nim.canBeCompatible('DVB-S2'):
                    self.systemEntry = getConfigListEntry(_('System'), self.scan_sat.system)
                    self.list.append(self.systemEntry)
                else:
                    self.scan_sat.system.value = eDVBFrontendParametersSatellite.System_DVB_S
                
                self.list.append(getConfigListEntry(_('Frequency'), self.scan_sat.frequency))
                self.list.append(getConfigListEntry(_('Polarization'), self.scan_sat.polarization))
                self.list.append(getConfigListEntry(_('Symbol rate'), self.scan_sat.symbolrate))
                self.list.append(getConfigListEntry(_('Inversion'), self.scan_sat.inversion))
                
                if self.scan_sat.system.value == eDVBFrontendParametersSatellite.System_DVB_S:
                    self.list.append(getConfigListEntry(_('FEC'), self.scan_sat.fec))
                elif self.scan_sat.system.value == eDVBFrontendParametersSatellite.System_DVB_S2:
                    self.list.append(getConfigListEntry(_('FEC'), self.scan_sat.fec_s2))
                    self.modulationEntry = getConfigListEntry(_('Modulation'), self.scan_sat.modulation)
                    self.list.append(self.modulationEntry)
                    self.list.append(getConfigListEntry(_('Roll-off'), self.scan_sat.rolloff))
                    self.list.append(getConfigListEntry(_('Pilot'), self.scan_sat.pilot))
        
        self['config'].list = self.list
        self['config'].l.setList(self.list)
    
    def createConfig(self, foo):
        self.tuning_type = ConfigSelection(
            default='single_transponder',
            choices=[('single_transponder', _('PomBiss transponder'))]
        )
        
        self.orbital_position = config.plugins.PomBiss.feedpos.value
        
        ScanSetup.createConfig(self, self.frontendData)
        
        # ذخیره مقادیر از config PomBiss
        self.scan_sat.system.value = eDVBFrontendParametersSatellite.System_DVB_S2
        self.scan_sat.frequency.value = config.plugins.PomBiss.feedfreq.value
        self.scan_sat.symbolrate.value = config.plugins.PomBiss.feedsr.value
        self.scan_sat.inversion.value = eDVBFrontendParametersSatellite.Inversion_Unknown
        
        try:
            self.scan_sat.fec_s2.value = eDVBFrontendParametersSatellite.FEC_Auto
        except:
            self.scan_sat.fec_s2.value = eDVBFrontendParametersSatellite.FEC_3_4
        
        self.scan_sat.modulation.value = eDVBFrontendParametersSatellite.Modulation_8PSK
        
        # پلاریزاسیون
        if config.plugins.PomBiss.feedpol.value == 0:
            self.scan_sat.polarization.value = eDVBFrontendParametersSatellite.Polarisation_Horizontal
        else:
            self.scan_sat.polarization.value = eDVBFrontendParametersSatellite.Polarisation_Vertical
        
        try:
            self.scan_sat.rolloff.value = eDVBFrontendParametersSatellite.RollOff_auto
        except:
            self.scan_sat.rolloff.value = eDVBFrontendParametersSatellite.RollOff_alpha_0_35
        
        self.scan_sat.pilot.value = eDVBFrontendParametersSatellite.Pilot_Unknown
        
        self.feid = int(config.plugins.PomBiss.nimnum.value)
        
        self.satList = []
        self.scan_satselection = []
        for slot in nimmanager.nim_slots:
            if slot.isCompatible('DVB-S'):
                self.satList.append(nimmanager.getSatListForNim(slot.slot))
                self.scan_satselection.append(
                    getConfigSatlist(self.orbital_position, self.satList[slot.slot])
                )
            else:
                self.satList.append(None)
    
    def getSelectedSatIndex(self, v):
        index = 0
        none_cnt = 0
        for n in self.satList:
            if self.satList[index] is None:
                none_cnt += 1
            if index == int(v):
                return index - none_cnt
            index += 1
        return -1
    
    def retuneSat(self):
        if not self.tuning_sat.value:
            return
        
        satpos = int(self.tuning_sat.value)
        
        if self.tuning_type.value == 'single_transponder':
            if self.scan_sat.system.value == eDVBFrontendParametersSatellite.System_DVB_S2:
                fec = self.scan_sat.fec_s2.value
            else:
                fec = self.scan_sat.fec.value
            
            transponder = (
                self.scan_sat.frequency.value,
                self.scan_sat.symbolrate.value,
                self.scan_sat.polarization.value,
                fec,
                self.scan_sat.inversion.value,
                satpos,
                self.scan_sat.system.value,
                self.scan_sat.modulation.value,
                self.scan_sat.rolloff.value,
                self.scan_sat.pilot.value
            )
            
            if self.initcomplete:
                self.tuner.tune(transponder)
            
            self.transponder = transponder
    
    def retune(self, configElement=None):
        if self.DVB_type.value == 'DVB-S':
            self.retuneSat()
    
    def keyGoScan(self):
        self.frontend = None
        try:
            if self.raw_channel:
                del self.raw_channel
        except:
            pass
        
        tlist = []
        
        if self.DVB_type.value == 'DVB-S':
            try:
                self.addSatTransponder(
                    tlist,
                    self.transponder[0],
                    self.transponder[1],
                    self.transponder[2],
                    self.transponder[3],
                    self.transponder[4],
                    self.tuning_sat.orbital_position,
                    self.transponder[6],
                    self.transponder[7],
                    self.transponder[8],
                    self.transponder[9]
                )
                self.startScan(tlist, self.feid)
            except Exception as e:
                self.session.open(
                    MessageBox,
                    _('Scan error: %s') % str(e)[:100],
                    MessageBox.TYPE_ERROR
                )
    
    def startScan(self, tlist, feid):
        flags = 0
        networkid = 0
        self.session.openWithCallback(
            self.startScanCallback,
            ServiceScan,
            [{'transponders': tlist, 'feid': feid, 'flags': flags, 'networkid': networkid}]
        )
    
    def startScanCallback(self, answer=None):
        if answer:
            self.doCloseRecursive()
    
    def keyCancel(self):
        if self.session.postScanService and self.frontend:
            self.frontend = None
            del self.raw_channel
        self.close(False)
    
    def doCloseRecursive(self):
        if self.session.postScanService and self.frontend:
            self.frontend = None
            del self.raw_channel
        self.close(True)


def PomBissScanMain(session, close=None, **kwargs):
    nimList = []
    for n in nimmanager.nim_slots:
        if not n.isCompatible('DVB-S'):
            continue
        if n.config_mode in ('loopthrough', 'satposdepends', 'nothing'):
            continue
        nimList.append(n)
    
    if len(nimList) == 0:
        session.open(MessageBox, _('No satellite tuner configured.'), MessageBox.TYPE_ERROR)
    else:
        session.open(PomBissScan)
