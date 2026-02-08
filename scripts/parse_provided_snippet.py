from bs4 import BeautifulSoup
import re, pprint

snippet = '''<table cellpadding="4" cellspacing="1" width="100%" ng-repeat="cann in CorpannData.Table" ng-show="CorpannData.Table.length" class="ng-scope">
                                                                        <tbody><tr>

                                                                            <td class="tdcolumngrey" width="70%" style="font-weight:bold;" valign="middle">
                                                                                <span ng-bind-html="cann.NEWSSUB" class="ng-binding">Ramchandra Leasing &amp; Finance Ltd - 538540 - Board Meeting Intimation for Intimation Of Board Meeting Under Regulation 29 Of SEBI (Listing Obligations And Disclosure Requirements) Regulations, 2015</span>
                                                                            </td>

                                                                    


                                                                            <!-- ngIf: cann.CATEGORYNAME != 'NULL'  --><td class="tdcolumngrey ng-binding ng-scope" style="font-weight:bold;" valign="middle" width="20%" ng-if="cann.CATEGORYNAME != 'NULL' ">Board Meeting</td><!-- end ngIf: cann.CATEGORYNAME != 'NULL'  -->
                                                                            <!-- ngIf: cann.CATEGORYNAME == 'NULL'  -->
                                                                            <td class="tdcolumngrey" valign="middle" align="center" width="5%">
                                                                                <!-- ngIf: cann.AUDIO_VIDEO_FILE.length>0 -->
                                                                            </td>
                                                                            <!-- ngIf: cann.PDFFLAG==0 && cann.ATTACHMENTNAME --><td class="tdcolumngrey ng-scope" valign="middle" ng-if="cann.PDFFLAG==0 &amp;&amp; cann.ATTACHMENTNAME" align="center" width="10%">
                                                                                <a class="tablebluelink" href="/xml-data/corpfiling/AttachLive/ecf56b5a-1603-4818-a527-c9fb87fc710f.pdf" target="_blank">
                                                                                    <i class="fa fa-file-pdf-o redpdficon" src="" alt="" border="0"></i>
                                                                                </a><!-- ngIf: cann.Fld_Attachsize !=null &&  cann.Fld_Attachsize &gt; 99999  --><span ng-if="cann.Fld_Attachsize !=null &amp;&amp;  cann.Fld_Attachsize &gt; 99999 " class="ng-binding ng-scope">0.80 MB</span><!-- end ngIf: cann.Fld_Attachsize !=null &&  cann.Fld_Attachsize &gt; 99999  -->
                                                                                <!-- ngIf: cann.Fld_Attachsize !=null && cann.Fld_Attachsize <99999  -->

                                                                            </td><!-- end ngIf: cann.PDFFLAG==0 && cann.ATTACHMENTNAME -->


                                                                            <!-- ngIf: cann.PDFFLAG==1 && cann.ATTACHMENTNAME -->

                                                                            <!-- ngIf: cann.PDFFLAG==2 && cann.ATTACHMENTNAME -->

                                                                            <!-- ngIf: !cann.ATTACHMENTNAME -->

                                                                            <!-- ngIf: cann.News_submission_dt && cann.DissemDT  && cann.TimeDiff --><td class="tdcolumngrey ng-scope" valign="middle" ng-if="cann.News_submission_dt &amp;&amp; cann.DissemDT  &amp;&amp; cann.TimeDiff" width="5%" align="center">
                                                                                <!-- ngIf: cann.FILESTATUS != 'X' --><a target="_blank" ng-if="cann.FILESTATUS != 'X'" ng-click="fn_dwnldxbrl(cann.NEWSID,cann.SCRIP_CD)" class="ng-scope">
                                                                                    XBRL
                                                                                </a><!-- end ngIf: cann.FILESTATUS != 'X' -->
                                                                                <!-- ngIf: cann.FILESTATUS == 'X' -->
                                                                            </td><!-- end ngIf: cann.News_submission_dt && cann.DissemDT  && cann.TimeDiff -->

                                                                            <!-- ngIf: !cann.TimeDiff -->


                                                                        </tr>
                                                                        <tr style="background-color: white; height: 32px;">

                                                                            <td style="background-color:white;padding-left: 5px" colspan="5">

                                                                                <div id="morec3c48a5b-04df-4c37-96a1-57db0ce7ca68" style="display:block">
                                                                                    <span id="c3c48a5b-04df-4c37-96a1-57db0ce7ca68" ng-bind-html="cann.HEADLINE" class="ng-binding">Ramchandra Leasing &amp; Finance Ltdhas informed BSE that the meeting of the Board of Directors of the Company is scheduled on 14/02/2026 ,inter alia, to consider and approve Dear Sir/Madam,
Pursuant ....</span>
                                                                                    <!-- ngIf: cann.MORE!='' --><a href="#" class="tablebluelink ng-scope" ng-if="cann.MORE!=''" ng-click="moreclick(cann.NEWSID,'more','less',0)">Read More..</a><!-- end ngIf: cann.MORE!='' -->
                                                                                </div>

                                                                                <div id="lessc3c48a5b-04df-4c37-96a1-57db0ce7ca68" style="display:none">
                                                                                    <span ng-bind-html="cann.MORE" class="ng-binding">Ramchandra Leasing &amp; Finance Ltdhas informed BSE that the meeting of the Board of Directors of the Company is scheduled on 14/02/2026 ,inter alia, to consider and approve Dear Sir/Madam,
Pursuant to Regulation 29 of the SEBI (Listing Obligations And Disclosure Requirements) Regulations, 2015, we wish to inform you that a meeting of the Board of Directors of the Company is scheduled to be held on Saturday, February 14, 2026 inter alia:
a. To consider and approve the Unaudited Financial Results of the Company for the quarter and Nine months ended December 31, 2025 
b. To take note of the Limited Review Report for the quarter and Nine months ended December 31, 2025
c. To take note of the resignation/appointment of Directors.
d. Other matters as may deem fit by the Board
Kindly take the same on record.
</span>

                                                                                    <a href="#" class="tablebluelink" ng-click="moreclick(cann.NEWSID,'more','less',1)">Read less..</a>
                                                                                </div>





                                                                            </td>

                                                                        </tr>

                                                                        <!-- ngIf: cann.TimeDiff --><tr style="background-color:white;height:32px;" ng-if="cann.TimeDiff" class="ng-scope">
                                                                            <td style="background-color:white" colspan="5"> &nbsp;&nbsp;Exchange Received Time<b class="ng-binding"> 08-02-2026 22:21:32</b> Exchange Disseminated Time<b class="ng-binding"> 08-02-2026 22:21:34</b> Time Taken<b class="ng-binding"> 00:00:02</b></td>

                                                                        </tr><!-- end ngIf: cann.TimeDiff -->
                                                                        <!-- ngIf: !cann.TimeDiff -->
                                                                        <tr class="__web-inspector-hide-shortcut__"><td class="tdcolumn" colspan="5">&nbsp; </td></tr>
                                                                    </tbody></table>'''

soup = BeautifulSoup(snippet, 'html.parser')
rows = soup.find_all('tr')

for row in rows:
    cols = row.find_all('td')
    if len(cols) >= 3:
        date = cols[0].text.strip()
        scrip = cols[1].text.strip()
        title = cols[2].text.strip()
        # fallback extract
        if not scrip or not re.search(r'\d', scrip):
            m = re.search(r'\b(\d{5,6})\b', title)
            if m:
                scrip = m.group(1)
        print('date:', date)
        print('scrip:', scrip)
        print('title:', title)
        print('---')
