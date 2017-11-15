import ROOT
import os
import sys
import optparse
import numpy as np
import array

from UserCode.VptGenAnalysis.vecbosKinUtils import *

"""
"""
def parseDataFromTree(opt,histos=None,maxPerc=25):

    #parse the matrix-element weights to store
    wgtList=[]
    try:
        wgtList=[int(wgt) for wgt in opt.wgtList.split(',')]
    except:
        pass
    
    #analyse events in trees
    data=ROOT.TChain('analysis/data')
    if opt.input.find('/store')==0 :
        data.AddFile('root://eoscms//eos/cms/%s'%opt.input)
    else:
        data.AddFile(opt.input)
    nevts=data.GetEntries()
    cut=ROOT.TTreeFormula('cuts',opt.cuts,data)
    print '[parseDataFromTree] with %d'%nevts
    print '\t pre-selection to be applied is %s'%opt.cuts

    #for each event compute variables and store required weights
    nevtsSel=0
    evVals,wgtVals,iniWgtVals=[],[],[]
    lp4=[ROOT.TLorentzVector(0,0,0,0),ROOT.TLorentzVector(0,0,0,0)]
    for i in xrange(0,nevts):
        data.GetEntry(i)

        #print status of the analysis
        perc=float(100.*i)/float(nevts)
        if perc>maxPerc : break
        if i%1000==0 : 
            sys.stdout.write('\r [ %d/%d ] done' %(int(perc),int(maxPerc)))
            sys.stdout.flush()

        mewgts=[]
        if len(wgtList)!=0:
            mewgts=[data.w[iw] for iw in wgtList]
        else:
            mewgts=[data.w[iw] for iw in xrange(0,data.nw)]
        iniwgts=[1]

        #presel events (it may issue a warning which can be safely disregarded)
        #cf https://root.cern.ch/phpBB3/viewtopic.php?t=14213
        if not cut.EvalInstance() : continue

        #fill the lepton kinematics depending on whether it's a W or a Z like candidate
        if data.nl>1:
            for il in xrange(0,2):
                lp4[il].SetPtEtaPhiM(data.pt[il],data.eta[il],data.phi[il],data.m[il])
            if lp4[0].Pt()<20 or lp4[1].Pt()<1 or ROOT.TMath.Abs(lp4[0].Eta())>2.5 or ROOT.TMath.Abs(lp4[1].Eta())>2.5 : continue
        else:
            lp4[0].SetPtEtaPhiM(data.pt[0],data.eta[0],data.phi[0],data.m[0])
            lp4[1].SetPtEtaPhiM(data.nusum_pt,data.nusum_eta,data.nusum_phi,0.)
            if lp4[0].Pt()<20 or ROOT.TMath.Abs(lp4[0].Eta())>2.5 : continue

        nevtsSel+=1

        #charge selection
        if opt.charge!=0 and data.charge[0]!=opt.charge : continue

        #lepton kinematics
        varVals=[lp4[0].Pt(), lp4[0].Rapidity(), lp4[1].Pt(), lp4[1].Rapidity()]

        #vector boson kinematics
        vpt = lp4[0]+lp4[1]
        varVals += [vpt.M(), vpt.Pt(), vpt.Rapidity()]

        #MET and transverse mass
        met=ROOT.TLorentzVector(0,0,0,0)
        met.SetPtEtaPhiM(data.genmet_pt,data.genmet.eta,data.genmet_phi,0.)
        varVals += [ met.Pt(), calcMt(p1=lp4[0],p2=met) ]

        if histos:
            for iv in xrange(0,len(varVals)):
                for iw in xrange(0,len(mewgts)):
                    for ip in xrange(0,len(iniwgts)):                   
                        key=(iv,iw,ip)
                        val=varVals[iv]
                        wgt=mewgts[iw]*iniwgts[ip]
                        histos[key].Fill(val,wgt)
        else:
            evVals.append( varVals )
            wgtVals.append( mewgts )
            iniWgtVals.append( iniwgts )

    print '[parseDataFromTree] %d events pre-selected'%nevtsSel

    #all done here
    return (evVals,wgtVals,iniWgtVals)

"""
"""
def fillHistos(opt) :

    allHistos={}

    #open file with template histograms or scan a couple of events to determine binning
    data=None
    fTempl=None
    try:
        fTempl=ROOT.TFile.Open(opt.templ)
        print '[fillHistos] using templates from %s'%fTempl.GetName()

        for obj in fTempl.GetListOfKeys():
            keyName=obj.GetName()
            var,wgt,iniWgt = keyName.split('_')
            if opt.templMode==2 and not var in ['v1','v4','v10'] : continue
            key=(int(var.replace('v','')),int(wgt.replace('w','')),int(iniWgt.replace('p','')))
            allHistos[key]=fTempl.Get(keyName).Clone()
            allHistos[key].Reset('ICE')
            allHistos[key].SetDirectory(0)
    except:
        pass

    data=parseDataFromTree(opt,maxPerc=50.0,histos=None)
    print '[fillHistos] defining templates for %d variables and %d selected events'%(len(data[0][0]),len(data[0]))

    #compute quantiles for n bins
    q     = [i for i in xrange(0,opt.nbins)] if data else None
    qVals = np.percentile(np.array(data[0]),q, axis=0).T if data else None

    #define binnings for the histos        
    for iv in xrange(0,len(data[0][0])):

        #bin definition for this variable
        binDef=[val for val in np.unique(qVals[iv]) if not np.isnan(val) ]

        for iw in xrange(0,len(data[1][0])):
            for ip in xrange(0,len(data[2][0])):

                #start new histo (from template if available, otherwise use quantiles)
                key=(iv,iw,ip)
                if key in allHistos: continue

                keyName='v%d_w%d_p%d'%(iv,iw,ip)
                allHistos[key]=ROOT.TH1F(keyName,'%s;;Events / bin'%keyName,len(binDef)-1,array.array('d',binDef))
                allHistos[key].Sumw2()
                allHistos[key].SetDirectory(0)


    #fill histos 
    parseDataFromTree(opt,maxPerc=100,histos=allHistos)

    #get initial sum of weights for normalization
    fIn=ROOT.TFile.Open('root://eoscms//eos/cms/%s'%opt.input)
    sumw=fIn.Get('analysis/weights')
    sumw.SetDirectory(0)
    fIn.Close()

    #write histos to file
    fOut=ROOT.TFile.Open(opt.output,'RECREATE')
    for key in allHistos:         
        totalWeights=sumw.GetBinContent(key[1]+1)
        if totalWeights==0:
            print 'Skipping',key,'sum weights=0'
            continue
        for xbin in xrange(1,allHistos[key].GetNbinsX()+1):
            binw=allHistos[key].GetXaxis().GetBinWidth(xbin)*totalWeights
            allHistos[key].SetBinContent(xbin, allHistos[key].GetBinContent(xbin)/binw )
            allHistos[key].SetBinError  (xbin, allHistos[key].GetBinError(xbin)/binw )            
        allHistos[key].SetDirectory(fOut)
        allHistos[key].Write()
    fOut.Close()

    #all done here
    print '[fillHistos] %d results can be found in %s'%(len(allHistos),opt.output)



"""
"""
def main():

    #configuration
    usage = 'usage: %prog [options]'
    parser = optparse.OptionParser(usage)
    parser.add_option('-i', '--in',     dest='input',   help='input file [%default]',       default='/store/cmst3/user/psilva/Wmass/ntuples/ZJ_central/ZJ_central.root', type='string')
    parser.add_option(      '--nbins',  dest='nbins',   help='n bins [%default]',           default=100,                                                       type=int)
    parser.add_option('-o', '--out',    dest='output',  help='output file [%default]',      default='ZJ_central.root',                                        type='string')
    parser.add_option('-c', '--cuts',   dest='cuts',    help='simple cuts to apply to the tree [%default]', default='nl==2',                                  type='string')
    parser.add_option('-w', '--wgt',    dest='wgtList', help='weight list (csv)[%default]', default='',                                                       type='string')
    parser.add_option(      '--iniWgt', dest='iniWgt',  help='include initial state weights [%default]', default=False,                                       action='store_true')
    parser.add_option(      '--templ',  dest='templ',   help='histogram templates (keep binning) [%default]', default=None,                                   type='string')
    parser.add_option(      '--templMode',  dest='templMode',   help='1=use all histos, 2=recycle only Vpt [%default]', default=1,                            type=int)
    parser.add_option(      '--charge',    dest='charge', help='charge selector [%default]', default=0, type=int)
    (opt, args) = parser.parse_args()

    fillHistos(opt)

"""
for execution from another script
"""
if __name__ == "__main__":
    sys.exit(main())
