from antelope import orb, Pkt
#from pysnmp.entity.rfc3413.oneliner import ntforb
import logging
from datetime import datetime

logging.basicConfig(level=logging.DEBUG)

ORB_NAME = 'anzaacq.ucsd.edu:status'
ORB_SELECT = '.*/BBA/DC'
UPS_CHANS=['ACFAIL','HAZARD']
STATEFILE='state/dcupsmon'

SNMP_TRAP_RECEIVERS=[
    ['anfmonl.ucsd.edu', 162, 'public'],
]

class EnhancedPacket(Pkt.Packet):
    """wrapper class with better search capabilities for BRTT Pkt.Packet"""

    def __init__(self, srcname=None, time=None, packet=None):
        super(EnhancedPacket, self).__init__(srcname, time, packet)
        self._rehashChannels()

    def _rehashChannels(self):
        #prime the channel name index
        counter=0
        self._chanindex={}
        for chan in self.channels:
            self._chanindex[chan.chan]=counter
            counter += 1

    def unstuff(self, srcname, time, raw_packet):
        """Unstuff a packet using Pkt.Packet.unstuff, then update our state"""
        pkt_type=super(EnhancedPacket, self).unstuff(srcname, time, raw_packet)
        self._rehashChannels()
        return pkt_type

    def getChannelByName(self, channame):
        idx = self._chanindex[channame]
        return self.channels[idx]


class TimestampedValue():
    """Track a value and the time it changed"""

    def __init__(self, value, changetime=datetime.now()):
        # verify that we got passed a datetime object for changedDateTime
        if not isinstance(changetime, datetime):
            raise TypeError(repr(changetime)+" is not a datetime object")
        self.value=value
        self._changed=changetime

    def update(self, value, changetime=datetime.now()):
        # verify that we got passed a datetime object for changedDateTime
        if not isinstance(changetime, datetime):
            raise TypeError(repr(changetime)+" is not a datetime object")
        self.value=value
        self._changed=changetime

    def getChanged(self):
        return _changed

class UpsStateViewer:
    def update(self, subject):
        print subject

class DcupsState(object):
    def __init__(self, name, hazardMinutes=5):
        """constructor for a data concentrator UPS state tracker

        name is the name of the UPS

        hazardMinutes is how many minutes are left of run time when the hazard
        channel is non-zero
        """
        self.name = name
        self._observers = []
        self.hazardMinutes=hazardMinutes

        for c in UPS_CHANS:
            self.__dict__[c]=TimestampedValue(0)

    def __repr__(self):
        return "%s(%r)" % (self.__class__, self.__dict__)

    def __str__(self):
        return "%s %s: hazardMinutes %s, ACFAIL: %s, HAZARD: %s" % (
            self.__class__, self.name, self.hazardMinutes, self.ACFAIL.value,
            self.HAZARD.value)

    def attach(self, observer):
        if not observer in self._observers:
            self._observers.append(observer)

    def detach(self, observer):
        try:
            self._observers.remove(observer)
        except ValueError:
            pass

    def notify(self, modifier=None):
        for observer in self._observers:
            if modifier != observer:
                observer.update(self)

    def update(self, time, **kwargs):
        #logging.debug("got an update: " + str(kwargs))
        changed={}
        if isinstance(time,datetime):
            changetime=time
        else:
            changetime=datetime.fromtimestamp(time)

        for key in kwargs:
            old = self.__dict__[key]
            if old.value != kwargs[key]:
                changed[key]=(old.value, kwargs[key])
                old.update(kwargs[key], changetime)

        if len(changed) > 0:
            logging.debug("Something changed, notifying observers")
            self.notify()


class DcupsMon(object):
    """Monitor an orb for UPS alarms from an SIO Data Concentrator

    Monitors the status packets emitted by the SIO Data Concentrator for
    changes to the ACFAIL and HAZARD fields
    """

    def __init__( self, orbname, select=ORB_SELECT,
        # reject=None,
                ):
        logging.debug("Create new DcupsMon")
        self.state={}
        self.pkt_count = 0

        self.orbname = orbname
        self.select = select
        #self.reject = reject
        self.orb=orb.Orb(orbname, exhume=STATEFILE,
                    auto_bury=True, bury_interval=1)
        self.connect()

    def connect(self):
        self.orb.connect()
        pktid = self.orb.position('oldest')
        #pktid = self.orb.tell()
        num_sources = self.orb.select(self.select)

        logging.info("Connected to %s, %d sources match selection %s" % (
            self.orbname, num_sources, self.orb.select))

    def getDcupsState(self, srcname):
            """ Get the current sourcename's state object """
            try:
                dcupsstate=self.state[srcname]
            except KeyError:
                logging.debug('Initializing state for ' + srcname)
                dcupsstate=DcupsState(srcname)
                dcupsstate.attach(UpsStateViewer())
                self.state[srcname]=dcupsstate

            return dcupsstate


    def reap_once(self, timeout=1):
        pkt = EnhancedPacket()
        pktid, srcname, pkttime, pktbuf = self.orb.reap(timeout=timeout)
        self.pkt_count += 1
        pkt_type = pkt.unstuff(srcname,pkttime,pktbuf)
        if pkt_type == Pkt.Pkt_wf:
            channames = [ chan.chan for chan in pkt.channels ]

            if len(set(UPS_CHANS).intersection(channames)) != len(UPS_CHANS):
                logging.warning('Packet does not contain UPS status')
                return

            # Assume from here on that packet is a DC status packet
            # and that each channel contains the same number of samples at the
            # same data rate.
            # Use a representative channel
            repchan=pkt.getChannelByName(UPS_CHANS[0])
            nsamp = repchan.nsamp
            samprate = repchan.samprate
            time = repchan.time
            dcupsstate=self.getDcupsState(srcname)

            for samp in range(nsamp):
                stime=time + samp*samprate
                kwargs={}
                for c in UPS_CHANS:
                    kwargs[c]=pkt.getChannelByName(c).data[samp]
                dcupsstate.update(stime, **kwargs)
#            for chan in pkt.channels:
#                if chan.chan in UPS_CHANS:
#                    printed = 0
#                    for samp in chan.data:
#                        if samp != s[chan.chan]:
#                            if not printed:
#                                printed = 1
#                                print "pktid: %d time: %s" % (pktid, pkt.time)
#                                print ("%s: %s" % (chan.chan, chan.data))
#
#                            logging.warning('%s %s changed from %d to %d' % (
#                                srcname, chan.chan, s[chan.chan], samp))
#                            s[chan.chan]=samp

if __name__ == "__main__":
    u = DcupsMon(orbname=ORB_NAME,select=ORB_SELECT)

    while True:
        try:
            u.reap_once()
        except orb.OrbIncompleteException:
            print "finished reaping after %d packets" % u.pkt_count
            break
