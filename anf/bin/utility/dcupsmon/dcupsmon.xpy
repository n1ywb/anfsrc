from antelope import orb, Pkt
#from pysnmp.entity.rfc3413.oneliner import ntforb
import logging
from collections import defaultdict

logging.basicConfig(level=logging.DEBUG)

ORB_NAME = 'anzaacq:status'
ORB_SELECT = '.*/BBA/DC'
UPS_CHANS=['ACFAIL','HAZARD']
STATEFILE='state/dcupsmon'

SNMP_TRAP_RECEIVERS=[
    ['anfmonl.ucsd.edu', 162, 'public'],
]

def _stationStateFactory():
    return dict.fromkeys(UPS_CHANS, 0)


class DCUPSMon(object):
    """Monitor SIO Data Concentrator for UPS alarms

    Monitors the status packets emitted by the SIO Data Concentrator for changes to the
    ACFAIL and HAZARD fields
    """

    def __init__(
        self,
        orbname,
        select=ORB_SELECT,
        # reject=None,
    ):
        self.state=defaultdict(_stationStateFactory)
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

    def reap_once(self, timeout=1):
        pkt = Pkt.Packet()
        pktid, srcname, pkttime, pktbuf = self.orb.reap(timeout=timeout)
        self.pkt_count += 1
        pkt_type = pkt.unstuff(srcname,pkttime,pktbuf)
        if pkt_type == Pkt.Pkt_wf:
            channames = [ chan.chan for chan in pkt.channels ]

            if len(set(UPS_CHANS).intersection(channames)) != len(UPS_CHANS):
                logging.warning('Packet does not contain UPS status')
                return

            # Assume from here on that packet is a DC status packet
            s=self.state[srcname]
            for chan in pkt.channels:
                if chan.chan in UPS_CHANS:
                    printed = 0
                    for samp in chan.data:
                        if samp != s[chan.chan]:
                            if not printed:
                                printed = 1
                                print "pktid: %d time: %s" % (pktid, pkt.time)
                                print ("%s: %s" % (chan.chan, chan.data))

                            logging.warning('%s %s changed from %d to %d' % (
                                srcname, chan.chan, s[chan.chan], samp))
                            s[chan.chan]=samp

if __name__ == "__main__":
    u = DCUPSMon(orbname=ORB_NAME,select=ORB_SELECT)

    while True:
        try:
            u.reap_once()
        except orb.OrbIncompleteException:
            print "finished reaping after %d packets" % u.pkt_count
            break
