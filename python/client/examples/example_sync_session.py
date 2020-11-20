
#
# Example of a synchronous python session
#

# from pyspec.css_logger import log
# log.start()

from pyspec.client import spec
import time

sess = spec("fourc")

#
# some useful functions
#
print("Connected to %s - version %s" % (sess.get_name(), sess.spec_version))
print( sess.get_motors() )
print( sess.get_positions() )

#
# reading variables
#
scan_n = sess.get("SCAN_N")
datafile = sess.get("DATAFILE")

print("Last scan number was: " + str( sess.get("SCAN_N")))
print("Using datafile: %s" % datafile )

# 
# get a motor object
# 
phi = sess.get_motor('chi')
print( phi.get_position() )
print( phi.read('step_size') )

# you can alsog get a motor object as an attribute

print("Chi")
chi = sess.chi
print( "Pos before: %s"  % chi.get_position() ) 
# a synchronous move
chi.mvr(2)
print( "Pos after: %s"  % chi.get_position() ) 

pos_after = chi.position
# an asynchronous move
chi.start_move(pos_after - 2)
# do something else
print( chi.read('slew_rate') )
time.sleep(0.1)
while chi.moving:
    print(" - moving")
    print(" - position is: %s" % chi.position )
    time.sleep(0.1)
print("move finished")
print( "Pos end: %s"  % chi.get_position() ) 

#
# setting a new datafile
sess.run_cmd("newfile /tmp/mydata.dat")

