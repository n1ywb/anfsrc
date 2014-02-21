BIN=dmcorbreport

include $(ANFMAKE)

ipdb: GeoLiteCity.dat

GeoLiteCity.dat: GeoLiteCity.dat.gz
	rm -f $@
	gzip -d $@.gz

GeoLiteCity.dat.gz: FORCED
	curl -O http://geolite.maxmind.com/download/geoip/database/$@
