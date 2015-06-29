"""
read_baler44_status_page

Retrieve and organize Baler44 status details via http

Originally based on a Perl script by Allan Sauter and Juan Reyes

Rewritten by Geoff Davis <geoff@ucsd.edu> to use Grequests
"""

#from antelope import datascope
from antelope.datascope import dbopen, closing, freeing, \
        dbDATABASE_NAME, dbTABLE_NAME, dbTABLE_PRESENT, DatascopeError
from antelope.stock import now, epoch2str
import logging
from anf.eloghandler import ElogHandler
import sys
import argparse
import grequests
import re
from collections import defaultdict
import json

EXIT_NOSTATIONS=10
EXIT_DBERROR=11
EXIT_JSONERROR=12

logging.basicConfig()

class BalerException(Exception):
    """base class for our exceptions"""
    pass

class BalerError(BalerException):
    """base class for errors"""
    pass

class BalerJSONWriteError(BalerError):
    """problem with writing the JSON files"""
    pass

class BalerNoTableError(BalerError):
    """Required Database table not found"""
    def __init(self,dbname,tablename):
        self.dbname = dbname
        self.tablename = tablename
        self.msg = 'Required database table %s.%s not found' % (dbname,
                                                                tablename)

class BalerStations():
    """List of stations with Baler44s installed"""

    all_known_stations=[]
    stations={}

    def __init__(self, dbmaster, loglevel=logging.INFO, select=None,
                 reject=None):
        self.dbmaster = dbmaster
        self.loglevel = loglevel
        self.select = select
        self.reject = reject

        self.logger=logging.getLogger(__name__)
        self.logger.setLevel(loglevel)

        self.update()

    def update(self):
        """Update the list of stations from the dbmaster"""

        self.logger.debug('Opening ' + self.dbmaster + ':')
        with closing(dbopen(self.dbmaster, 'r')) as db:
            self.stations=self._get_stations_from_db(db)

    def _get_stations_from_db(self, db):
        """ Get the list of valid stations from the db

        TODO: once dbmaster is modified, we need to get the real baler TCP.
        We currently use the default of 5381
        """

        ipms = r'(?P<ip>[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}):[\d]{1,5}'
        ipre = re.compile(ipms)
        stations=defaultdict(dict)
        deployment = self._tablelookup(db, 'deployment') # was db_on
        stabaler = self._tablelookup(db, 'stabaler')     # was db_sta
        staq330 = self._tablelookup(db, 'staq330')       # was db_ip

        sstr='stabaler.model =~ /PacketBaler44/ && endtime == NULL'
        self.logger.debug('dbsubset("%s")' % sstr)
        with freeing(stabaler.subset(sstr)) as balers:
            # was db_1
            if balers.record_count == 0:
                self.logger.warning('No records found')
                return {}
            for br in balers.iter_record():
                (dlsta,net,sta) = br.getv('dlsta', 'net', 'sta')

                self.logger.debug('[%s] [%s] [%s]' % (dlsta,net,sta))
                stations[sta]['dlsta']  = dlsta
                stations[sta]['sta']    = sta
                stations[sta]['net']    = net
                stations[sta]['status'] = 'Decom'
                stations[sta]['ip']     = 0
                stations[sta]['bport']  = 5381 # default baler port

        # For whatever reason, the original script dumped a JSON file with a
        # list of all valid stations, with no other information other than
        # that, and prior to subsetting.. Save that as a list so that we can
        # replicate the functionality.
        self.all_known_stations=stations.keys()

        # subset stations
        for sta in stations.keys():
            if self.select:
                if not re.match(self.select, sta):
                    del(stations[sta])
            if self.reject:
                if re.match(self.reject, sta):
                    del(stations[sta])

        for sta in stations.keys():
            s='sta == "%s" && snet == "%s" && endtime == NULL'
            deployment.record=-1
            if deployment.find(s % (sta, stations[sta]['net'])):

                stations[sta]['status'] = 'Active'

                if stations[sta]['status'] == 'Decom':
                    next

                self.logger.debug(sta + ' set to "Active"')

            # Get IP for station
            staq330.record=-1
            recordid = staq330.find('dlsta == "%s" && endtime == NULL' %
                                    stations[sta]['dlsta'])

            if recordid >=0:
                self.logger.debug(staq330)
                staq330.record=recordid
                inp = staq330.getv('inp')
                inp=inp[0]

                self.logger.debug('%s inp=>%s' % (sta, inp))

                try:
                    m=ipre.match(inp)
                    ip = m.group('ip')
                    if ip:
                        stations[sta]['ip']=ip
                except TypeError as e:
                    self.logger.critical('No value for inp for ' + sta)


            self.logger.info('%(dlsta)s:  %(status)s %(ip)s' % (stations[sta]))

        return stations

    def _tablelookup(self, db, tablename):
        """open a view and verify that it has records"""

        self.logger.debug('Lookup %s table...'%tablename)
        dbtableview = db.lookup(table=tablename)
        dbname = dbtableview.query(dbDATABASE_NAME)
        tablename=dbtableview.query(dbTABLE_NAME)
        self.logger.debug('Verify database table: %s.%s' % (dbname, tablename))

        tablepresent=dbtableview.query(dbTABLE_PRESENT)
        if not tablepresent:
            self.logger.critical('%s.%s table not available' % (dbname, tablename))
            raise BalerNoTableError(dbname, tablename)
        self.logger.debug('%s.%s table OK' % (dbname,tablename))
        return dbtableview

class BalerDownloader():
    """Class to download data from Balers using GRequests"""
    def __init__(self, dlsta, net, sta, ip, port, loglevel=logging.INFO):
        self.loglevel=loglevel
        self.dlsta=dlsta
        self.net=net
        self.sta=sta
        self.ip=ip
        self.port=port

        self.logger=logging.getLogger(__name__)
        self.logger.setLevel(loglevel)

    def url(self):
        return 'http://%s:%s/stats.html' % (self.ip, self.port)

    def responseHandler(self,r,*args,**kwargs):
        """callback function to update baler information

        The grequests library uses the requests library under the hook. Making
        a request results in a Response object being passed to this callback.
        """
        self.logger.info("BalerDownloader(%s): Got a response for %s" % (
            self.dlsta, r.url))

    def request(self):
        """Generate an AsyncRequest with a callback to this object

        The returned object is suitable for use by the grequests.map()
        function.
        """
        return grequests.get(url=self.url(), callback=self.responseHandler)

def main(argv=sys.argv):
    logger = logging.getLogger()
    # Remove the default handler and add ours
    logger.handlers=[]
    handler = ElogHandler()
    logger.addHandler(handler)

    # Set the logging level
    logger.setLevel(logging.INFO)

    parser = argparse.ArgumentParser('retrieve baler44 status details')
    parser.add_argument('output_dir', help='directory to store status data')
    parser.add_argument('dbmaster', help='Antelope dbmaster path')
    parser.add_argument('--debug', '-d', action='store_true', help='Debug mode')
    parser.add_argument('--select', '-s', default=None, help='Process only stations matching this regular expression')
    parser.add_argument('--reject', '-r', default=None, help='Do not process stations matching this regular expression')
    args=parser.parse_args()

    if args.debug == True:
        logger.setLevel(logging.DEBUG)

    logger.debug("logging level set to "+str(logger.level))

    try:
        bs=BalerStations(args.dbmaster,
                         loglevel=logger.level,
                         select=args.select,
                         reject=args.reject)

        make_baler44_status_json(args.output_dir, bs.all_known_stations)
        retrieve_status_from_balers(bs.stations)
    except BalerException as e:
        logger.exception('A problem with baler processing:')
        return(EXIT_NOSTATIONS)
    except DatascopeError as e:
        logger.exception('A problem with the database occured:')
        return(EXIT_DBERROR)
    except BalerJSONWriteError as e:
        logger.exception('Could not write one of the JSON files out:')
        return(EXIT_JSONERROR)

    # If we make it here everything went well.
    return(0)

def make_baler44_status_json(output_dir, stations):
    """dump a list of all stations with Balers to baler44_status.json

    @throws BalerJSONWriteError
    """
    fname=os.path.join(output_dir, 'baler44_status.json')
    logging.debug('Prepare JSON file: ' + fname)

    out={
        'updated': epoch2str(now(),'%Y-%m-%d %H:%M:%S'),
        'stations': stations,
    }
    # TODO: actually write this to a file
    print json.dumps(out, indent=4)

def retrieve_status_from_balers(stations, poolsize=100):
    """request status pages from stations"""

    downloaders = [BalerDownloader(net=stations[s]['net'],
                                   sta=stations[s]['sta'],
                                   dlsta=stations[s]['dlsta'],
                                   ip=stations[s]['ip'],
                                   port=stations[s]['bport']) for s in stations.keys()]

    reqs = [dl.request() for dl in downloaders]

    print reqs
    responses = grequests.map(reqs, poolsize)

if __name__ == '__main__':
    sys.exit(main())
