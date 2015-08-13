import os
from antelope import orb, Pkt
#from pysnmp.entity.rfc3413.oneliner import ntforb
import logging
import threading
from datetime import datetime, timedelta

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
        """Return the PktChannel object with chan attribute matching name

        *WARNING* In the case of name collisions, only one channel will be
        returned - the one with the highest index number in the channels tuple.
        """
        idx = self._chanindex[channame]
        return self.channels[idx]

    @Pkt.Packet.channels.setter
    def channels(self,channels):
        super(EnhancedPacket, self).channels(channels)
        self._rehashChannels()

class TimestampedValue(object):
    """Track a value and the time it changed"""

    def __init__(self, value, changetime=datetime.now()):
        # verify that we got passed a datetime object for changedDateTime
        if not isinstance(changetime, datetime):
            raise TypeError(repr(changetime)+" is not a datetime object")
        self.value=value
        self.changed=changetime

    def __set__(self):
        self.update(value)

    def update(self, value, changetime=datetime.now()):
        # verify that we got passed a datetime object for changedDateTime
        if not isinstance(changetime, datetime):
            raise TypeError(repr(changetime)+" is not a datetime object")
        self.value=value
        self.changed=changetime

class UpsStateViewer(object):

    notify_interval=60.0
    def __init__(self):
        self.notifierthread=None

    def update(self, subject):
        print subject
        if subject.isOnBattery():
            self.check_notifier(subject)
        else:
            self.cancel_notifier()
            self.print_offbattery(subject)

    def check_notifier(self, subject):
        """Check and start the notifier thread"""
        if not self.notifierthread or self.notifierthread.isAlive() == False:
            self.notifierthread = TimedExecutor(self.notify_interval,
                                                self.print_onbattery,
                                                True,
                                                [subject])
            self.notifierthread.start()
        else:
            logging.debug('Notifier thread already running for '+subject.name)

    def cancel_notifier(self):
        if self.notifierthread:
            self.notifierthread.cancel()
            self.notifierthread=None

    def print_onbattery(self, subject):
        print "UPS has been on battery for %s seconds." % subject.timeOnBattery()
        timeleft=subject.runtimeleft()
        if timeleft:
            print "UPS has %s remaining runtime" % timeleft
        else:
            print "UPS remaining runtime unknown"

    def print_offbattery(self, subject):
            lastbattery = subject.lastElapsedOnBattery
            if lastbattery:
                print "UPS no longer on battery. Total time on battery: %s" % \
                        lastbattery


class TimedExecutor(threading.Thread):
    """Call a function repeatedly after a specified number of seconds

        t=TimedExecutor(30.0, f, *args=[], **kwargs={})
        t.start()
        t.cancel()
    """
    def __init__(self, interval, function, atstart=False, args=[], kwargs={}):
        threading.Thread.__init__(self)
        self.interval = interval
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.atstart = atstart
        self.finished = threading.Event()

    def cancel(self):
        """Stop running the repeating task"""
        self.finished.set()

    def run_forever(self):
        while True:
            self.finished.wait(self.interval)
            if self.finished.is_set():
                break
            else:
                self.function(*self.args, **self.kwargs)

    def run(self):
        if self.atstart:
            if not self.finished.is_set():
                self.function(*self.args, **self.kwargs)
        self.run_forever()

class DcupsState(object):
    """Track the state of a UPS as reported by a Data Concentrator

    Expects to see the HAZARD and ACFAIL attributes updated, typically by
    reading from an orbserver and unstuffing packets

    Thread safety: this object will automatically attempt to acquire an
    internal lock for operations involving data reads and writes.
    """
    def __init__(self, name, hazardMinutes=5):
        """constructor for a data concentrator UPS state tracker

        name is the name of the UPS

        hazardMinutes is how many minutes are left of run time when the hazard
        channel is non-zero
        """
        self.lock = threading.RLock()
        self.notifier_lock = threading.RLock()
        self.name = name
        self._observers = []
        self.hazardMinutes=hazardMinutes

        self._onBatteryStart=None
        self.lastElapsedOnBattery=None # last time between ACFAIL on and off

        for c in UPS_CHANS:
            self.__dict__[c]=TimestampedValue(0)

    def __repr__(self):
        with self.rlock:
            return "%s(%r)" % (self.__class__, self.__dict__)

    def __str__(self):
        with self.rlock:
            return "%s %s: hazardMinutes %s, ACFAIL: %s, HAZARD: %s" % (
                self.__class__, self.name, self.hazardMinutes, self.ACFAIL.value,
                self.HAZARD.value)

    def runtimeleft(self):
        """if the UPS is in ACFAIL and the HAZARD is on, report time to shutdown
        Returns a datetime timedelta object
        Otherwise return None
        """
        with self.lock:
            if self.ACFAIL.value > 0 and self.HAZARD.value > 0:
                return datetime.now() - self.HAZARD.changed
            else:
                return None

    def isOnBattery(self):
        with self.lock:
            return self.ACFAIL.value > 0

    def timeOnBattery(self):
        """Returns how long the UPS has been on battery"""
        with self.lock:
            if self.isOnBattery():
                return datetime.now() - self.ACFAIL.changed
            else:
                return timedelta(0)

    def attach(self, observer):
        with self.notifier_lock:
            if not observer in self._observers:
                self._observers.append(observer)

    def detach(self, observer):
        with self.notifier_lock:
            try:
                self._observers.remove(observer)
            except ValueError:
                pass

    def notify(self, modifier=None):
        with self.notifier_lock:
            for observer in self._observers:
                if modifier != observer:
                    observer.update(self)

    def _process_changes(self, changes):
        """Update statistics for state changes"""
        logging.debug("_process_changes: " + str(changes))
        with self.lock:
            try:
                if changes['ACFAIL'][1] > 0:
                    self._onBatteryStart = self.ACFAIL.changed
                elif changes['ACFAIL'][1] == 0:
                    self.lastElapsedOnBattery = self.ACFAIL.changed - \
                            self._onBatteryStart
                    self._onBatteryStart = None
            except KeyError:
                pass

    def update(self, time, modifier=None, **kwargs):
        """Handle an update to state attributes"""

        #logging.debug("got an update: " + str(kwargs))
        changes={}
        if isinstance(time,datetime):
            changetime=time
        else:
            changetime=datetime.fromtimestamp(time)

        for key in kwargs:
            if key not in UPS_CHANS:
                # Make sure we don't update an attribute that we shouldn't
                next

            with self.lock:
                old = self.__dict__[key]
                if old.value != kwargs[key]:
                    changes[key]=(old.value, kwargs[key])
                    old.update(kwargs[key], changetime)

        if len(changes) > 0:
            self._process_changes(changes)
            logging.debug("Something changed, notifying observers")
            self.notify(modifier=modifier)


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
            self.orbname, num_sources, self.select))

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
                dcupsstate.update(time=stime, modifier=self, **kwargs)

if __name__ == "__main__":
    # Always release the GIL with the Antelope bindings
    os.environ['ANTELOPE_PYTHON_GILRELEASE']='1'
    u = DcupsMon(orbname=ORB_NAME,select=ORB_SELECT)

    while True:
        try:
            u.reap_once()
        except orb.OrbIncompleteException:
            print "finished reaping after %d packets" % u.pkt_count
            break
