"""
read_baler44_status_page

Retrieve and organize Baler44 status details via http

Originally based on a Perl script by Allan Sauter and Juan Reyes

Rewritten by Geoff Davis <geoff@ucsd.edu> to use Grequests
"""

#from antelope import datascope
from antelope.datascope import dbopen, closing, freeing, \
        dbDATABASE_NAME, dbTABLE_NAME, dbTABLE_PRESENT, DatascopeError, Dbptr
import logging
from anf.eloghandler import ElogHandler
import sys
import argparse
#import grequests
import re
from collections import defaultdict

EXIT_NOSTATIONS=10
EXIT_DBERROR=11

class BalerException(Exception):
    """base class for our exceptions"""
    pass

class BalerError(BalerException):
    """base class for errors"""
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
        """ Get the list of valid stations from the db"""

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
                stations[sta]['net']    = net
                stations[sta]['status'] = 'Decom'
                stations[sta]['ip']     = 0

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
            if deployment.find(s % (sta, stations[sta]['net'])):

                stations[sta]['status'] = 'Active'

                if stations[sta]['status'] == 'Decom':
                    next

                self.logger.debug(sta + ' set to "Active"')

            # Get IP for station
            recordid = staq330.find('dlsta == "%s" && endtime == NULL' % dlsta)

            if recordid >=0:
                sip=Dbptr(staq330)
                sip.record=recordid

                inp = sip.getv('inp')
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

def main(argv=sys.argv):
    logging.basicConfig()
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
    except BalerException as e:
        logger.exception('A problem with baler processing:')
        return(EXIT_NOSTATIONS)
    except DatascopeError as e:
        logger.exception('A problem with the database occured:')
        return(EXIT_DBERROR)

if __name__ == '__main__':
    sys.exit(main())
