#!/opt/antelope/current/bin/perl

use lib "/opt/antelope/current/data/perl" ;
require 'cgi-lib.pl';

$registrydb="~rt/db/ucsd_orbregistry";

use orb;
use Datascope;
use Socket;

$match="";
$match2="";
&ReadParse;

%matchhash;


if (defined $in{"match"})
{
    $match=$in{"match"};
    $match =~ s/\%2F/\//g;
    $match =~ s/\%5C/\\/g;
    $match =~ s/\\\//\//g;
    $match2=" ($match)";
    $match =~ s/\//\\\//g;
    
}
print "Content-type: text/html\nPragma: no-cache\n\n";
if ($in{"mode"} eq "orb")
{
    $mode2="Server";
    print "<HTML><HEAD><TITLE>ORB Topo $mode2 Display$match2</TITLE></HEAD>\n<BODY BGCOLOR=FFFFFF>";
}
elsif ($in{"mode"} eq "connection")
{
    $mode2="Connection";
    print "<HTML><HEAD><TITLE>ORB Topo $mode2 Display$match2</TITLE></HEAD>\n<BODY BGCOLOR=FFFFFF>";
}
elsif ($in{"mode"} eq "process")
{
    $mode2="Client";
    print "<HTML><HEAD><TITLE>ORB Topo $mode2 Display</TITLE></HEAD>\n<BODY BGCOLOR=FFFFFF>";
}

if ($match ne "" && $in{"mode"} ne "process")
{
    print "<TABLE WIDTH=100%><TR><TD WIDTH=100%><CENTER><H1>ORB Topology $mode2 Display for$match2</H1></CENTER>\n<HR></TD><TD ALIGN=RIGHT><A HREF=\"http://roadnet.ucsd.edu/\"><IMG SRC=\"http://roadnet.ucsd.edu/images/sub-sidebar_r13_c1.jpg\" WIDTH=156 HEIGHT=103 BORDER=0></A></TD></TR></TABLE>";
}
else
{
    print "<TABLE WIDTH=100%><TR><TD WIDTH=100%><CENTER><H1>ORB Topology $mode2 Display</H1></CENTER>\n<HR></TD><TD ALIGN=RIGHT><A HREF=\"http://roadnet.ucsd.edu/\"><IMG SRC=\"http://roadnet.ucsd.edu/images/sub-sidebar_r13_c1.jpg\" WIDTH=156 HEIGHT=103 BORDER=0></A></TD></TR></TABLE>";
}

if ($in{"mode"} eq "orb")
{
    ($orbname,$orbport)=split /:/, $in{"orbname"};

    $orbname2=$orbname;
    $srcnameip=$orbname;
    $srcnameip=inet_aton($srcnameip);
    $srcnameip=gethostbyaddr($srcnameip, AF_INET);
    if ($srcnameip ne "")
    { $orbname2=$srcnameip; }

    $orbport2=$orbport;
    foreach $portname (`egrep \"\s*$orbport\s*\" /opt/antelope/current/data/pf/orbserver_names.pf`)
    {
	if ($portname =~ /\s+$orbport\s+/)
	{
	    ($orbport2,$mold)=split /\s+/,$portname;
	}
    }

    $n=`/opt/antelope/current/bin/dbsubset $registrydb.servers "serveraddress=='$orbname' && serverport==$orbport" | /opt/antelope/current/bin/dbselect - host started orb_start nclients nsources maxdata when version`;
    ($host,$started,$orb_start,$nclients,$nsources,$maxdata,$when,$version)=split /\s+/, $n, 8;
    print "<h3>Server Info</H3>\n";
    $when = strtime($when);
    print "<B>ORB Name:</B> $orbname2:$orbport2 (valid as of $when UTC)<BR>\n";
    print "<B>ORB Location:</B> $host<BR>\n";
    print "<B>ORB Software:</B> $version<BR>\n";
    $started=strtdelta(time()-$started);
    $orb_start=strtdelta(time()-$orb_start);
    print "<B>ORB Uptime:</B> $started (last initalized $orb_start)<BR>\n";
    $maxdata=sprintf("%.2f MB",$maxdata/1024.0/1024.0);
    print "<B>ORB Stats:</B> $nsources sources, $nclients clients, $maxdata buffer size<BR>\n";
    print "<B>More Info:</B><A HREF=\"#client\">Clients</A> <A HREF=\"#sources\">Sources</A><BR>\n<HR>\n<H3>Clients</H3>";

    open(FOO,"> /tmp/orbtopo.$$.dot");
    print FOO "Digraph orbtopo {\n\trankdir=\"LR\";\n";
    print FOO "\t\"$orbname2:$orbport2\" [shape=hexagon,style=filled,fillcolor=lightgoldenrod1]\n";
    foreach $i (`/opt/antelope/current/bin/dbsubset $registrydb.clients "serveraddress=='$orbname' && serverport==$orbport" | /opt/antelope/current/bin/dbselect - thread perm latency_sec what`)
    {
	chomp($i);
	$i=~s/^\s+//;
	($thread,$perm,$latency,$what,$j2)=split /\s+/, $i, 6;
	chomp($what);
	$latency=strtdelta($latency);
	$what=~s/\s\s+//g;
	print FOO "\t\"$thread\" [shape=hexagon,style=filled,fillcolor=lightgoldenrod1, label=\"$what\", href=\"orbtopo_detail.cgi?mode=process&threadid=$thread&orbname=$orbname:$orbport&match=$match\"]\n";
	if ($perm =~ /r/)
	{
	    print FOO "\t\"$orbname2:$orbport2\"->\"$thread\" [color=blue, label=\"latency: $latency\"]";
	}
	else
	{
	    print FOO "\t\"$thread\"->\"$orbname2:$orbport2\" [color=blue, label=\"latency: $latency\"]";
	}
    }
    print FOO "}\n";
    close(FOO);

    `/usr/bin/dot -Tpng -o /var/Web/tmp/orbtopo.$$.png /tmp/orbtopo.$$.dot 2>/dev/null`;
    $map=`/usr/bin/dot -Tcmapx -o /dev/stdout /tmp/orbtopo.$$.dot 2>/dev/null`;
    
    print "<BR><A NAME=\"clients\"><img src=\"/tmp/orbtopo.$$.png\" border=0 usemap=\"#orbtopo\" ismap>\n$map\n";
    
    if ($match ne "")
    {
	print "<BR>\n<HR>\n<A NAME=\"sources\"><H3>Sources matching regex$match2</H3>\n";
    }
    else
    {
	print "<BR>\n<HR>\n<A NAME=\"sources\"><H3>All Sources in $orbname2:$orbport2</H3>\n";
    }

    print "<TABLE BORDER=0>\n<TR><TH>Source Name</TH><TH>Latency</TH><TH>Duration</TH><TH>Size</TH></TR>\n";
    $scnt=0;
    $matchsearch="";
    if ($match ne "")
    {
	$matchsearch=" && srcname =~ /$match/";
    }
    foreach $i (`/opt/antelope/current/bin/dbsubset $registrydb.sources "serveraddress=='$orbname' && serverport==$orbport$matchsearch" | /opt/antelope/current/bin/dbselect - srcname latency_sec soldest_time slatest_time nbytes`)
    {
	($srcname,$latency,$sold,$snew,$bytes)=split /\s+/, $i;
	$latency=strtdelta($latency);
	$stime=strtdelta($snew-$sold);
	$bytes=$bytes/1024.0/1024.0;
	printf "<TR><TD><A HREF=\"orbtopo.cgi?match=$srcname\">$srcname</A></TD><TD>$latency</TD><TD>$stime</TD><TD>%.2f MB</TD></TR>\n", $bytes;
	$scnt++;
    }
    print "</TABLE>\n<BR>\n$scnt sources found.</BODY></HTML>\n";
    unlink("/tmp/orbtopo.$$.dot");
    

}
elsif ($in{"mode"} eq "connection")
{
    print "Bug Kent! I don't know the relation between connections and clients..\n";
    print "</BODY></HTML>\n";
}
elsif ($in{"mode"} eq "process")
{
    ($orbname,$orbport)=split /:/, $in{"orbname"};

    $srcnameip=$orbname;
    $srcnameip=inet_aton($srcnameip);
    $srcnameip=gethostbyaddr($srcnameip, AF_INET);
    if ($srcnameip ne "")
    { $orbname2=$srcnameip; }

    foreach $portname (`egrep \"\s*$orbport\s*\" /opt/antelope/current/data/pf/orbserver_names.pf`)
    {
	if ($portname =~ /\s+$orbport\s+/)
	{
	    ($orbport2,$mold)=split /\s+/,$portname;
	}
    }

    $thread=$in{"threadid"};

    $n=`/opt/antelope/current/bin/dbsubset $registrydb.clients "serveraddress=='$orbname' && serverport==$orbport && thread==$thread" | /opt/antelope/current/bin/dbselect -F : - written read started latency_sec select reject clientaddress perm what`;
    chomp($n);
    $n=~s/^\s+//;
    ($write,$read,$start,$latency,$select,$reject,$add,$perm,$what)=split /:/, $n, 9;
    if ($add !~ /127\.0\.0\.1/)
    {
	$srcnameip=$add;
	$srcnameip=inet_aton($srcnameip);
	$srcnameip=gethostbyaddr($srcnameip, AF_INET);
	if ($srcnameip ne "")
	{ $add2=$srcnameip; }
    }
    else
    {
	$add2=$orbname2;
    }

    print "<B>Running on:</B> $add2<BR>\n";
    print "<B>Process Name:</B> $what<BR>\n";
    print "<HR><BR>";
    print "<B>ORB Name:</B> $orbname2:$orbport2<BR>\n";
    $mod="write mode";
    if ($perm eq "r")
    {
	$mod="read mode";
    }
    printf "<B>ORB Data:</B> read: %.2f MB write: %.2f MB $mod<BR>\n",$read/1024.0/1024.0,$write/1024.0/1024.0;
    if ($select =~ /^\s+$/)
    {	$select=".*";}
    if ($reject =~ /^\s+$/)
    {	$reject="None";}
    printf "<B>ORB Regex:</B> select /$select/, reject /$reject/\n";
    $latency=strtdelta($latency);
    $start=strtdelta(time()-$start);
    print "<HR><BR>";
    print "<B>Process timing:</B> Latency: $latency, duration: $start\n<BR><BR>\n";
    print "<B>ORBs running this software:</B>\n\n<TABLE>";
    foreach $i (`/opt/antelope/current/bin/dbsubset $registrydb.clients "what=~/^orb2orb.*/" | /opt/antelope/current/bin/dbselect -F : - serveraddress serverport latency_sec what`)
    {
	($sadd,$sport,$lat,$what) = split /:/, $i, 4;
	$sadd =~ s/^\s+//;
	$sport =~ s/^\s+//;
	$sadd =~ s/\s+$//;
	$what =~ s/^\s+//;
	$what =~ s/\s+$//;
	$sport =~ s/\s+$//;
	$sadd2=$sadd;
	$sport2=$sport;
	$srcnameip=$sadd;
	$srcnameip=inet_aton($srcnameip);
	$srcnameip=gethostbyaddr($srcnameip, AF_INET);
	if ($srcnameip ne "")
	{ $sadd2=$srcnameip; }
	
	foreach $portname (`egrep \"\s*$sport\s*\" /opt/antelope/current/data/pf/orbserver_names.pf`)
	{
	    if ($portname =~ /\s+$sport\s+/)
	    {
		($sport2,$mold)=split /\s+/,$portname;
	    }
	}
	$lat=strtdelta($lat);
	print "<TR><TD>*</TD><TD><A HREF=\"orbtopo_detail.cgi?mode=orb&orbname=$sadd:$sport\">$sadd2:$sport2</A></TD><TD>$lat</TD><TD>$what</TD></TR>\n";
    }
    print "</TABLE>";
    print "</BODY></HTML>\n";
}
