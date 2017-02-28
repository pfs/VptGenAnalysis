
from WMCore.Configuration import Configuration
import os
config = Configuration()

config.section_("General")
config.General.requestName = "_REQUEST_"
config.General.workArea = "grid"
config.General.transferOutputs=True

config.section_("JobType")
config.JobType.pluginName = "Analysis"
config.JobType.psetName = "_PSET_"
config.JobType.disableAutomaticOutputCollection = False
config.JobType.pyCfgParams = ['output=_REQUEST_','ueTune=CUEP8M2T4','photos=True','nFinal=2']

config.section_("Data")
config.Data.inputDataset = "_DSET_"
config.Data.inputDBS = "global"
config.Data.splitting = "FileBased"
config.Data.unitsPerJob = 10
config.Data.publication = False
config.Data.ignoreLocality = True
config.Data.outLFNDirBase = '/store/group/phys_top/psilva/Wmass/_REQUEST_'

config.section_("Site")
config.Site.storageSite = "T2_CH_CERN"
