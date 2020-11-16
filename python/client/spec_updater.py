
import asyncore
import threading
import time

try:
    import gevent
    gevent_ok = True
except:
    gevent_ok = False

THREAD, GEVENT = 0,1

class spec_updater(object):
    default_update_time = 10 # millisecs

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

        self.update_func = (update_func is None) and \
                self._update or update_func

        self.set_update_time(update_time)

    def set_update_time(self, update_time):
        self.update_time = update_time is None and \
                              self.default_update_time or update_time
        self.update_time /= 1000.0 # in seconds

    def _update (self):
        asyncore.loop(timeout=1, count=1)

    def start(self):
        self.started = True
        self.start_thread()

    def stop(self,timeout=1):
        self.started = False
        s0 = time.time()
        while self.thread.isAlive():
            time.sleep(0.1)
            if time.time() -s0 > timeout:
                print("cannot stop thread. killing it")
                self.kill()

    def kill(self):
        self.thread.kill()

    def is_running(self):
        if self.thread is not None and self.thread.isAlive():
            return True
        return False

    def start_thread(self):
        self.thread = threading.Thread(target=self._loop)
        self.thread.start() 

    def _loop(self):
        while True:
            try:
                if not self.started:
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
            print("going out")
            print(updater.thread.isAlive())
            updater.stop()
            break
