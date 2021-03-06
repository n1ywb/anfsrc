try:
    #import inspect
    import os
    import sys
except Exception, e:
    raise ImportError("Problems importing libraries.%s %s" % (Exception, e))

try:
    import antelope.stock as stock
except Exception, e:
    raise ImportError("Problems loading ANTELOPE libraries. %s(%s)" % (Exception, e))


try:
    from soh2mongo.logging_class import getLogger
except Exception, e:
    raise ImportError("Problem loading logging_class. %s(%s)" % (Exception, e))


class stateFile:
    """
    Track some information from the realtime process into
    a STATEFILE.
    Save value of pktid in file.
    """
    def __init__(self, filename=False, start='oldest'):

        self.logging = getLogger('stateFile')

        self.logging.debug( "stateFile.init()" )

        self.filename = filename
        self.packet = start
        self.time = 0
        self.strtime = 'n/a'
        self.latency = 'n/a'
        self.pid = 'PID %s' % os.getpid()

        if not filename: return

        self.directory, self.filename = os.path.split(filename)

        if self.directory and not os.path.isdir( self.directory ):
            os.makedirs( self.directory )

        self.file = os.path.join( self.directory, self.filename )

        self.logging.debug( 'Open file for STATE tracking [%s]' % self.file )
        if os.path.isfile( self.file ):
            self.open_file('r+')
            self.read_file()
        else:
            self.open_file('w+')

        if not os.path.isfile( self.file ):
            raise sohException( 'Cannot create STATE file %s' % self.file )

    def last_packet(self):
        self.logging.info( 'last pckt:%s' % self.packet )
        return self.packet

    def last_time(self):
        self.logging.info( 'last time:%s' % self.time )
        return self.time

    def read_file(self):
        self.pointer.seek(0)

        try:
            temp = self.pointer.read().split('\n')
            self.logging.info( 'Previous STATE file %s' % self.file )
            self.logging.info( temp )

            self.packet = int(float(temp[0]))
            self.time = float(temp[1])
            self.strtime = temp[2]
            self.latency = temp[3]

            self.logging.info( 'Previous - %s PCKT:%s TIME:%s LATENCY:%s' % \
                        (self.pid, self.packet, self.time, self.latency) )

            if not float(self.packet): raise
        except:
            self.logging.warning( 'Cannot find previous state on STATE file [%s]' % self.file )



    def set(self, pckt, time):

        self.logging.debug( 'set %s to %s' % (self.filename, pckt) )

        if not self.filename: return

        self.packet = pckt
        self.time = time
        self.strtime = stock.strlocalydtime(time).strip()
        self.latency = stock.strtdelta( stock.now()-time ).strip()

        #self.logging.debug( 'latency: %s' % self.latency )

        try:
            self.pointer.seek(0)
            self.pointer.write( '%s\n%s\n%s\n%s\n%s\n' % \
                    (self.packet,self.time,self.strtime,self.latency,self.pid) )
        except Exception, e:
            raise sohException( 'Problems while writing to state file: %s %s' % (self.file,e) )

    def open_file(self, mode):
        try:
            self.pointer = open(self.file, mode, 0)
        except Exception, e:
            raise sohException( 'Problems while opening state file: %s %s' % (self.file,e) )


