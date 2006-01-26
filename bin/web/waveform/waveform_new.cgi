#!/opt/antelope/current/bin/perl
use lib "/opt/antelope/current/data/perl";

use orb;
use Datascope;
require 'cgi-lib.pl';

$program="waveform_new.cgi";
$antpath="/opt/antelope/current/bin";
@dirs=("db","sccdbs","smerdbs","hpwrendb","siodbs","sdscdbs");
$ENV{"PFPATH"}="/opt/antelope/current/data/pf:/home/rt/pf";
$dbroot="/home/rt/rtsystems/roadnet";
$timezone_val="UTC";
$calibopt="Calibrated";
$titlelookup="/var/Web/waveform_titles.txt";
$url="n=n";
$level=0;
$mode="init";
$maxlevel=1;
$ymin="";
$ymax="";
$custom="None";
$capp="All";
$adv="off";
$conv = "1.0";
$coff = "0.0";
$sizeh = "640";
$sizev = "288";
$graph_format = "png";

&ReadParse;

if (defined $in{"mode"})
{
    $mode=$in{"mode"};
}

if (defined $in{"level"})
{
    $level=$in{"level"};
    #$url="level=$level";
}

if (defined $in{"maxlevel"})
{
    $maxlevel=$in{"maxlevel"};
    $url="maxlevel=$maxlevel";
}

if (defined $in{"adv"})
{
    $adv=$in{"adv"};
    $url.="&adv=$adv";
}

if (defined $in{"custom"} && $adv eq "on")
{
    $custom=$in{"custom"};
    if ($custom ne "None")
    {
	($nconv,$conv,$coff)=split /;/, $custom, 3;
	$url.="&conv=$conv&nconv=$nconv&econv=on&coff=$coff";
	$econv="on";
	$econvi=1;
     }
}

if (defined $in{"timezone"})
{
    $timezone_val=$in{"timezone"};
    $url.="&timezone=$timezone_val";
}

if (defined $in{"calibopt"} && $adv eq "on")
{
    $calibopt=$in{"calibopt"};
    $url.="&calibopt=$calibopt";
}

if (defined $in{"econv"} && $custom eq "None" && $adv eq "on")
{
    $econv=$in{"econv"};
    $url.="&econv=$econv";
    $econvi=0;
    if ($econv eq "on")
    {
	$econvi=1;
    }
}
if (defined $in{"capp"} && $adv eq "on")
{
    $capp=$in{"capp"};
    $url.="&capp=$capp";
}

if (defined $in{"conv"} && $custom eq "None" && $adv eq "on")
{
    $conv=$in{"conv"};
    $url.="&conv=$conv";
}

if (defined $in{"coff"} && $custom eq "None" && $adv eq "on")
{
    $coff=$in{"coff"};
    $url.="&coff=$coff";
}

if (defined $in{"nconv"} && $custom eq "None" && $adv eq "on")
{
    $nconv=$in{"nconv"};
    $url.="&nconv=$nconv";
}

if (defined $in{"ymin"} && $adv eq "on")
{
    $ymin=$in{"ymin"};
    $url.="&ymin=$ymin";
}

if (defined $in{"ymax"} && $adv eq "on")
{
    $ymax=$in{"ymax"};
    $url.="&ymax=$ymax";
}

if (defined $in{"sizeh"} && $adv eq "on")
{
    $sizeh=$in{"sizeh"};    
    if ($sizeh < 50)
    {
	$sizeh = 50;
    }
    $url.="&sizeh=$sizeh";
}

if (defined $in{"sizev"} && $adv eq "on")
{
    $sizev=$in{"sizev"};
    if ($sizev < 50)
    {
	$sizev = 50;
    }
    $url.="&sizev=$sizev";
}

if (defined $in{"form"} && $adv eq "on")
{
    $graph_format=$in{"form"};
    if ($graph_format ne "ps")
    {
	$graph_format="png";
    }
    $url.="&form=$graph_format";
}

if (defined $in{"gridopt"})
{
    $gridopt=$in{"gridopt"};
    $url.="&gridopt=$gridopt";
}

if ($level>0)
{
    $start=$in{"start"};
    $end=$in{"end"};
    $url.="&start=$start&end=$end";
}

for ($lcv=0;$lcv<$level;$lcv++)
{
    my $dbloop=$in{"db$lcv"};
    my $stachanloop=$in{"stachan$lcv"};
    my $samprateloop=$in{"samprate$lcv"};
    my $segtypeloop=$in{"segtype$lcv"};
    $url.="&db$lcv=$dbloop&stachan$lcv=$stachanloop&samprate$lcv=$samprateloop&segtype$lcv=$segtypeloop";
}

if ($mode eq "init")
{
    foreach $d (@dirs)
    {
	foreach $file (`ls $dbroot/$d/`)
	{
	    open(file2,"$dbroot/$d/$file");
	    if (-f file2)
	    {
		@s=`head -3 $dbroot/$d/$file`;
		if ($s[1] =~ /^schema\s+rt1.0/)
		{
		    chomp($file);
		    $a="_";
		    push(@l,"$d$a$file");
		}
	    }
	    close(file2);
	}
    }

    my $str="Select a database";
    if ($level>0)
    {
	$str=sprintf("Select a database for dataset %d",$level+1);
    }

    #@l=`/bin/grep rt1.0 $dbroot/db/*`;
    print "Content-type: text/html\nPragma: no-cache\n\n";
    print "<HTML><HEAD><TITLE>ROADNet Waveform Display (Select Database)</TITLE></HEAD>\n<BODY BGCOLOR=WHITE><TABLE WIDTH=100%><TD><H1>ROADNet Waveform Display</H1>\n<HR></TD><TD ALIGN=RIGHT><A HREF=\"http://roadnet.ucsd.edu/\"><IMG BORDER=0 SRC=\"/images/waveform/roadnet-logo-small.jpg\"></A></TD></TABLE>\n<h3>$str</h3>\n<TABLE WIDTH=100%><TD><UL>\n";
    foreach $item (@l)
    {
	(@c1)=split /\//, $item;
	($db,$c2)=split /:/, $c1[$#c1];
	($c1,$dbs)=split /_/, $db;
	print "<LI><A HREF=\"$program?$url&level=$level&mode=sta&db$level=$db\">$dbs</A></LI>\n";
    }
    print "</UL></TD><TD ALIGN=RIGHT>";
    &print_sidebar;
    print "</TD></TABLE>\n</BODY></HTML>\n";	
    exit(0);
}
elsif ($mode eq "sta")
{
    ($ddir,$dbf)=split /_/, $in{"db$level"};
    $db=$in{"db$level"};

    my $str="Select a Station/Channel";
    if ($level>0)
    {
	$str=sprintf("Select a Station/Channel for dataset %d",$level+1);
    }

    print "Content-type: text/html\nPragma: no-cache\n\n";
    print "<HTML><HEAD><TITLE>ROADNet Waveform Display (Select Station/Channel)</TITLE></HEAD>\n<BODY BGCOLOR=WHITE><TABLE WIDTH=100%><TD><H1>ROADNet Waveform Display</H1>\n<HR></TD><TD ALIGN=RIGHT><A HREF=\"http://roadnet.ucsd.edu/\"><IMG BORDER=0 SRC=\"/images/waveform/roadnet-logo-small.jpg\"></A></TD></TABLE>\n<h3>$str</h3>\n<TABLE WIDTH=100%><TD><UL>\n";
    $first=1;

    foreach $i (`cat /var/Web/status.txt`)
    {
	($net,$sta,$chan,$rest)=split /\s/,$i, 4;
	$sta=substr($sta,0,6);
	$chan=substr($chan,0,8);
	$statushash{"$net$sta$chan"}=$rest;
    }

    $n="";
    if ($dbf eq "pfo")
    {
	$n="n";
    }
    foreach $item (`$antpath/dbjoin $dbroot/$ddir/$dbf.schanloc $dbroot/$ddir/$dbf.snetsta | $antpath/dbselect - snet sta chan | sort -u -k1,1 -k2,2 -k3,3$n`)
    {
	chomp($item);
	($net,$sta,$cha,$c1)=split /\s+/,$item;
	$item="$sta $cha";
	$item =~ s/ +/_/g;
	#$item =~ s/_$//;
	if ($sta ne $last_sta)
	{
	    if ($first)
	    {
		$first=0;
		print "<LI>$sta\n<UL>\n";
	    }
	    else
	    {
		print "</UL></LI>\n<LI>$sta\n<UL>\n";
	    }
	}

	($loc,$cur,$calib,$segtype,$samprate,$val,$cval)=split /\s/, $statushash{"$net$sta$cha"};

	$range24=$cur-24*60*60;
	$range48=$cur-48*60*60;
	$range7=$cur-7*24*60*60;
	$c2="_$cha";

	my $str="&mode=graph$maxlevel&level=$level";
	if ($level+1<$maxlevel)
	{
	    my $newlevel=$level+1;
	    $str="&mode=init&level=$newlevel";
	}

	if ($level == 0)
	{
	    print "<LI><A HREF=\"$program?$url&level=$level&mode=stachan&db$level=$db&stachan$level=$item\">$cha</A> &nbsp&nbsp(<A HREF=\"$program?$url$str&db$level=$db&stachan$level=$item&start=$range24&end=$cur&samprate$level=$samprate&segtype$level=$segtype\">24 hr</A>, <A HREF=\"$program?$url$str&db$level=$db&stachan$level=$item&start=$range48&end=$cur&samprate$level=$samprate&segtype$level=$segtype\">48 hr</A>, <A HREF=\"$program?$url$str&db$level=$db&stachan$level=$item&start=$range7&end=$cur&samprate$level=$samprate&segtype$level=$segtype\">7 days</A>)</LI>";
	}
	else
	{
	    print "<LI><A HREF=\"$program?$url$str&db$level=$db&stachan$level=$item&samprate$level=$samprate&segtype$level=$segtype\">$cha</A></LI>";
	}
	$last_sta=$sta;
    }
    print "</UL></LI></UL></TD><TD ALIGN=RIGHT VALIGN=TOP>\n";
    &print_sidebar;
    print "</TD></TABLE></BODY></HTML>\n";	
}
elsif ($mode eq "stachan")
{
    ($ddir,$dbf)=split /_/, $in{"db$level"};
    $db=$in{"db$level"};
    $stachan=$in{"stachan$level"};
    ($sta,$chan)=split /\_/,$stachan,2;

    $start=$end=0;

    foreach $item (`$antpath/dbsubset $dbroot/$ddir/$dbf.wfdisc "sta == '$sta' && chan == '$chan'" | $antpath/dbselect - time endtime samprate segtype`)
    {
	($c1, $m1,$m2,$samprate,$segtype,$c1)=split /\s+/,$item;
	chomp($segtype);
	if ($segtype eq "")
	{
	    $segtype="NONE";
	}
	if ($start == 0)
	{
	    $start=$m1;
	}
	if ($m1<$start)
	{
	    $start=$m1;
	}
	
	if ($m2>$end)
	{
	    $end=$m2;
	}
    }

    print "Content-type: text/html\nPragma: no-cache\n\n";
    print "<HTML><HEAD><TITLE>ROADNet Waveform Display (Select time range)</TITLE></HEAD>\n<BODY BGCOLOR=WHITE><TABLE WIDTH=100%><TD><H1>ROADNet Waveform Display</H1>\n<HR></TD><TD ALIGN=RIGHT><A HREF=\"http://roadnet.ucsd.edu/\"><IMG BORDER=0 SRC=\"/images/waveform/roadnet-logo-small.jpg\"></A></TD></TABLE><BR><TABLE WIDTH=100%><TD><B>Database:</B> $dbf<BR>\n<B>Station_Channel:</B> $stachan<BR>\n";
    $in{"segtype0"}=$segtype;
    $c=`$antpath/trlookup_segtype $segtype`;
    chomp($c);
    if ($c eq "")
    { $c = "no units"; }
    print "<B>Units:</B> $c<BR>";
    $st_ascii=`$antpath/epoch -o $timezone_val $start`;
    chomp($st_ascii);
    $end_ascii=`$antpath/epoch -o $timezone_val $end`;
    chomp($end_ascii);
    print "<B>Data starts:</B> $st_ascii<BR>";
    print "<B>Data ends:</B> $end_ascii<BR>";
    $range=($end-$start)/(24*60*60);
    printf("<B>Data Span:</B> %0.3f Days<BR>",$range);

    $latency=(time()-$end)/60/60;
    printf("<B>Data Latency:</B> %0.2f hours<BR>",$latency);
    print "<P><H3>Select a time range to display</h3>\n";
    print "<UL>";
    $cur=$end;

    my $str="&mode=graph$maxlevel&level=$level";
    if ($level+1<$maxlevel)
    {
	my $newlevel=$level+1;
	$str="&mode=init&level=$newlevel";
    }

    $range=$cur-5*60;
    print "<LI><A HREF=\"$program?$url$str&db$level=$db&stachan$level=$stachan&start=$range&end=$cur&samprate$level=$samprate&segtype$level=$segtype\">Last 5 min</A> (<A HREF=\"$program?$url&mode=raw&db=$db&stachan=$stachan&start=$range&end=$cur&samprate=$samprate&segtype=$segtype\">raw</A>)</LI>\n";
    $range=$cur-1*60*60;
    print "<LI><A HREF=\"$program?$url$str&db$level=$db&stachan$level=$stachan&start=$range&end=$cur&samprate$level=$samprate&segtype$level=$segtype\">Last 1 hr</A> (<A HREF=\"$program?$url&mode=raw&db=$db&stachan=$stachan&start=$range&end=$cur&samprate=$samprate&segtype=$segtype\">raw</A>)</LI>\n";
    $range=$cur-6*60*60;
    print "<LI><A HREF=\"$program?$url$str&db$level=$db&stachan$level=$stachan&start=$range&end=$cur&samprate$level=$samprate&segtype$level=$segtype\">Last 6 hrs</A> (<A HREF=\"$program?$url&mode=raw&db=$db&stachan=$stachan&start=$range&end=$cur&samprate=$samprate&segtype=$segtype\">raw</A>)</LI>\n";
    $range=$cur-12*60*60;
    print "<LI><A HREF=\"$program?$url$str&db$level=$db&stachan$level=$stachan&start=$range&end=$cur&samprate$level=$samprate&segtype$level=$segtype\">Last 12 hrs</A> (<A HREF=\"$program?$url&mode=raw&db=$db&stachan=$stachan&start=$range&end=$cur&samprate=$samprate&segtype=$segtype\">raw</A>)</LI>\n";
    $range=$cur-24*60*60;
    print "<LI><A HREF=\"$program?$url$str&db$level=$db&stachan$level=$stachan&start=$range&end=$cur&samprate$level=$samprate&segtype$level=$segtype\">Last 24 hrs</A> (<A HREF=\"$program?$url&mode=raw&db=$db&stachan=$stachan&start=$range&end=$cur&samprate=$samprate&segtype=$segtype\">raw</A>)</LI>\n";
    $range=$cur-48*60*60;
    print "<LI><A HREF=\"$program?$url$str&db$level=$db&stachan$level=$stachan&start=$range&end=$cur&samprate$level=$samprate&segtype$level=$segtype\">Last 2 days</A> (<A HREF=\"$program?$url&mode=raw&db=$db&stachan=$stachan&start=$range&end=$cur&samprate=$samprate&segtype=$segtype\">raw</A>)</LI>\n";
    $range=$cur-7*24*60*60;
    print "<LI><A HREF=\"$program?$url$str&db$level=$db&stachan$level=$stachan&start=$range&end=$cur&samprate$level=$samprate&segtype$level=$segtype\">Last 7 days</A> (<A HREF=\"$program?$url&mode=raw&db=$db&stachan=$stachan&start=$range&end=$cur&samprate=$samprate&segtype=$segtype\">raw</A>)</LI>\n";
    $range=$cur-30*24*60*60;
    print "<LI><A HREF=\"$program?$url$str&db$level=$db&stachan$level=$stachan&start=$range&end=$cur&samprate$level=$samprate&segtype$level=$segtype\">Last 30 days</A> (<A HREF=\"$program?$url&mode=raw&db=$db&stachan=$stachan&start=$range&end=$cur&samprate=$samprate&segtype=$segtype\">raw</A>)</LI>\n";
    print "<LI><A HREF=\"$program?$url$str&db$level=$db&stachan$level=$stachan&start=$start&end=$end&samprate$level=$samprate&segtype$level=$segtype\">All Data (slow)</A> (<A HREF=\"$program?$url&mode=raw&db=$db&stachan=$stachan&start=$start&end=$end&samprate=$samprate&segtype=$segtype\">raw</A>)</LI>\n";
    print "</UL>";
    print "\n<HR>\n<H3>Choose your own time frame ($timezone_val)</H3>\n";

    $cur_time=time();
    $emon=`/opt/antelope/current/bin/epoch -o $timezone_val +%m $cur_time $timezone_val`;
    chomp($emon);
    $eday=`/opt/antelope/current/bin/epoch -o $timezone_val +%d $cur_time $timezone_val`;
    chomp($eday);
    $eyear=`/opt/antelope/current/bin/epoch -o $timezone_val +%Y $cur_time`;
    chomp($eyear);
    $ehr=`/opt/antelope/current/bin/epoch -o $timezone_val +%H $cur_time`;
    chomp($ehr);
    $emin=`/opt/antelope/current/bin/epoch -o $timezone_val +%M $cur_time`;
    chomp($emin);
    $esec=`/opt/antelope/current/bin/epoch -o $timezone_val +%S.%s $cur_time`;
    chomp($esec);

    $cur_time-=30*60;

    $smon=`/opt/antelope/current/bin/epoch -o $timezone_val +%m $cur_time`;
    chomp($smon);
    $sday=`/opt/antelope/current/bin/epoch -o $timezone_val +%d $cur_time`;
    chomp($sday);
    $syear=`/opt/antelope/current/bin/epoch -o $timezone_val +%Y $cur_time`;
    chomp($syear);
    $shr=`/opt/antelope/current/bin/epoch -o $timezone_val +%H $cur_time`;
    chomp($shr);
    $smin=`/opt/antelope/current/bin/epoch -o $timezone_val +%M $cur_time`;
    chomp($smin);
    $ssec=`/opt/antelope/current/bin/epoch -o $timezone_val +%S.%s $cur_time`;
    chomp($ssec);

    print "<TABLE><TD><FORM METHOD=POST ACTION=$program><P>Start (mm/dd/yyyy hh:mm:ss.sss): <INPUT TYPE=text NAME=smon VALUE=$smon SIZE=2> <B>/</B> <INPUT TYPE=TEXT NAME=sday VALUE=$sday SIZE=2> <B>/</B> <INPUT TYPE=TEXT NAME=syear VALUE=$syear SIZE=4> <INPUT TYPE=TEXT NAME=shr VALUE=$shr size=2> <B>:</B> <INPUT TYPE=TEXT NAME=smin VALUE=$smin size=2> <B>:</B> <INPUT TYPE=TEXT NAME=ssec VALUE=$ssec size=6></P>";
    print "<P> End (mm/dd/yyyy hh:mm:ss.sss): <INPUT TYPE=text NAME=emon VALUE=$emon SIZE=2> <B>/</B> <INPUT TYPE=TEXT NAME=eday VALUE=$eday SIZE=2> <B>/</B> <INPUT TYPE=TEXT NAME=eyear VALUE=$eyear SIZE=4>  <INPUT TYPE=TEXT NAME=ehr VALUE=$ehr size=2> <B>:</B> <INPUT TYPE=TEXT NAME=emin VALUE=$emin size=2> <B>:</B> <INPUT TYPE=TEXT NAME=esec VALUE=$esec size=6></P>";
    print "Graph Type: <SELECT NAME=type><OPTION>Graph</OPTION><OPTION>Raw</OPTION><OPTION>XML</OPTION><OPTION>Cumulative</OPTION><OPTION VALUE=rawc>Raw Cumulative</OPTION></SELECT><BR><P>";
    print "<INPUT TYPE=HIDDEN NAME=samprate VALUE=$samprate><INPUT TYPE=hidden NAME=maxlevel VALUE=$maxlevel><INPUT TYPE=HIDDEN NAME=segtype VALUE=$segtype><INPUT TYPE=HIDDEN NAME=mode VALUE=usertime><INPUT TYPE=HIDDEN NAME=db VALUE=$db><INPUT TYPE=HIDDEN NAME=stachan VALUE=$stachan><INPUT TYPE=SUBMIT VALUE=\"Your own time\"><INPUT TYPE=HIDDEN NAME=url VALUE=$url><INPUT TYPE=HIDDEN NAME=timezone VALUE=$timezone_val></FORM></TD>";
    print "<TD></TD>\n</TABLE>\n";
    print "</TD><TD ALIGN=RIGHT VALIGN=TOP>";
    &print_sidebar;
    print "</BODY></HTML>\n";
}
elsif ($mode eq "timezone")
{
    $db=$in{"db$level"};
    $stachan=$in{"stachan$level"};
    $rmode=$in{'rmode'};
    print "Location: $program?$url&level=$level&mode=$rmode&db$level=$db&stachan$level=$stachan\n\n";
}
elsif ($mode eq "usertime")
{
    $db=$in{'db'};
    $stacha=$in{'stachan'};
    $mon=$in{'smon'};
    $day=$in{'sday'};
    $year=$in{'syear'};
    $hr=$in{'shr'};
    $min=$in{'smin'};
    $sec=$in{'ssec'};
    $time=`$antpath/epoch -i $timezone_val $mon/$day/$year $hr:$min:$sec`;
    ($c2,$eps,$c1)=split /\s+/, $time;
    $mon=$in{'emon'};
    $day=$in{'eday'};
    $year=$in{'eyear'};
    $hr=$in{'ehr'};
    $min=$in{'emin'};
    $sec=$in{'esec'};
    $samprate=$in{'samprate'};
    $segtype=$in{'segtype'};
    $type=$in{'type'};
    $url=$in{'url'};
    $time=`$antpath/epoch -i $timezone_val $mon/$day/$year $hr:$min:$sec`;
    ($c2,$epe,$c1)=split /\s+/, $time;
    if ($type eq "Raw")
    {
	print "Location: $program?$url&mode=raw&db=$db&stachan=$stacha&start=$eps&end=$epe&samprate=$samprate&segtype=$segtype\n\n";
    }
    elsif ($type eq "Cumulative")
    {
	print "Location: $program?$url&mode=Cumulative&db0=$db&stachan0=$stacha&start=$eps&end=$epe&samprate0=$samprate&segtype0=$segtype\n\n";
    }
    elsif ($type eq "rawc")
    {
	print "Location: $program?$url&mode=rawc&db=$db&stachan=$stacha&start=$eps&end=$epe&samprate=$samprate&segtype=$segtype\n\n";
    }
    elsif ($type eq "XML")
    {
	print "Location: $program?$url&mode=xml&db=$db&stachan=$stacha&start=$eps&end=$epe&samprate=$samprate&segtype=$segtype\n\n";
    }
    elsif ($maxlevel == 1)
    {
	print "Location: $program?$url&mode=graph1&db0=$db&stachan0=$stacha&start=$eps&end=$epe&samprate0=$samprate&segtype0=$segtype\n\n";
    }
    else
    {
	print "Location: $program?$url&level=1&mode=init&db0=$db&stachan0=$stacha&start=$eps&end=$epe&samprate0=$samprate&segtype0=$segtype\n\n";
    }
}
elsif ($mode eq "graph1" || $mode eq "graph2" || $mode eq "graph3" || $mode eq "Cumulative")
{
    ($ddir,$dbf)=split /_/, $in{"db0"};
    ($ddir1,$dbf1)=split /_/, $in{"db1"};
    ($ddir2,$dbf2)=split /_/, $in{"db2"};
    $db=$in{"db0"};
    $db1=$in{"db1"};
    $db2=$in{"db2"};
    $stacha=$in{"stachan0"};
    $stacha1=$in{"stachan1"};
    $stacha2=$in{"stachan2"};
    ($sta,$chan)=split /_/, $stacha,2;
    ($sta1,$chan1)=split /_/, $stacha1,2;
    ($sta2,$chan2)=split /_/, $stacha2,2;
    $start=$in{"start"};

    $end=$in{"end"};
    $samprate=$in{"samprate0"};
    $segtype=$in{"segtype0"};
    $samprate1=$in{"samprate1"};
    $segtype1=$in{"segtype1"};
    $samprate2=$in{"samprate2"};
    $segtype2=$in{"segtype2"};

    if ($samprate == 0)
    {$samprate=1;}
    if ($samprate1 == 0)
    {$samprate1=1;}
    if ($samprate2 == 0)
    {$samprate2=1;}

    $samples=($end-$start)*$samprate;
    $samples1=($end-$start)*$samprate1;
    $samples2=($end-$start)*$samprate2;
    if ($samples > 10000000 || ($mode eq "graph2" && $samples+$samples1 > 10000000)|| ($mode eq "graph3" && $samples+$samples1+$samples2 > 10000000))
    {
	print stderr "$program Status: 400\n";
	print "Status: 400\nContent-type: text/html\n\n<HTML><HEAD><TITLE>400 Bad Request</TITLE></HEAD><BODY><H1>400 Bad Request</h1><HR><P>You requested $samples samples but no one is authorized for more then 10,000,0000 samples per graph.</P></BODY></HTML>\n";
	exit(0);
    }

    if (($samples > 200000  || ($mode eq "graph2" && $samples+$samples1 > 200000)|| ($mode eq "graph3" && $samples+$samples1+$samples2 > 200000)) && (!defined $ENV{"REMOTE_USER"}))
    {
	    print stderr "$program Status: 401\n";
	    if ($mode eq "graph2")
	    {
		$samples+=$samples1;
	    }
	    if ($mode eq "graph3")
	    {
		$samples+=$samples1+$samples2;
	    }
	    print "Status: 401\nContent-type: text/html\n\n<HTML><HEAD><TITLE>401 Unauthorized</TITLE></HEAD><BODY><H1>401 Unauthorized</H1><HR><P>You requested $samples samples but you are not authorized for that many samples per graph. Less than 200,000 samples does not require authorization. If you have authorization, please visit: <A HREF=\"/auth/$program?$url&level=$level&mode=$mode&db$level=$db&stachan$level=$stacha&start=$start&end=$end&samprate$level=$samprate+&segtype$level=$segtype\">Your data</A>.</P><BR><P>In the future you may go direct to: <A HREF=\"/auth/$program\">http://mercali.ucsd.edu/auth/$program</A>. If you need authorization, please contact Todd Hansen.</P>";
	    #print %ENV;
	    #print "</PRE></BODY></HTML>";
	#print "Location: /auth/$program?$db+$stacha+$start+$end+$samprate+$segtype\n\n";
	exit(0);
    }

    if (($v=`ps ax | grep gnuplot | grep -v grep | grep -v "sh -c" | wc -l`) > 9)
    {
	print stderr "$program Status: 503\n";
	print "Status: 503\nContent-type: text/html\n\n<HTML><HEAD><TITLE>503 Waveform Service overloaded</TITLE></HEAD><BODY><H1>503 Waveform Service overloaded, try again later</h1><HR><P>You requested $samples samples of data but you are competing with $v other users and your request was denied due to the number of users, regardless of the size of your request.</P></BODY></HTML>\n";
	exit(0);
    }

    $none=1;
    $cval="-c";
    $cdesc="";
    if ($calibopt eq "Uncalibrated")
    {
	$cval="";
	$cdesc=" Uncalibrated";
    }

    open(TMP,">/tmp/waveform.$$.dat");
    open(DATA,"$antpath/trsample -ot $cval -n $samples -s \"sta=='$sta' && chan=='$chan'\" $dbroot/$ddir/$dbf $start $end|");
#    foreach $item (`$antpath/trsample -ot $cval -n $samples -s "sta=='$sta' && chan=='$chan'" $dbroot/$ddir/$dbf $start $end`)
    my $cur=0;
    while ($item = <DATA>)
    {
	$none=0;
	chomp($item);
	@array=split /\s+/, $item;

	if ($#array==1)
	{
	    $time=epoch2str($array[0],"%d/%m/%Y.%H:%M:%S.%s",$timezone_val);
	    if (abs($array[1])<=32767)
	    {
		if (defined $orig_time && ($array[0]-$orig_time) > (1/$samprate)*1.5 )
		{
			print TMP "\n";	
		}
		if ($econvi && ($capp == 1 || $capp eq "All"))
		{
		    $array[1]=$array[1]*$conv+$coff;
		}
		if ($mode eq "Cumulative")
		{
		    $cur+=$array[1];
		    print TMP "$time $cur\n";
		}
		else
		{
		    print TMP "$time $array[1]\n";
		}
		$orig_time=$array[0];
	    }
	    else
	    {
		print TMP "\n";
	    }
	}
    }
    close(TMP);
    close(DATA);

    if ($mode eq "graph2" || $mode eq "graph3")
    {
	open(TMP,">/tmp/waveform2.$$.dat");
	open(DATA,"$antpath/trsample -ot $cval -n $samples1 -s \"sta=='$sta1' && chan=='$chan1'\" $dbroot/$ddir1/$dbf1 $start $end|");
#	foreach $item (`$antpath/trsample -ot $cval -n $samples1 -s "sta=='$sta1' && chan=='$chan1'" $dbroot/$ddir1/$dbf1 $start $end`)
	while ($item = <DATA>)
	{
	    $none=0;
	    chomp($item);
	    @array=split /\s+/, $item;
	    
	    if ($#array==1)
	    {
		$time=epoch2str($array[0],"%d/%m/%Y.%H:%M:%S.%s",$timezone_val);
		if (abs($array[1])<=32767)
		{
		    if (defined $orig_time && ($array[0]-$orig_time) > (1/$samprate1)*1.5 )
		    {
			print TMP "\n";	
		    }
		    if ($econvi && ($capp == 2 || $capp eq "All"))
		    {
			$array[1]=$array[1]*$conv+$coff;
		    }
		    print TMP "$time $array[1]\n";
		    $orig_time=$array[0];
		}
		else
		{
		    print TMP "\n";
		}
	    }
	}
	close(TMP);
	close(DATA);
    }

    if ($mode eq "graph3")
    {
	open(TMP,">/tmp/waveform3.$$.dat");
	open(DATA,"$antpath/trsample -ot $cval -n $samples2 -s \"sta=='$sta2' && chan=='$chan2'\" $dbroot/$ddir2/$dbf2 $start $end|");
#	foreach $item (`$antpath/trsample -ot $cval -n $samples2 -s "sta=='$sta2' && chan=='$chan2'" $dbroot/$ddir2/$dbf2 $start $end`)
	while ($item = <DATA>)
	{
	    $none=0;
	    chomp($item);
	    @array=split /\s+/, $item;
	    
	    if ($#array==1)
	    {
		$time=epoch2str($array[0],"%d/%m/%Y.%H:%M:%S.%s",$timezone_val);
		if (abs($array[1])<=32767)
		{
		    if (defined $orig_time && ($array[0]-$orig_time) > (1/$samprate2)*1.5 )
		    {
			print TMP "\n";	
		    }

		    if ($econvi && ($capp == 3 || $capp eq "All"))
		    {
			$array[1]=$array[1]*$conv+$coff;
		    }
		    print TMP "$time $array[1]\n";
		    $orig_time=$array[0];
		}
		else
		{
		    print TMP "\n";
		}
	    }
	}
	close(DATA);
	close(TMP);
    }

    if ($none==0)
    {
	if ($graph_format eq "ps")
	{
	    $str = "Content-type: application/postscript\nPragma: no-cache\n\n";
	}
	else
	{
	    $str = "Content-type: image/png\nPragma: no-cache\n\n";
	}

	open(FOO,">/dev/stdout");
	syswrite(FOO,$str,length($str));
	close(FOO);
	
	open(GIF, "| /usr/bin/gnuplot > /dev/stdout");

	$time=epoch2str($start,"%m/%d/%Y");

	$c1="";
	$c2="";

	if ($econvi && $capp eq "All")
	{
	    $c=$nconv;
	}
	else
	{
	    if ($capp == 1 && $econvi)
	    {
		$c=$nconv;
	    }
	    else
	    {
		$c=`$antpath/trlookup_segtype $segtype`;
		chomp($c);
		if ($c eq "")
		{	
		    $c="no units";
		}
	    }
	    
	    if ($mode eq "graph2" && ($segtype1 ne $segtype || ($econv && ($capp ==1 || $capp==2))))
	    {
		if ($capp == 2 && $econvi)
		{
		    $c=$nconv;
		}
		else
		{
		    $c1=`$antpath/trlookup_segtype $segtype1`;
		    chomp($c1);
		    if ($c1 eq "")
		    {	
			$c1="no units";
		    }
		    $c.=" (blue)\\n$c1 (red)";
		}
	    }
	
	    
	    if ($mode eq "graph3" && ($segtype1 ne $segtype || $segtype2 ne $segtype || $econvi))
	    {
		if ($capp == 2 && $econvi)
		{
		    $c=$nconv;
		}
		else
		{
		    $c1=`$antpath/trlookup_segtype $segtype1`;
		    chomp($c1);
		    if ($c1 eq "")
		    {	
			$c1="no units";
		    }
		}

		if ($capp == 3 && $econvi)
		{
		    $c=$nconv;
		}
		else
		{
		    $c2=`$antpath/trlookup_segtype $segtype2`;
		    chomp($c2);
		    if ($c2 eq "")
		    {	
			$c2="no units";
		    }
		}
		$c.=" (blue)\\n$c1 (red)\\n$c2 (green)";
	    }
	}

	$gtitle=`grep \"$db $stacha\" $titlelookup`;
	chomp($gtitle);

	($c1,$c2,$gtitle)=split /\s+/,$gtitle,3;
	if ($gtitle eq "")
	{
	    $gtitle="$dbf $stacha";
	}

	if ($mode eq "graph2")
	{
	    $gtitle1=`grep \"$db1 $stacha1\" $titlelookup`;
	    chomp($gtitle1);
	    ($c1,$c2,$gtitle1)=split /\s+/,$gtitle1,3;
	    if ($gtitle1 eq "")
	    {
		$gtitle1="$dbf1 $stacha1";
	    }
	    $gtitle.=" vs. $gtitle1";
	}

	if ($mode eq "graph3")
	{
	    $gtitle1=`grep \"$db1 $stacha1\" $titlelookup`;
	    chomp($gtitle1);
	    ($c1,$c2,$gtitle1)=split /\s+/,$gtitle1,3;
	    if ($gtitle1 eq "")
	    {
		$gtitle1="$dbf1 $stacha1";
	    }
	    $gtitle2=`grep \"$db2 $stacha2\" $titlelookup`;
	    chomp($gtitle2);
	    ($c1,$c2,$gtitle2)=split /\s+/,$gtitle2,3;
	    if ($gtitle2 eq "")
	    {
		$gtitle2="$dbf2 $stacha2";
	    }
	    $gtitle.=" / $gtitle1 / $gtitle2";
	}
	   
	if ($mode eq 'Cumulative')
	{
	    print GIF "set ylabel \"$c\\nCumulative\"\n";
	}
	else
	{
	    print GIF "set ylabel \"$c\"\n";
	}
	print GIF "set timefmt \"%d\/%m\/%Y.%H:%M:%S\"\n";
	print GIF "set xdata time\n";
	if ($gridopt==1)
	{
	    print GIF "set grid\n";
	}
	print GIF "set xtics rotate autofreq\n";
	if ($end-$start > 24*3*60*60)
	{
	    print GIF "set format x \" %m/%d/%y\"\n";
	    print GIF "set title \"$gtitle$cdesc\"\n";
	}
	else
	{
	    print GIF "set format x \" %H:%M\"\n";
	    print GIF "set title \"$gtitle$cdesc (start: $time)\"\n";
	}

	print GIF "set yrange [$ymin:$ymax]\n";

	print GIF "set data style lines \n";
	print GIF "set xlabel \"Time $timezone_val\"\n";
#	print GIF "set size 1,0.6\n";
	$sizeh=$sizeh/640;
	$sizev=$sizev/480;
	print GIF "set size $sizeh,$sizev\n";

	if ($graph_format eq "ps")
	{
	    print GIF "set terminal postscript eps color solid\n";
	    $color1="3";
	    $color2="1";
	    $color3="11";
	}
	else
	{
	    print GIF "set terminal png color\n";
	    $color1="8";
	    $color2="1";
	    $color3="2";
	}

	if ($mode eq "graph3")
	{
	    print GIF "plot \"/tmp/waveform.$$.dat\" using 1:2 title \"$db $stacha\" $color1, \"/tmp/waveform2.$$.dat\" using 1:2 title \"$db1 $stacha1\" $color2, \"/tmp/waveform3.$$.dat\" using 1:2 title \"$db2 $stacha2\" $color3\n";
	}
	if ($mode eq "graph2")
	{
	    print GIF "plot \"/tmp/waveform.$$.dat\" using 1:2 title \"$db $stacha\" $color1, \"/tmp/waveform2.$$.dat\" using 1:2 title \"$db1 $stacha1\" $color2\n";
	}
	else
	{
	    print GIF "plot \"/tmp/waveform.$$.dat\" using 1:2 notitle $color1\n";
	}
	close GIF;
    }
    else
    {
	print "Content-type: text/plain\nPragma: no-cache\n\n";
	print "No Data Available for this time range\n";
    }

    unlink("/tmp/waveform.$$.dat");
    unlink("/tmp/waveform2.$$.dat");
}
elsif ($mode eq "raw" || $mode eq "xml" || $mode eq "rawc")
{
    ($ddir,$dbf)=split /_/, $in{"db"};
    $db=$in{"db"};
    $stacha=$in{"stachan"};
    ($sta,$chan)=split /_/, $stacha, 2;
    $start=$in{"start"};
    $end=$in{"end"};
    $samprate=$in{"samprate"};
    $segtype=$in{"segtype"};

    $samples=(24*60*60)*$samprate;

    if ($mode eq "raw" || $mode eq "rawc")
    {
	print "Content-type: text/plain\nPragma: no-cache\n\n";
	$c=`$antpath/trlookup_segtype $segtype`;
	chomp($c);
	if ($c eq "")
	{
	    $c="no units";
	}
	print "#Units = $c\n";
    }
    else
    {
	print "Content-type: text/xml\nPragma: no-cache\n\n";
    }

    if ($mode ne "rawc")
    {
	print `/var/Web/xml_get.pl $mode $dbroot/$ddir/$dbf $sta $chan $start $end $samples`;
    }
    else
    {
	print "#Cumulative values are marked with a *, be aware that out of order data will bust this calculation\n\n";
	$val=0;

	foreach $i (`$antpath/trsample -ot -c -n $samples -s \"sta=='$sta' && chan=='$chan'\" $dbroot/$ddir/$dbf $start $end`)
	{
	    print $i;
	    if ($i!~/^\s/)
	    {
		chomp($i);
		($time,$c)=split /\s+/,$i;
		if (abs($c) < 32767)
		{
		    $val+=$c;
		}
		print "*$time\t$val\n";
		
	    }
	}
    }
}

sub print_sidebar
{
    my $p="";
    if ($maxlevel>1)
    {
	$p="s";
    }
    print "<FORM METHOD=POST ACTION=$program><TABLE><TR><TD><h3>Global Options</h3><HR></TD></TR><TR><TD><INPUT TYPE=HIDDEN NAME=mode VALUE=timezone><INPUT TYPE=HIDDEN NAME=samprate$level VALUE=$samprate><INPUT TYPE=HIDDEN NAME=segtype$level VALUE=$segtype><INPUT TYPE=HIDDEN NAME=db$level VALUE=$db>";

    if ($level>0)
    {
	$start=$in{"start"};
	$end=$in{"end"};
	print "<INPUT TYPE=HIDDEN NAME=start VALUE=$start><INPUT TYPE=HIDDEN NAME=end VALUE=$end>";
    }

    for ($lcv=0;$lcv<$level;$lcv++)
    {
	my $dbloop=$in{"db$lcv"};
	my $stachanloop=$in{"stachan$lcv"};
	my $samprateloop=$in{"samprate$lcv"};
	my $segtypeloop=$in{"segtype$lcv"};
	print "<INPUT TYPE=HIDDEN NAME=db$lcv VALUE=$dbloop><INPUT TYPE=HIDDEN NAME=stachan$lcv VALUE=$stachanloop>";
	print "<INPUT TYPE=HIDDEN NAME=samprate$lcv VALUE=$samprateloop><INPUT TYPE=HIDDEN NAME=segtype$lcv VALUE=$segtypeloop>";
    }

    print "<INPUT TYPE=HIDDEN NAME=level VALUE=$level><INPUT TYPE=HIDDEN NAME=rmode VALUE=$mode><INPUT TYPE=HIDDEN NAME=stachan$level VALUE=$stachan>\n";

    print "<SELECT NAME=maxlevel>";
    $selected="";
    for ($lcv2=1;$lcv2<4;$lcv2++)
    {
	if ($lcv2==$maxlevel)
	{
	    $selected="SELECTED";
	}
	print "<OPTION $selected VALUE=$lcv2>$lcv2 dataset</OPTION>";
	$selected="";
    }
    
    print "</SELECT>";
    
    if ($adv eq "on")
    {
	print "<BR><BR><SELECT NAME=calibopt>";
	if ($calibopt eq "Uncalibrated")
	{
	    print "<OPTION>Calibrated</OPTION>";	
	    print "<OPTION SELECTED>Uncalibrated</OPTION>";
	}
	else
	{
	    print "<OPTION SELECTED>Calibrated</OPTION>";	
	    print "<OPTION>Uncalibrated</OPTION>";
	}
    }

    print "</SELECT><BR><BR><SELECT NAME=gridopt>";
    if ($gridopt==1)
    {
	print "<OPTION VALUE=0>No Grid</OPTION>";	
	print "<OPTION SELECTED VALUE=1>Show Grid</OPTION>";
    }
    else
    {
	print "<OPTION SELECTED VALUE=0>No Grid</OPTION>";	
	print "<OPTION VALUE=1>Show Grid</OPTION>";
    }

    print "</SELECT><BR><BR><SELECT NAME=timezone>";
    print "<OPTION>UTC</OPTION>";
    if ($timezone_val eq "US/Pacific")
    {print "<OPTION SELECTED>";}
    else
    {print "<OPTION>";}
    print "US/Pacific</OPTION>";
    if ($timezone_val eq "US/Mountain")
    {print "<OPTION SELECTED>";}
    else
    {print "<OPTION>";}
    print "US/Mountain</OPTION>";
    if ($timezone_val eq "US/Central")
    {print "<OPTION SELECTED>";}
    else
    {print "<OPTION>";}
    print "US/Central</OPTION>";
    if ($timezone_val eq "US/Eastern")
    {print "<OPTION SELECTED>";}
    else
    {print "<OPTION>";} 
    print "US/Eastern</OPTION>";
    if ($timezone_val eq "US/Alaska")
    {print "<OPTION SELECTED>";}
    else
    {print "<OPTION>";}
    print "US/Alaska</OPTION>";
    if ($timezone_val eq "US/Hawaii")
    {print "<OPTION SELECTED>";}
    else
    {print "<OPTION>";}
    print "US/Hawaii</OPTION>";
    $g="";
    if ($adv eq "on")
    {
	$g="checked";
    }
    print "</SELECT><BR><BR><B>Advanced:</B> <INPUT TYPE=CHECKBOX NAME=adv $g>";
    if ($adv eq "on")
    {
	print "<BR><BR><B>Fix Y-range:</B> <INPUT TYPE=TEXT NAME=\"ymin\" SIZE=3 VALUE=\"$ymin\"> min to <INPUT TYPE=TEXT NAME=\"ymax\" SIZE=3 VALUE=\"$ymax\"> max";
	print "<BR><BR><B>Image Size:</B> <INPUT TYPE=TEXT NAME=\"sizev\" SIZE=3 VALUE=\"$sizev\"> vert to <INPUT TYPE=TEXT NAME=\"sizeh\" SIZE=3 VALUE=\"$sizeh\"> horiz";
	
	if ($econv eq "on")
	{
	    $checked_box = "Checked";
	}
	print "<BR><BR><TABLE><TD><B>Convert Units:</B><INPUT TYPE=CHECKBOX NAME=econv $checked_box></TD<TD>Name: <INPUT TYPE=TEXT NAME=nconv VALUE=\"$nconv\" SIZE=5></TD><TR><TD><SELECT NAME=capp>";
	print "<OPTION>All</OPTION>\n";
	for ($lcv2=1;$lcv2<4;$lcv2++)
	{
	    if ($capp == $lcv2)
	    {
		print "<OPTION SELECTED VALUE=$lcv2>Chan $lcv2</OPTION>\n";
	    }
	    else
	    {
		print "<OPTION VALUE=$lcv2>Chan $lcv2</OPTION>\n";
	    }
	}
	print "</SELECT></TD><TD>Conversion: <INPUT TYPE=TEXT NAME=conv VALUE=\"$conv\" SIZE=4></TD><TR><TD></TD><TD>Offset: <INPUT TYPE=TEXT NAME=coff VALUE=\"$coff\" SIZE=4></TD>";
	
	$g=$capp;
	if ($g eq "All")
	{$g=1;}
	$g--;
	
	if (defined $in{"segtype$g"})
	{
	    
	    if ($in{"segtype$g"} eq "t")
	    {
		print "<TR><TD COLSPAN=2><SELECT NAME=custom>";
		print "<OPTION VALUE=\"None\" SELECTED>Predefined</OPTION>";
		print "<OPTION VALUE=\"Fahrenheit;1.8;32\">to Fahrenheit</OPTION>";
		print "<OPTION VALUE=\"Kelvin;1.0;273.15\">to Kelvin</OPTION>";
		print "</SELECT></TD>";
	    }
	}
	print "</TABLE>\n";
	
	print "<BR><BR><B>Graph Format:</B> <SELECT NAME=form>\n";
	if ($graph_format eq "ps")
	{
	    print "<OPTION VALUE=png>PNG</OPTION>\n";
	    print "<OPTION VALUE=ps SELECTED>PostScript</OPTION>\n";
	}
	else
	{
	    print "<OPTION VALUE=png SELECTED>PNG</OPTION>\n";
	    print "<OPTION VALUE=ps>PostScript</OPTION>\n";
	}
	print "</SELECT>";
    }

    print "<BR><BR><INPUT TYPE=SUBMIT VALUE=\"Set Options\"><BR><BR><BR><FONT SIZE=-1><A HREF=\"$program\">Start Over</A></FONT></FORM></TD></TR></TABLE>";    
}
