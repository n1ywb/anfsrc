
DEST=$(ANF)

Include :: $(DEST)/include/anfmake
install :: $(DEST)/include/anfmake

all Include install installMAN pf relink tags :: FORCED
	@-DIRS="$(DIRS)" ;\
	for i in $$DIRS ; do \
	    printf "+    %-40s  %s\n" $$i "`date`" ; \
	    if [ -f $$i/Makefile -o -f $$i/makefile ] ; then ( cd $$i && $(MAKE) $@ ; ) ; else if [ -d $$i ] ; then echo Error: no Makefile in `pwd`/$$i ; fi ; fi ; \
	done

clean :: FORCED
	@-DIRS="$(DIRS)" ;\
	for i in $$DIRS ; do \
	    printf "+    %-40s  %s\n" $$i "`date`" ; \
	    if [ -f $$i/Makefile -o -f $$i/makefile ] ; then ( cd $$i && $(MAKE) $@ ; ) ; else if [ -d $$i ] ; then echo Error: no Makefile in `pwd`/$$i ; fi ; fi ; \
	done
	$(RM) anfmake

uninstall :: FORCED
	@-if [ -r $(DEST)/include/anfmake ] ; then \
	    DIRS="$(DIRS)" ;\
	    for i in $$DIRS ; do \
	        printf "+    %-40s  %s\n" $$i "`date`" ; \
	        if [ -f $$i/Makefile -o -f $$i/makefile ] ; then ( cd $$i && $(MAKE) $@ ; ) ; else if [ -d $$i ] ; then echo Error: no Makefile in `pwd`/$$i ; fi ; fi ; \
	    done ; \
	    $(RM) $(DEST)/include/anfmake; \
	fi

FORCED:

$(DEST)/include/anfmake: anfmake
	deposit -r anfmake $@

anfmake: solaris linux darwin darwin-intel common
	$(RM) -f $@
	@case `uname -s` in \
	    SunOS) cp solaris $@; cp solaris $@ ;; \
	    Linux) cp linux   $@; echo cp linux $@ ;; \
	    Darwin) case `uname -p` in \
		powerpc) cp darwin  $@; echo cp darwin $@ ;; \
		i386) cp darwin-intel  $@; echo cp darwin-intel $@ ;; \
		*) echo "Error: processor type `uname -p` on Darwin not recognized." ;; \
	    esac ;; \
	    *)  echo "Error: System type `uname -s` not recognized." ;;\
	esac
	cat common >> $@

