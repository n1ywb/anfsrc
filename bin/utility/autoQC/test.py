#######################################################################
import sys
import os

sys.path.append(os.environ['ANTELOPE'] + '/data/python')

from antelope.stock import pfread, str2epoch, epoch2str, now
from antelope.datascope import dbopen, dbclose, dblookup
from math import pow, fsum, sqrt
import numpy as np

#######################################################################

class QC_Obj:
    def __init__(self,params):     
        self.dbpath = params['dbpath']
        self.sta = params['sta']
        self.chan = params['chan']
        self.time_lag = params['time_lag']
        self.time_window = params['time_window']
        self.RMS_bool = params['RMS_bool']
        self.RMS_range = params['RMS_range']
        self.DC_offset_bool = params['DC_offset_bool']
        self.DC_offset_range = params['DC_offset_range']
        self.linear_trend_bool = params['linear_trend_bool']
        self.linear_trend_range = params['linear_trend_range']
        self.skewness_bool = params['skewness_bool']
        self.QC_network_report = params['QC_network_report']

    def runQC(self):
        print '%s:%s' % (self.sta, self.chan)
        try:
            self.load_trace()
        except LoadTrace_Error as err:
            raise RunQC_Error(err.message)
        if self.DC_offset_bool: self.DC_offset_test()
        if self.RMS_bool: self.RMS_test()        
        if self.linear_trend_bool: self.linear_trend_test()
        if self.skewness_bool: self.skewness_test()
        self.trace.trdestroy()
        print''

    def plot(self):
        import matplotlib.pyplot as plt
        self.load_trace()
        d = self.trace.data()
        m = fsum(d)/len(d)
        rms = sqrt(fsum([pow(val-m,2) for val in d])/len(d))
        
        time,endtime,nsamp = self.trace.getv('time','endtime','nsamp')
#        print len(d),len(np.arange(time,endtime,(endtime-time)/nsamp)),time,endtime,nsamp
        x = np.arange(time,endtime,(endtime-time)/nsamp)
        M,b = np.polyfit(x,d,1)

        plt.plot(x,d,'b-',x,[M*X + b for X in x],'r-')
        plt.show()
        self.trace.trdestroy()
        
    def load_trace(self):
        db = dbopen(self.dbpath,'r')
        vw_wf = db.lookup(table='wfdisc')
        ts = str2epoch(epoch2str(now(),'%Y%j')) - self.time_lag
        te = ts + self.time_window
        i = vw_wf.find('sta =~ /%s/ && chan =~ /%s/ && time <= _%f_ && endtime\
            >= _%f_' % (self.sta, self.chan, ts, te),vw_wf.nrecs(),
            reverse=True)
        if not i < 0:
            vw_wf = vw_wf.list2subset(i)
        else:
            i = vw_wf.nrecs()
            recs = []
            while not i < 0:
                i = vw_wf.find('sta =~ /%s/ && chan =~ /%s/ && time <= _%f_ &&\
                    endtime >= _%f_' % (self.sta,self.chan,te,ts),i,
                    reverse=True)
                if not i < 0:
                    recs.append(i)
                elif len(recs) == 0:
                    raise LoadTrace_Error('No records found in wfdisc for %s:%s' \
                        % (self.sta, self.chan))
                    return 0
            vw_wf = vw_wf.list2subset(recs)

        tr = vw_wf.loadchan(ts,te,self.sta,self.chan)
        tr.record = 0
        tr.apply_calib()
        self.trace = tr
        db.close()

    def DC_offset_test(self):
        d = self.trace.data()
        m = fsum(d)/len(d)
        if m < self.DC_offset_range[0] or m > self.DC_offset_range[1]:
            params['message'] = 'DC offset test failed. DC offset = %.3f' % m
            params['sta'] = self.sta
            params['chan'] = self.chan
            self.QC_network_report.add_issue(QC_Issue(params))

    def RMS_test(self):
        d = self.trace.data()
        m = fsum(d)/len(d)
        rms = sqrt(fsum([pow(val-m,2) for val in d])/len(d))
        if rms < self.RMS_range[0] or rms > self.RMS_range[1]:
            params['message'] = 'RMS test failed. RMS = %.3f' % rms
            params['sta'] = self.sta
            params['chan'] = self.chan
            self.QC_network_report.add_issue(QC_Issue(params))

    def linear_trend_test(self):
        d = self.trace.data()
        time,endtime,nsamp = self.trace.getv('time','endtime','nsamp')
        m,b = np.polyfit(np.arange(time,endtime,(endtime-time)/nsamp),d,1)
        if m < self.linear_trend_range[0] or m > self.linear_trend_range[1]:
            params['message'] = 'Linear trend test failed. Slope = %.3f' % m
            params['sta'] = self.sta
            params['chan'] = self.chan
            self.QC_network_report.add_issue(QC_Issue(params))
#        else: print '%s:%s Slope - %.3f',
        
    def skewness_test(self):
        tr = self.trace.trcopy()
        tr.filter('BW 0.05 4 1.0 4')
        d = tr.data()
        tr.trdestroy()
        std = np.std(d,dtype=np.float64)
        
#        import matplotlib.pyplot as plt
#        plt.plot(d,'b-',[std for val in d],'r-',[-std for val in d],'r-')
#        plt.show()
        print '%s:%s standard deviation - %.3f' % (self.sta,self.chan,std)
        
#######################################################################

class LoadTrace_Error(Exception):
    def __init__(self,message):
        self.message = message
        
#######################################################################

class RunQC_Error(Exception):
    def __init__(self,message):
        self.message = message

#######################################################################

class QC_Issue():
    def __init__(self,params):
        self.message = params['message']
        self.sta = params['sta']
        self.chan = params['chan']

#######################################################################
     
class QC_Station_Report():
    def __init__(self,QC_issue):
        self.sta = QC_issue.sta
        self.QC_issues = [QC_issue]
        
    def append_issue(self,QC_issue):
        self.QC_issues.append(QC_issue)
        
    def summarize(self):
        """Return a string summarizing station wide QC issues, grouped\
        by channel."""
        summary = '%s\n' % self.sta
        current_chan = ''
        for QC_issue in self.QC_issues:
            if not QC_issue.chan == current_chan:
                summary = '%s\t%s\n' % (summary,QC_issue.chan)
                current_chan = QC_issue.chan
            summary = '%s\t\t%s\n' % (summary,QC_issue.message)
        return summary
            

#######################################################################

class QC_Network_Report():
    def __init__(self,email):
        self.QC_station_reports = []
        self.email = email
        
    def add_issue(self,QC_issue):
        if QC_issue.sta not in [QC_sta_rep.sta for QC_sta_rep in \
            self.QC_station_reports]:
                self.add_station_report(QC_Station_Report(
                    QC_issue))
        else:
            self.append_issue(QC_issue)
                
#        if len(self.QC_issues) == 0: self.QC_issues.append(QC_issue)
#        else:
#            try:
#                i = 0
#                while self.QC_issues[i].sta <= QC_issue.sta and i : i = i+1
#                self.QC_issues.insert(i,QC_issue)
#            except IndexError:
#                self.QC_issues.append(QC_issue)

    def add_station_report(self,QC_station_report):
        """Add a new station report to network report"""
        try:
            i = 0
            while self.QC_station_reports[i].sta <= QC_station_report.sta:
                i = i+1
            self.QC_station_reports.insert(i,QC_station_report)
        except IndexError:
            self.QC_station_reports.append(QC_station_report)
    
    def append_issue(self,QC_issue):
        """Append an issue to an existing station report"""
        i = 0
        while not self.QC_station_reports[i].sta == QC_issue.sta: i = i+1
        self.QC_station_reports[i].append_issue(QC_issue)
    
    def summarize(self):
        """Create a Network wide summary of QC issues, grouped by\
        station and channel"""
        summary = 'QC Report for NETWORK - DATE\n\n'
        for QC_station_report in self.QC_station_reports:
            summary = '%s%s\n' % (summary,QC_station_report.summarize())
        return summary

#######################################################################

def get_stachan_list(dbpath,exclude_stachan,time_lag,time_window):
    """Return a dictionary of station:[channels] pairs to be QC'd.
    Ignore station channel pairs in exclude_stachan."""
    if '.*' in exclude_stachan: exclude_all = exclude_stachan.pop('.*')
    else: exclude_all = None
        
    l = len(exclude_stachan)
    i = 1
    st = None
    for key in exclude_stachan:
        if i == 1:
            st = '('
        st = '%ssta !~ /%s/' % (st,key)
        if i < l:
            st = '%s && ' % st
        else:
            st = '%s)' % st
        i = i+1
    for key in exclude_stachan:
        st = '%s || (sta =~ /%s/ && ' % (st,key)
        l = len(exclude_stachan[key])
        i = 1
        for chan in exclude_stachan[key]:
            st = '%schan !~ /%s/' % (st,chan)
            if i < l:
                st = '%s && ' % st
            i = i+1
        st = '%s )' % st
    if exclude_all:
        l = len(exclude_all)
        i=1
        st = '(%s) && (' % st
        for chan in exclude_all:
            st = '%s chan !~ /%s/' % (st,chan)
            if i < l:
                st = '%s &&' % st
            else:
                st = '%s )' % st
            i = i+1
    db = dbopen(dbpath,'r')
    vw_sitechan = db.lookup(table='sitechan')
    ts = str2epoch(epoch2str(now(),'%Y%j')) - time_lag
    te = ts + time_window
    if st:
        vw_sitechan = vw_sitechan.subset('%s && ondate < _%f_ && (offdate > \
            _%f_ || offdate == NULL)' % (st,ts,te))
    stachan = {}
    for vw_sitechan.record in range(vw_sitechan.nrecs()):
        sta = vw_sitechan.getv('sta')[0]
        if sta in stachan:
            chan = vw_sitechan.getv('chan')[0]
            if chan not in stachan[sta]:
                stachan[sta].append(vw_sitechan.getv('chan')[0])
        else:
            stachan[sta] = [vw_sitechan.getv('chan')[0]]
    db.close()
    return stachan

#######################################################################

pf = pfread('autoQC')
QC_network_report = QC_Network_Report(pf['email'])
params = {}
params['dbpath'] = '/anf/ANZA/rt/anza/anza'
params['time_lag'] = pf['time_lag']
params['time_window'] = pf['time_window']
params['RMS_bool'] = pf['RMS_bool']
params['DC_offset_bool'] = pf['DC_offset_bool']
params['linear_trend_bool'] = pf['linear_trend_bool']
params['skewness_bool'] = pf['skewness_bool']
params['QC_network_report'] = QC_network_report
exclude_stachan = eval(pf['exclude_stachan'])
RMS_ranges = pf['RMS_ranges']
RMS_default_range = pf['RMS_default_range']
DC_offset_ranges = pf['DC_offset_ranges']
DC_offset_default_range = pf['DC_offset_default_range']
linear_trend_ranges = pf['linear_trend_ranges']
linear_trend_default_range = pf['linear_trend_default_range']

stachan = get_stachan_list(params['dbpath'],exclude_stachan,params['time_lag'],
    params['time_window'])

objs = []

for sta in stachan:
    params['sta'] = sta
    params['RMS_range'] = eval(RMS_ranges[sta]) if sta in RMS_ranges else \
        eval(RMS_default_range)
        
    params['DC_offset_range'] = eval(DC_offset_ranges[sta]) if sta in DC_offset_ranges \
        else eval(DC_offset_default_range)
        
    params['linear_trend_range'] = eval(linear_trend_ranges[sta]) if sta in \
        linear_trend_ranges else eval(linear_trend_default_range)

    for chan in stachan[sta]:
        params['chan'] = chan
        objs.append(QC_Obj(params))
i = 0
for obj in objs:
    if i < 9:
        try:
            obj.runQC()
            #obj.plot()
        except RunQC_Error as err:
            print err.message
    i = i+1
print QC_network_report.summarize()
#for obj in objs: obj.runQC()

print 'Fin.'
