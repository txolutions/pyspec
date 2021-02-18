#!/usr/bin/env python

#******************************************************************************
#
#  @(#)specfile.py	3.3  05/11/20 CSS
#
#  "pyspec" Release 3
#
#  Copyright (c) 2013,2014,2015,2016,2018,2020
#  by Certified Scientific Software.
#  All rights reserved.
#
#  Permission is hereby granted, free of charge, to any person obtaining a
#  copy of this software ("pyspec") and associated documentation files (the
#  "Software"), to deal in the Software without restriction, including
#  without limitation the rights to use, copy, modify, merge, publish,
#  distribute, sublicense, and/or sell copies of the Software, and to
#  permit persons to whom the Software is furnished to do so, subject to
#  the following conditions:
#
#  The above copyright notice and this permission notice shall be included
#  in all copies or substantial portions of the Software.
#
#  Neither the name of the copyright holder nor the names of its contributors
#  may be used to endorse or promote products derived from this software
#  without specific prior written permission.
#
#     * The software is provided "as is", without warranty of any   *
#     * kind, express or implied, including but not limited to the  *
#     * warranties of merchantability, fitness for a particular     *
#     * purpose and noninfringement.  In no event shall the authors *
#     * or copyright holders be liable for any claim, damages or    *
#     * other liability, whether in an action of contract, tort     *
#     * or otherwise, arising from, out of or in connection with    *
#     * the software or the use of other dealings in the software.  *
#
#******************************************************************************

"""

****************
specfile
****************

Description
****************
Utility to handle data files in spec data format

Classes
****************
To check the definition of the spec data file format check `certif.com`_

.. _`certif.com`: http://www.certif.com/spec_help/scans.html

"""

version = "1.0"

import sys
import os
import getopt

SPECD='/usr/local/lib/spec.d'
specd = os.environ.get('SPECD', SPECD)
sys.path.append( specd )

try:
   from pyspec.file.spec import FileSpec
except ImportError:
   print("Cannot find filespec module. Try setting SPECD variable")
   sys.exit(0)

outformats = ['csv', 'tabs', 'spec']

def printUsage(msg=None, longmode=False):
    if msg:
       print(msg)

    if not longmode:
       print("""Usage: %(progname)s [options] filename [scanlist] 
   type \"%(progname)s -h\" for a detailed help """ % {'progname': os.path.basename(sys.argv[0])} )
    else:
       print("""
Usage: %(progname)s [options] filename [scanlist]

Options are: 
  -f format
      Format of the output files. Format can be one out of "tabs", "csv" or "spec"
      Default output format is "tabs"

  -O 
      Do not overwrite existing files. By default %(progname)s will overwrite existing files
      if they have the same name

  -S 
      Use single file for output. Useful particularly in the case of "spec" output format

  -p  prefix
      Use `prefix` as prefix for output files
      The default is to set prefix as the the root name of the original file

  -s  suffix

  -d outdir
      Use `outdir` directory to write output files. The default is to use the  
      root name of the original file. 
      
  -l 
      List scans in file in condensed mode
  -L 
      List scans in file in non condensed mode

  -a 
      Extract all scans in the file

  -h 
      Prints this help and exits

  -V 
      Prints program version


Specifying a scanlist:
  scanlist can be given as a list of scan numbers or scan ranges (
  using ":" to specify a specify first and last scan number in range. 
  Either "," or <space> can be used 
  to separate arguments.

  Examples of valid scan specification are:
     %(progname)s myfile.dat 3 6 8
     %(progname)s myfile.dat 3,6,8
     %(progname)s myfile.dat 3,6:12,37
     %(progname)s myfile.dat 3 6:12 37
     %(progname)s myfile.dat 3,6:12 37
 
  Remember you can also use the "-a" flag to extract all scans in a file


""" % { 'progname': os.path.basename(sys.argv[0])})

def parseScanArgs(scanarg):

    args1 = scanarg.split()
    args = [] 
    for arg in args1:
       args.extend( arg.split(",") )

    scanlist = []

    for arg in args:
      if arg.find(":") != -1:
         slist = None
         try:
             arg1, arg2 = arg.split(":")
             iarg1 = int(arg1)
             iarg2 = int(arg2)
             if iarg2 <= iarg1:
                raise "Bad scan arguments"
             else:
                slist = [ str(val) for val in range(iarg1, iarg2+1) ]
         except:
             raise "Bad scan arguments"
         scanlist.extend(slist)
      else:
         iarg = arg
         scanlist.append(iarg)

    return scanlist

def formatScanList(scanlist, condensed=True):
    strlist = ""
    prev = -1
    openlist = False

    sep = ""
    for scanno in scanlist:
        if not condensed: 
           strlist += ( sep + str(scanno) )
        else:
           if scanno == (prev + 1):
              openlist = True
           else:
              if openlist:
                 strlist += ":"
                 strlist += str(prev)
              strlist += ( sep + str(scanno) )
              openlist = False
        prev = scanno
        sep = ","
    else:
        if condensed and openlist:
           strlist += ":"
           strlist += str(scanno)

    return strlist

def main():

    outformat = "tabs"
    suffix    = None
    prefix    = None
    outdir    = None

    overw_flag  = False
    single_flag = False
    all_flag    = False
    list_flag   = False

    if len(sys.argv) < 2:
       printUsage()
       sys.exit(0)

    try:
       optlist, args = getopt.getopt(sys.argv[1:], "f:s:p:d:alLOShV")
    except:
       printUsage(msg="wrong usage")
       sys.exit(1)

    for o,a in optlist:
        if o == '-h':
             printUsage(longmode=True)
             sys.exit(0)
        elif o == '-V':
            print(version)
            sys.exit(0)
        elif o == "-f":
            outformat = a
        elif o == '-p':
            prefix = a
        elif o == '-s':
            suffix = a
        elif o == '-d':
            outdir = a
        elif o == "-l":
            list_flag = True
            condensed = True
        elif o == "-L":
            list_flag = True
            condensed = False
        elif o == '-O':
            overw_flag = True
        elif o == '-a':
            all_flag = True
        elif o == '-S':
            single_flag = True

    if len(args) == 0:
       printUsage("You should specify an input filename")
       sys.exit(0)

    if outformat not in outformats:
        printUsage( msg="Wrong output format specified. Valid formats are %s" % ",".join(outformats))
        sys.exit(1)

    filename = args[0]

    if len(args) > 1:
       scanargs = " ".join( args[1:] )
    else:
       scanargs = None

    # check if file exists and it is plain and readable file
    if not os.path.exists(filename):
        print("File %s does not exist." % filename) 
        sys.exit(1)

    # open file. check if any scan could  be indexed
    try:
        fs = FileSpec(filename)
    except:
        import traceback
        traceback.print_exc()
        print("Cannot index file %s." % filename)
        sys.exit(1)

    if len(fs) <= 0:
        print("Cannot index file %s." % filename)
        sys.exit(1)

    if list_flag:
        scanlist = [ scan.getNumber() for scan in fs ]
        strlist = formatScanList( scanlist, condensed=condensed )
        print(strlist)
        sys.exit(0)

    # prepare the scan list to extract
    scanlist = None
    if scanargs is not None:
       #try: 
          scanlist = parseScanArgs( scanargs ) 
       #except:
          #print("Wrong scan selection")
          #sys.exit(1)
       
    scans = []
    if scanlist:
       for scanno in scanlist:
           sparts = scanno.split(".")
           sno  = int(sparts[0])
           if len(sparts) > 1:
              sord = int(sparts[1])
           else:
              sord = 0
           scan = fs.getScanByNumber( int(sno), int(sord) ) 
           if scan:
              scans.append( scan ) 
           else:
              print("Cannot find scan %d(%d) in file %s" % (sno,sord,filename))
    else:
       if all_flag:
          # extract them all
          scans = [ scan for scan in fs ]

    inprefix = os.path.splitext( os.path.basename( filename ))[0]

    if not outdir:
       outdir = inprefix

    if not suffix:
       if outformat == "csv":
          suffix = "csv"
       else:
          suffix = "dat"

    if not prefix:
        prefix = inprefix

    if not os.path.exists(outdir):
       os.makedirs(outdir)

    for scan in scans:
 
       if single_flag:
          outfile = os.path.join( outdir, "%s_bundle.%s" % ( prefix, suffix ))
       else:
          outfile = os.path.join( outdir, "%s_%s.%s" % ( prefix, scan.getNumber(), suffix ))

       # find alternative name if not set to overwrite
       if not overw_flag and not single_flag:
          tryno = 0
          while os.path.exists(outfile):
             tryno += 1
             outfile = os.path.join( outdir, "%s_%s-%d.%s" % ( prefix, scan.getNumber(), tryno, suffix )) 

       scan.save(outfile, format=outformat, append=single_flag)
 
if __name__ == "__main__":
     main()
