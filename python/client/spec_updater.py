#  %W%  %G% CSS
#  "pyspec" Release %R%
#

import asyncore
import threading
import weakref
import time

try:
    import gevent
    gevent_ok = True
except:
    gevent_ok = False

THREAD, GEVENT = 0,1

from pyspec.css_logger import log
from pyspec.utils import async_loop

class spec_updater(object):
    default_update_time = 5 # millisecs

    def __init__(self, method=THREAD, update_func=None, update_time=None): 

        self.started = False
        self.thread = None
        self.greenlet = None

        if method == THREAD:
            self._method = THREAD
        elif method == GEVENT:
            if not gevent_ok:
                raise Exception("spec_updater gevent selected "
                                "but gevent module cannot be imported")
            else:
                raise Exception("gevent method is not yet implemented")
                self._method = GEVENT
                pass
        else:
            raise Exception("wrong method for spec_updater. " 
                            "only thread and gevent supported")

        self.update_func = (update_func is not None) \
                and update_func or self._update
        self.set_update_time(update_time)

    def set_update_time(self, update_time):
        self.update_time = update_time is None and \
                              self.default_update_time or update_time
        self.update_time /= 1000.0 # in seconds
        log.log(2, " starting spec updater. update time is %s" % self.update_time)


        # minimum 10 milliseconds update cycle time
        if self.update_time < 0.005:
            log.log(2, "update time of %s secs too short. using 0.01")
            self.update_time = 0.005

    def _update(self):
        # asyncore.loop(timeout=1, count=1)
        async_loop(timeout=0.01, count=1)

    def start(self):
        self.started = True
        self.start_thread()

    def stop(self,timeout=0.3):
        self.started = False
        s0 = time.time()
        try:
            while self.thread.isAlive():
                time.sleep(0.1)
                if time.time() -s0 > timeout:
                    print("cannot stop thread. killing it")
                    self.kill()
        except ImportError:
            self.kill()
            print("i am already done")

    def kill(self):
        self.started = False
        #self.thread.kill()

    def is_running(self):
        if self.thread is not None and self.thread.isAlive():
            return True
        return False

    def start_thread(self):
        self.thread = threading.Thread(target=self._loop)
        # daemon flag sets thread to stop on main thread control-C
        self.thread.daemon = True
        self.thread.start() 

    def _loop(self):
        log.log(2, "starting thread loop - update_time is %s" % self.update_time)
        while True:
            try:
                if not self.started:
                    log.log(2, "setting thread started to False. quitting")
                    break
                self.update_func()
                time.sleep(self.update_time)
            except:
                import traceback
                print(traceback.format_exc())
                break

if __name__ == '__main__':
    def say():
        print("hello")

    updater = spec_updater(update_func=say, update_time=50)
    updater.start()

    while True:
        try:
            time.sleep(0.2)
        except KeyboardInterrupt:
            break
