"""
Download all ROS 2025 meeting documents to:
  E:\\wamp64\\www\\Power.Talks\\Documents Database\\ERCOT.STKHDR.MEETS\\ROS\\YYYY-MM-DD\\
"""

import os
import time
import requests
from urllib.parse import urlparse, unquote

BASE_DIR = r"E:\wamp64\www\Power.Talks\Documents Database\ERCOT.STKHDR.MEETS\ROS"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.ercot.com/",
}

MEETINGS = {
    "2025-01-09": [
        "https://www.ercot.com/files/docs/2025/02/10/APPROVED-Minutes-ROS-20250109-.doc",
        "https://www.ercot.com/files/docs/2025/01/09/2025-ros-combined-ballot-20250109.xls",
        "https://www.ercot.com/files/docs/2025/01/08/02-2025_segment_representatives-ros.doc",
        "https://www.ercot.com/files/docs/2025/01/08/02-chair-and-vc-tac-and-subs-election-process.docx",
        "https://www.ercot.com/files/docs/2025/01/06/03-ros-agenda-20250109-v2.docx",
        "https://www.ercot.com/files/docs/2025/01/02/04-draft-minutes-ros.zip",
        "https://www.ercot.com/files/docs/2024/12/23/November%202024%20ERCOT%20Operations%20Report%20Public.docx",
        "https://www.ercot.com/files/docs/2025/01/08/systemplanningros_nov2024.docx",
        "https://www.ercot.com/files/docs/2025/01/02/11-ndswg_report_to_ros_010925.pptx",
        "https://www.ercot.com/files/docs/2025/01/02/12-planning-working-group-report_01092025.pptx",
        "https://www.ercot.com/files/docs/2025/01/02/13-dwg-report-to-ros---january-2025.pptx",
        "https://www.ercot.com/files/docs/2025/01/06/14-ibrwg-report-to-ros-010925.docx",
        "https://www.ercot.com/files/docs/2025/01/09/17-sswg-report-to-ros-1-9-2025.pptx",
        "https://www.ercot.com/files/docs/2025/01/02/18-january_otwg_updates.pptx",
        "https://www.ercot.com/files/docs/2025/01/06/19-2024-ros-goals-tac-approved-03272024.doc",
        "https://www.ercot.com/files/docs/2025/01/09/meeting-materials-20250109.zip",
        "https://www.ercot.com/files/docs/2025/01/02/revision-request-ros-20240109.zip",
    ],
    "2025-02-06": [
        "https://www.ercot.com/files/docs/2025/03/10/APPROVED-Minutes-ROS-20240206.doc",
        "https://www.ercot.com/files/docs/2025/02/06/2025-ros-combined-ballot-20250206.xls",
        "https://www.ercot.com/files/docs/2025/01/30/02-ros-agenda-20250206.docx",
        "https://www.ercot.com/files/docs/2025/02/04/03-draft-minutes-ros-20250109-v2.doc",
        "https://www.ercot.com/files/docs/2025/02/03/05-2025-ros-wg-leadership-nominated.docx",
        "https://www.ercot.com/files/docs/2025/01/30/06-2024-ros-goals-tac-approved-03272024.doc",
        "https://www.ercot.com/files/docs/2025/01/24/december-2024-ercot-operations-report-public.docx",
        "https://www.ercot.com/files/docs/2025/01/24/systemplanningros_dec2024.docx",
        "https://www.ercot.com/files/docs/2025/02/04/12-owg_ros_20250206.pptx",
        "https://www.ercot.com/files/docs/2025/02/03/13-ndswg_report_to_ros_020625_rg.pptx",
        "https://www.ercot.com/files/docs/2025/01/30/14-planning-working-group-report_02062025.pptx",
        "https://www.ercot.com/files/docs/2025/02/03/15-ibrwg-report-to-ros-020625.docx",
        "https://www.ercot.com/files/docs/2025/02/03/15-2025_feb_ros_nogrr272_pgrr121_ercot.pdf",
        "https://www.ercot.com/files/docs/2025/02/04/17-pdcwg-report-to-ros_020625.pptx",
        "https://www.ercot.com/files/docs/2025/02/06/18-sswg-report-to-ros-2-6-2025.pptx",
        "https://www.ercot.com/files/docs/2025/02/06/meeting-materials-ros-20250206.zip",
        "https://www.ercot.com/files/docs/2025/02/05/revision-request-ros-20240206.zip",
    ],
    "2025-03-06": [
        "https://www.ercot.com/files/docs/2025/04/14/APPROVED-Minutes-ROS-20250306-.doc",
        "https://www.ercot.com/files/docs/2025/03/06/2025-ROS-Combined-Ballot-20250306.xls",
        "https://www.ercot.com/files/docs/2025/02/27/02.-ROS-Agenda-20250306.docx",
        "https://www.ercot.com/files/docs/2025/02/27/03.-Draft-Minutes-ROS-20240206.doc",
        "https://www.ercot.com/files/docs/2025/02/27/05.-2024-ros-goals-tac-approved-03272024.doc",
        "https://www.ercot.com/files/docs/2025/02/27/05.-TAC-Strategic-Objectives-Approved-02272025.pptx",
        "https://www.ercot.com/files/docs/2025/03/06/January-2025-ERCOT-Operations-Report-Public-1.docx",
        "https://www.ercot.com/files/docs/2025/02/13/systemplanningros_jan2025.docx",
        "https://www.ercot.com/files/docs/2025/03/04/06.-GTCUpdate_ROS_March2025.pdf",
        "https://www.ercot.com/files/docs/2025/02/27/12.-OWG_ROS_20250306.pptx",
        "https://www.ercot.com/files/docs/2025/02/27/14.-Planning-Working-Group-Update_03062025.pptx",
        "https://www.ercot.com/files/docs/2025/02/28/17.-IBRWG-Report-to-ROS-030625.docx",
        "https://www.ercot.com/files/docs/2025/02/27/18.-20250306_DWG-Report-to-ROS-March-2025.pptx",
        "https://www.ercot.com/files/docs/2025/03/04/19.-PDCWG-Report-to-ROS_030625.pptx",
        "https://www.ercot.com/files/docs/2025/02/28/20.-SPWG-ROS-Update-03-06-2025.pptx",
        "https://www.ercot.com/files/docs/2025/02/27/21.-SSWG_Update_ROS_03062025.pptx",
        "https://www.ercot.com/files/docs/2025/03/06/Meeting-Materials-20250306.zip",
        "https://www.ercot.com/files/docs/2025/03/05/Revision-Request-ROS-20250306.zip",
    ],
    "2025-04-03": [
        "https://www.ercot.com/files/docs/2025/05/22/APPROVED-Minutes-ROS-20250403-.doc",
        "https://www.ercot.com/files/docs/2025/04/03/2025-ROS-Combined-Ballot-20250403.xls",
        "https://www.ercot.com/files/docs/2025/04/01/ROS-Agenda-20250403.v2.docx",
        "https://www.ercot.com/files/docs/2025/03/27/03.-Draft-Minutes-ROS-20250306-.doc",
        "https://www.ercot.com/files/docs/2025/03/27/05.-2025-ROS-Goals.doc",
        "https://www.ercot.com/files/docs/2025/03/27/05.-TAC-Strategic-Objectives-Approved-02272025.pptx",
        "https://www.ercot.com/files/docs/2025/03/25/February-2025-ERCOT-Operations-Report-Public.docx",
        "https://www.ercot.com/files/docs/2025/03/18/SystemPlanningROS_Feb2025.docx",
        "https://www.ercot.com/files/docs/2025/04/03/06.-GTCUpdate_ROS_April_2025.pptx",
        "https://www.ercot.com/files/docs/2025/03/27/11.-OWG_ROS_20250403.pptx",
        "https://www.ercot.com/files/docs/2025/03/27/12.-NDSWG-report-to-ROS-20250403x.pptx",
        "https://www.ercot.com/files/docs/2025/03/27/13.-SPWG-ROS-Update-04-03-2025.pptx",
        "https://www.ercot.com/files/docs/2025/03/27/13.-Proposed_spwg_procedures_040325.docx",
        "https://www.ercot.com/files/docs/2025/03/27/14.-SSWG_Update_ROS_04032025.pptx",
        "https://www.ercot.com/files/docs/2025/03/27/15.-Planning-Working-Group-Update_040325.pptx",
        "https://www.ercot.com/files/docs/2025/03/27/17.-20250403_DWG-Report-to-ROS-April-2025.pptx",
        "https://www.ercot.com/files/docs/2025/03/27/18.-IBRWG_Scope_ROS_Approved_20230706.docx",
        "https://www.ercot.com/files/docs/2025/03/31/19.-IBRWG-Report-to-ROS-040325.docx",
        "https://www.ercot.com/files/docs/2025/03/27/21.-April_OTWG_Updates.pptx",
        "https://www.ercot.com/files/docs/2025/04/03/Meeting-Materials-ROS-20250403.zip",
        "https://www.ercot.com/files/docs/2025/03/31/Revision-Request-ROS-20250403.zip",
    ],
    "2025-05-01": [
        "https://www.ercot.com/files/docs/2025/06/16/APPROVED-Minutes-ROS-20250501.doc",
        "https://www.ercot.com/files/docs/2025/05/01/2025-ROS-Combined-Ballot-20250501.xls",
        "https://www.ercot.com/files/docs/2025/05/01/2025-ROS-Ballot-20250501-Waive-Notice-NPRR1282-and-NOGRR277.xls",
        "https://www.ercot.com/files/docs/2025/05/01/2025-ROS-Ballot-20250501-DWG-Manual.xls",
        "https://www.ercot.com/files/docs/2025/04/29/02.-ROS-Agenda-2025040501.v2.docx",
        "https://www.ercot.com/files/docs/2025/04/24/03.-Draft-Minutes-ROS-20250403-.doc",
        "https://www.ercot.com/files/docs/2025/04/25/SystemPlanningROS_Mar2025.docx",
        "https://www.ercot.com/files/docs/2025/04/28/10.-OWG_ROS_20250501.pptx",
        "https://www.ercot.com/files/docs/2025/04/29/12.-PDCWG-Report-to-ROS_050125.pptx",
        "https://www.ercot.com/files/docs/2025/04/24/14.-Proposed_spwg_procedures_050125.docx",
        "https://www.ercot.com/files/docs/2025/05/01/15.-SSWG_Update_ROS_05012025.pptx",
        "https://www.ercot.com/files/docs/2025/05/01/16.-202505_DWG-Report-to-ROS-May-2025.pptx",
        "https://www.ercot.com/files/docs/2025/05/01/16.-DRAFT-Dwg_Procedure_Manual_Revision_23-AGS-ESR-and-Load-Model-Posting.docx",
        "https://www.ercot.com/files/docs/2025/04/30/17.-Planning-Working-Group-Update_050125.pptx",
        "https://www.ercot.com/files/docs/2025/04/28/19.-IBRWG-Report-to-ROS-050125.docx",
        "https://www.ercot.com/files/docs/2025/04/28/20.-April_OTWG_Updates.pptx",
        "https://www.ercot.com/files/docs/2025/04/24/21.-2026-Draft-Block-Meeting-Schedule.v2.xls",
        "https://www.ercot.com/files/docs/2025/05/01/Meeting-Materials-ROS-20250501.zip",
        "https://www.ercot.com/files/docs/2025/04/30/Revision-Request-ROS-20250501.zip",
        "https://www.ercot.com/files/docs/2025/08/07/March-2025-ERCOT-Operations-Report-Public_rev1.docx",
    ],
    "2025-05-20": [
        "https://www.ercot.com/files/docs/2025/05/20/2025-ROS-NOGRR265-Email-Ballot-20250520.xls",
        "https://www.ercot.com/files/docs/2025/05/20/2025-ROS-NOGRR277-Email-Ballot-20250520.xls",
    ],
    "2025-06-05": [
        "https://www.ercot.com/files/docs/2025/07/29/APPROVED-Minutes-ROS-20250605.doc",
        "https://www.ercot.com/files/docs/2025/06/05/ROS-20250605-Ballot-Combined.xls",
        "https://www.ercot.com/files/docs/2025/05/29/ROS-Agenda-20250605.docx",
        "https://www.ercot.com/files/docs/2025/05/29/3.-Draft-Minutes-ROS-20250501.doc",
        "https://www.ercot.com/files/docs/2025/05/13/SystemPlanningROS_April2025.docx",
        "https://www.ercot.com/files/docs/2025/06/04/06.-EPRI_Iberian_Blackout_2025Apr28_for_ERCOT_v2.pdf",
        "https://www.ercot.com/files/docs/2025/06/04/07._09.-June-2025-ROS_ERCOT-Comments-to-NOGRR272-PGRR121-NPRR1278.pdf",
        "https://www.ercot.com/files/docs/2025/06/05/07.-ERCOT_NPRR1283_Overview_R1.pptx",
        "https://www.ercot.com/files/docs/2025/06/03/12.-SSWG_Update_ROS_06052025_R2.pptx",
        "https://www.ercot.com/files/docs/2025/06/03/12.-SSWG_Procedure_Manual_Pending_ROS-approval_06052025_Final.docx",
        "https://www.ercot.com/files/docs/2025/05/29/13.-OWG_ROS_20250605.pptx",
        "https://www.ercot.com/files/docs/2025/06/05/14.-Planning-Working-Group-Update_06_05_25.pptx",
        "https://www.ercot.com/files/docs/2025/06/04/15.-20250605_DWG-Report-to-ROS-June-2025.pptx",
        "https://www.ercot.com/files/docs/2025/05/29/12.-Draft-DWG-Procedure-Manual-Revision_15.-24-PSSE-version-transition-and-load-survey.docx",
        "https://www.ercot.com/files/docs/2025/06/04/17.-PDCWG-Report-to-ROS_060525.pptx",
        "https://www.ercot.com/files/docs/2025/05/29/18.-VPWG_update_to_ROS_May.pptx",
        "https://www.ercot.com/files/docs/2025/06/05/Revision-Request-ROS-20250605.zip",
        "https://www.ercot.com/files/docs/2025/08/07/April-2025-ERCOT-Operations-Report-Public_rev1.docx",
    ],
    "2025-07-10": [
        "https://www.ercot.com/files/docs/2025/08/07/APPROVED-Minutes-ROS-20250710.doc",
        "https://www.ercot.com/files/docs/2025/07/21/ROS-20250710-Ballot-Combined.xls",
        "https://www.ercot.com/files/docs/2025/07/03/02.-ROS-Agenda-20250710-.docx",
        "https://www.ercot.com/files/docs/2025/07/03/03.-Draft-Minutes-ROS-20250605-.doc",
        "https://www.ercot.com/files/docs/2025/06/23/SystemPlanningROS_May2025.docx",
        "https://www.ercot.com/files/docs/2025/07/07/10.-SPWG-ROS-Update-07-10-2025.pptx",
        "https://www.ercot.com/files/docs/2025/07/03/11.-SSWG_Update_ROS_07102025.pptx",
        "https://www.ercot.com/files/docs/2025/07/07/13.-OWG_ROS_20250710.v2.pptx",
        "https://www.ercot.com/files/docs/2025/07/08/14.-Planning-Working-Group-update-7102025.pptx",
        "https://www.ercot.com/files/docs/2025/07/03/15.-20250710_DWG-Report-to-ROS-July-2025.pptx",
        "https://www.ercot.com/files/docs/2025/07/09/17.-PDCWG-Report-to-ROS_071025.pptx",
        "https://www.ercot.com/files/docs/2025/07/07/19.-IBRWG-Report-to-ROS-071025.docx",
        "https://www.ercot.com/files/docs/2025/07/03/20.-July_OTWG_Updates.pptx",
        "https://www.ercot.com/files/docs/2025/07/03/21.-Biennial-Structural-Review-ROS-and-WGs.v3_-final.docx",
        "https://www.ercot.com/files/docs/2025/07/09/Meeting-Materials-ROS-20250710.zip",
        "https://www.ercot.com/files/docs/2025/07/09/Revision-Requests-ROS-20250710.zip",
        "https://www.ercot.com/files/docs/2025/08/07/May-2025-ERCOT-Operations-Report-Public_rev1.docx",
    ],
    "2025-08-07": [
        "https://www.ercot.com/files/docs/2025/09/12/APPROVED-Minutes-ROS-20250807.doc",
        "https://www.ercot.com/files/docs/2025/08/07/ROS-20250807-Ballot-2026-AS-Methodology.xls",
        "https://www.ercot.com/files/docs/2025/08/07/ROS-20250807-Ballot-NOGRR272-and-PGRR121.xls",
        "https://www.ercot.com/files/docs/2025/08/07/ROS-20250807-Ballot-Combined.xls",
        "https://www.ercot.com/files/docs/2025/07/31/ROS-Agenda-20250807.docx",
        "https://www.ercot.com/files/docs/2025/08/04/03.-Draft-Minutes-ROS-20250710.doc",
        "https://www.ercot.com/files/docs/2025/07/15/SystemPlanningROS_June2025.docx",
        "https://www.ercot.com/files/docs/2025/08/11/05.-ros_2026_AS_Methodology_08072025_REVISED.zip",
        "https://www.ercot.com/files/docs/2025/08/05/05.-ros_2026_AS_Methodology_08072025-v2.zip",
        "https://www.ercot.com/files/docs/2025/08/05/05.-IMM-Commentary-on-2026-AS-Methodology-for-WMS-and-ROS.pdf",
        "https://www.ercot.com/files/docs/2025/08/01/10.-OWG_ROS_20250807.pptx",
        "https://www.ercot.com/files/docs/2025/08/05/11.-SPWG-ROS-Update-8-07-2025.pptx",
        "https://www.ercot.com/files/docs/2025/08/05/12.-SSWG_Update_ROS_08072025.pptx",
        "https://www.ercot.com/files/docs/2025/08/05/14.-Planning-Working-Group-update-08072025.pptx",
        "https://www.ercot.com/files/docs/2025/08/05/15.-PDCWG-Report-to-ROS_080725.pptx",
        "https://www.ercot.com/files/docs/2025/08/04/16.-IBRWG-Report-to-ROS-080725.docx",
        "https://www.ercot.com/files/docs/2025/08/06/Meeting-Materials-ROS-20250807.zip",
        "https://www.ercot.com/files/docs/2025/08/06/Revision-Requests-ROS-20250807.zip",
        "https://www.ercot.com/files/docs/2025/08/07/June-2025-ERCOT-Operations-Report-Redline-Public_rev1.docx",
    ],
    "2025-09-11": [
        "https://www.ercot.com/files/docs/2025/11/10/APPROVED-Minutes-ROS-20250911.doc",
        "https://www.ercot.com/files/docs/2025/09/11/ROS-20250911-Ballot-Combined.xls",
        "https://www.ercot.com/files/docs/2025/09/08/02.-ROS-Agenda-20250911v.2.docx",
        "https://www.ercot.com/files/docs/2025/09/10/03.-Draft-Minutes-ROS-20250807.doc",
        "https://www.ercot.com/files/docs/2025/09/11/05.-2025-EIA-Data-RFI-ROS.pdf",
        "https://www.ercot.com/files/docs/2025/09/10/05.-2025-ERCOT-UFLS-Survey-Results-PUBLIC-.v2.pptx",
        "https://www.ercot.com/files/docs/2025/09/08/05.-July-2025-ERCOT-Operations-Report-Redline_Public.docx",
        "https://www.ercot.com/files/docs/2025/09/08/05.-SystemPlanningROS_July2025.docx",
        "https://www.ercot.com/files/docs/2025/09/04/05.-Far-West-ROS_V2.potx.pptx",
        "https://www.ercot.com/files/docs/2025/09/04/09.-MTE_2025_v2.xlsx",
        "https://www.ercot.com/files/docs/2025/09/08/09.-OWG_ROS_20250911.pptx",
        "https://www.ercot.com/files/docs/2025/09/04/10.-VPWG_update_to_ROS_August.pptx",
        "https://www.ercot.com/files/docs/2025/09/08/11.-Planning-Working-Group-update-09112025.pptx",
        "https://www.ercot.com/files/docs/2025/09/04/12.-Draft_ROS_Procedures_20250828.doc",
        "https://www.ercot.com/files/docs/2025/09/04/14.-SSWG_Update_ROS_09112025.pptx",
        "https://www.ercot.com/files/docs/2025/09/04/14.-SSWG_Procedure_Manual_ROS_Approved_06052025_Update_08202025.docx",
        "https://www.ercot.com/files/docs/2025/09/04/16.-20250902_DWG-Report-to-ROS-September-2025.pptx",
        "https://www.ercot.com/files/docs/2025/09/08/17.-IBRWG-REport-to-ROS-09112025.docx",
        "https://www.ercot.com/files/docs/2025/09/11/Meeting-Materials-ROS-20250911.zip",
        "https://www.ercot.com/files/docs/2025/09/04/Revision-Requests-ROS-20250911.zip",
    ],
    "2025-10-02": [
        "https://www.ercot.com/files/docs/2025/11/10/APPROVED-Minutes-ROS-20251002.doc",
        "https://www.ercot.com/files/docs/2025/10/02/20251002-ROS-Ballot-Combined.xls",
        "https://www.ercot.com/files/docs/2025/10/01/02.-ROS-Agenda-20251002.v3.docx",
        "https://www.ercot.com/files/docs/2025/09/30/04.-August-2025-ERCOT-Operations-Report-Public_rev1.docx",
        "https://www.ercot.com/files/docs/2025/10/08/04.-August-2025-ERCOT-Operations-Report-Public_rev2.v2.docx",
        "https://www.ercot.com/files/docs/2025/09/30/04.-SystemPlanningROS_Aug2025.docx",
        "https://www.ercot.com/files/docs/2025/09/26/09.-OWG_ROS_20251002.pptx",
        "https://www.ercot.com/files/docs/2025/09/29/10.-Planning-Working-Group-update-10022025.pptx",
        "https://www.ercot.com/files/docs/2025/09/25/12.-MWG-Procedures-WMS-to-ROS-Revision-09_11_25.doc_safe.pdf",
        "https://www.ercot.com/files/docs/2025/10/01/12.-2025-ROS-Meter-Working-Group-Leadership-Nominees-20251002.pptx",
        "https://www.ercot.com/files/docs/2025/10/02/12.-MWG-Procedures-WMS-to-ROS-Revision_redlines.doc",
        "https://www.ercot.com/files/docs/2025/09/29/13.-IBRWG-Report-to-ROS-10022025.docx",
        "https://www.ercot.com/files/docs/2025/10/01/14.-October_OTWG_Updates.pptx",
        "https://www.ercot.com/files/docs/2025/10/01/15.-PDCWG-Report-to-ROS_100225.pptx",
        "https://www.ercot.com/files/docs/2025/09/26/16.-SSWG_Update_ROS_10022025.pptx",
        "https://www.ercot.com/files/docs/2025/10/02/17.-NOGRR245-12312025-Deadline.pptx",
        "https://www.ercot.com/files/docs/2025/10/08/Meeting-Materials-ROS-20251002.zip",
        "https://www.ercot.com/files/docs/2025/10/01/Revision-Requests-ROS-20251002.zip",
    ],
    "2025-11-06": [
        "https://www.ercot.com/files/docs/2025/12/10/APPROVED-Minutes-ROS-20251106.doc",
        "https://www.ercot.com/files/docs/2025/11/06/20251106-ROS-Ballot-Combined.xls",
        "https://www.ercot.com/files/docs/2025/11/06/20251106-ROS-Ballot-Grant-PGRR132-Urgent-Status.xls",
        "https://www.ercot.com/files/docs/2025/11/06/20251106-ROS-Ballot-Grant-PGRR133-Urgent-Status.xls",
        "https://www.ercot.com/files/docs/2025/11/04/02.-ROS-Agenda-20251106.v3.docx",
        "https://www.ercot.com/files/docs/2025/10/30/03.-Draft-Minutes-ROS-20250911.doc",
        "https://www.ercot.com/files/docs/2025/11/04/03.-Draft-Minutes-ROS-20251002.doc",
        "https://www.ercot.com/files/docs/2025/10/30/05.-September-2025-ERCOT-Operations-Report-Public.docx",
        "https://www.ercot.com/files/docs/2025/11/06/05.-SystemPlanningROS_Sept2025.docx",
        "https://www.ercot.com/files/docs/2025/11/04/10.-Planning-Working-Group-update-11062025.pptx",
        "https://www.ercot.com/files/docs/2025/10/31/12.-20251106_DWG-Report-to-ROS-November-2025.pptx",
        "https://www.ercot.com/files/docs/2025/11/03/13.-IBRWG-Report-to-ROS-11062025.docx",
        "https://www.ercot.com/files/docs/2025/11/06/16.-SSWG_Update_ROS_11062025.pptx",
        "https://www.ercot.com/files/docs/2025/11/06/Meeting-Materials-ROS-20251106.zip",
        "https://www.ercot.com/files/docs/2025/11/06/Revision-Requests-ROS-20251106.zip",
    ],
    "2025-12-04": [
        "https://www.ercot.com/files/docs/2026/01/08/APPROVED-Minutes-ROS-20251204.doc",
        "https://www.ercot.com/files/docs/2025/12/04/20251204-ROS-Ballot-Combined.xls",
        "https://www.ercot.com/files/docs/2025/12/04/20251204-ROS-Ballot-PGRR132.xls",
        "https://www.ercot.com/files/docs/2025/11/26/02.-ROS-Agenda-20251204.docx",
        "https://www.ercot.com/files/docs/2025/11/26/03.-DRAFT-Minutes-ROS-20251106.doc",
        "https://www.ercot.com/files/docs/2025/11/26/05.-October-2025-ERCOT-Operations-Report-Public.docx",
        "https://www.ercot.com/files/docs/2025/11/26/05.-SystemPlanningROS_Oct2025.docx",
        "https://www.ercot.com/files/docs/2025/12/01/11.-OWG_ROS_20251204.pptx",
        "https://www.ercot.com/files/docs/2025/12/02/12.-Planning-Working-Group-update-12042025.pptx",
        "https://www.ercot.com/files/docs/2025/12/03/16.-PDCWG-Report-to-ROS_120425.pptx",
        "https://www.ercot.com/files/docs/2025/11/26/18.-SPWG-ROS-Update-12-04-2025.pptx",
        "https://www.ercot.com/files/docs/2025/11/26/19.-VPWG_update_to_ROS_Nov.pptx",
        "https://www.ercot.com/files/docs/2025/12/03/Meeting-Materials-ROS-20251204.zip",
        "https://www.ercot.com/files/docs/2025/11/26/Revision-Requests-ROS-20251204.zip",
    ],
}


def download_file(url, folder):
    filename = unquote(os.path.basename(urlparse(url).path))
    dest = os.path.join(folder, filename)
    if os.path.exists(dest):
        print(f"  [SKIP] {filename}")
        return "skip"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=60)
        resp.raise_for_status()
        with open(dest, "wb") as f:
            f.write(resp.content)
        kb = len(resp.content) // 1024
        print(f"  [OK]   {filename}  ({kb} KB)")
        return "ok"
    except Exception as e:
        print(f"  [ERR]  {filename}  — {e}")
        return "err"


def main():
    total_ok = total_skip = total_err = 0
    for date_str in sorted(MEETINGS):
        folder = os.path.join(BASE_DIR, date_str)
        os.makedirs(folder, exist_ok=True)
        urls = MEETINGS[date_str]
        print(f"\n[ROS {date_str}]  {len(urls)} document(s)  ->  {folder}")
        for url in urls:
            result = download_file(url, folder)
            if result == "ok":
                total_ok += 1
            elif result == "skip":
                total_skip += 1
            else:
                total_err += 1
            time.sleep(0.5)

    print(f"\n{'='*60}")
    print(f"Done.  Downloaded: {total_ok}  |  Skipped: {total_skip}  |  Errors: {total_err}")


if __name__ == "__main__":
    main()
