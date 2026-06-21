# ERCOT Stakeholder Meetings — Download & Update Skill

> **Purpose:** A complete reference for fetching ERCOT stakeholder committee meeting schedules from ercot.com and generating per-committee Excel workbooks with historical and future meetings, hyperlinks, color-coded status rows, and a Summary sheet.
>
> **Always begin with Step 0.** The live committee list at `ercot.com/committees` is the authoritative source of scope. Do not rely on a cached list — groups are added, disbanded, or renamed over time.

---

## Step 0 — Discover the Full Committee List (Always Do This First)

Before fetching any meeting data, retrieve the current list of all groups from the ERCOT committees index page and decide which ones fall within scope.

### 0.1 Fetch the Index Page

```
web_fetch(url="https://www.ercot.com/committees",
          html_extraction_method="markdown",
          text_content_token_limit=10000)
```

This page lists every active group with its URL. As of May 2026, the full hierarchy returned is:

```
Board of Directors
  ├── Finance and Audit Committee        /committees/board/finance_audit
  ├── HR and Governance Committee        /committees/board/hr_governance
  └── Technology and Security Committee  /committees/board/tech-security

Technical Advisory Committee (TAC)      /committees/tac
  ├── Large Load Working Group (LLWG)    /committees/tac/llwg
  ├── Credit Finance Sub Group (CFSG)    /committees/tac/cfsg
  └── Real-Time Co-optimization plus
      Batteries Task Force (RTCBTF) *    /committees/tac/rtcbtf  ← may redirect to inactive

Protocol Revision Subcommittee (PRS)    /committees/prs

Retail Market Subcommittee (RMS)        /committees/rms
  ├── TDTMS Working Group                /committees/rms/tdtms
  ├── TXSETLP Working Group              /committees/rms/txsetlp
  └── RMTTF Task Force                   /committees/rms/rmttf

Reliability and Operations Sub. (ROS)   /committees/ros
  ├── Black Start WG (BSWG)              /committees/ros/bswg
  ├── Dynamics WG (DWG)                  /committees/ros/dwg
  ├── Inverter-Based Resource WG (IBRWG) /committees/ros/ibrwg
  ├── Meter WG (MWG)                     /committees/ros/mwg
  ├── Network Data Support WG (NDSWG)    /committees/ros/ndswg
  ├── Operations WG (OWG)                /committees/ros/owg
  ├── Operations Training WG (OTWG)      /committees/ros/otwg
  ├── Performance, Disturbance,
      Compliance WG (PDCWG)              /committees/ros/pdcwg
  ├── Planning WG (PLWG)                 /committees/ros/plwg
  ├── System Protection WG (SPWG)        /committees/ros/spwg
  ├── Steady State WG (SSWG)             /committees/ros/sswg
  └── Voltage Profile WG (VPWG)          /committees/ros/vpwg

Wholesale Market Subcommittee (WMS)     /committees/wms
  ├── Congestion Management WG (CMWG)    /committees/wms/cmwg
  ├── Demand Side WG (DSWG)              /committees/wms/dswg
  ├── Supply Analysis WG (SAWG)          /committees/wms/sawg
  └── Wholesale Market WG (WMWG)         /committees/wms/wmwg

Inactive Groups                          /committees/inactive
  ├── Resource Cost WG (RCWG)            /committees/inactive/rcwg
  ├── RTCBTF (winding down)              /committees/inactive/rtcbtf  *moved here 2026
  └── IBR Task Force (IBRTF) — 2022 only /committees/inactive/ibrtf/2022
```

> **Note:** The `/committees/inactive` section requires a separate fetch. RTCBTF was nominally under TAC in the nav but its year-archive pages moved to `/committees/inactive/rtcbtf/YEAR` as of 2026.

### 0.2 Apply Scope Criteria

For each group found in Step 0.1, evaluate it against all four criteria. A group is **IN SCOPE** only if it passes all four:

| # | Criterion | Rationale |
|---|---|---|
| **A** | Has its own `/YEAR` sub-page structure **or** lists meetings directly on its main page via any discoverable hyperlink pattern | Required for year-by-year historical data extraction. The `/YEAR` sub-page is the most common pattern, but some groups (e.g. Board, TAC) list meetings on their main page with the same `ercot.com/calendar/MMDDYYYY-[name]` link format — these qualify equally. |
| **B** | Has a standalone meeting list with per-meeting calendar links in the format `ercot.com/calendar/MMDDYYYY-[group-name]-[type]` | Ensures each meeting row is individually linkable. Groups whose meetings only appear as entries on a parent group's page (e.g. Board sub-committees whose meetings are absorbed into Board agendas) do not qualify unless they have their own separate calendar entries. |
| **C** | Is active or has a meaningful inactive history worth preserving | No value building a file for a group with zero meetings |
| **D** | Is listed under `ercot.com/committees` and appears in the ERCOT stakeholder process — including governance bodies (Board, TAC) whose meetings are public and open to market participants | Removed the previous exclusion of governance bodies. Board and TAC meetings are public, use the same URL and data patterns as all other committees, and are relevant context for the full stakeholder hierarchy. |

**How to test Criterion A:** Attempt `web_fetch` on `https://www.ercot.com/committees/<path>/YEAR` for the most recent year. If the page lists meetings under a "Scheduled Meetings and Meeting Details" heading, it passes. If it returns the parent page or a 404, also check whether the group's **main page** (without `/YEAR`) already lists meetings with `ercot.com/calendar/MMDDYYYY-[name]` links — if so, it still passes Criterion A.

**How to test Criterion B:** Look for individual calendar hyperlinks in the format `ercot.com/calendar/MMDDYYYY-[group-name]-[meeting-type]` in the meeting list. All currently in-scope groups use this pattern. Groups that only appear inside another group's agenda documents (PDFs or DOCs) do not pass.

### 0.3 Scope Decision Table

Apply the criteria to the full group list. The table below reflects the May 2026 evaluation — **re-run this evaluation on each use** in case groups have been added or disbanded:

| Group | Abbrev | A: /YEAR + calendar slug | B: Own calendar entries? | C: History? | D: Listed under /committees? | Decision |
|---|---|---|---|---|---|---|
| Board of Directors | **Board** | ✓ `/YEAR` 2002+; `MMDDYYYY-Board-of-Directors-Meeting` | ✓ | ✓ | ✓ | ✅ **IN SCOPE** |
| Finance & Audit Committee | **F&A** | ✓ `/YEAR` 2004+; `MMDDYYYY-Finance-_-Audit-Committee` | ✓ | ✓ | ✓ | ✅ **IN SCOPE** |
| HR & Governance Committee | **HR&G** | ✓ `/YEAR` 2002+; `MMDDYYYY-HR-_-Governance-Committee` | ✓ | ✓ | ✓ | ✅ **IN SCOPE** |
| Technology & Security Committee | **T&S** | ✓ `/YEAR` 2023+; `MMDDYYYY-Technology-_-Security-Committee` | ✓ | ✓ | ✓ | ✅ **IN SCOPE** |
| Technical Advisory Committee | **TAC** | ✓ `/YEAR` 2002+; `MMDDYYYY-TAC-Meeting` or `MMDDYYYY-Special-TAC-Meeting` | ✓ | ✓ | ✓ | ✅ **IN SCOPE** |
| Large Load Working Group | **LLWG** | ✓ `/YEAR` 2025+; `MMDDYYYY-LLWG-Meeting` | ✓ | ✓ | ✓ | ✅ **IN SCOPE** |
| Credit Finance Sub Group | **CFSG** | ✓ `/YEAR` 2023+; `MMDDYYYY-CFSG-Meeting[-_-Webex]` | ✓ | ✓ | ✓ | ✅ **IN SCOPE** |
| RT Co-optimization + Batteries TF *(now inactive)* | **RTCBTF** | ✓ `/YEAR` 2023–2025 at `/committees/inactive/rtcbtf/YEAR`; `MMDDYYYY-RTCBTF-Meeting[-_-Webex]` | ✓ | ✓ (winding down 2026) | ✓ | ✅ **IN SCOPE** — inactive tab (like IBRTF) |
| Protocol Revision Subcommittee | **PRS** | ✓ `/YEAR` 2010+; `MMDDYYYY-PRS-Meeting` | ✓ | ✓ | ✓ | ✅ **IN SCOPE** |
| Retail Market Subcommittee | **RMS** | ✓ `/YEAR` 2010+; `MMDDYYYY-RMS-Meeting[-_-Webex]` | ✓ | ✓ | ✓ | ✅ **IN SCOPE** |
| TDTMS Working Group | **TDTMS** | ✓ `/YEAR` 2015+; `MMDDYYYY-TDTMS-Meeting[-_-Webex]` | ✓ | ✓ | ✓ | ✅ **IN SCOPE** |
| TXSETLP Working Group | TXSETLP | ✗ no `/YEAR` archive pages; `MMDDYYYY-Texas-SET_LP-Meeting[-_]` on main page only | ✓ (main page only) | ✓ | ✓ | **OUT** — Criterion A: no `/YEAR` archive, main-page list only with no historical data |
| RMTTF Task Force | **RMTTF** | ✓ `/YEAR` 2015+; `MMDDYYYY-RMTTF-Meeting[-_-Webex]` | ✓ | ✓ | ✓ | ✅ **IN SCOPE** |
| Reliability & Operations Sub. | **ROS** | ✓ `/YEAR` 2010+; `MMDDYYYY-ROS-Meeting[-_-Webex]` | ✓ | ✓ | ✓ | ✅ **IN SCOPE** |
| Inverter-Based Resource WG | **IBRWG** | ✓ `/YEAR` 2023+; `MMDDYYYY-IBRWG-Meeting-_-Webex` | ✓ | ✓ | ✓ | ✅ **IN SCOPE** |
| Black Start WG | **BSWG** | ✓ `/YEAR` 2002+; `MMDDYYYY-BSWG-Meeting[-_-Webex]` | ✓ | ✓ | ✓ | ✅ **IN SCOPE** |
| Dynamics WG | **DWG** | ✓ `/YEAR` 2003+; `MMDDYYYY-DWG-Meeting-_-Webex` | ✓ | ✓ | ✓ | ✅ **IN SCOPE** |
| Meter WG | **MWG** | ✓ `/YEAR` 2002+ (gap: no 2015); `MMDDYYYY-MWG-Meeting[-_-Webex]` | ✓ | ✓ | ✓ | ✅ **IN SCOPE** |
| Network Data Support WG | **NDSWG** | ✓ `/YEAR` 2002–2024; `MMDDYYYY-NDSWG-Meeting[-_-Webex]` | ✓ | ✓ | ✓ | ✅ **IN SCOPE** |
| Operations WG | **OWG** | ✓ `/YEAR` (verify year range); `MMDDYYYY-OWG-Meeting[-_-Webex]` | ✓ | ✓ | ✓ | ✅ **IN SCOPE** |
| Operations Training WG | **OTWG** | ✓ `/YEAR` (verify year range); `MMDDYYYY-OTWG-Meeting[-_-Webex]` | ✓ | ✓ | ✓ | ✅ **IN SCOPE** |
| Performance, Disturbance, Compliance WG | **PDCWG** | ✓ `/YEAR` (verify year range); `MMDDYYYY-PDCWG-Meeting[-_-Webex]` | ✓ | ✓ | ✓ | ✅ **IN SCOPE** |
| Planning WG | **PLWG** | ✓ `/YEAR` 2010+; `MMDDYYYY-PLWG-Meeting[-_-Webex]` | ✓ | ✓ | ✓ | ✅ **IN SCOPE** |
| System Protection WG | **SPWG** | ✓ `/YEAR` (verify year range); `MMDDYYYY-SPWG-Meeting[-_-Webex]` | ✓ | ✓ | ✓ | ✅ **IN SCOPE** |
| Steady State WG | **SSWG** | ✓ `/YEAR` (verify year range); `MMDDYYYY-SSWG-Meeting[-_-Webex]` | ✓ | ✓ | ✓ | ✅ **IN SCOPE** |
| Voltage Profile WG | **VPWG** | ✓ `/YEAR` (verify year range); `MMDDYYYY-VPWG-Meeting[-_-Webex]` | ✓ | ✓ | ✓ | ✅ **IN SCOPE** |
| Wholesale Market Subcommittee | **WMS** | ✓ `/YEAR` 2010+; `MMDDYYYY-WMS-Meeting[-_-Webex]` | ✓ | ✓ | ✓ | ✅ **IN SCOPE** |
| Congestion Management WG | **CMWG** | ✓ `/YEAR` 2010+; `MMDDYYYY-CMWG-Meeting[-_-Webex]` | ✓ | ✓ | ✓ | ✅ **IN SCOPE** |
| Demand Side WG | **DSWG** | ✓ `/YEAR` 2002+; `MMDDYYYY-DSWG-Meeting[-_-Webex]` (also `Joint-DSWG_WMWG-Meeting`) | ✓ | ✓ | ✓ | ✅ **IN SCOPE** |
| Supply Analysis WG | **SAWG** | ✓ `/YEAR` 2015+; `MMDDYYYY-SAWG-Meeting-_-Webex` | ✓ | ✓ | ✓ | ✅ **IN SCOPE** |
| Wholesale Market WG | **WMWG** | ✓ `/YEAR` 2019+; `MMDDYYYY-WMWG-Meeting[-_-Webex]` (also `Joint-DSWG_WMWG-Meeting`) | ✓ | ✓ | ✓ | ✅ **IN SCOPE** |
| IBR Task Force *(inactive)* | IBRTF | ✓ 2022 only at `/committees/inactive/ibrtf/2022`; `MMDDYYYY-IBRTF-Meeting` | ✓ | ✓ (predecessor) | ✓ | ✅ **IN SCOPE** — tab in IBRWG file |

### 0.4 What To Do If the List Has Changed

If Step 0.1 returns a group **not in the table above**, run this check before deciding:

1. Try `web_fetch` on `https://www.ercot.com/committees/<path>/YEAR` for the current year.
2. If a page with a meeting list exists → Criterion A passes. Evaluate B–D manually.
3. If all four criteria pass → add to scope, create a new Excel file, update Section 1 of this document.
4. If a previously in-scope group has disappeared from the index → mark it inactive; keep its existing Excel file but stop updating it.

---

## 1. Confirmed In-Scope Committees

The groups confirmed in-scope after Step 0 evaluation. **Treat this list as a snapshot, not a permanent truth** — always verify via Step 0 before starting work.

**Board and sub-committees:**

| # | Abbreviation | Full Name | URL Pattern | Year Range | Output File |
|---|---|---|---|---|---|
| 1 | **Board** | Board of Directors | `ercot.com/committees/board/YEAR` | 2002–present | `ERCOT_Board_Meetings_YYYY_YYYY.xlsx` |
| 1a | **F&A** | Finance and Audit Committee | `ercot.com/committees/board/finance_audit/YEAR` | 2004–present | `ERCOT_FA_Meetings_YYYY_YYYY.xlsx` |
| 1b | **HR&G** | HR and Governance Committee | `ercot.com/committees/board/hr_governance/YEAR` | 2002–present | `ERCOT_HRG_Meetings_YYYY_YYYY.xlsx` |
| 1c | **T&S** | Technology and Security Committee | `ercot.com/committees/board/tech-security/YEAR` | 2023–present | `ERCOT_TS_Meetings_YYYY_YYYY.xlsx` |

**TAC and sub-groups:**

| # | Abbreviation | Full Name | URL Pattern | Year Range | Output File |
|---|---|---|---|---|---|
| 2 | **TAC** | Technical Advisory Committee | `ercot.com/committees/tac/YEAR` | 2002–present | `ERCOT_TAC_Meetings_YYYY_YYYY.xlsx` |
| 2a | **LLWG** | Large Load Working Group | `ercot.com/committees/tac/llwg/YEAR` | 2025–present | `ERCOT_LLWG_Meetings_YYYY_YYYY.xlsx` |
| 2b | **CFSG** | Credit Finance Sub Group | `ercot.com/committees/tac/cfsg/YEAR` | 2023–present | `ERCOT_CFSG_Meetings_YYYY_YYYY.xlsx` |
| 2c | **RTCBTF** | RT Co-optimization + Batteries TF *(now inactive)* | `ercot.com/committees/inactive/rtcbtf/YEAR` | 2023–2026 | *(tab in TAC file or standalone)* |

**Subcommittees and working groups:**

| # | Abbreviation | Full Name | URL Pattern | Year Range | Output File |
|---|---|---|---|---|---|
| 3 | **PRS** | Protocol Revision Subcommittee | `ercot.com/committees/prs/YEAR` | 2010–present | `ERCOT_PRS_Meetings_YYYY_YYYY.xlsx` |
| 4 | **RMS** | Retail Market Subcommittee | `ercot.com/committees/rms/YEAR` | 2010–present | `ERCOT_RMS_Meetings_YYYY_YYYY.xlsx` |
| 4a | **TDTMS** | Texas Data Transport and MarkeTrak Systems WG | `ercot.com/committees/rms/tdtms/YEAR` | 2015–present | `ERCOT_TDTMS_Meetings_YYYY_YYYY.xlsx` |
| 4b | **RMTTF** | Retail Market Training Task Force | `ercot.com/committees/rms/rmttf/YEAR` | 2015–present | `ERCOT_RMTTF_Meetings_YYYY_YYYY.xlsx` |
| 5 | **ROS** | Reliability and Operations Subcommittee | `ercot.com/committees/ros/YEAR` | 2010–present | `ERCOT_ROS_Meetings_YYYY_YYYY.xlsx` |
| 5a | **IBRWG** | Inverter-Based Resource Working Group | `ercot.com/committees/ros/ibrwg/YEAR` | 2023–present | `ERCOT_IBRWG_Meetings_YYYY_YYYY.xlsx` |
| 5b | **BSWG** | Black Start Working Group | `ercot.com/committees/ros/bswg/YEAR` | 2002–present | `ERCOT_BSWG_Meetings_YYYY_YYYY.xlsx` |
| 5c | **DWG** | Dynamics Working Group | `ercot.com/committees/ros/dwg/YEAR` | 2003–present | `ERCOT_DWG_Meetings_YYYY_YYYY.xlsx` |
| 5d | **MWG** | Meter Working Group | `ercot.com/committees/ros/mwg/YEAR` | 2002–present | `ERCOT_MWG_Meetings_YYYY_YYYY.xlsx` |
| 5e | **NDSWG** | Network Data Support Working Group | `ercot.com/committees/ros/ndswg/YEAR` | 2002–present | `ERCOT_NDSWG_Meetings_YYYY_YYYY.xlsx` |
| 5f | **OWG** | Operations Working Group | `ercot.com/committees/ros/owg/YEAR` | verify | `ERCOT_OWG_Meetings_YYYY_YYYY.xlsx` |
| 5g | **OTWG** | Operations Training Working Group | `ercot.com/committees/ros/otwg/YEAR` | verify | `ERCOT_OTWG_Meetings_YYYY_YYYY.xlsx` |
| 5h | **PDCWG** | Performance, Disturbance, Compliance WG | `ercot.com/committees/ros/pdcwg/YEAR` | verify | `ERCOT_PDCWG_Meetings_YYYY_YYYY.xlsx` |
| 5i | **PLWG** | Planning Working Group | `ercot.com/committees/ros/plwg/YEAR` | 2010–present | `ERCOT_PLWG_Meetings_YYYY_YYYY.xlsx` |
| 5j | **SPWG** | System Protection Working Group | `ercot.com/committees/ros/spwg/YEAR` | verify | `ERCOT_SPWG_Meetings_YYYY_YYYY.xlsx` |
| 5k | **SSWG** | Steady State Working Group | `ercot.com/committees/ros/sswg/YEAR` | verify | `ERCOT_SSWG_Meetings_YYYY_YYYY.xlsx` |
| 5l | **VPWG** | Voltage Profile Working Group | `ercot.com/committees/ros/vpwg/YEAR` | verify | `ERCOT_VPWG_Meetings_YYYY_YYYY.xlsx` |
| 6 | **WMS** | Wholesale Market Subcommittee | `ercot.com/committees/wms/YEAR` | 2010–present | `ERCOT_WMS_Meetings_YYYY_YYYY.xlsx` |
| 6a | **CMWG** | Congestion Management Working Group | `ercot.com/committees/wms/cmwg/YEAR` | 2010–present | `ERCOT_CMWG_Meetings_YYYY_YYYY.xlsx` |
| 6b | **DSWG** | Demand Side Working Group | `ercot.com/committees/wms/dswg/YEAR` | 2002–present | `ERCOT_DSWG_Meetings_YYYY_YYYY.xlsx` |
| 6c | **SAWG** | Supply Analysis Working Group | `ercot.com/committees/wms/sawg/YEAR` | 2015–present | `ERCOT_SAWG_Meetings_YYYY_YYYY.xlsx` |
| 6d | **WMWG** | Wholesale Market Working Group | `ercot.com/committees/wms/wmwg/YEAR` | 2019–present | `ERCOT_WMWG_Meetings_YYYY_YYYY.xlsx` |

**Inactive predecessors (included as tabs in parent files):**

| # | Abbreviation | Full Name | URL | Notes |
|---|---|---|---|---|
| — | **IBRTF** | IBR Task Force | `ercot.com/committees/inactive/ibrtf/2022` | Tab in IBRWG file |
| — | **RTCBTF** | RT Co-optimization + Batteries TF | `ercot.com/committees/inactive/rtcbtf/YEAR` | Standalone file or tab in TAC file |

> **TXSETLP is the only currently listed group that remains OUT of scope:** it has calendar entries on its main page but no `/YEAR` archive pages, making historical extraction impossible.

**Individual meeting calendar URL patterns (confirmed from live pages):**

| Committee | Calendar URL slug |
|---|---|
| Board | `MMDDYYYY-Board-of-Directors-Meeting` |
| F&A | `MMDDYYYY-Finance-_-Audit-Committee` |
| HR&G | `MMDDYYYY-HR-_-Governance-Committee` |
| T&S | `MMDDYYYY-Technology-_-Security-Committee` |
| TAC | `MMDDYYYY-TAC-Meeting` or `MMDDYYYY-Special-TAC-Meeting` |
| LLWG | `MMDDYYYY-LLWG-Meeting` |
| CFSG | `MMDDYYYY-CFSG-Meeting[-_-Webex]` |
| RTCBTF | `MMDDYYYY-RTCBTF-Meeting[-_-Webex]` |
| PRS | `MMDDYYYY-PRS-Meeting` |
| RMS | `MMDDYYYY-RMS-Meeting[-_-Webex]` |
| TDTMS | `MMDDYYYY-TDTMS-Meeting[-_-Webex]` |
| RMTTF | `MMDDYYYY-RMTTF-Meeting[-_-Webex]` |
| ROS | `MMDDYYYY-ROS-Meeting[-_-Webex]` |
| IBRWG | `MMDDYYYY-IBRWG-Meeting-_-Webex` |
| BSWG | `MMDDYYYY-BSWG-Meeting[-_-Webex]` |
| DWG | `MMDDYYYY-DWG-Meeting-_-Webex` |
| MWG | `MMDDYYYY-MWG-Meeting[-_-Webex]` |
| NDSWG | `MMDDYYYY-NDSWG-Meeting[-_-Webex]` |
| OWG | `MMDDYYYY-OWG-Meeting[-_-Webex]` |
| OTWG | `MMDDYYYY-OTWG-Meeting[-_-Webex]` |
| PDCWG | `MMDDYYYY-PDCWG-Meeting[-_-Webex]` |
| PLWG | `MMDDYYYY-PLWG-Meeting[-_-Webex]` |
| SPWG | `MMDDYYYY-SPWG-Meeting[-_-Webex]` |
| SSWG | `MMDDYYYY-SSWG-Meeting[-_-Webex]` |
| VPWG | `MMDDYYYY-VPWG-Meeting[-_-Webex]` |
| WMS | `MMDDYYYY-WMS-Meeting[-_-Webex]` |
| CMWG | `MMDDYYYY-CMWG-Meeting[-_-Webex]` |
| DSWG | `MMDDYYYY-DSWG-Meeting[-_-Webex]` or `Joint-DSWG_WMWG-Meeting[-_]` |
| SAWG | `MMDDYYYY-SAWG-Meeting-_-Webex` |
| WMWG | `MMDDYYYY-WMWG-Meeting[-_-Webex]` or `Joint-DSWG_WMWG-Meeting[-_]` |

> **Pattern note:** `[-_-Webex]` means the suffix is present for virtual meetings and absent for in-person. A small number of groups (e.g. SAWG) are consistently all-Webex. Non-meeting events (trainings, workshops) may appear in a group's list with different slug formats — classify these as `Special` type.

**Latest (current year) URLs — Chair/VC as of May 2026:**

> **Filling/refreshing Chair & Vice Chair.** A `—` means the entry hasn't been
> looked up, not that the group has no leaders. Every active group lists its
> Chair/Vice Chair in the **Contact Information** section of its Latest URL —
> `web_fetch` that page to fill the blank. Keep this table in sync with the `C`
> registry in `Database Codes/download_STKHDR_Meets/gen_stkhdr_profiles.py`
> (the downstream source for group profiles), and regenerate manifests/profiles
> after a change. Co-chaired groups: list all chairs as `A / B / C (Co-Chairs)`.
> Inactive task forces publish no leadership — leave `—`.

| Committee | Latest URL | Chair | Vice Chair |
|---|---|---|---|
| Board | `https://www.ercot.com/committees/board` | Bill Flores | Peggy Heeg |
| F&A | `https://www.ercot.com/committees/board/finance_audit` | Christopher Krummel | — |
| HR&G | `https://www.ercot.com/committees/board/hr_governance` | Peggy Heeg | — |
| T&S | `https://www.ercot.com/committees/board/tech-security` | John Swainson | — |
| TAC | `https://www.ercot.com/committees/tac` | Caitlin Smith | Martha Henson |
| LLWG | `https://www.ercot.com/committees/tac/llwg` | Bob Wittmeyer | Patrick Gravois |
| CFSG | `https://www.ercot.com/committees/tac/cfsg` | Jett Price | Loretto Martin |
| RTCBTF | `https://www.ercot.com/committees/inactive/rtcbtf` | *(winding down)* | — |
| PRS | `https://www.ercot.com/committees/prs` | Diana Coleman | Eric Blakey |
| RMS | `https://www.ercot.com/committees/rms` | John Schatz | Debbie McKeever |
| TDTMS | `https://www.ercot.com/committees/rms/tdtms` | Sheri Wiegand | Rob Bevill / Monica Jones |
| RMTTF | `https://www.ercot.com/committees/rms/rmttf` | Melinda Earnest / Tomas Fernandez / Deborah McKeever | — |
| ROS | `https://www.ercot.com/committees/ros` | Sandeep Borkar | Shane Thomas |
| IBRWG | `https://www.ercot.com/committees/ros/ibrwg` | Julia Matevosyan | Miguel Cova Acosta |
| BSWG | `https://www.ercot.com/committees/ros/bswg` | Michael Dieringer | Cerina Rivera-Terrell |
| DWG | `https://www.ercot.com/committees/ros/dwg` | Aditi Upadhyay | Xuan Wu |
| MWG | `https://www.ercot.com/committees/ros/mwg` | Kyle Stuckly | Tony Davis |
| NDSWG | `https://www.ercot.com/committees/ros/ndswg` | Teddi Flessner | Vincent Cutlip |
| OWG | `https://www.ercot.com/committees/ros/owg` | Rickey Floyd | Tyler Springer |
| OTWG | `https://www.ercot.com/committees/ros/otwg` | Manuel Sanchez | Mike Flores |
| PDCWG | `https://www.ercot.com/committees/ros/pdcwg` | Paul Messmann | Luis Hinojosa |
| PLWG | `https://www.ercot.com/committees/ros/plwg` | Mina Turner | Kiran Kota |
| SPWG | `https://www.ercot.com/committees/ros/spwg` | Uchenna Ndusorouwa | Jourdan Watkins |
| SSWG | `https://www.ercot.com/committees/ros/sswg` | Chris Ramirez | Weiwei Hu |
| VPWG | `https://www.ercot.com/committees/ros/vpwg` | Charles Aleman | Alison Flint |
| WMS | `https://www.ercot.com/committees/wms` | Blake Holt | Jim Lee |
| CMWG | `https://www.ercot.com/committees/wms/cmwg` | Chenyan Guo | Shane Thomas |
| DSWG | `https://www.ercot.com/committees/wms/dswg` | Nathaniel Mancha | *(open)* |
| SAWG | `https://www.ercot.com/committees/wms/sawg` | Kevin Hanson | Pete Warnken / Greg Lackey |
| WMWG | `https://www.ercot.com/committees/wms/wmwg` | Amanda Frazier | Trevor Safko |

---

## 2. Step-by-Step Fetch Procedure

### 2.1 Unlock Year URLs

ERCOT blocks direct fetches of year sub-pages unless the URL was first discovered via a search result. Use this two-step unlock for each committee before fetching year pages:

```
STEP A — Search to unlock:
  web_search("ERCOT <COMMITTEE_NAME> meetings <CURRENT_YEAR> site:ercot.com")
  → This surfaces the year URL (e.g. ercot.com/committees/rms/2025) in results.

STEP B — Fetch the year page:
  web_fetch(url="https://www.ercot.com/committees/<path>/YEAR",
            html_extraction_method="markdown",
            text_content_token_limit=12000)
```

> **Why 12000?** ERCOT pages carry ~8000 tokens of nav boilerplate before the meeting list. A limit of 10000 sometimes truncates the list itself. 12000 is reliably sufficient.

### 2.2 Page Anatomy — What to Extract

Each year page contains a section like:

```
#### Scheduled Meetings and Meeting Details
* [Jan 14, 2010](https://www.ercot.com/calendar/01142010-ROS-Meeting)
* [Apr 15, 2010](https://www.ercot.com/calendar/04152010-ROS-Meeting)
   (CANCELLED)
* [Oct 22, 2010](https://www.ercot.com/calendar/10222010-ROS-Email-Vote-Re_)
   (RESCHEDULED TO [Nov 05, 2010](...))
```

Extract for each line:
- **Date** — e.g. `Jan 14, 2010`
- **URL** — the calendar link, e.g. `https://www.ercot.com/calendar/01142010-ROS-Meeting`
- **Meeting Type** — inferred from the URL slug (see §2.3)
- **Note** — `Cancelled`, `Rescheduled to <date>`, or blank

### 2.3 Infer Meeting Type from URL Slug

| URL slug contains | Meeting Type |
|---|---|
| `-Meeting-_-Webex`, `-by-Webex`, `-_-Webex` | `WebEx` |
| `-Email-Vote`, `-Email-vote` | `Email Vote` |
| `-Special-` | `Special` |
| `-Joint-` | `Joint` |
| `-Information-Session`, `-Info-Session`, `-INFORMATION-SESSION` | `Info Session` |
| `-Leadership-` | `Leadership Meeting` |
| `-Task-Force-` | `Task Force` |
| `-Working-Group-` | `Working Group Session` |
| `-User-Interaction`, `-Market-Update` | `Market Update` |
| `Board-of-Directors-Meeting` (no other qualifier) | `Regular` |
| `TAC-Meeting` (no other qualifier) | `Regular` |
| `Special-TAC-Meeting` | `Special` |
| anything else ending in `-Meeting` | `Regular` |

### 2.4 Determine Past vs Upcoming

Compare each meeting date to today's date at generation time:

```python
from datetime import date, datetime

TODAY = date.today()

def get_status(date_str, note):
    if note == "Cancelled":
        return "Cancelled"
    if note.startswith("Rescheduled"):
        return note
    try:
        d = datetime.strptime(date_str, "%b %d, %Y").date()
        return "Past" if d <= TODAY else "Upcoming"
    except:
        return "Past"
```

---

## 3. Excel File Structure

Each in-scope committee (identified in Step 0) gets **one `.xlsx` file** with:
- **Sheet 1 — Summary** (year-level overview)
- **One sheet per year** (individual meetings with clickable links)

### 3.1 Summary Sheet Layout

| Col | Width | Content |
|---|---|---|
| A | 8 | Year |
| B | 24 | Year Page URL (hyperlinked) |
| C | 14 | Total Entries |
| D | 14 | Actual Meetings (non-cancelled, non-rescheduled-original) |
| E | 17 | Cancelled / Other |

- Row 1: Title (merged A–E), navy font `1A3A5C`, size 14 bold
- Row 2: Source URL + generation date (merged A–E), grey italic size 9
- Row 3: Spacer (or predecessor notice for IBRWG)
- Row 4: Column headers — navy fill `1A3A5C`, white bold text
- Rows 5…N: One row per year, alternating white/light-blue fill
- Totals row: Navy fill with SUM formulas
- Legend section below totals: Color swatches with labels

### 3.2 Year Sheet Layout

| Col | Width | Content |
|---|---|---|
| A | 6 | Row # |
| B | 18 | Date |
| C | 20–22 | Meeting Type |
| D | 22 | Status (Past / Upcoming / Cancelled / Rescheduled to DATE) |
| E | 66 | Full meeting URL (hyperlinked) |

- Row 1: Sheet title, navy font
- Row 2: Source URL (hyperlinked)
- Row 3: Spacer
- Row 4: Column headers (navy fill `1A3A5C`); for IBRWG predecessor tab, purple fill `4A235A`
- Data rows: Color-coded per §4
- Final row: `"Total entries: N"`

---

## 4. Color Coding Reference

| Meeting Type | Fill Hex | Font |
|---|---|---|
| Regular | `FFFFFF` white | Black |
| WebEx | `E8EAF6` light indigo | Black |
| Email Vote | `E8F5E9` light green | Black |
| Special Meeting | `F3E5F5` light purple | Black |
| Joint Meeting | `E0F2F1` teal tint | Black |
| Info Session | `FFF9C4` light yellow | Black |
| Task Force / WG Session | `FBE9E7` salmon tint | Black |
| Leadership Meeting | `F3E5F5` light purple | Black |
| Market Update | `FBE9E7` salmon tint | Black |
| **Cancelled** | `FFEBEE` light red | Red `C62828`, italic |
| **Rescheduled (original date)** | `FFF8E1` light amber | Orange `E65100`, italic |
| IBRTF predecessor rows | `F3E5F5` light purple | Purple `6A1B9A` |

**Standard header fill:** `1A3A5C` navy — white bold text  
**IBRTF header fill:** `4A235A` dark purple — white bold text

---

## 5. Python Build Template

```python
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from datetime import date, datetime

# ── Shared style constants ──────────────────────────────────────────────────
HDR_FILL   = PatternFill("solid", start_color="1A3A5C")
HDR_FONT   = Font(name="Arial", bold=True, color="FFFFFF", size=11)
thin       = Side(style="thin", color="CCCCCC")
BORDER     = Border(left=thin, right=thin, top=thin, bottom=thin)
CTR        = Alignment(horizontal="center", vertical="center")
LEFT       = Alignment(horizontal="left", vertical="center")
NORMAL     = Font(name="Arial", size=10)
BOLD       = Font(name="Arial", bold=True, size=10)
LINK_FONT  = Font(name="Arial", size=10, color="1565C0", underline="single")

def fill(h): return PatternFill("solid", start_color=h)

TYPE_FILLS = {
    "Regular":            fill("FFFFFF"),
    "WebEx":              fill("E8EAF6"),
    "Email Vote":         fill("E8F5E9"),
    "Special":            fill("F3E5F5"),
    "Joint":              fill("E0F2F1"),
    "Info Session":       fill("FFF9C4"),
    "Task Force":         fill("FBE9E7"),
    "Leadership Meeting": fill("F3E5F5"),
    "Market Update":      fill("FBE9E7"),
}
CANCELLED_FILL   = fill("FFEBEE")
CANCELLED_FONT   = Font(name="Arial", color="C62828", size=10, italic=True)
RESCHEDULED_FILL = fill("FFF8E1")
RESCHEDULED_FONT = Font(name="Arial", color="E65100", size=10, italic=True)
ALT_FILL         = fill("F0F4F8")

TODAY = date.today()

def get_status(date_str, note):
    if note == "Cancelled":
        return "Cancelled"
    if note.startswith("Rescheduled"):
        return note
    try:
        d = datetime.strptime(date_str, "%b %d, %Y").date()
        return "Past" if d <= TODAY else "Upcoming"
    except:
        return "Past"

# ── DATA structure ──────────────────────────────────────────────────────────
# DATA = {
#   YEAR: [
#     (date_str, url, meeting_type, note),
#     ...
#   ],
#   ...
# }
# note values: "", "Cancelled", "Rescheduled to <date>"

# ── Build workbook ──────────────────────────────────────────────────────────
def build_workbook(committee_name, base_url, DATA, output_path):
    wb = Workbook()
    ws_sum = wb.active
    ws_sum.title = "Summary"
    ws_sum.sheet_view.showGridLines = False

    for col, w in zip("ABCDE", [8, 24, 14, 14, 17]):
        ws_sum.column_dimensions[col].width = w

    years = sorted(DATA.keys())

    ws_sum.merge_cells("A1:E1")
    ws_sum["A1"] = f"ERCOT {committee_name} — Meeting Schedule {min(years)}–{max(years)}"
    ws_sum["A1"].font = Font(name="Arial", bold=True, size=14, color="1A3A5C")
    ws_sum["A1"].alignment = LEFT
    ws_sum.row_dimensions[1].height = 30

    ws_sum.merge_cells("A2:E2")
    ws_sum["A2"] = f"Source: {base_url}  |  As of {TODAY.strftime('%B %d, %Y')}"
    ws_sum["A2"].font = Font(name="Arial", size=9, color="666666", italic=True)
    ws_sum.row_dimensions[2].height = 16
    ws_sum.row_dimensions[3].height = 8

    for col, hdr in enumerate(
            ["Year", "Year Page URL", "Total Entries", "Actual Meetings", "Cancelled/Other"], 1):
        c = ws_sum.cell(row=4, column=col, value=hdr)
        c.font = HDR_FONT; c.fill = HDR_FILL; c.alignment = CTR; c.border = BORDER
    ws_sum.row_dimensions[4].height = 22

    for i, yr in enumerate(years):
        row = 5 + i
        entries = DATA[yr]
        total  = len(entries)
        actual = sum(1 for e in entries
                     if e[3] != "Cancelled" and not e[3].startswith("Rescheduled"))
        other  = total - actual
        yr_url = f"{base_url}/{yr}" if yr < max(years) else base_url
        rf     = ALT_FILL if i % 2 == 1 else fill("FFFFFF")

        c = ws_sum.cell(row=row, column=1, value=yr)
        c.font = BOLD; c.alignment = CTR; c.border = BORDER; c.fill = rf

        c2 = ws_sum.cell(row=row, column=2, value=yr_url)
        c2.font = LINK_FONT; c2.hyperlink = yr_url
        c2.alignment = LEFT; c2.border = BORDER; c2.fill = rf

        for col, val in [(3, total), (4, actual), (5, other)]:
            c = ws_sum.cell(row=row, column=col, value=val)
            c.font = NORMAL; c.alignment = CTR; c.border = BORDER; c.fill = rf
        ws_sum.row_dimensions[row].height = 18

    tot_row = 5 + len(years)
    for col in range(1, 6):
        c = ws_sum.cell(row=tot_row, column=col)
        c.border = BORDER; c.fill = HDR_FILL
        c.font = Font(name="Arial", bold=True, color="FFFFFF", size=10)
        c.alignment = CTR
    for col in [3, 4, 5]:
        ws_sum.cell(row=tot_row, column=col).value = (
            f"=SUM({get_column_letter(col)}5:{get_column_letter(col)}{tot_row - 1})")
    ws_sum.cell(row=tot_row, column=1).value = "TOTAL"
    ws_sum.row_dimensions[tot_row].height = 22

    # ── Year sheets ───────────────────────────────────────────────────────────
    for yr in years:
        ws = wb.create_sheet(title=str(yr))
        ws.sheet_view.showGridLines = False
        ws.column_dimensions["A"].width = 6
        ws.column_dimensions["B"].width = 18
        ws.column_dimensions["C"].width = 22
        ws.column_dimensions["D"].width = 22
        ws.column_dimensions["E"].width = 66

        yr_url = f"{base_url}/{yr}" if yr < max(years) else base_url

        ws.merge_cells("A1:E1")
        ws["A1"] = f"{yr} ERCOT {committee_name} Meetings"
        ws["A1"].font = Font(name="Arial", bold=True, size=13, color="1A3A5C")
        ws["A1"].alignment = LEFT
        ws.row_dimensions[1].height = 28

        ws.merge_cells("A2:E2")
        ws["A2"] = f"Source: {yr_url}"
        ws["A2"].font = Font(name="Arial", size=9, color="1565C0",
                             italic=True, underline="single")
        ws["A2"].hyperlink = yr_url; ws["A2"].alignment = LEFT
        ws.row_dimensions[2].height = 16
        ws.row_dimensions[3].height = 8

        for col, hdr in enumerate(["#", "Date", "Meeting Type", "Status", "Meeting URL"], 1):
            c = ws.cell(row=4, column=col, value=hdr)
            c.font = HDR_FONT; c.fill = HDR_FILL; c.alignment = CTR; c.border = BORDER
        ws.row_dimensions[4].height = 22

        for i, (dt, url, mtype, note) in enumerate(DATA[yr]):
            row = 5 + i
            status = get_status(dt, note)

            if note == "Cancelled":
                bg = CANCELLED_FILL; tf = CANCELLED_FONT
            elif note.startswith("Rescheduled"):
                bg = RESCHEDULED_FILL; tf = RESCHEDULED_FONT
            else:
                bg = TYPE_FILLS.get(mtype, fill("FFFFFF")); tf = NORMAL

            ws.cell(row=row, column=1, value=i + 1).fill = bg
            ws.cell(row=row, column=1).font = Font(name="Arial", size=9, color="888888")
            ws.cell(row=row, column=1).alignment = CTR
            ws.cell(row=row, column=1).border = BORDER

            for col, val, fnt, aln in [
                    (2, dt, tf, LEFT), (3, mtype, tf, CTR), (4, status, tf, CTR)]:
                c = ws.cell(row=row, column=col, value=val)
                c.font = fnt; c.alignment = aln; c.border = BORDER; c.fill = bg

            c5 = ws.cell(row=row, column=5, value=url)
            c5.hyperlink = url
            c5.font = (Font(name="Arial", size=10, color="AAAAAA", italic=True)
                       if note == "Cancelled" else LINK_FONT)
            c5.alignment = LEFT; c5.border = BORDER; c5.fill = bg
            ws.row_dimensions[row].height = 17

        cnt_row = 5 + len(DATA[yr])
        ws.merge_cells(f"A{cnt_row}:D{cnt_row}")
        ws.cell(row=cnt_row, column=1, value=f"Total entries: {len(DATA[yr])}")
        ws.cell(row=cnt_row, column=1).font = Font(name="Arial", bold=True,
                                                    size=10, color="1A3A5C")
        ws.cell(row=cnt_row, column=1).alignment = LEFT
        ws.row_dimensions[cnt_row].height = 18

    wb.save(output_path)
    print(f"Saved: {output_path}")
```

---

## 6. IBRWG Special Handling (Predecessor IBRTF)

IBRWG was established in 2023, replacing the IBRTF Task Force (2022 only). IBRTF is now listed under `/committees/inactive` — which is why Step 0.1 instructs you to check that section separately. The IBRWG file includes an **extra tab for IBRTF 2022** with distinct purple styling to signal it is a predecessor group.

```python
IBRTF_HDR_FILL = PatternFill("solid", start_color="4A235A")  # dark purple
IBRTF_ROW_FILL = PatternFill("solid", start_color="F3E5F5")  # light purple

# Predecessor notice in Row 2 of the IBRTF tab:
ws["A2"] = "⚠  PREDECESSOR GROUP — Now Inactive. Replaced by IBRWG from 2023 onward."
ws["A2"].font = Font(name="Arial", size=9, color="6A1B9A", italic=True)

# IBRTF 2022 URL (found via /committees/inactive in Step 0.1):
"https://www.ercot.com/committees/inactive/ibrtf/2022"
```

Tab order in the IBRWG file: `Summary | IBRTF 2022 | 2023 | 2024 | 2025 | 2026`

---

## 7. Updating an Existing File

When a new year begins or new meetings are added mid-year:

1. **Re-run Step 0** — fetch `https://www.ercot.com/committees` to confirm no groups have been added, renamed, or disbanded since the last run. Update Section 1 of this document if the scope has changed.
2. **Fetch the Latest page** for each in-scope committee (`/committees/<path>`) — always has the current year's full list.
3. **Compare** existing data vs page data — look for new entries, cancellations, reschedulings.
4. **Add a new year tab** if the year has rolled over; update the Summary row for that year.
5. For mid-year updates, only the current-year tab needs rebuilding — past years are stable.

### Key fields to re-check each update run:
- Whether any previously out-of-scope group now has `/YEAR` pages (Criterion A newly satisfied)
- Chair / Vice Chair names (shown on the Latest page; reflect in the Summary title row)
- New entries appended at the end of the current-year list
- Status changes: `(CANCELLED)` or `(RESCHEDULED TO ...)` annotations on existing entries

---

## 8. Meeting Calendar URL Pattern

Each individual meeting calendar page follows this pattern:

```
https://www.ercot.com/calendar/MMDDYYYY-<COMMITTEE>-Meeting[-_-Webex]
```

Examples:
```
https://www.ercot.com/calendar/01092025-ROS-Meeting-_-Webex
https://www.ercot.com/calendar/02172026-RMS-Meeting
https://www.ercot.com/calendar/04272026-IBRWG-Meeting-_-Webex
https://www.ercot.com/calendar/06052025-ROS-Meeting-_-Webex
```

These pages contain: agenda PDFs, key documents, attendance instructions, and Webex connection info. They are the correct link destination for each data row in the Excel files.

---

## 9. Known Data Quirks by Committee

### Board
- Meets quarterly (4 sessions/year, each spanning two consecutive days — e.g. Feb 9 + Feb 10)
- All meetings are Regular type; occasional Special meetings added mid-year
- Public and open to attendance; webcasts archived on ercot.com
- Calendar URL slug: `MMDDYYYY-Board-of-Directors-Meeting`
- 2026 Chair: Bill Flores / VC: Peggy Heeg
- Year pages go back to 2002 — one of the longest historical ranges of any group

### TAC
- Meets approximately monthly; some months have two entries (regular + special)
- Uses `-Special-TAC-Meeting` slug for special sessions — classify as `Special`
- 2026 includes a rescheduled Special meeting (May 6 → May 13)
- All meetings open to stakeholders; webcasts archived
- Calendar URL slug: `MMDDYYYY-TAC-Meeting` or `MMDDYYYY-Special-TAC-Meeting`
- 2026 Chair: Caitlin Smith / VC: Martha Henson
- Year pages go back to 2002

### LLWG
- Established 2025, replacing the Large Flexible Load Task Force (LFLTF, now inactive)
- `/YEAR` pages exist from 2025 only — shortest history of any in-scope group
- Meets approximately monthly; some months have two entries due to reschedulings
- Highly active in 2026 due to the Batch Study Process for Large Load Interconnections
- Calendar URL slug: `MMDDYYYY-LLWG-Meeting` (no Webex suffix even for virtual sessions)
- 2026 Chair: Bob Wittmeyer / VC: Patrick Gravois

### CFSG
- Established 2023; `/YEAR` pages from 2023–present
- Nearly all meetings are WebEx-only: slug ends in `-Meeting-_-Webex`; occasional in-person entries use just `-Meeting`
- Meets approximately monthly (13 entries in 2026 including one rescheduled)
- Apr 2026: original Apr 22 meeting rescheduled to Apr 28
- 2026 Chair: Jett Price / VC: Loretto Martin

### WMS
- Clean monthly schedule
- Occasional special/joint meetings

### CMWG
- Heavy cancellations 2010–2014; Joint CMWG/PLWG meetings in 2011
- Sparse 2015–2016; every 2025 meeting rescheduled ~4 days prior
- All meetings WebEx-only from 2020+

### ROS
- 2010 includes OGRR Task Force meetings (separate calendar entries)
- Email votes appear most years
- WebEx from Oct 2020+; 2021 full-WebEx year
- 2026 Chair: Sandeep Borkar (promoted from VC); VC: Shane Thomas

### IBRWG
- **All meetings WebEx-only** (no in-person, every year)
- 2023 launched mid-year (Aug–Dec only, 5 meetings)
- 2024: two meetings in January (12th and 22nd)
- 2025: 2 cancellations and 2 reschedulings
- 2026: Jan cancelled; Apr 24 rescheduled to Apr 27
- Chair: Julia Matevosyan / VC: Miguel Cova Acosta

### RMS
- Generally meets 1st or 2nd Tuesday of month
- 2014 is the most chaotic year: 15 entries, multiple cancellations
- 2016–2017 had heavy cancellation rates (4–5 per year)
- 2020: Mar–May replaced by Info Sessions + Email Votes (COVID); WebEx from Oct
- 2025: 2 reschedulings (May, Jun); 3 cancellations
- 2026 Chair: John Schatz / VC: Debbie McKeever (roles swapped from 2025)

---

## 10. Complete File Inventory (as of May 2026)

| File | Sheets | Year Range | Total Entries |
|---|---|---|---|
| `ERCOT_Board_Meetings_2002_2026.xlsx` | 26 | 2002–2026 | ~230 |
| `ERCOT_TAC_Meetings_2002_2026.xlsx` | 26 | 2002–2026 | ~290 |
| `ERCOT_LLWG_Meetings_2025_2026.xlsx` | 3 | 2025–2026 | ~25 |
| `ERCOT_CFSG_Meetings_2023_2026.xlsx` | 5 | 2023–2026 | ~55 |
| `ERCOT_PRS_Meetings_2010_2026.xlsx` | 18 | 2010–2026 | ~285 |
| `ERCOT_WMS_Meetings_2010_2026.xlsx` | 18 | 2010–2026 | ~265 |
| `ERCOT_CMWG_Meetings_2010_2026.xlsx` | 18 | 2010–2026 | ~235 |
| `ERCOT_ROS_Meetings_2010_2026.xlsx` | 18 | 2010–2026 | ~305 |
| `ERCOT_IBRWG_Meetings_2022_2026.xlsx` | 6 | 2022–2026 | ~52 |
| `ERCOT_RMS_Meetings_2010_2026.xlsx` | 18 | 2010–2026 | ~280 |

> **Note:** Board and TAC files have not yet been built — they are added to scope as of this revision. Build them using the standard Python template in §5 with the URL patterns from §1.

---

## 11. Quick-Reference: Year Page URL Table

### Board
| Year | URL |
|---|---|
| 2002–2025 | `https://www.ercot.com/committees/board/YEAR` |
| 2026 (latest) | `https://www.ercot.com/committees/board` |

### TAC
| Year | URL |
|---|---|
| 2002–2025 | `https://www.ercot.com/committees/tac/YEAR` |
| 2026 (latest) | `https://www.ercot.com/committees/tac` |

### LLWG
| Year | URL |
|---|---|
| 2025 | `https://www.ercot.com/committees/tac/llwg/2025` |
| 2026 (latest) | `https://www.ercot.com/committees/tac/llwg` |

### CFSG
| Year | URL |
|---|---|
| 2023–2025 | `https://www.ercot.com/committees/tac/cfsg/YEAR` |
| 2026 (latest) | `https://www.ercot.com/committees/tac/cfsg` |

### PRS
| Year | URL |
|---|---|
| 2010–2025 | `https://www.ercot.com/committees/prs/YEAR` |
| 2026 (latest) | `https://www.ercot.com/committees/prs` |

### WMS
| Year | URL |
|---|---|
| 2010–2025 | `https://www.ercot.com/committees/wms/YEAR` |
| 2026 (latest) | `https://www.ercot.com/committees/wms` |

### CMWG
| Year | URL |
|---|---|
| 2010–2025 | `https://www.ercot.com/committees/wms/cmwg/YEAR` |
| 2026 (latest) | `https://www.ercot.com/committees/wms/cmwg` |

### ROS
| Year | URL |
|---|---|
| 2010–2025 | `https://www.ercot.com/committees/ros/YEAR` |
| 2026 (latest) | `https://www.ercot.com/committees/ros` |

### IBRWG
| Year | URL |
|---|---|
| 2022 (IBRTF) | `https://www.ercot.com/committees/inactive/ibrtf/2022` |
| 2023–2025 | `https://www.ercot.com/committees/ros/ibrwg/YEAR` |
| 2026 (latest) | `https://www.ercot.com/committees/ros/ibrwg` |

### RMS
| Year | URL |
|---|---|
| 2010–2025 | `https://www.ercot.com/committees/rms/YEAR` |
| 2026 (latest) | `https://www.ercot.com/committees/rms` |

---

## 12. Search Queries to Unlock Year Pages

If a year page fetch returns a PERMISSIONS_ERROR, run the matching search first:

```
Board: "ERCOT Board of Directors meetings YEAR ercot.com/committees/board"
TAC:   "ERCOT Technical Advisory Committee TAC meetings YEAR ercot.com/committees/tac"
LLWG:  "ERCOT Large Load Working Group LLWG meetings YEAR ercot.com/committees/tac/llwg"
CFSG:  "ERCOT Credit Finance Sub Group CFSG meetings YEAR ercot.com/committees/tac/cfsg"
PRS:   "ERCOT Protocol Revision Subcommittee PRS meetings YEAR ercot.com"
WMS:   "ERCOT Wholesale Market Subcommittee WMS meetings YEAR ercot.com"
CMWG:  "ERCOT Congestion Management Working Group CMWG meetings YEAR ercot.com"
ROS:   "ERCOT Reliability Operations Subcommittee ROS meetings YEAR site:ercot.com"
IBRWG: "ERCOT Inverter-Based Resource Working Group IBRWG meetings YEAR ercot.com"
RMS:   "ERCOT Retail Market Subcommittee RMS meetings YEAR ercot.com"
```

After the search, any `web_fetch` call for a URL that appeared in the results will succeed.

---

## 13. Full Hierarchy with Scope Decisions (from Step 0)

```
Board of Directors                          ✅ IN SCOPE  (MMDDYYYY-Board-of-Directors-Meeting; /YEAR 2002+)
  ├── Finance and Audit Committee           ✅ IN SCOPE  (MMDDYYYY-Finance-_-Audit-Committee; /YEAR 2004+)
  ├── HR and Governance Committee           ✅ IN SCOPE  (MMDDYYYY-HR-_-Governance-Committee; /YEAR 2002+)
  └── Technology and Security Committee     ✅ IN SCOPE  (MMDDYYYY-Technology-_-Security-Committee; /YEAR 2023+)

Technical Advisory Committee (TAC)          ✅ IN SCOPE  (MMDDYYYY-TAC-Meeting; /YEAR 2002+)
  ├── Large Load Working Group (LLWG)       ✅ IN SCOPE  (MMDDYYYY-LLWG-Meeting; /YEAR 2025+)
  ├── Credit Finance Sub Group (CFSG)       ✅ IN SCOPE  (MMDDYYYY-CFSG-Meeting[-_-Webex]; /YEAR 2023+)
  └── RT Co-optimization + Batteries TF     ✅ IN SCOPE  (MMDDYYYY-RTCBTF-Meeting[-_-Webex]; inactive /YEAR 2023–2026)

Protocol Revision Subcommittee (PRS)        ✅ IN SCOPE  (MMDDYYYY-PRS-Meeting; /YEAR 2010+)

Retail Market Subcommittee (RMS)            ✅ IN SCOPE  (MMDDYYYY-RMS-Meeting[-_-Webex]; /YEAR 2010+)
  ├── TDTMS Working Group                   ✅ IN SCOPE  (MMDDYYYY-TDTMS-Meeting[-_-Webex]; /YEAR 2015+)
  ├── TXSETLP Working Group                 ⚠️  OUT — calendar links exist but no /YEAR archive pages
  └── RMTTF Task Force                      ✅ IN SCOPE  (MMDDYYYY-RMTTF-Meeting[-_-Webex]; /YEAR 2015+)

Reliability and Operations Sub. (ROS)       ✅ IN SCOPE  (MMDDYYYY-ROS-Meeting[-_-Webex]; /YEAR 2010+)
  ├── Black Start WG (BSWG)                 ✅ IN SCOPE  (MMDDYYYY-BSWG-Meeting[-_-Webex]; /YEAR 2002+)
  ├── Dynamics WG (DWG)                     ✅ IN SCOPE  (MMDDYYYY-DWG-Meeting-_-Webex; /YEAR 2003+)
  ├── Inverter-Based Resource WG (IBRWG)    ✅ IN SCOPE  (MMDDYYYY-IBRWG-Meeting-_-Webex; /YEAR 2023+)
  ├── Meter WG (MWG)                        ✅ IN SCOPE  (MMDDYYYY-MWG-Meeting[-_-Webex]; /YEAR 2002+)
  ├── Network Data Support WG (NDSWG)       ✅ IN SCOPE  (MMDDYYYY-NDSWG-Meeting[-_-Webex]; /YEAR 2002+)
  ├── Operations WG (OWG)                   ✅ IN SCOPE  (MMDDYYYY-OWG-Meeting[-_-Webex]; verify /YEAR range)
  ├── Operations Training WG (OTWG)         ✅ IN SCOPE  (MMDDYYYY-OTWG-Meeting[-_-Webex]; verify /YEAR range)
  ├── PDC WG (PDCWG)                        ✅ IN SCOPE  (MMDDYYYY-PDCWG-Meeting[-_-Webex]; verify /YEAR range)
  ├── Planning WG (PLWG)                    ✅ IN SCOPE  (MMDDYYYY-PLWG-Meeting[-_-Webex]; /YEAR 2010+)
  ├── System Protection WG (SPWG)           ✅ IN SCOPE  (MMDDYYYY-SPWG-Meeting[-_-Webex]; verify /YEAR range)
  ├── Steady State WG (SSWG)                ✅ IN SCOPE  (MMDDYYYY-SSWG-Meeting[-_-Webex]; verify /YEAR range)
  └── Voltage Profile WG (VPWG)             ✅ IN SCOPE  (MMDDYYYY-VPWG-Meeting[-_-Webex]; verify /YEAR range)

Wholesale Market Subcommittee (WMS)         ✅ IN SCOPE  (MMDDYYYY-WMS-Meeting[-_-Webex]; /YEAR 2010+)
  ├── Congestion Management WG (CMWG)       ✅ IN SCOPE  (MMDDYYYY-CMWG-Meeting[-_-Webex]; /YEAR 2010+)
  ├── Demand Side WG (DSWG)                 ✅ IN SCOPE  (MMDDYYYY-DSWG-Meeting[-_-Webex]; /YEAR 2002+)
  ├── Supply Analysis WG (SAWG)             ✅ IN SCOPE  (MMDDYYYY-SAWG-Meeting-_-Webex; /YEAR 2015+)
  └── Wholesale Market WG (WMWG)            ✅ IN SCOPE  (MMDDYYYY-WMWG-Meeting[-_-Webex]; /YEAR 2019+)

Inactive Groups
  ├── IBR Task Force (IBRTF) — 2022 only   ✅ IN SCOPE (tab inside IBRWG file)
  ├── RTCBTF (2023–2026)                    ✅ IN SCOPE (standalone or tab in TAC file)
  └── Resource Cost WG (RCWG)              [OUT — no /YEAR pages confirmed]
```

---

*Last compiled: May 4, 2026. Step 0 scope evaluation performed against `https://www.ercot.com/committees` as retrieved on May 4, 2026. All Excel files built from live ercot.com data.*

---

## 14. Document Download — Overview

Each meeting calendar page (§8) lists downloadable documents: agendas, minutes, presentations, handouts, and supporting materials. This section defines how to fetch those pages, extract document links, and save the files to a structured folder hierarchy.

**Root download directory:**
```
E:\wamp64\www\Power.Talks\Documents Database\ERCOT.STKHDR.MEETS\
```

**Folder hierarchy:**
```
ERCOT.STKHDR.MEETS\
  └── <COMMITTEE_ABBREV>\          ← e.g. ROS, TAC, RMS, IBRWG …
       └── YYYY-MM-DD\             ← ISO date of the meeting (sortable)
            ├── Agenda.pdf
            ├── Minutes.pdf
            └── <other documents>
```

**Rules:**
- One subfolder per committee abbreviation (use the exact abbreviations from §1: `Board`, `FA`, `HRG`, `TS`, `TAC`, `LLWG`, `CFSG`, `RTCBTF`, `PRS`, `RMS`, `TDTMS`, `RMTTF`, `ROS`, `IBRWG`, `BSWG`, `DWG`, `MWG`, `NDSWG`, `OWG`, `OTWG`, `PDCWG`, `PLWG`, `SPWG`, `SSWG`, `VPWG`, `WMS`, `CMWG`, `DSWG`, `SAWG`, `WMWG`, `IBRTF`).
- One subfolder per meeting date in `YYYY-MM-DD` format. If a meeting spans two consecutive days (e.g. Board), use the **first** day as the folder name.
- All documents for the same meeting date go into the same `YYYY-MM-DD` folder regardless of document type.
- Create folders with `os.makedirs(..., exist_ok=True)` — never fail if the folder already exists.
- If a filename already exists in the target folder, **skip it** (do not overwrite) and log a `[SKIP]` message.

---

## 15. Meeting Calendar Page Structure

A meeting calendar page (e.g. `https://www.ercot.com/calendar/01092025-ROS-Meeting-_-Webex`) typically contains:

```
## <Meeting Title>
**Date:** January 09, 2025
**Location:** Webex

### Agenda
  [Agenda.pdf](https://www.ercot.com/files/docs/2025/01/09/Agenda.pdf)

### Meeting Materials
  [Presentation1.pdf](https://www.ercot.com/files/docs/2025/01/09/Presentation1.pdf)
  [Handout.pdf](https://www.ercot.com/files/docs/2025/01/09/Handout.pdf)

### Minutes
  [Minutes.pdf](https://www.ercot.com/files/docs/2025/01/09/Minutes.pdf)
```

Document links typically resolve to `https://www.ercot.com/files/docs/YYYY/MM/DD/<filename>` or similar paths under `ercot.com`. Extract **all** `<a href>` targets that end in a downloadable extension: `.pdf`, `.docx`, `.doc`, `.xlsx`, `.xls`, `.pptx`, `.ppt`, `.zip`.

Exclude:
- Navigation links (same-domain links to `/committees/`, `/calendar/`, `/about/`, etc.)
- External links (non-`ercot.com` domains)
- Webex / meeting-join URLs

---

## 16. Document Download Fetch Procedure

### 16.1 Unlock the Calendar Page

ERCOT calendar pages may require the same two-step unlock as year pages (§2.1):

```
STEP A — Search to unlock:
  web_search("ERCOT <COMMITTEE> meeting <MMDDYYYY> site:ercot.com")
  → Surfaces the calendar URL in results.

STEP B — Fetch the calendar page:
  web_fetch(url="https://www.ercot.com/calendar/MMDDYYYY-<SLUG>",
            html_extraction_method="markdown",
            text_content_token_limit=12000)
```

### 16.2 Extract Document Links

Parse the fetched markdown for links whose `href` ends with a downloadable extension:

```python
import re

DOWNLOADABLE_EXTS = (".pdf", ".docx", ".doc", ".xlsx", ".xls",
                     ".pptx", ".ppt", ".zip")

def extract_doc_links(markdown_text):
    """Return list of absolute URLs for downloadable documents."""
    pattern = r'\[([^\]]+)\]\((https?://[^)]+)\)'
    links = []
    for _label, url in re.findall(pattern, markdown_text):
        if url.lower().endswith(DOWNLOADABLE_EXTS):
            links.append(url)
    return links
```

### 16.3 Determine Target Folder

```python
from datetime import datetime
import os

BASE_DIR = r"E:\wamp64\www\Power.Talks\Documents Database\ERCOT.STKHDR.MEETS"

def get_target_folder(committee_abbrev, meeting_date_str):
    """
    meeting_date_str: 'Jan 09, 2025' or 'January 09, 2025' (any strptime-parseable form)
    Returns the absolute path to the YYYY-MM-DD subfolder.
    """
    for fmt in ("%b %d, %Y", "%B %d, %Y", "%m/%d/%Y", "%Y-%m-%d"):
        try:
            d = datetime.strptime(meeting_date_str.strip(), fmt).date()
            break
        except ValueError:
            continue
    else:
        raise ValueError(f"Cannot parse date: {meeting_date_str!r}")

    folder = os.path.join(BASE_DIR, committee_abbrev, d.strftime("%Y-%m-%d"))
    os.makedirs(folder, exist_ok=True)
    return folder
```

---

## 17. Python Download Script Template

```python
import os
import re
import requests
from datetime import datetime
from urllib.parse import urlparse

BASE_DIR = r"E:\wamp64\www\Power.Talks\Documents Database\ERCOT.STKHDR.MEETS"
DOWNLOADABLE_EXTS = (".pdf", ".docx", ".doc", ".xlsx", ".xls",
                     ".pptx", ".ppt", ".zip")
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

# ── Helpers ──────────────────────────────────────────────────────────────────

def extract_doc_links(markdown_text):
    pattern = r'\[([^\]]+)\]\((https?://[^)]+)\)'
    return [
        url for _label, url in re.findall(pattern, markdown_text)
        if url.lower().endswith(DOWNLOADABLE_EXTS)
    ]

def parse_meeting_date(date_str):
    for fmt in ("%b %d, %Y", "%B %d, %Y", "%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Cannot parse date: {date_str!r}")

def get_target_folder(committee_abbrev, meeting_date):
    folder = os.path.join(BASE_DIR, committee_abbrev,
                          meeting_date.strftime("%Y-%m-%d"))
    os.makedirs(folder, exist_ok=True)
    return folder

def download_file(url, target_folder):
    filename = os.path.basename(urlparse(url).path)
    if not filename:
        filename = url.split("/")[-1]
    dest = os.path.join(target_folder, filename)
    if os.path.exists(dest):
        print(f"  [SKIP] {filename} — already exists")
        return
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        with open(dest, "wb") as f:
            f.write(resp.content)
        print(f"  [OK]   {filename}  ({len(resp.content) // 1024} KB)")
    except Exception as e:
        print(f"  [ERR]  {filename} — {e}")

# ── Main: download all documents for a single meeting ────────────────────────

def download_meeting_docs(committee_abbrev, meeting_date_str,
                          calendar_markdown):
    """
    committee_abbrev  : e.g. 'ROS', 'TAC', 'IBRWG'
    meeting_date_str  : e.g. 'Jan 09, 2025'
    calendar_markdown : full markdown text from web_fetch of the calendar page
    """
    meeting_date  = parse_meeting_date(meeting_date_str)
    target_folder = get_target_folder(committee_abbrev, meeting_date)
    doc_links     = extract_doc_links(calendar_markdown)

    print(f"\n[{committee_abbrev}] {meeting_date}  →  {target_folder}")
    print(f"  Found {len(doc_links)} downloadable link(s)")
    for url in doc_links:
        download_file(url, target_folder)

# ── Batch: iterate over a committee's full meeting list ──────────────────────

def download_committee_docs(committee_abbrev, meetings):
    """
    meetings: list of (date_str, calendar_url, meeting_type, note)
              — same structure as DATA[yr] in §5.
    Only downloads meetings whose note != 'Cancelled'.
    """
    import time

    for date_str, cal_url, _mtype, note in meetings:
        if note == "Cancelled":
            print(f"  [SKIP] {date_str} — cancelled")
            continue
        try:
            # Two-step unlock: search first, then fetch
            # (Caller should run web_search before calling this function
            #  if operating in an environment that enforces the unlock.)
            resp = requests.get(cal_url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            # Convert HTML → plain text; for full markdown fidelity use
            # the web_fetch tool instead of requests when running inside Claude.
            markdown = resp.text
        except Exception as e:
            print(f"  [ERR]  Fetch {cal_url} — {e}")
            continue

        download_meeting_docs(committee_abbrev, date_str, markdown)
        time.sleep(1)   # polite crawl delay


# ── Usage example ─────────────────────────────────────────────────────────────
#
#   from ercot_downloader import download_meeting_docs
#
#   # After fetching the calendar page with web_fetch:
#   download_meeting_docs(
#       committee_abbrev  = "ROS",
#       meeting_date_str  = "Jan 09, 2025",
#       calendar_markdown = <markdown returned by web_fetch>
#   )
#
#   # Result folder: E:\...\ERCOT.STKHDR.MEETS\ROS\2025-01-09\
```

---

## 18. Download Integration with the Fetch Workflow

When running inside Claude Code (using `web_fetch` and `web_search` tools rather than `requests`), use this procedure for each meeting:

```
For each (date_str, calendar_url, meeting_type, note) in the committee's meeting list:

  1. Skip if note == "Cancelled".

  2. Unlock the calendar page:
     web_search("<COMMITTEE> <date_str> site:ercot.com")

  3. Fetch the calendar page:
     web_fetch(url=calendar_url,
               html_extraction_method="markdown",
               text_content_token_limit=12000)

  4. Extract document links from the returned markdown (§16.2).

  5. For each document URL found:
     a. Derive the target folder:
        BASE_DIR\<COMMITTEE_ABBREV>\YYYY-MM-DD\
     b. Download the file to that folder (skip if already present).

  6. Log results: committee, date, folder path, files downloaded / skipped / errored.
```

**Folder creation is automatic** — `os.makedirs(..., exist_ok=True)` handles both new and existing paths without error.

**Polite crawl:** Insert at least a 1-second delay between consecutive calendar-page fetches for the same committee to avoid rate-limiting.

---

## 19. Expected Folder Output Example

After running a full download pass for ROS (2025) and IBRWG (2025):

```
ERCOT.STKHDR.MEETS\
  ├── IBRWG\
  │    ├── 2025-02-28\
  │    │    ├── IBRWG_Agenda_02282025.pdf
  │    │    └── IBRWG_Presentation_02282025.pdf
  │    ├── 2025-04-25\
  │    │    └── IBRWG_Agenda_04252025.pdf
  │    └── 2025-06-27\
  │         ├── IBRWG_Agenda_06272025.pdf
  │         └── IBRWG_Minutes_06272025.pdf
  └── ROS\
       ├── 2025-01-09\
       │    ├── ROS_Agenda_01092025.pdf
       │    ├── ROS_Presentation_01092025.pdf
       │    └── ROS_Minutes_01092025.pdf
       ├── 2025-03-13\
       │    └── ROS_Agenda_03132025.pdf
       └── 2025-05-08\
            ├── ROS_Agenda_05082025.pdf
            └── ROS_Minutes_05082025.pdf
```

Each meeting's documents are co-located under their `YYYY-MM-DD` date folder. The same folder is reused if downloads are run incrementally — already-present files are skipped, new files are added alongside them.
