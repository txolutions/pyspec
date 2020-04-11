#******************************************************************************
#
#  %W%  %G% CSS
#
#  "pyspec" Release %R%
#
#  Copyright (c) 2020
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

PY2=
PY3=

ifneq (, $(shell which python3 ))
       override PY3="python3"
endif

ifneq (, $(shell which python2 ))
       override PY2="python2"
endif

SHELL   = /bin/sh
OWNER   = specadm
SPECD   = /usr/local/lib/spec.d
INSDIR  = /usr/local/bin
TAR     = tar
PACK    = gzip -c
UNPACK  = gunzip -c
SPEC_SRC = ../..

CHOWN   = chown

DIST_SRC = VERSION.py

SRC = Makefile ${DIST_SRC} versionsave version_template.py

TOOLS = specfile roi_selector

PY_SRC = css_logger.py utils.py __init__.py

MODULES = datashm.so 

CLIENT_SRC = __init__.py saferef.py Spec.py SpecArray.py SpecChannel.py \
	SpecClientError.py SpecCommand.py SpecConnection.py SpecConnectionsManager.py \
	SpecCounter.py SpecEventsDispatcher.py SpecMessage.py SpecMotor.py \
	SpecReply.py SpecScan.py SpecServer.py SpecVariable.py SpecWaitObject.py

HDW_SRC = __init__.py eigerclient.py server.py

GRAPHICS_SRC = __init__.py graphics_rc.py qwt_import.py matplotlib_import.py \
	PySide_import.py PyQt4_import.py PyQt5_import.py PySide2_import.py \
	QVariant.py

FILE_SRC = __init__.py spec.py tiff.py

PYDOC_SRC = spec_help.tpl SpecHTMLreST.py SpecMANreST.py

DATASHM_SRC = datashm_py.c setup.py README

DOCS_SRC = installation.rst spec_format.rst 

# Keep gmake from trying to check out a file from  source code control
%: %,v
%: RCS/%,v
%: RCS/%
%: s.%
%: SCCS/s.%

it: prep_dist

install:
	@echo "Installing pyspec modules ..."
	@for i in ${TOOLS}; do rm -f ${INSDIR}/$$i; \
		sed "/^SPECD=/s;=.*;='${SPECD}';" tools/$$i > ${INSDIR}/$$i; \
		( chmod 555 ${INSDIR}/$$i; ${CHOWN} ${OWNER} ${INSDIR}/$$i; ) \
	    done; \
	mkdir -p ${SPECD}/pyspec
	@echo " Copying pyspec files ..." ; \
	 ${UNPACK} pyspec_built.tar.gz | (cd ${SPECD}/pyspec && ${TAR} xf - )
	@echo " Changing ownership of pyspec files to ${OWNER} ... " ; \
	 cd ${SPECD}/pyspec ; ${CHOWN} -R ${OWNER} . 

install_it: owner_chk untar
	@if [ -f pyspec_built.tar.gz ] ; then make -e install ; fi

prep_datashm:
ifneq (,${PY2})
	@echo "Compiling datashm module for ${PY2}"
	@cd datashm >/dev/null; ${PY2} setup.py --specsrc=${SPEC_SRC} build
endif
ifneq (,${PY3})
	@echo "Compiling datashm module for ${PY3}"
	@cd datashm >/dev/null; ${PY3} setup.py --specsrc=${SPEC_SRC} build
endif

version:
	@echo "Generating VERSION.py python file"
	@./versionsave

dist: prep_dist tarball

prep_dist: prep_datashm 
	-@rm -rf pyspec.tmp
	@mkdir pyspec.tmp
	@mkdir pyspec.tmp/client 
	@mkdir pyspec.tmp/hardware 
	@mkdir pyspec.tmp/graphics 
	@mkdir pyspec.tmp/file 
	@mkdir pyspec.tmp/doc 
	@cp VERSION.py pyspec.tmp/
	 (cd pyspec >/dev/null; cp ${PY_SRC} ../pyspec.tmp/)
	 (cd pyspec/client >/dev/null; cp ${CLIENT_SRC} ../../pyspec.tmp/client/)
	 (cd pyspec/hardware >/dev/null; cp ${HDW_SRC} ../../pyspec.tmp/hardware/)
	 (cd pyspec/graphics >/dev/null; cp ${GRAPHICS_SRC} ../../pyspec.tmp/graphics/)
	 (cd pyspec/file >/dev/null; cp ${FILE_SRC} ../../pyspec.tmp/file/)
	 (cd pyspec/doc >/dev/null; cp ${PYDOC_SRC} ../../pyspec.tmp/doc/)
ifneq (,${PY2})
	@cd datashm >/dev/null; ${PY2} setup.py --specsrc=${SPEC_SRC} install --install-lib=../pyspec.tmp
	@cd pyspec.tmp && ${PY2} -m compileall .
endif
ifneq (,${PY3})
	@cd datashm >/dev/null; ${PY3} setup.py --specsrc=${SPEC_SRC} install --install-lib=../pyspec.tmp
	@cd pyspec.tmp && ${PY3} -m compileall .
endif
	@cd pyspec.tmp >/dev/null; chmod a-w * */*; \
		chmod u+w client ; \
		chmod u+w hardware ; \
		chmod u+w graphics ; \
		chmod u+w file ; \
		chmod u+w doc ; \
		chmod -f u+w __pycache__ */__pycache__  || :
	@cd pyspec.tmp >/dev/null; ${TAR} cf - . | ${PACK} > ../pyspec_built.tar.gz

owner_chk:
	@( file=/tmp/tmp.$$$$ ; cp /dev/null $$file ; \
		if ${CHOWN} ${OWNER} $$file ; then rm -f $$file ; exit 0 ; \
		else echo "Can't change file ownership to ${OWNER}" ; \
		rm -f $$file ; exit 1 ; fi )

untar:
	@sh -c "if test -s pyspec_src.tar.gz ; then \
	    echo \"Uncompressing and detarring pyspec archive ... \" ; \
	    ( ${UNPACK} pyspec_src.tar.gz || echo XX ) | ${TAR} xf - || exit 1 ; \
	    ${CHOWN} -f -R ${OWNER} . ; \
	    rm -f pyspec_src.tar.gz ; \
	fi ; exit 0"

list:
	-@rm -f ,list; ( \
	  for i in ${SRC}; do echo $$i; done; \
	  for i in ${DOCS_SRC}; do echo docs/$$i; done; \
	  for i in ${TOOLS}; do echo tools/$$i; done; \
	  for i in ${DATASHM_SRC}; do echo datashm/$$i; done; \
	  for i in ${PY_SRC}; do echo pyspec/$$i; done; \
	  for i in ${CLIENT_SRC}; do echo pyspec/client/$$i; done; \
	  for i in ${HDW_SRC}; do echo pyspec/hardware/$$i; done; \
	  for i in ${GRAPHICS_SRC}; do echo pyspec/graphics/$$i; done; \
	  for i in ${FILE_SRC}; do echo pyspec/file/$$i; done; \
	  for i in ${PYDOC_SRC}; do echo pyspec/doc/$$i; done; \
	 ) > ,list

distlist:
	-@rm -f ,distlist; ( \
	  for i in ${DOCS_SRC}; do echo docs/$$i; done; \
	  for i in ${DIST_SRC}; do echo $$i; done; \
	  for i in ${MODULES}; do echo $$i; done; \
	  for i in ${TOOLS}; do echo tools/$$i; done; \
	  for i in ${PY_SRC}; do echo pyspec/$$i; done; \
	  for i in ${CLIENT_SRC}; do echo pyspec/client/$$i; done; \
	  for i in ${HDW_SRC}; do echo pyspec/hardware/$$i; done; \
	  for i in ${GRAPHICS_SRC}; do echo pyspec/graphics/$$i; done; \
	  for i in ${FILE_SRC}; do echo pyspec/file/$$i; done; \
	) > ,distlist

tarball:
	@rm -f pyspec_src.tar.gz; ${TAR} cf - ${DIST_SRC} `\
	  for i in ${DOCS_SRC}; do echo docs/$$i; done; \
	  for i in ${TOOLS}; do echo tools/$$i; done; \
	  for i in ${DATASHM_SRC}; do echo datashm/$$i; done; \
	  for i in ${PY_SRC}; do echo pyspec/$$i; done; \
	  for i in ${CLIENT_SRC}; do echo pyspec/client/$$i; done; \
	  for i in ${HDW_SRC}; do echo pyspec/hardware/$$i; done; \
	  for i in ${GRAPHICS_SRC}; do echo pyspec/graphics/$$i; done; \
	  for i in ${FILE_SRC}; do echo pyspec/file/$$i; done; \
	  for i in ${PYDOC_SRC}; do echo pyspec/doc/$$i; done; `\
	  | ${PACK} > pyspec_src.tar.gz

clean:
	-@rm -rf pyspec.tmp
	-@rm -f pyspec_src.tar.gz pyspec_built.tar.gz
	-@rm -f *.o *.bak core datashm/*.bak 
	-@rm -f pyspec/*.pyc
	-@rm -f pyspec/client/*.pyc
	-@rm -f pyspec/hardware/*.pyc
	-@rm -f graphics/*.pyc
	-@rm -f pyspec/file/*.pyc
	-@rm -f pyspec/doc/*.pyc
	-@rm -fr datashm/build datashm/datashm.o datashm/sps.o
