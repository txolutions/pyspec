#******************************************************************************
#
#  %W%  %G% CSS
#
#  "pyspec" Release %R%
#
#  Copyright (c) 2020,2021,2022
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
ifneq (, $(shell which python3 2>/dev/null))
       override PY3="python3"
endif
ifneq (, $(shell which python2 2>/dev/null))
       override PY2="python2"
endif

ifndef PY2
  ifneq (, $(shell which python 2>/dev/null))
        override PY2="python"
  endif
endif

OWNER := $(shell grep -s owner= ../install_data | sed 's/owner=//')
SPECD := $(shell grep -s aux= ../install_data | sed 's/aux=//')

ifeq (${strip ${SPECD}}, )
SPECD = /usr/local/lib/spec.d
endif
ifeq (${strip ${OWNER}}, )
OWNER = specadm
endif
ifeq (${strip ${CHOWN}}, )
CHOWN = chown
endif

SHELL   = /bin/sh
INSDIR  = /usr/local/bin
TAR     = tar

# removed to be used with --specsrc=
#SPEC_SRC = ../..

DIST_SRC = VERSION.py MANIFEST.in setup.py

SRC = Makefile ${DIST_SRC} versionsave version_template.py

TOOLS = specfile roi_selector

TOOLS_PY = specfile.py roi_selector.py

PY_SRC = css_logger.py utils.py ordereddict.py __init__.py

MODULES = datashm.so 

CLIENT_SRC = __init__.py saferef.py SpecArray.py SpecChannel.py \
	SpecClientError.py SpecCommand.py SpecConnection.py SpecConnectionsManager.py \
	SpecCounter.py SpecEventsDispatcher.py SpecMessage.py SpecMotor.py \
	SpecReply.py SpecScan.py SpecServer.py SpecVariable.py SpecWaitObject.py \
	spec_shm.py spec_updater.py

EXAMPLES = README example_qt_command.py	example_qt_motor.py \
	example_qt_status.py example_qt_variable.py example_calc_server.py \
	example_sync_session.py

HDW_SRC = __init__.py server.py

GRAPHICS_SRC = __init__.py graphics_rc.py qwt_import.py matplotlib_import.py \
	PySide_import.py PyQt4_import.py PyQt5_import.py PySide2_import.py \
	PySide6_import.py PyQt6_import.py \
	QVariant.py

FILE_SRC = __init__.py spec.py tiff.py

PYDOC_SRC = __init__.py spec_help.tpl SpecHTMLreST.py SpecMANreST.py

DATASHM_SRC = datashm_py.c setup.py README

# DOCS_SRC = installation.rst spec_format.rst 

DIRS = docs tools python python/datashm \
	python/client python/client/examples python/hardware \
	python/graphics python/tools python/file python/doc

DEPENDS = VERSION.py \
	 $(addprefix python/, ${PY_SRC}) \
	 $(addprefix python/client/, ${CLIENT_SRC}) \
	 $(addprefix python/client/examples/, ${EXAMPLES}) \
	 $(addprefix python/hardware/, ${HDW_SRC}) \
	 $(addprefix python/graphics/, ${GRAPHICS_SRC}) \
	 $(addprefix python/tools/, ${TOOLS_PY}) \
	 $(addprefix python/file/, ${FILE_SRC}) \
	 $(addprefix python/doc/, ${PYDOC_SRC})

# Keep gmake from trying to check out a file from  source code control
%: %,v
%: RCS/%,v
%: RCS/%
%: s.%
%: SCCS/s.%

it: prep_dist

install:
	@echo "Installing pyspec modules ..."
	@if [ -d ${SPECD}/pyspec ] ; then \
	    echo " Clearing out old pyspec files ..." ; \
	    rm -rf ${SPECD}/pyspec ; \
	fi
	@mkdir ${SPECD}/pyspec
	@echo " Copying pyspec files ..." ; \
	    cat pyspec_built.tar.gz | (cd ${SPECD}/pyspec >/dev/null && ${TAR} xfz - )
	@for i in ${TOOLS}; do rm -f ${INSDIR}/$$i; \
		sed '/^SPECD/s;-.*};-${SPECD}};' tools/$$i >${INSDIR}/$$i; \
		( chmod 555 ${INSDIR}/$$i; ${CHOWN} ${OWNER} ${INSDIR}/$$i; ) \
	    done;
	@if [ "${CHOWN}" = "chown" ] ; then \
	 echo " Changing ownership of pyspec files to ${OWNER} ... " ; \
	 cd ${SPECD}/pyspec ; ${CHOWN} -R ${OWNER} . ; fi

install_it: owner_chk untar
	@if [ -f pyspec_built.tar.gz ] ; then make -e install ; fi

prep_datashm:
ifneq (,${PY2})
	@echo "Compiling datashm module for ${PY2}"
	@cd python/datashm >/dev/null; ${PY2} setup.py build
endif
ifneq (,${PY3})
	@echo "Compiling datashm module for ${PY3}"
	@cd python/datashm >/dev/null; ${PY3} setup.py build
endif
	@touch prep_datashm

version:
	@echo "Generating VERSION.py python file"
	@./versionsave

dist: prep_dist tarball

prep_dist: prep_datashm pyspec_built.tar.gz

pyspec_built.tar.gz: ${DEPENDS}
	-@rm -rf pyspec.tmp
	@mkdir pyspec.tmp
	@mkdir pyspec.tmp/client 
	@mkdir pyspec.tmp/client/examples
	@mkdir pyspec.tmp/hardware 
	@mkdir pyspec.tmp/graphics 
	@mkdir pyspec.tmp/tools 
	@mkdir pyspec.tmp/file 
	@mkdir pyspec.tmp/doc 
	@cp VERSION.py pyspec.tmp/
	 (cd python >/dev/null; cp ${PY_SRC} ../pyspec.tmp/)
	 (cd python/client >/dev/null; cp ${CLIENT_SRC} ../../pyspec.tmp/client/)
	 (cd python/client/examples >/dev/null; cp ${EXAMPLES} ../../../pyspec.tmp/client/examples)
	 (cd python/hardware >/dev/null; cp ${HDW_SRC} ../../pyspec.tmp/hardware/)
	 (cd python/graphics >/dev/null; cp ${GRAPHICS_SRC} ../../pyspec.tmp/graphics/)
	 (cd python/tools >/dev/null; cp ${TOOLS_PY} ../../pyspec.tmp/tools/)
	 (cd python/file >/dev/null; cp ${FILE_SRC} ../../pyspec.tmp/file/)
	 (cd python/doc >/dev/null; cp ${PYDOC_SRC} ../../pyspec.tmp/doc/)
ifneq (,${PY2})
	@cd python/datashm >/dev/null; ${PY2} setup.py install --install-lib=../../pyspec.tmp
	@cd pyspec.tmp && ${PY2} -m compileall .
endif
ifneq (,${PY3})
	@cd python/datashm >/dev/null; ${PY3} setup.py install --install-lib=../../pyspec.tmp
	@cd pyspec.tmp && ${PY3} -m compileall .
endif
	@cd pyspec.tmp >/dev/null; chmod a-w * */*; \
		chmod u+w client ; \
		chmod u+w client/examples ; \
		chmod u+w hardware ; \
		chmod u+w graphics ; \
		chmod u+w tools ; \
		chmod u+w file ; \
		chmod u+w doc ; \
		chmod -f u+w __pycache__ */__pycache__  || :
	@cd pyspec.tmp >/dev/null; ${TAR} cfz ../pyspec_built.tar.gz .

owner_chk:
	@( file=/tmp/tmp.$$$$ ; cp /dev/null $$file ; \
		if ${CHOWN} ${OWNER} $$file ; then rm -f $$file ; exit 0 ; \
		else echo "Can't change file ownership to ${OWNER}" ; \
		rm -f $$file ; exit 1 ; fi )

untar:
	@sh -c "if test -s pyspec.tar.gz ; then \
	    echo \"Uncompressing and detarring pyspec archive ... \" ; \
	    tar xfz pyspec.tar.gz || exit 1 ; \
	    rm -f pyspec.tar.gz ; \
	fi ; ${CHOWN} -f -R ${OWNER} . ; exit 0"

list:
	-@rm -f ,list; ( \
	  for i in ${SRC}; do echo $$i; done; \
	  for i in ${DATASHM_SRC}; do echo python/datashm/$$i; done; \
	  for i in ${TOOLS}; do echo tools/$$i; done; \
	  for i in ${PY_SRC}; do echo python/$$i; done; \
	  for i in ${TOOLS_PY}; do echo python/tools/$$i; done; \
	  for i in ${CLIENT_SRC}; do echo python/client/$$i; done; \
	  for i in ${EXAMPLES}; do echo python/client/examples/$$i; done; \
	  for i in ${HDW_SRC}; do echo python/hardware/$$i; done; \
	  for i in ${GRAPHICS_SRC}; do echo python/graphics/$$i; done; \
	  for i in ${FILE_SRC}; do echo python/file/$$i; done; \
	  for i in ${PYDOC_SRC}; do echo python/doc/$$i; done; \
	 ) > ,list

# for i in ${DOCS_SRC}; do echo docs/$$i; done; \

distlist:
	-@rm -f ,distlist; ( \
	  for i in ${DIST_SRC}; do echo $$i; done; \
	  for i in ${MODULES}; do echo python/client/$$i; done; \
	  for i in ${TOOLS}; do echo tools/$$i; done; \
	  for i in ${TOOLS_PY}; do echo python/tools/$$i; done; \
	  for i in ${PY_SRC}; do echo python/$$i; done; \
	  for i in ${CLIENT_SRC}; do echo python/client/$$i; done; \
	  for i in ${EXAMPLES}; do echo python/client/examples/$$i; done; \
	  for i in ${HDW_SRC}; do echo python/hardware/$$i; done; \
	  for i in ${GRAPHICS_SRC}; do echo python/graphics/$$i; done; \
	  for i in ${FILE_SRC}; do echo python/file/$$i; done; \
	) > ,distlist

tarball:
	@rm -f pyspec.tar.gz; ${TAR} cfz pyspec.tar.gz `\
	  for i in ${SRC}; do echo $$i; done; \
	  for i in ${TOOLS}; do echo tools/$$i; done; \
	  for i in ${DATASHM_SRC}; do echo python/datashm/$$i; done; \
	  for i in ${PY_SRC}; do echo python/$$i; done; \
	  for i in ${CLIENT_SRC}; do echo python/client/$$i; done; \
	  for i in ${EXAMPLES}; do echo python/client/examples/$$i; done; \
	  for i in ${HDW_SRC}; do echo python/hardware/$$i; done; \
	  for i in ${GRAPHICS_SRC}; do echo python/graphics/$$i; done; \
	  for i in ${TOOLS_PY}; do echo python/tools/$$i; done; \
	  for i in ${FILE_SRC}; do echo python/file/$$i; done; \
	  for i in ${PYDOC_SRC}; do echo python/doc/$$i; done; `

clean:
	@rm -rf pyspec.tmp
	@rm -f pyspec.tar.gz pyspec_built.tar.gz
	@rm -f *.o *.bak core
	@for i in ${DIRS}; do rm -f $$i/*.o $$i/*.bak ; done
	@rm -fr python/datashm/build
