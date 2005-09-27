# 
# rtbackup_srb
# Program to back-up Datascope data to a Storage Resource Broker
# Kent Lindquist
# Lindquist Consulting
# 2004
#

use Datascope;
require "getopts.pl";
use Fcntl ':flock';
use rtmail;
use sysinfo;

sub rtbackup_srb_die {
	my( $msg ) = @_;

	if( $failure_email_recipients ne "" ) {

		elog_complain( "Sending failure message to $failure_email_recipients:\n" );

		my( $now ) = epoch2str( now(), "%D (%j) %T %Z" );

		my( $host ) = my_hostname();

    		my ($result, $rmsg) = rtmail(
	     		-to => $failure_email_recipients,
	     		-subject => "rtbackup_srb failure on $host: $now",
	     		-msg => $msg,
	     		-background=>1 
	     		) ;
	}
	
	elog_die( $msg );
}

sub check_lock {
	my( $lockfile_name ) = @_;

	$lockfile_name = ".$lockfile_name";

	if( $opt_v ) {
		elog_notify( "Locking $lockfile_name...." );
	}

	open( LOCK, ">$lockfile_name" );

	if( flock( LOCK, LOCK_EX|LOCK_NB ) != 1 ) {

		rtbackup_srb_die( "Failed to lock '$lockfile_name'! Bye.\n" );
	}

	print LOCK "$$\n"; 

	if( $opt_v ) {
		elog_notify( "Locking $lockfile_name....Locked." );
	}

	system( "orb2db_msg $q $dbname pause" );

	return;
}

sub release_lock {
	my( $lockfile_name ) = @_;

	system( "orb2db_msg $q $dbname continue" );

	$lockfile_name = ".$lockfile_name";
	
	flock( LOCK, LOCK_UN );

	close( LOCK );

	if( $opt_v ) {
		elog_notify( "Unlocked $lockfile_name" );
	}

	return;
}

sub Smkdir_p {
	my( $collection ) = @_;

	if( $opt_v ) {
		elog_notify( "Making top-level collection '$collection'\n" );
	}

	if( ( $rc = system( "$Smkdir_path $collection" ) ) == 0 ) {

		return;
	}	

	# Assume the collection is an absolute path with a home:

	$collection =~ m@(/.*home/[^/]+)(/.*)?@;

	$home = $1;
	
	if( ! defined( $2 ) ) {

		return;
	}

	my( @parts ) = split( m@/@, $2 );

	my( $subcoll ) = $home;

	while( $part = shift( @parts ) ) {

		$subcoll .= "/$part";
		system( "$Smkdir_path $subcoll" );
	}
}

sub make_subcollections {
	my( $top_collection ) = pop( @_ );
	my( @db ) = @_;

	Smkdir_p( $top_collection );

	@dbpaths = dbsort( @db, "-u", "dir" );

	$npaths = dbquery( @dbpaths, dbRECORD_COUNT );

	for( $dbpaths[3] = 0; $dbpaths[3] < $npaths; $dbpaths[3]++ ) {

		$dir = dbgetv( @dbpaths, "dir" );

		if( $opt_v ) {

			elog_notify( "Making sub-collection '$dir'\n" );
		}

		my( @parts ) = split( m@/@, $dir );

		my( $subcoll ) = $top_collection;

		while( $part = shift( @parts ) ) {

			$subcoll .= "/$part";
			system( "$Smkdir_path $subcoll" );
		}
	}
}

elog_init( $0, @ARGV );

$num_errors = 0;
@ARGV_PRESERVE = @ARGV;

if ( ! &Getopts('n:s:p:vefi') || @ARGV != 2 ) { 

	die ( "Usage: rtbackup_srb [-efvi] [-n days] [-p pfname] [-s wfdisc_subset] database collection\n" ) ; 

} else {
	
	if( $opt_v ) {
	
		elog_notify( "Executing $0 " . join( " ", @ARGV_PRESERVE ) . "\n" );
	}

	$collection = pop( @ARGV );
	$dbname = pop( @ARGV );
}

if( $opt_p ) {

	$Pf = $opt_p;

} else {

	$Pf = "rtbackup_srb";
}

if( $opt_v ) {

	$v = "-v";
	$q = "";

} else {

	$v = "";
	$q = "-q";
}

if( $opt_f ) {

	$f = "-f";

} else {

	$f = "";
}

$failure_email_recipients = pfget( $Pf, "failure_email_recipients" );
$Spath = pfget( $Pf, "Spath" );
@replicated_backup_resources = @{pfget( $Pf, "replicated_backup_resources" )};
@backup_tables = @{pfget( $Pf, "backup_tables" )};

if( $collection !~ m@^/([-_a-zA-Z0-9]+)/home/.+@ ) {

	rtbackup_srb_die( 
		  "The SRB Zone must be explicitly specified in the collection ".
	          "name, e.g. /A_ZONE/home/somedir\n" );
} else {

	$Szone = $1;

	if( $opt_v ) {

		elog_notify( "Szone is $Szone\n" );
	}
}

@Scommands = ( "Sput",
	       "Smkdir",
	       "Senv",
	       "SgetU",
	       "Sbkupsrb",
	       "Sreplicate",
	     );

foreach $Scommand ( @Scommands ) {

	$var = "$Scommand" . "_path";

	if( defined( $Spath ) && $Spath ne "" && 
	    -x "$Spath/$Scommand" ) {
		
		$$var = "$Spath/$Scommand";

	} elsif( -x ( $apath = datafile( "PATH", "$Scommand" ) ) ) {
			
		$$var = $apath;

	} else {
		
		rtbackup_srb_die( 
		     "rtbackup_srb: Couldn't find the command '$Scommand'! " .
		     "Please update your path or set the Spath parameter " .
		     "in $Pf.pf. Bye.\n" );
	}
}

if( $opt_v ) {
	elog_notify( "Initializing SRB connection:\n" );
}

$mdasAuthFile = "/tmp/MdasAuth.$<.$$";
$mdasEnvFile = "/tmp/MdasEnv.$<.$$";

$ENV{mdasAuthFile} = $mdasAuthFile;
$ENV{mdasEnvFile} = $mdasEnvFile;

open( A, ">$mdasAuthFile" );
print A pfget( $Pf, "MdasAuth" );
close( A );

open( E, ">$mdasEnvFile" );
print E pfget( $Pf, "MdasEnv" );
close( E );

if( $opt_v ) {
	elog_notify( "Testing SRB connection:\n" );
}

if( ( $rc = system( "$SgetU_path > /dev/null 2>&1" ) ) != 0 ) {

	rtbackup_srb_die( "SRB connection Failed! Bye.\n" );

} else {

	if( $opt_v ) {
		
		elog_notify( "SRB connection Initialized\n" );
	}
}

( $descriptor_dir, $descriptor_basename, $descriptor_suffix ) = 
						parsepath( $dbname );

if( defined( $descriptor_suffix ) && $descriptor_suffix ne "" ) {

	$descriptor_basename .= ".$descriptor_suffix";
}

check_lock( "rtdbclean" );

@db = dbopen( "$dbname", "r+" );

@schema_tables = dbquery( @db, dbSCHEMA_TABLES );

if( ! grep( /wfsrb/, @schema_tables ) ) {

	release_lock( "rtdbclean" );

	rtbackup_srb_die( "No table 'wfsrb' in schema for '$dbname'. Bye!\n" );
}

@dbwfsrb_base = dblookup( @db, "", "wfsrb", "", "" );

if( ! dbquery( @dbwfsrb_base, dbTABLE_IS_WRITABLE ) ) {

	release_lock( "rtdbclean" );

	rtbackup_srb_die( "Table '$dbname.wfsrb' is not writable. Bye!\n" );
}

$wfsrb_table_filename = dbquery( @dbwfsrb_base, dbTABLE_FILENAME );

@dbwfdisc = dblookup( @db, "", "wfdisc", "", "" );
undef @dbview;

if( $opt_s ) {

	if( $opt_v ) {

		elog_notify( "Subsetting wfdisc for records matching " .
			     "'$opt_s'\n" );
	}

	@dbwfdisc = dbsubset( @dbwfdisc, "$opt_s" );

	@dbview = @dbwfdisc;
}

if( $opt_n ) {
	
	$min_lddate = str2epoch( "now" ) - $opt_n * 86400;

	if( $opt_v ) {

		elog_notify( "Subsetting wfdisc for records with lddate newer than " .
			     strtime( $min_lddate ) . " UTC\n" );
	}

	@dbwfdisc = dbsubset( @dbwfdisc, "lddate >= $min_lddate" );

	if( defined( @dbview ) ) {
		
		dbfree( @dbview );

		undef @dbview;
	}

	@dbview = @dbwfdisc;
}

if( $opt_e ) {

	$jdate_today = epoch2str( str2epoch( "now" ), "%Y%j" );

	if( $opt_v ) {

		elog_notify( "Excluding data on and later than today's " .
			     "jdate of $jdate_today\n" );
	}
	
	@dbwfdisc = dbsubset( @dbwfdisc, "jdate < $jdate_today" );

	if( defined( @dbview ) ) {
		
		dbfree( @dbview );

		undef @dbview;
	}

	@dbview = @dbwfdisc;
}

@dbwfsrb = dblookup( @db, "", "wfsrb", "", "" );

if( $opt_n ) {

	$dbwfdisc[3] = dbSCRATCH;

	$min_wfdisc_time = dbex_eval( @dbwfdisc, "min(time)" );
	$max_wfdisc_endtime = dbex_eval( @dbwfdisc, "max(endtime)" );

	$dbwfdisc[3] = dbALL;

	$expr = "time <= $max_wfdisc_endtime && endtime >= $min_wfdisc_time";

	elog_notify( "Subsetting wfsrb table with '$expr'\n" );

	@dbwfsrb = dbsubset( @dbwfsrb, $expr );
}

@db = dbnojoin( @dbwfdisc, @dbwfsrb );

$nrecs_new_wfsrb = dbquery( @db, dbRECORD_COUNT );

if( $nrecs_new_wfsrb <= 0 ) {

	if( $opt_v ) {
		
		elog_notify( "No records to add to SRB.\n" );
	}

} else {

	make_subcollections( @db, $collection );

	for( $db[3] = 0; $db[3] < $nrecs_new_wfsrb; $db[3]++ ) {
		
		( $sta, $chan, $time, $wfid, $chanid, $jdate, $endtime,
	  	$nsamp, $samprate, $calib, $calper, $instype, $segtype,
  	  	$datatype, $clip, $dir, $dfile, $foff, $commid ) =
	
			dbgetv( @db,
				"sta", "chan", "time", "wfid",
				"chanid", "jdate", "endtime",
				"nsamp", "samprate", "calib",
				"calper", "instype", "segtype",
				"datatype", "clip", "dir", "dfile",
				"foff", "commid" );
	
		$filename = dbextfile( @db );
	
		$Scoll = $collection . "/" . $dir;
		$Sobj = $dfile;
	
		# Don't re-add the same file just because of different 
		# foff values for different rows:
	
		if( ! defined( $Added{$filename} ) ) {
	
			if( $opt_v ) {
				elog_notify( "Adding file $dfile to $Szone:$Scoll\n" );
			}
	
			$rc = system( "$Sput_path $v $f $filename $Scoll" );
	
			if( $rc == -1 ) {
				
				release_lock( "rtdbclean" );

				rtbackup_srb_die( "Fatal: Perl failed to launch Sput for $filename: $!. Bye!\n" );
			} elsif( $rc != 0 ) {
	
				elog_complain( "Sput failed for $filename!!\n" );
	
				$num_errors++;
	
				next;
			}
	
			$Added{$filename}++;
		}
	
		$dbwfsrb_base[3] = dbaddnull( @dbwfsrb_base );
	
		dbputv( @dbwfsrb_base,
			"sta", $sta,
			"chan", $chan,
			"time", $time,
			"wfid", $wfid,
			"chanid", $chanid,
			"jdate", $jdate,
			"endtime", $endtime,
			"nsamp", $nsamp,
			"samprate", $samprate,
			"calib", $calib,
			"calper", $calper,
			"instype", $instype,
			"segtype", $segtype,
			"datatype", $datatype,
			"clip", $clip,
			"Szone", $Szone,
			"Scoll", $Scoll,
			"Sobj", $Sobj,
			"foff", $foff,
			"commid", $commid );
	}
}

unless( $opt_i ) {

	$descriptor_filename = dbquery( @db, dbDATABASE_FILENAME );

	if( $opt_v ) {
		elog_notify( "Adding $descriptor_filename to $Szone:$collection\n" );
	}

	# Always force overwrite:
	$rc = system( "$Sput_path $v -f $descriptor_filename $collection/$descriptor_basename" );

	if( $rc == -1 ) {
	
		release_lock( "rtdbclean" );
	
		rtbackup_srb_die( "Fatal: Perl failed to launch Sput command for $descriptor_filename: $!. Bye!\n" );

	} elsif( $rc != 0 ) {

		elog_complain( "Sput failed for $descriptor_filename!!\n" );
	
		$num_errors++;
	}

	$tables_version = str2epoch( "now" );

	foreach $table ( @backup_tables ) {

		@db = dblookup( @db, "", "$table", "", "" );

		$present = dbquery( @db, dbTABLE_PRESENT );

		if( ! $present ) { 

			next; 
		}

		$table_filename = dbquery( @db, dbTABLE_FILENAME );

		if( $opt_v ) {
			elog_notify( "Adding $table_filename to $Szone:$collection " .
			     	"as $descriptor_basename.$table\n" );
		}
	
		$rc = system( "$Sput_path $v -f $table_filename $collection/$descriptor_basename.$table" );

		if( $rc == -1 ) {

			release_lock( "rtdbclean" );

			rtbackup_srb_die( "Fatal: Perl failed to launch Sput $table_filename: $!. Bye!\n" );

		} elsif( $rc != 0 ) {

			elog_complain( "Sput failed for $table_filename!!\n" );

			$num_errors++;

		} else {

			if( $opt_v ) {
				elog_notify( "Replicating $descriptor_basename.$table " .
				     	"with version string '$tables_version'\n" );
			}

			$rc = system( "$Sreplicate_path $v -V $tables_version " .
			      	"$collection/$descriptor_basename.$table" );

			if( $rc == -1 ) {

				release_lock( "rtdbclean" );

				rtbackup_srb_die( "Fatal: Perl failed to launch Sreplicate for $table_filename: $!. Bye!\n" );
	
			} elsif( $rc != 0 ) {

				elog_complain( "Sreplicate failed for $table_filename!!\n" );

				$num_errors++;
			}
		}
	}
}

dbclose( @db );

release_lock( "rtdbclean" );

unless( $opt_i ) {

	foreach $resource ( @replicated_backup_resources ) {

		if( $opt_v ) {
			
			elog_notify( "Backing up top-level collection " .
				     "to resource '$resource'\n" );
		}

		$rc = system( "$Sbkupsrb_path -r -S $resource $collection" );

		if( $rc == -1 ) {

			rtbackup_srb_die( "Fatal: Perl failed to launch Sbkupsrb for resource '$resource': $!. Bye!\n" );

		} elsif( $rc != 0 ) {

			elog_complain( "Sbkupsrb failed for resource '$resource'!!\n" );

			$num_errors++;
		}
	}
}

unlink( "$mdasAuthFile" );
unlink( "$mdasEnvFile" );

if( $num_errors > 0 ) {

	rtbackup_srb_die( "Total of $num_errors errors during run " . 
			  "(see rtbackup_srb log for details)\n" );

} else {

	elog_notify( "Total of $num_errors errors during run\n" );
	exit( 0 );
}
