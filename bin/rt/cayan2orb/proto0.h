/*
 Copyright (c) 2003 The Regents of the University of California
 All Rights Reserved
 
 Permission to use, copy, modify and distribute any part of this software for
 educational, research and non-profit purposes, without fee, and without a
 written agreement is hereby granted, provided that the above copyright
 notice, this paragraph and the following three paragraphs appear in all
 copies.
 
 Those desiring to incorporate this software into commercial products or use
 for commercial purposes should contact the Technology Transfer Office,
 University of California, San Diego, 9500 Gilman Drive, La Jolla, CA
 92093-0910, Ph: (858) 534-5815.
 
 IN NO EVENT SHALL THE UNIVESITY OF CALIFORNIA BE LIABLE TO ANY PARTY FOR
 DIRECT, INDIRECT, SPECIAL, INCIDENTAL, OR CONSEQUENTIAL DAMAGES, INCLUDING
 LOST PROFITS, ARISING OUT OF THE USE OF THIS SOFTWARE, EVEN IF THE UNIVERSITY
 OF CALIFORNIA HAS BEEN ADIVSED OF THE POSSIBILITY OF SUCH DAMAGE.
 
 THE SOFTWARE PROVIDED HEREIN IS ON AN "AS IS" BASIS, AND THE UNIVERSITY OF
 CALIFORNIA HAS NO OBLIGATION TO PROVIDE MAINTENANCE, SUPPORT, UPDATES,
 ENHANCEMENTS, OR MODIFICATIONS.  THE UNIVERSITY OF CALIFORNIA MAKES NO
 REPRESENTATIONS AND EXTENDS NO WARRANTIES OF ANY KIND, EITHER IMPLIED OR
 EXPRESS, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
 MERCHANTABILITY OR FITNESS FOR A PARTICULAR PURPOSE, OR THAT THE USE OF THE
 SOFTWARE WILL NOT INFRINGE ANY PATENT, TRADEMARK OR OTHER RIGHTS.

   This code was created as part of the ROADNet project.
   See http://roadnet.ucsd.edu/ 

   Written By: Todd Hansen 1/3/2003
   Updated By: Todd Hansen 9/30/2003

   The data loggers this code communicates with were created by Douglas
   Alden, using a protocol he specified.
*/

void p0_pressure(struct Packet *orbpkt, char *staid, unsigned char *buf);
void p0_nwind0(struct Packet *orbpkt, char *staid, unsigned char *buf);
void p0_ewind0(struct Packet *orbpkt, char *staid, unsigned char *buf);
void p0_windgust0(struct Packet *orbpkt, char *staid, unsigned char *buf);
void p0_dgust0(struct Packet *orbpkt, char *staid, unsigned char *buf);
void p0_nwind1(struct Packet *orbpkt, char *staid, unsigned char *buf);
void p0_ewind1(struct Packet *orbpkt, char *staid, unsigned char *buf);
void p0_windgust1(struct Packet *orbpkt, char *staid, unsigned char *buf);
void p0_dgust1(struct Packet *orbpkt, char *staid, unsigned char *buf);
void p0_temp0(struct Packet *orbpkt, char *staid, unsigned char *buf);
void p0_temp1(struct Packet *orbpkt, char *staid, unsigned char *buf);
void p0_humidity(struct Packet *orbpkt, char *staid, unsigned char *buf);
void p0_rain(struct Packet *orbpkt, char *staid, unsigned char *buf);
void p0_solar(struct Packet *orbpkt, char *staid, unsigned char *buf);
void p0_voltage(struct Packet *orbpkt, char *staid, unsigned char *buf);
void p0_numframes(struct Packet *orbpkt, char *staid, unsigned char *buf);

void p0_start2orb(int orbfd, unsigned char *buf);
void p0_data2orb(int orbfd, unsigned char *buf);
