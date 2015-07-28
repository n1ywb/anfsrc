import imp, time
import mock
import datetime
dcupsmon=imp.load_source('dcupsmon', './dcupsmon.xpy')

class TestTimedExecutor:
    def printer(self):
        print "running"

    def setUp(self):
        print("")
        print("Starting up the TimedExecutor object")
        self.te = dcupsmon.TimedExecutor(1.0, self.printer,
                                         atstart=True)

    def tearDown(self):
        #self.te.join(1)
        pass

    def testTimedExecutor(self):
        assert self.te.isAlive() == False
        self.te.start()
        print "Sleeping main thread for 5 seconds"
        time.sleep(5)
        assert self.te.isAlive()
        time.sleep(1)
        self.te.cancel()
        self.te.join(1)
        assert (self.te.isAlive() == False)

class TestUpsStateViewer:
    def setUp(self):
        self.v = dcupsmon.UpsStateViewer()

    def testUpsStateViewer(self):
        assert self.v.notifierthread == None
        self.v.notify_interval=1.0
        ts=mock.Mock()
        ts.isOnBattery = mock.MagicMock(return_value=False)
        ts.timeOnBattery = mock.MagicMock(return_value=datetime.timedelta(5))
        self.v.update(ts)
        assert self.v.notifierthread == None

        ts.isOnBattery = mock.MagicMock(return_value=True)
        self.v.update(ts)
        assert self.v.notifierthread != None

    def tearDown(self):
        self.v.cancel_notifier()
