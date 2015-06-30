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
#import atomicfile
from bs4 import BeautifulSoup

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

    _ipms = r'(?P<ip>[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}):[\d]{1,5}'
    re_ip = re.compile(_ipms)

    def __init__(self, dbmaster, loglevel=logging.INFO, select=None,
                 reject=None):
        self.dbmaster = dbmaster
        self.loglevel = loglevel
        self.re_select = re.compile(select) if select else None
        self.re_reject = re.compile(reject) if reject else None

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
        # list of all valid stations prior to subsetting, with no other
        # information other than the station names. Save that as a list so that
        # we can replicate the functionality.
        self.all_known_stations=stations.keys()

        # subset stations
        for sta in stations.keys():
            if self.re_select:
                if not self.re_select.match(sta):
                    del(stations[sta])
            if self.re_reject:
                if self.re_reject.match(sta):
                    del(stations[sta])

        for sta in stations.keys():
            s='sta == "%s" && snet == "%s" && endtime == NULL'
            deployment.record=-1
            if deployment.find(s % (sta, stations[sta]['net'])):

                stations[sta]['status'] = 'Active'

                if stations[sta]['status'] == 'Decom':
                    continue

                self.logger.debug(sta + ' set to "Active"')

            # Get IP for station
            staq330.record=-1
            recordid = staq330.find('dlsta == "%s" && endtime == NULL' %
                                    stations[sta]['dlsta'])

            if recordid >=0:
                staq330.record=recordid
                inp = staq330.getv('inp')
                inp=inp[0]

                self.logger.debug('%s inp=>%s' % (sta, inp))

                try:
                    m=self.re_ip.match(inp)
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

class BalerStatusDownloader():
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

        self._request=None # the AsyncRequest that we generate with request()
        self.response=None # The Response returned by the AsyncRequest

        # self.data contains what will get dumped out to JSON
        self.data={
            'station': sta,
        }

    def url(self):
        return 'http://%s:%s/stats.html' % (self.ip, self.port)

    def responseHandler(self,r,*args,**kwargs):
        """callback function to update baler information

        The grequests library uses the requests library under the hook. Making
        a request results in a Response object being passed to this callback.
        """
        self.logger.info("BalerStatusDownloader(%s): Got a response for %s" % (
            self.dlsta, r.url))

        self.response=r
        self.process_response()
        self.logger.debug("responseHandler: Done with callback")

    def request(self):
        """Generate an AsyncRequest with a callback to this object

        The returned object is suitable for use by the grequests.map()
        function.
        """
        if self._request is None:
            self._request = grequests.get(
                url=self.url(),
                callback=self.responseHandler,
                timeout=30,
            )
        return self._request

    def process_response(self):
        self.data.update(parse_baler_status_page(self.response.content))
        self.problems = self._check_data()
        self.logger.debug("Station " + self.sta + ": " +json.dumps(self.data))

    def _check_data(self):
        """
        Private function to validate self.data

        Checks values against thresholds, comparing some values to previous
        values (as loaded from the history).
        """
        problems=[]

        # TODO: a whole bunch
        return problems

class App():
    def main(self,argv=sys.argv):
        # Set up logging with the ElogHandler
        self.logger = logging.getLogger()

        self.logger.handlers=[]
        handler = ElogHandler()
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

        # Retrieve arguments
        parser = argparse.ArgumentParser('retrieve baler44 status details')
        parser.add_argument('output_dir', help='directory to store status data')
        parser.add_argument('dbmaster', help='Antelope dbmaster path')
        parser.add_argument('--debug', '-d', action='store_true', help='Debug mode')
        parser.add_argument('--select', '-s', default=None, help='Process only stations matching this regular expression')
        parser.add_argument('--reject', '-r', default=None, help='Do not process stations matching this regular expression')
        self.args=parser.parse_args()

        if self.args.debug == True:
            self.logger.setLevel(logging.DEBUG)

        self.logger.info("logging level set to "+str(self.logger.level))

        # process all the things
        try:
            # Load list of BalerStations
            bs=BalerStations(self.args.dbmaster,
                             loglevel=self.logger.level,
                             select=self.args.select,
                             reject=self.args.reject)

            # Make first stage JSON file
            self.make_baler44_status_json(self.args.output_dir, bs.all_known_stations)

            # Retrieve the baler status from the active stations
            self.retrieve_status_from_balers(bs.stations)

        except BalerException as e:
            self.logger.exception('A problem with baler processing:')
            return(EXIT_NOSTATIONS)
        except DatascopeError as e:
            self.logger.exception('A problem with the database occured:')
            return(EXIT_DBERROR)
        except BalerJSONWriteError as e:
            self.logger.exception('Could not write one of the JSON files out:')
            return(EXIT_JSONERROR)

        # If we make it here everything went well.
        return(0)

    def make_baler44_status_json(self, output_dir, stations):
        """dump a list of all stations with Balers to baler44_status.json

        @throws BalerJSONWriteError
        """
        fname=os.path.join(output_dir, 'baler44_status.json')
        self.logger.debug('Prepare JSON file: ' + fname)

        out={
            'updated': epoch2str(now(),'%Y-%m-%d %H:%M:%S'),
            'stations': stations,
        }
        # TODO: actually write this to a file
        self.logger.debug(json.dumps(out, indent=4))

    def retrieve_status_from_balers(self, stations, poolsize=100):
        """request status pages from stations"""

        downloaders = [BalerStatusDownloader(
            net=v['net'],
            sta=k,
            dlsta=v['dlsta'],
            ip=v['ip'],
            port=v['bport'],
            loglevel=self.logger.level,
        ) for k,v in stations.items()]

        reqs = [dl.request() for dl in downloaders]

        # Exception handler not available in current PyPI version 0.2.0 but is
        # there in HEAD
        try:
            responses = grequests.map(reqs, poolsize,
                                      exception_handler=self.greq_ex_handler)
        except TypeError as e:
            logging.warning('Version of grequests in use does not support custom ' +
                           'exception handler. Expect log spam from request ' +
                           'failures.')
            responses = grequests.map(reqs, poolsize)

        # Output some summary info
        failed = [ d.sta for d in downloaders if not d.response ]
        logging.info("Summary: Received responses from %d of %d stations" % (
            len(responses), len(reqs)))
        logging.info("%d stations failed, %d succeeded" % (
            len(failed), len(reqs)-len(failed)))


    def greq_ex_handler(self, request, exception):
        self.logger.warning(request.url + "failed with " + exception)

# Precompile a bunch of useful regular expressions
_res={
    'firmware': re.compile('Inc\. (\w+)-(\w+)-(\w+) tag (\d+) at (.+)$'),
    'reboots': re.compile('^last baler reboot:\s+(.+)\s+reboots:\s+(\d+)\s+runtime:\s+(.+)$'),
    'media1': re.compile('^MEDIA site 1 crc=(\w+) (.+) state: (\w+)\s+capacity=(\S+)\s+free=(\S+)$'),
    'media2': re.compile('^MEDIA site 2 crc=(\w+) (.+) state: (\w+)\s+capacity=(\S+)\s+free=(\S+)$'),
    'batt': re.compile('^upsvolts=(\S+)\s+primaryvolts=(\S+)\s+degc=(\S+)$'),
    'baler_opt': re.compile('^baler cfg options:\s+(.+)$'),
    'baler_cpu_speed': re.compile('^cpu speed\s+(.+)$'),
    'mseed_records': re.compile('^mseed record generator at (\d+) and last flush at (\d+)$'),
    'baler_records': re.compile('^routing turnons=\d+\s+primary records written=(\d+)\s+secondary records written=(\d+)$'),
    'media_last_file_time': re.compile('^media last write time: (.+)$'),
    #'media_last_file': re.compile('^last media file written: (.+)$'),
    'media_last_file': re.compile('^last media file written: (\S.+)$'),
    'q330_connection': re.compile('^(\S+) Q330 connection$'),
    'proxy_port': re.compile('^proxy base port:\s+(\d+)$'),
    'public_ip': re.compile('^public ip discovered:\s+(\S+)$'),
    'HWaddr': re.compile('HWaddr\s+(\S+)\s*$'),
    'float': re.compile('\d+\.\d+'),
    'int': re.compile('\d+')
}
def parse_baler_status_page(content):
    """
    Parse a baler status page

    Returns a dict of key/values as read from the baler page
    """

    # Initialize our default values
    data={
        'updated': epoch2str(now(), '%Y-%m-%d %H:%M:%S'),
        'updated_epoch': now(),
    }

    section_handlers = {
        'Baler Information'                   : _parse_Baler_Information,
        'Media File Lists'                    : _parse_Media_File_Lists,
        'Q330 Information'                    : None,
        'Environmental Processor Information' : None,
        'MSEED Channel Information'           : None,
        'Event Detector Information'          : None,
        'Baler-Q330 Connection Status'        : None,
        'Extended Media Identification'       : None,
    }

    soup=BeautifulSoup(content, 'lxml') # looks like we have lxml in $ANF

    # Get the station name from the title element. It's also available in the
    # sole h3 tag in the page
    ttext=soup.title.string
    m=re.match('.* - Station (\w+-\w+)$',ttext)
    data['name'] = m.group(1) if m else '-'

    # get all the sections, delineated by h4 tags
    sections=soup.find_all('h4')

    logging.debug("Section Handlers: "+str(section_handlers.keys()))
    for section in sections:
        logging.debug("Looking at section " + section.string)
        sibling = section.next_sibling.next_sibling # skip newline
        predata=None
        if (sibling is None) or (sibling.name != 'pre') or (sibling.string is None):
            logging.critical("Can't find data for section %s" % section.string)
        else:
            predata=sibling.string

        if section.string in section_handlers.keys():
            h = section_handlers[section.string]
            if h is not None:
                data.update( h( predata ) )
                logging.debug("Processing section " + section.string)
            else:
                logging.debug("Skipping section " + section.string)
        else:
            logging.warning("Unknown section encountered: \"%s\"" %
                           section.string)
    return data

def _parse_Baler_Information(content):
    """
    parse the "Baler Information" section of the baler status page.
    Should be the text content of the pre tag immediately following the h4 tag
    """
    fields = [
        'media_status', 'full_tag', 'firmware', 'tag', 'tag_date',
        'reboot', 'reboot_total', 'runtime',
        'media_1', 'media_1_name', 'media_1_state', 'media_1_capacity', 'media_1_free',
        'media_2', 'media_2_name', 'media_2_state', 'media_2_capacity', 'media_2_free',
        'upsvolts', 'primaryvolts', 'degc',
        'cfg',
        'cpu',
        'record_generator', 'last_flush',
        'records_primary', 'records_secondary',
        'last_file_time',
        'last_file',
        'q330_connection',
        'proxy_port',
        'public_ip',
        'mac',
    ]

    # Set our defaults to a hyphen
    data={el: '-' for el in fields}

    if content:
        lines=content.splitlines()

        data['media_status']=lines[3] # Not an easy regex, hope format is fixed

        # loop through the lines looking for our regexes
        for line in lines:
            m = _res['firmware'].search(line)
            if m:
                data['full_tag']='%s-%s-%s' % m.group(1,2,3)
                data['firmware']=m.group(2)
                data['tag']=m.group(4)
                data['tag_date']=m.group(5)
                continue

            m = _res['reboots'].search(line)
            if m:
                data['reboot']=m.group(1)
                data['reboot_total']=m.group(2)
                if 'd' in m.group(3):
                    data['runtime']='%0.2f' % float(m.group(3)[:-1])
                continue

            m = _res['media1'].search(line)
            if m:
                data.update({
                    'media_1': m.group(1),
                    'media_1_name' : m.group(2),
                    'media_1_state' : m.group(3),
                    'media_1_capacity' : m.group(4),
                    'media_1_free' : m.group(5),
                })
                continue

            m = _res['media2'].search(line)
            if m:
                data.update({
                    'media_2': m.group(1),
                    'media_2_name' : m.group(2),
                    'media_2_state' : m.group(3),
                    'media_2_capacity' : m.group(4),
                    'media_2_free' : m.group(5),
                })
                continue

            m = _res['batt'].search(line)
            if m:
                if _res['float'].match(m.group(1)):
                    data['upsvolts']     = '%0.3f' % float(m.group(1))
                if _res['float'].match(m.group(2)):
                    data['primaryvolts'] = '%0.3f' % float(m.group(2))
                if _res['float'].match(m.group(3)):
                    data['degc']         = '%0.3f' % float(m.group(3))
                continue

            m = _res['baler_opt'].search(line)
            if m:
                data['cfg']=m.group(1)
                continue

            m = _res['baler_cpu_speed'].search(line)
            if m:
                if _res['int'].match(m.group(1)):
                    data['cpu'] = '%0d' % int(m.group(1))
                continue

            m = _res['mseed_records'].search(line)
            if m:
                if _res['int'].match(m.group(1)):
                    data['record_generator'] = '%0d' % int(m.group(1))
                if _res['int'].match(m.group(2)):
                    data['last_flush'] = '%0d' % int(m.group(2))
                continue

            m = _res['baler_records'].search(line)
            if m:
                if _res['int'].match(m.group(1)):
                    data['records_primary'] = '%0d' % int(m.group(1))
                if _res['int'].match(m.group(2)):
                    data['records_secondary'] = '%0d' % int(m.group(2))
                continue

            m = _res['media_last_file_time'].search(line)
            if m:
                data['last_file_time'] = m.group(1)
                continue

            m = _res['media_last_file'].search(line)
            if m:
                # original perl code looked like this:
                #   @temp_array =  split '/', $temp_1;
                #   if ( $temp_array[-1] =~ /\S+/ ) {
                #     $temp_1 = $temp_array[-1];
                #   }
                #   else { $temp_1 = join '/', @temp_array; }
                # We don't need to check for empty strings here due to a regex
                # tweak, so if we find anything, just strip the path
                # components off and use the basename of the file
                a = m.group(1).split('/')
                data['last_file'] = a[-1]
                continue

            m = _res['q330_connection'].search(line)
            if m:
                data['q330_connection'] = m.group(1)
                continue

            m = _res['proxy_port'].search(line)
            if m:
                data['proxy_port'] = m.group(1)
                continue

            m = _res['public_ip'].search(line)
            if m:
                data['public_ip'] = m.group(1)
                continue

            m = _res['HWaddr'].search(line)
            if m:
                data['mac'] = m.group(1)
                continue


    return data

def _parse_Media_File_Lists(content):
    """
    parse the "Media File Lists" section

    BeautifulSoup will return an empty string if the media file lists section
    only contains <a> tags, since those count as child tags rather than the
    "string" text of the pre tag.

    ILLEGAL MEDIA FILE NAMES is in the Media File Lists section.
    Original script craps out the whole line rather than removing the "ILLEGAL
    MEDIA FILE NAMES" stuff at the beginning, so the data ends up looking like:
      "illegal_file_names":"ILLEGAL MEDIA FILE NAMES: 12 (active), 0 (reserve)",
    """
    data={'illegal_file_names': ''}
    if content:

        lines=content.splitlines()

        illegal=None
        for l in lines:
            if 'ILLEGAL MEDIA FILE NAMES' in l:
                data['illegal_file_names'] = l
                break

    return data

if __name__ == '__main__':
    app=App()
    sys.exit(app.main())
