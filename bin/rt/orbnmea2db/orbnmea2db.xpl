#
# orbnmea2db
# Kent Lindquist
# Lindquist Consulting
# 2003-2004
#
use Datascope ;
use orb;

require "getopts.pl";

chomp( $Program = `basename $0` );

if( ! &Getopts( "vom:r:" ) || $#ARGV < 1 ) {
	die( "Usage: $Program [-v] orbname dbname [after [until]]\n" );
} else {
	$orbname = $ARGV[0];
	$dbname = $ARGV[1];
	if( $#ARGV >= 2 ) {
		eval( "\$after = str2epoch( \"$ARGV[2]\" );" );
		if( ! defined( $after ) ) {
			die( "Failed to convert \"$ARGV[2]\". Bye.\n" ); 
		}
	}
	if( $#ARGV >= 3 ) {
		eval( "\$until = str2epoch( \"$ARGV[3]\" );" );
		if( ! defined( $until ) ) {
			die( "Failed to convert \"$ARGV[3]\". Bye.\n" ); 
		}
	}
} 

if( $opt_v ) {
	$Verbose++;
}

if( $opt_v && $opt_o ) {
	elog_notify( "orbnmea2db: running in overwrite mode\n" );
}

if( ! -e "$dbname" ) {
	open( D, ">$dbname" );
	print D "#\nschema nmea0.1\n";
	close( D );
}

@db = dbopen( "$dbname", "r+" );
@db = dblookup( @db, "", "raw", "", "" );

$orbfd = orbopen( $orbname, "r&" );

if( $opt_m ) {
	$nmatch = orbselect( $orbfd, $opt_m );
} else {
	$nmatch = orbselect( $orbfd, ".*/EXP/NMEA" );

}

if( $Verbose ) {
	print STDERR "$nmatch sources selected\n";
}

if( $opt_r ) {
	$nmatch = orbreject( $orbfd, $opt_r );
	if( $Verbose ) {
		 print STDERR "$nmatch sources selected after reject expression\n";
	}
}

if( defined( $after ) ) {

	orbafter( $orbfd, $after );
}

for( ;; ) {
	($pktid, $srcname, $time, $packet, $nbytes) = orbreap($orbfd) ;

	if( defined( $until ) && $time > $until ) {
		if( $Verbose ) {
			print STDERR "Completed through ", 
				     strtime( $until ), ". Bye.\n";
		}
		exit( 0 );
	}

	if( $srcname !~ m@/EXP/NMEA@ ) {
		if( $Verbose ) {
			print STDERR "Skipping $srcname, does not match /EXP/NMEA\n";
			next;
		}
	}

	( $version, $block ) = unpack( "na*", $packet );
	chomp( $block );
	$block =~ s/\r$//;
	
	$source = $srcname;
	$source =~ s@/.*@@;

	$block =~ /\$([A-Z]+),/ && ( $code = $1 );

	if( $Verbose ) {
		print "From $source at $time we have $code:\n\t$block\n";
	}

	if( $opt_o ) {

		$expr = "source == \"$source\" && nmeacode == \"$code\"";
		$db[3] = dbfind( @db, $expr, -1 );
	}

	if( ! $opt_o || $db[3] < 0 ) {

		$db[3] = dbaddnull( @db );
	}

	dbputv( @db, "source", $source,
		     "time", $time,
		     "nmeacode", $code, 
		     "nmeastring", $block );
}
