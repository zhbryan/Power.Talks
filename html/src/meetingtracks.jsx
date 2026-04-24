// ERCOT stakeholder meeting process — navigable org chart with meeting records
const ERCOT_ORG = {
  id: "BOD",
  name: "ERCOT Board of Directors",
  tag: "Board",
  children: [
    {
      id: "TAC",
      name: "Technical Advisory Committee",
      tag: "TAC",
      children: [
        {
          id: "ROS",
          name: "Reliability & Operations Subcommittee",
          tag: "ROS",
          children: [
            { id: "OWG",   name: "Operations Working Group",                 tag: "OWG"   },
            { id: "PDCWG", name: "Performance, Disturbance & Compliance WG", tag: "PDCWG" },
            { id: "DWG",   name: "Dynamics Working Group",                   tag: "DWG"   },
            { id: "NDSWG", name: "Network Data Support WG",                  tag: "NDSWG" },
            { id: "SAWG",  name: "System Protection WG",                     tag: "SAWG"  },
          ],
        },
        {
          id: "WMS",
          name: "Wholesale Market Subcommittee",
          tag: "WMS",
          children: [
            { id: "CMWG",  name: "Congestion Management WG",                 tag: "CMWG"  },
            { id: "QMWG",  name: "Qualification Methodology WG",             tag: "QMWG"  },
            { id: "MCWG",  name: "Market Credit WG",                         tag: "MCWG"  },
            { id: "DSWG",  name: "Demand Side WG",                           tag: "DSWG"  },
            { id: "SAWG2", name: "Supply Analysis WG",                       tag: "SAWG"  },
          ],
        },
        {
          id: "RMS",
          name: "Retail Market Subcommittee",
          tag: "RMS",
          children: [
            { id: "COPS",  name: "Commercial Operations Subcommittee",       tag: "COPS"  },
            { id: "RMPTF", name: "Retail Market Processes TF",               tag: "RMPTF" },
            { id: "TDTWG", name: "Texas Data Transport WG",                  tag: "TDTWG" },
            { id: "RCWG",  name: "Retail Customer WG",                       tag: "RCWG"  },
          ],
        },
        {
          id: "PLWG",
          name: "Protocol Revision Subcommittee",
          tag: "PRS",
          children: [
            { id: "LFSTF", name: "Load Forecasting Stakeholder TF",         tag: "LFSTF" },
            { id: "SMTF",  name: "Settlement Metering TF",                   tag: "SMTF"  },
            { id: "PIPTF", name: "Planning Interim Process TF",              tag: "PIPTF" },
          ],
        },
      ],
    },
  ],
};

const NODE_INFO = {
  BOD: {
    intro: "The ERCOT Board of Directors provides independent governance and strategic oversight of ERCOT as the ISO for the Texas interconnection, serving roughly 90% of the state's electric load.",
    purpose: "Set strategic direction, ensure financial and operational accountability, and safeguard reliability across the ERCOT market.",
    points: [
      "Composed of independent directors plus representatives from each market segment (generators, REPs, municipals, cooperatives, consumers, and industrials).",
      "Approves annual budgets, major capital projects, and ERCOT's strategic plan.",
      "Reviews and acts on TAC recommendations regarding protocol revisions.",
      "Oversees ERCOT management performance and reliability metrics reported quarterly.",
      "Open-session meetings are publicly accessible; closed sessions address confidential regulatory and legal matters.",
    ],
  },
  TAC: {
    intro: "The Technical Advisory Committee is the primary stakeholder advisory body to the ERCOT Board, coordinating technical and market policy work across all four standing subcommittees.",
    purpose: "Review, prioritize, and recommend protocol revisions and market rule changes before they advance to the Board for final approval.",
    points: [
      "Meets monthly; all market participants and interested parties may attend and comment.",
      "Receives reports and voting recommendations from ROS, WMS, RMS, and PRS subcommittees.",
      "Votes on NPRRs, NOGRRs, and other revision requests; results forwarded to the Board.",
      "Establishes and sunsets task forces and working groups as business needs evolve.",
      "Publishes detailed voting records and meeting materials on the ERCOT website within 10 business days.",
    ],
  },
  ROS: {
    intro: "The Reliability and Operations Subcommittee focuses on the technical reliability of the bulk electric system, operational procedures, and compliance with NERC and ERCOT reliability standards.",
    purpose: "Develop, review, and recommend changes to operating guides, planning criteria, and reliability standards affecting the ERCOT transmission system.",
    points: [
      "Reviews NOGRRs (Nodal Operating Guide Revision Requests) and related operating guide changes.",
      "Coordinates with ERCOT operations staff on outage coordination, system protection, and disturbance analysis.",
      "Oversees working groups covering dynamics, network data, outage coordination, and system protection.",
      "Monitors NERC Reliability Standard compliance and coordinates ERCOT's regional filings.",
      "Manages inverter-based resource integration and large-load interconnection technical reviews.",
    ],
  },
  WMS: {
    intro: "The Wholesale Market Subcommittee oversees the design, performance, and rule changes for ERCOT's wholesale energy, ancillary services, and congestion revenue markets.",
    purpose: "Evaluate and recommend wholesale market rule changes that promote competitive, efficient, and reliable energy pricing across the ERCOT footprint.",
    points: [
      "Reviews market design proposals including real-time co-optimization, ancillary services, and capacity mechanisms.",
      "Oversees working groups for congestion management, market credit, demand-side resources, and supply analysis.",
      "Analyzes Potomac Economics' Independent Market Monitor reports and recommends market efficiency improvements.",
      "Considers qualification methodology updates for resources participating in ERCOT markets.",
      "Coordinates with ERCOT on seasonal market assessments and summer/winter readiness reviews.",
    ],
  },
  RMS: {
    intro: "The Retail Market Subcommittee governs the competitive retail electricity market, overseeing the rules and processes that enable customer switching, metering, and data exchange between REPs and utilities.",
    purpose: "Maintain and improve the operational framework of Texas's competitive retail market, including transaction standards, settlement processes, and consumer protections.",
    points: [
      "Reviews and recommends changes to retail market rules, Texas SET transaction standards, and ERCOT retail systems.",
      "Oversees COPS, RMPTF, TDTWG, and RCWG for commercial operations and retail process improvements.",
      "Monitors REP compliance, MarkeTrak dispute resolution trends, and switch processing performance.",
      "Coordinates major retail transitions such as Lubbock market integration and new service territory additions.",
      "Manages mass transition protocols and procedures for REP exits and customer protection events.",
    ],
  },
  PLWG: {
    intro: "The Protocol Revision Subcommittee (PRS) manages the formal process for amending the ERCOT Nodal Protocols, acting as the procedural gatekeeper for all protocol revision requests submitted to ERCOT.",
    purpose: "Ensure that NPRRs and related revision requests are thoroughly reviewed, properly noticed, and voted on with full stakeholder participation before advancing to TAC.",
    points: [
      "Meets bi-weekly to triage, schedule, and vote on NPRRs, SCRs, and other protocol revision requests.",
      "Maintains the official NPRR docket, assigns revision numbers, and tracks disposition status.",
      "Publishes redlined protocol language and cost-benefit analyses for stakeholder review periods.",
      "Coordinates load forecasting, settlement metering, and planning process task forces.",
      "Manages effective dates and implementation timelines in coordination with ERCOT IT and operations.",
    ],
  },
  COPS: {
    intro: "The Commercial Operations Subcommittee handles the day-to-day commercial and settlement processes of the retail market, operating under the Retail Market Subcommittee.",
    purpose: "Oversee commercial operations between REPs, LSEs, and ERCOT, including settlements, data exchange, and dispute resolution processes.",
    points: [
      "Manages settlement timelines, invoice processes, and extracts for retail market participants.",
      "Coordinates data aggregation, unaccounted-for energy tracking, and profiling methodologies.",
      "Reviews and updates commercial protocols for REP-to-REP and REP-to-ERCOT transactions.",
      "Addresses disputes related to settlements, meter data, and transaction processing.",
      "Works with ERCOT IT on system enhancements to the Market Information System (MIS).",
    ],
  },
  OWG: {
    intro: "The Operations Working Group supports ROS by addressing day-to-day operational issues, outage coordination improvements, and real-time reliability procedures.",
    purpose: "Develop and refine operating procedures, outage coordination protocols, and emergency response guidelines for ERCOT system operators.",
    points: [
      "Reviews proposed changes to ERCOT operating guides and emergency operations plans.",
      "Coordinates seasonal readiness reviews, including summer and winter weather preparedness.",
      "Analyzes real-time operational events and recommends procedural improvements.",
      "Interfaces with transmission operators and generation owners on outage scheduling best practices.",
    ],
  },
  PDCWG: {
    intro: "The Performance, Disturbance and Compliance Working Group focuses on post-event analysis of system disturbances and NERC reliability standard compliance.",
    purpose: "Analyze grid disturbance events, track NERC compliance obligations, and recommend corrective actions to improve system reliability.",
    points: [
      "Reviews disturbance reports for events such as frequency excursions, voltage deviations, and generation trips.",
      "Monitors ERCOT's NERC reliability standard compliance program and audit findings.",
      "Develops corrective action plans for standards violations and near-misses.",
      "Coordinates with ERCOT operations on root-cause analysis of significant reliability events.",
    ],
  },
  DWG: {
    intro: "The Dynamics Working Group addresses dynamic modeling of ERCOT's power system, ensuring accurate simulation tools for planning and stability analysis.",
    purpose: "Maintain accurate dynamic models of generation resources and the transmission system to support reliable system planning and contingency studies.",
    points: [
      "Reviews and validates dynamic model data submitted by generators and transmission owners.",
      "Develops guidelines for inverter-based resource modeling as solar and wind penetration increases.",
      "Coordinates with planning engineers on stability studies and model validation benchmarks.",
      "Addresses emerging modeling challenges from battery storage and hybrid resource configurations.",
    ],
  },
  NDSWG: {
    intro: "The Network Data Support Working Group manages the accuracy and integrity of ERCOT's network model, which underpins all power flow, contingency, and planning studies.",
    purpose: "Ensure the ERCOT network model reflects the current state of the transmission system and that data submission processes are efficient and accurate.",
    points: [
      "Reviews data change requests for transmission topology, ratings, and substation configurations.",
      "Maintains processes for timely model updates following system additions and retirements.",
      "Coordinates with transmission owners on data quality and submission deadlines.",
      "Supports the annual model validation process for NERC and regional reliability assessments.",
    ],
  },
  SAWG: {
    intro: "The System Protection Working Group (SAWG) addresses protection system coordination, special protection schemes, and SPS/RAS design across the ERCOT system.",
    purpose: "Develop and review protection system requirements, special protection schemes, and remedial action schemes to maintain system reliability.",
    points: [
      "Reviews proposed SPS and RAS schemes submitted by transmission owners.",
      "Develops protection system design guidelines and performance requirements.",
      "Analyzes protection-related events and recommends improvements to settings and coordination.",
      "Coordinates with dynamics and planning groups on system protection impacts from new resource interconnections.",
    ],
  },
  CMWG: {
    intro: "The Congestion Management Working Group addresses transmission congestion pricing, congestion revenue rights, and related market mechanisms within ERCOT's nodal market.",
    purpose: "Evaluate and recommend improvements to congestion management tools, CRR auction design, and transmission constraint management processes.",
    points: [
      "Reviews CRR auction results, revenue adequacy, and constraint management performance.",
      "Analyzes transmission bottlenecks and recommends market or operational solutions.",
      "Coordinates with planning staff on congestion driven by new load and generation interconnections.",
      "Develops recommendations for improving nodal pricing accuracy and settlement point definitions.",
    ],
  },
  QMWG: {
    intro: "The Qualification Methodology Working Group develops the standards and processes for qualifying resources to participate in ERCOT's wholesale markets.",
    purpose: "Establish and maintain fair, transparent qualification standards for generators, loads, and aggregations seeking to offer ancillary services and energy in ERCOT markets.",
    points: [
      "Reviews qualification testing procedures for ancillary service capability verification.",
      "Addresses emerging qualification challenges for inverter-based resources and battery storage.",
      "Develops methodologies for aggregated demand response and distributed resource qualification.",
      "Coordinates with ERCOT operations on performance monitoring for qualified resources.",
    ],
  },
  MCWG: {
    intro: "The Market Credit Working Group oversees credit policy for ERCOT market participants, addressing collateral requirements, default risk, and credit exposure management.",
    purpose: "Maintain a robust credit framework that protects the market from participant default risk while minimizing unnecessary collateral burdens on creditworthy entities.",
    points: [
      "Reviews credit exposure calculation methodologies and collateral requirement formulas.",
      "Analyzes default events and recommends improvements to credit risk management practices.",
      "Develops policies for new participant types such as aggregators and virtual traders.",
      "Monitors market credit metrics and escalates concerns to WMS and TAC as appropriate.",
    ],
  },
  DSWG: {
    intro: "The Demand Side Working Group focuses on demand response, energy efficiency, and load participation mechanisms in the ERCOT wholesale market.",
    purpose: "Expand and improve demand-side resource participation in ERCOT markets to enhance reliability and provide competitive alternatives to generation resources.",
    points: [
      "Reviews proposed changes to demand response program rules and measurement & verification requirements.",
      "Develops recommendations for integrating large industrial loads as ancillary service providers.",
      "Analyzes barriers to retail customer participation in demand response programs.",
      "Coordinates with ERCOT on demand forecasting improvements and load flexibility modeling.",
    ],
  },
  SAWG2: {
    intro: "The Supply Analysis Working Group performs analysis of generation resource adequacy, capacity trends, and supply-side market dynamics within the ERCOT footprint.",
    purpose: "Provide stakeholders with rigorous analysis of generation adequacy, retirement risk, and capacity mix trends to inform market design and planning decisions.",
    points: [
      "Produces periodic generation adequacy assessments and reserve margin forecasts.",
      "Analyzes announced retirements and their reliability impact under different demand scenarios.",
      "Reviews interconnection queue trends and new resource entry timelines.",
      "Informs WMS deliberations on capacity market design and scarcity pricing mechanisms.",
    ],
  },
  RMPTF: {
    intro: "The Retail Market Processes Task Force develops and maintains the operational processes and system requirements for ERCOT's competitive retail market transactions.",
    purpose: "Ensure that retail transaction processes — switching, enrollment, drops, and settlements — function accurately and efficiently for all market participants.",
    points: [
      "Reviews Texas SET transaction standards and recommends version updates.",
      "Develops business requirements for ERCOT retail system enhancements.",
      "Coordinates MarkeTrak dispute resolution process improvements.",
      "Addresses retail process issues arising from new technology, metering deployments, or regulatory mandates.",
    ],
  },
  TDTWG: {
    intro: "The Texas Data Transport Working Group oversees the data communication standards and infrastructure used by ERCOT and market participants for retail market transactions.",
    purpose: "Maintain and evolve the technical standards for electronic data interchange between REPs, utilities, and ERCOT's retail settlement systems.",
    points: [
      "Manages Texas SET version releases and associated testing requirements.",
      "Addresses EDI transaction errors, data quality issues, and system interoperability challenges.",
      "Coordinates with ERCOT IT on retail system upgrades and new transaction types.",
      "Develops implementation timelines and transition plans for new data transport standards.",
    ],
  },
  RCWG: {
    intro: "The Retail Customer Working Group addresses policies and processes that directly affect retail electricity customers in the competitive Texas market.",
    purpose: "Represent and protect retail customer interests in ERCOT market rule development, focusing on consumer protections, billing accuracy, and service quality.",
    points: [
      "Reviews proposed rule changes for customer impact assessment.",
      "Develops recommendations on customer disclosure requirements, contract terms, and complaint processes.",
      "Addresses metering accuracy issues and meter data access rights for customers.",
      "Coordinates with the Public Utility Commission of Texas on retail market consumer protection initiatives.",
    ],
  },
  LFSTF: {
    intro: "The Load Forecasting Stakeholder Task Force engages market participants in improving ERCOT's short- and long-term load forecasting methodologies.",
    purpose: "Enhance forecast accuracy by incorporating stakeholder input on demand trends, weather sensitivity, and the impact of distributed energy resources on system load.",
    points: [
      "Reviews ERCOT's load forecasting models and evaluates proposed methodology improvements.",
      "Analyzes forecast error patterns and recommends adjustments for weather normalization.",
      "Addresses the impact of behind-the-meter solar, demand response, and EVs on net load forecasting.",
      "Coordinates with ERCOT planning on long-range load growth scenarios for resource adequacy studies.",
    ],
  },
  SMTF: {
    intro: "The Settlement Metering Task Force addresses metering standards, data validation, and settlement meter registration processes for ERCOT market participants.",
    purpose: "Ensure accurate, timely, and auditable settlement metering data flows from meters through ERCOT's settlement systems to support fair and correct market settlements.",
    points: [
      "Reviews settlement metering installation and maintenance requirements for generators and loads.",
      "Develops data validation rules and exception handling procedures for meter data gaps.",
      "Addresses advanced metering integration and interval data submission standards.",
      "Coordinates with RMS and COPS on settlement impacts of metering data quality issues.",
    ],
  },
  PIPTF: {
    intro: "The Planning Interim Process Task Force addresses interim planning processes and transmission project coordination during periods of significant grid change or regulatory transition.",
    purpose: "Maintain an effective and adaptive transmission planning process that responds to rapid changes in the generation mix, load growth, and policy requirements.",
    points: [
      "Develops interim procedures for large-load and generation interconnection during high-volume periods.",
      "Coordinates with ERCOT planning staff on study timelines and capacity constraint management.",
      "Reviews proposed improvements to the Regional Transmission Plan process.",
      "Addresses transmission planning challenges created by the growth of renewable energy and battery storage.",
    ],
  },
};

const MEETING_RECORDS = {
  BOD: {
    active: [
      { id: "BOD-2026-04", date: "Apr 22, 2026", title: "Open Session — Q2 Operations Review"         },
      { id: "BOD-2026-05", date: "May 20, 2026", title: "Open Session — Annual Budget Discussion"      },
      { id: "BOD-2026-06", date: "Jun 17, 2026", title: "Open Session — Strategic Planning"            },
    ],
    sunset: [
      { id: "BOD-2026-03", date: "Mar 25, 2026", title: "Open Session — Q1 Financial Review"           },
      { id: "BOD-2026-02", date: "Feb 18, 2026", title: "Open Session — Regulatory Update"             },
      { id: "BOD-2026-01", date: "Jan 21, 2026", title: "Open Session — 2026 Work Plan Approval"       },
      { id: "BOD-2025-12", date: "Dec 18, 2025", title: "Open Session — Q4 Reliability Report"         },
      { id: "BOD-2025-11", date: "Nov 19, 2025", title: "Open Session — Market Design Review"          },
      { id: "BOD-2025-10", date: "Oct 22, 2025", title: "Open Session — Grid Modernization Update"     },
    ],
  },
  TAC: {
    active: [
      { id: "TAC-2026-04", date: "Apr 30, 2026", title: "Regular — Spring Protocol Revisions"          },
      { id: "TAC-2026-05", date: "May 28, 2026", title: "Regular — Market Credit WG Report"            },
      { id: "TAC-2026-06", date: "Jun 25, 2026", title: "Regular — Summer Readiness Review"            },
    ],
    sunset: [
      { id: "TAC-2026-03", date: "Mar 26, 2026", title: "Regular — Transmission Planning Update"       },
      { id: "TAC-2026-02", date: "Feb 26, 2026", title: "Regular — Retail Market Subcommittee Report"  },
      { id: "TAC-2026-01", date: "Jan 29, 2026", title: "Regular — 2026 Technical Priorities"          },
      { id: "TAC-2025-12", date: "Dec 18, 2025", title: "Regular — Year-End Protocol Review"           },
      { id: "TAC-2025-11", date: "Nov 20, 2025", title: "Regular — NERC Standards Alignment"           },
    ],
  },
  ROS: {
    active: [
      { id: "ROS-2026-04", date: "Apr 08, 2026", title: "Monthly — Reliability Standards Update"       },
      { id: "ROS-2026-05", date: "May 13, 2026", title: "Monthly — Disturbance Analysis"               },
    ],
    sunset: [
      { id: "ROS-2026-03", date: "Mar 11, 2026", title: "Monthly — Q1 Operations Summary"              },
      { id: "ROS-2026-02", date: "Feb 11, 2026", title: "Monthly — NERC Compliance Review"             },
      { id: "ROS-2026-01", date: "Jan 14, 2026", title: "Monthly — 2026 Reliability Priorities"        },
      { id: "ROS-2025-12", date: "Dec 10, 2025", title: "Monthly — Year-End Reliability Assessment"    },
    ],
  },
  WMS: {
    active: [
      { id: "WMS-2026-04", date: "Apr 09, 2026", title: "Monthly — Congestion Revenue Rights"          },
      { id: "WMS-2026-05", date: "May 14, 2026", title: "Monthly — Market Credit Update"               },
    ],
    sunset: [
      { id: "WMS-2026-03", date: "Mar 12, 2026", title: "Monthly — Demand Response Programs"           },
      { id: "WMS-2026-02", date: "Feb 12, 2026", title: "Monthly — Ancillary Services Review"          },
      { id: "WMS-2026-01", date: "Jan 08, 2026", title: "Monthly — 2026 Wholesale Market Priorities"   },
      { id: "WMS-2025-12", date: "Dec 11, 2025", title: "Monthly — Year-End Market Performance"        },
    ],
  },
  RMS: {
    active: [
      { id: "RMS-2026-04", date: "Apr 15, 2026", title: "Monthly — Retail Competition Update"          },
      { id: "RMS-2026-05", date: "May 20, 2026", title: "Monthly — Switch Processing Review"           },
    ],
    sunset: [
      { id: "RMS-2026-03", date: "Mar 18, 2026", title: "Monthly — REP Compliance Report"              },
      { id: "RMS-2026-02", date: "Feb 19, 2026", title: "Monthly — Customer Complaint Trends"          },
      { id: "RMS-2026-01", date: "Jan 15, 2026", title: "Monthly — Retail Market 2026 Outlook"         },
      { id: "RMS-2025-12", date: "Dec 17, 2025", title: "Monthly — Year-End Retail Summary"            },
    ],
  },
  PLWG: {
    active: [
      { id: "PRS-2026-08", date: "Apr 24, 2026", title: "Bi-weekly — NPRR Review & Voting"            },
      { id: "PRS-2026-09", date: "May 08, 2026", title: "Bi-weekly — Protocol Redline Review"          },
      { id: "PRS-2026-10", date: "May 22, 2026", title: "Bi-weekly — NPRR Stakeholder Comments"        },
    ],
    sunset: [
      { id: "PRS-2026-07", date: "Apr 10, 2026", title: "Bi-weekly — NPRR Vote Tallies"               },
      { id: "PRS-2026-06", date: "Mar 27, 2026", title: "Bi-weekly — Protocol Change Review"           },
      { id: "PRS-2026-05", date: "Mar 13, 2026", title: "Bi-weekly — NPRR Disposition Update"          },
      { id: "PRS-2026-04", date: "Feb 27, 2026", title: "Bi-weekly — Q1 Protocol Review"               },
    ],
  },
};

const DEFAULT_RECORDS = {
  active: [
    { id: "MTG-2026-04", date: "Apr 16, 2026", title: "Standing — Q2 Work Plan Review"                },
    { id: "MTG-2026-05", date: "May 21, 2026", title: "Standing — Action Item Follow-up"               },
  ],
  sunset: [
    { id: "MTG-2026-03", date: "Mar 19, 2026", title: "Standing — Q1 Status Report"                   },
    { id: "MTG-2026-02", date: "Feb 20, 2026", title: "Standing — Technical Review"                    },
    { id: "MTG-2026-01", date: "Jan 16, 2026", title: "Standing — 2026 Goals & Objectives"            },
  ],
};

// Sunsetted / inactive ERCOT stakeholder bodies — sourced from ercot.com/committees/inactive
const SUNSET_GROUPS = [
  // Board
  { tag: "NC",      parent: "Board",   name: "Nominating Committee"                                        },
  { tag: "RMC",     parent: "Board",   name: "Reliability and Markets Committee"                           },
  { tag: "SNPC",    parent: "Board",   name: "Special Nodal Program Committee"                             },
  { tag: "SUDS",    parent: "Board",   name: "Subcommittee for Unaffiliated Director Searches"             },
  { tag: "TREAC",   parent: "Board",   name: "Texas Regional Entity Advisory Committee"                    },
  // Finance & Audit
  { tag: "CWG",     parent: "Finance", name: "Credit Work Group"                                           },
  // TAC
  { tag: "BESTF",   parent: "TAC",     name: "Battery Energy Storage Task Force"                           },
  { tag: "DGTF",    parent: "TAC",     name: "Distributed Generation Task Force"                           },
  { tag: "DREAMTF", parent: "TAC",     name: "Distributed Resource Energy and Ancillaries Market TF"       },
  { tag: "LFLTF",   parent: "TAC",     name: "Large Flexible Load Task Force"                              },
  { tag: "METF",    parent: "TAC",     name: "Market Enhancement Task Force"                               },
  { tag: "MPDJTF",  parent: "TAC",     name: "Market Participant Default Joint Task Force"                 },
  { tag: "NATF",    parent: "TAC",     name: "Nodal Advisory Task Force"                                   },
  { tag: "RTCTF",   parent: "TAC",     name: "Real-Time Co-Optimization Task Force"                        },
  { tag: "RTCBTF",  parent: "TAC",     name: "Real-Time Co-optimization plus Batteries Task Force"         },
  { tag: "RTWG",    parent: "TAC",     name: "Renewable Technologies Working Group"                        },
  { tag: "SWG",     parent: "TAC",     name: "Seminar Working Group"                                       },
  { tag: "TASORTF", parent: "TAC",     name: "TAC and Subcommittees Organizational Review Task Force"      },
  { tag: "TACSTF",  parent: "TAC",     name: "Technical Advisory Committee Special Task Force"             },
  { tag: "TNT",     parent: "TAC",     name: "Texas Nodal Team"                                            },
  { tag: "TPTF",    parent: "TAC",     name: "Texas Nodal Transition Plan Task Force"                      },
  // COPS
  { tag: "ADRTF",   parent: "COPS",    name: "Alternate Dispute Resolution Task Force"                     },
  { tag: "CCWG",    parent: "COPS",    name: "COPS Communication Working Group"                            },
  { tag: "CPRWG",   parent: "COPS",    name: "Commercial Protocol Revisions Working Group"                 },
  { tag: "CSWG",    parent: "COPS",    name: "Communications and Settlements Working Group"                },
  { tag: "DEWG",    parent: "COPS",    name: "Data Extracts Working Group"                                 },
  { tag: "DRTF",    parent: "COPS",    name: "Demand Response Task Force"                                  },
  { tag: "MDWG",    parent: "COPS",    name: "Market Data Working Group"                                   },
  { tag: "MISUG",   parent: "COPS",    name: "Market Information System User Group"                        },
  { tag: "NDSTF",   parent: "COPS",    name: "NOIE DRG Settlements Task Force"                            },
  { tag: "SDAWG",   parent: "COPS",    name: "Settlement and Data Aggregation Working Group"               },
  { tag: "SEWG",    parent: "COPS",    name: "Settlement and Extracts Working Group"                       },
  { tag: "UFETF",   parent: "COPS",    name: "Unaccounted for Energy Task Force"                           },
  // ROS
  { tag: "CIPAG",   parent: "ROS",     name: "Critical Infrastructure Protection Advisory Group"           },
  { tag: "DCPTF",   parent: "ROS",     name: "Data Change Process Task Force"                              },
  { tag: "DCCTF",   parent: "ROS",     name: "Double Circuit Outage Contingency Task Force"                },
  { tag: "DMTF",    parent: "ROS",     name: "Dynamic Model Task Force"                                    },
  { tag: "GRTF",    parent: "ROS",     name: "Generation Reactive Task Force"                              },
  { tag: "GMDTF",   parent: "ROS",     name: "Geomagnetic Disturbance Task Force"                         },
  { tag: "IBRTF",   parent: "ROS",     name: "Inverter-Based Resource Task Force"                          },
  { tag: "NPGRTF",  parent: "ROS",     name: "Nodal Protocol and Guides Resolution Task Force"             },
  { tag: "OGRTF",   parent: "ROS",     name: "Operating Guides Revision Task Force"                        },
  { tag: "ORG",     parent: "ROS",     name: "Operations Review Group"                                     },
  { tag: "OPSTF",   parent: "ROS",     name: "Operations and Planning Synchronization Task Force"          },
  { tag: "OCITF",   parent: "ROS",     name: "Outage Coordination Improvements Task Force"                 },
  { tag: "OCWG",    parent: "ROS",     name: "Outage Coordination Working Group"                           },
  { tag: "PRTF",    parent: "ROS",     name: "Patton Review Task Force"                                    },
  { tag: "PMTF",    parent: "ROS",     name: "Phasor Measurement Task Force"                               },
  { tag: "PGDTF",   parent: "ROS",     name: "Planning Geomagnetic Disturbance Task Force"                 },
  { tag: "RDWG",    parent: "ROS",     name: "Resource Data Working Group"                                 },
  { tag: "SPS2TF",  parent: "ROS",     name: "SPS Type 2 Task Force"                                      },
  { tag: "VRTF",    parent: "ROS",     name: "Voltage Reduction Task Force"                                },
  { tag: "WOTF",    parent: "ROS",     name: "Wind Operations Task Force"                                  },
  // RMS
  { tag: "AMWG",    parent: "RMS",     name: "Advanced Metering Working Group"                             },
  { tag: "DRNTF",   parent: "RMS",     name: "Disconnect/Reconnect Task Force"                             },
  { tag: "IGTF",    parent: "RMS",     name: "Inadvertent Gain Task Force"                                 },
  { tag: "IDRTF",   parent: "RMS",     name: "Interval Data Recorder Task Force"                           },
  { tag: "LRITF",   parent: "RMS",     name: "Lubbock Retail Integration Task Force"                       },
  { tag: "MKTTF",   parent: "RMS",     name: "MarkeTrak Task Force"                                        },
  { tag: "MARSTF",  parent: "RMS",     name: "Market Advanced Readings and Settlements Task Force"         },
  { tag: "MCT",     parent: "RMS",     name: "Market Coordination Team for Texas SET Version Releases"     },
  { tag: "MMWG",    parent: "RMS",     name: "Market Metrics Working Group"                                },
  { tag: "MTTF",    parent: "RMS",     name: "Mass Transition Task Force"                                  },
  { tag: "TAMTF",   parent: "RMS",     name: "Meter Tampering Task Force"                                  },
  { tag: "MITF",    parent: "RMS",     name: "Metering Issues Task Force"                                  },
  { tag: "PWG",     parent: "RMS",     name: "Profiling Working Group"                                     },
  { tag: "RAMP",    parent: "RMS",     name: "Retail Advanced Metering Process Task Force"                 },
  { tag: "RECTF",   parent: "RMS",     name: "Retail Emergency Conditions Task Force"                      },
  { tag: "RMRTF",   parent: "RMS",     name: "Retail Market Revisions Task Force"                          },
  { tag: "RMWG",    parent: "RMS",     name: "Retail Metering Working Group"                               },
  { tag: "STTF",    parent: "RMS",     name: "Sharyland Transition Task Force"                             },
  { tag: "TCTF",    parent: "RMS",     name: "Terms and Conditions Task Force"                             },
  { tag: "TXSET",   parent: "RMS",     name: "Texas Standard Electronic Transaction Working Group"         },
  { tag: "TTPT",    parent: "RMS",     name: "Texas Test Plan Team"                                        },
  { tag: "TITF",    parent: "RMS",     name: "Transaction Improvement Task Force"                          },
  // PRS
  { tag: "CRB",     parent: "PRS",     name: "CBA Review Board"                                            },
  { tag: "NPRSA",   parent: "PRS",     name: "Nodal Protocol/Reliability Standards Alignment TF"           },
  { tag: "PRRTF",   parent: "PRS",     name: "Protocol Revision Request Task Force"                        },
  { tag: "RPRSTF",  parent: "PRS",     name: "Replacement Reserve Service Task Force"                      },
  { tag: "RTF",     parent: "PRS",     name: "Resource Definition Task Force"                              },
  // WMS
  { tag: "BEERTF",  parent: "WMS",     name: "Balancing EILS and Extra Reserves Task Force"                },
  { tag: "COTF",    parent: "WMS",     name: "Co-Optimization Task Force"                                  },
  { tag: "CATF",    parent: "WMS",     name: "Cost Allocation Task Force"                                  },
  { tag: "EILTF",   parent: "WMS",     name: "Emergency Interruptible Load Task Force"                     },
  { tag: "ETWG",    parent: "WMS",     name: "Emerging Technologies Working Group"                         },
  { tag: "GATF",    parent: "WMS",     name: "Generation Adequacy Task Force"                              },
  { tag: "LTSTF",   parent: "WMS",     name: "Long-Term Solution Task Force"                               },
  { tag: "MSWG",    parent: "WMS",     name: "Market Settlements Working Group"                            },
  { tag: "NNSTF",   parent: "WMS",     name: "Nodal Non-Spin Task Force"                                   },
  { tag: "PERTF",   parent: "WMS",     name: "Potomac Economics Recommendations Task Force"                },
  { tag: "QSTF",    parent: "WMS",     name: "Quick Start Task Force"                                      },
  { tag: "RDTF",    parent: "WMS",     name: "Reliability Deployment Task Force"                           },
  { tag: "RTTF",    parent: "WMS",     name: "Renewables and Transmission Task Force"                      },
  { tag: "RCWG",    parent: "WMS",     name: "Resource Cost Working Group"                                 },
  { tag: "VCWG",    parent: "WMS",     name: "Verifiable Cost Working Group"                               },
  { tag: "FCTF",    parent: "WMS",     name: "WMS Frequency Control Task Force"                            },
  { tag: "WCATF",   parent: "WMS",     name: "Wind Cost Allocation Task Force"                             },
  // Other
  { tag: "CREZ",    parent: "Other",   name: "Competitive Renewable Energy Zone Task Force"                },
  { tag: "EMSWG",   parent: "Other",   name: "Energy Management Systems Working Group"                     },
  { tag: "FAST",    parent: "Other",   name: "Future Ancillary Services Team"                              },
  { tag: "NRWG",    parent: "Other",   name: "NERC Reliability Working Group"                              },
  { tag: "SDWG",    parent: "Other",   name: "Scenario Development Working Group"                          },
  { tag: "TRE",     parent: "Other",   name: "Texas Reliability Entity, Inc."                              },
  // Nodal Projects
  { tag: "APIS",    parent: "Nodal",   name: "Application Programming Interface Subgroup"                  },
  { tag: "CRR",     parent: "Nodal",   name: "Congestion Revenue Rights"                                   },
  { tag: "EDS",     parent: "Nodal",   name: "Early Delivery System Project"                               },
  { tag: "SEM",     parent: "Nodal",   name: "Single Entry Model"                                          },
];

const SUNSET_PARENTS = ["All","TAC","ROS","WMS","RMS","PRS","COPS","Board","Finance","Other","Nodal"];

function MeetingListPanel({ label, items, maxHeight, statusColor }) {
  const [query, setQuery] = React.useState("");
  const filtered = items.filter(item => {
    const q = query.trim().toLowerCase();
    if (!q) return true;
    return item.id.toLowerCase().includes(q) ||
           item.title.toLowerCase().includes(q) ||
           item.date.toLowerCase().includes(q);
  });
  return (
    <div className="mt-list-panel">
      <style>{`
        .mt-list-panel { margin-top: 14px; border-top: 1px dashed var(--rule-2); padding-top: 12px; }
        .mt-list-lbl-row { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
        .mt-list-lbl {
          font-family: var(--mono); font-size: 10px; font-weight: 600;
          letter-spacing: .1em; text-transform: uppercase; padding: 2px 8px; border-radius: 5px;
        }
        .mt-list-search-wrap { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
        .mt-list-search {
          flex: 1; padding: 6px 10px; border: 1px solid var(--rule-2); border-radius: 7px;
          background: var(--bg); color: var(--ink); font-family: var(--mono); font-size: 11.5px;
          outline: none; transition: border-color .15s;
        }
        .mt-list-search:focus { border-color: var(--accent); }
        .mt-list-search::placeholder { color: var(--muted); }
        .mt-list-count { font-family: var(--mono); font-size: 10.5px; color: var(--muted); white-space: nowrap; }
        .mt-list-scroll { overflow-y: auto; display: flex; flex-direction: column; gap: 1px; scrollbar-width: thin; }
        .mt-list-item {
          display: flex; align-items: center; gap: 10px; padding: 5px 8px; border-radius: 6px;
          border: 1px solid transparent; cursor: pointer; transition: background .12s, border-color .12s;
        }
        .mt-list-item:hover { background: var(--accent-soft); border-color: var(--rule-2); }
        .mt-list-id { font-family: var(--mono); font-size: 11px; font-weight: 600; color: var(--accent-2); min-width: 96px; flex-shrink: 0; }
        .mt-list-date { font-family: var(--mono); font-size: 10.5px; color: var(--muted); white-space: nowrap; flex-shrink: 0; }
        .mt-list-title { font-size: 12px; color: var(--ink-2); line-height: 1.3; flex: 1; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .mt-list-item:hover .mt-list-title { color: var(--ink); }
        .mt-list-empty { padding: 14px; text-align: center; font-size: 12px; color: var(--muted); }
      `}</style>
      <div className="mt-list-lbl-row">
        <span className="mt-list-lbl" style={{ background: statusColor + "22", color: statusColor }}>{label}</span>
      </div>
      <div className="mt-list-search-wrap">
        <input className="mt-list-search" type="text"
          placeholder={`Search ${label.toLowerCase()} meetings…`}
          value={query} onChange={e => setQuery(e.target.value)} spellCheck={false}
        />
        <span className="mt-list-count">{filtered.length} / {items.length}</span>
      </div>
      <div className="mt-list-scroll" style={{ maxHeight }}>
        {filtered.length === 0
          ? <div className="mt-list-empty">No matching meetings</div>
          : filtered.map(item => (
            <div key={item.id} className="mt-list-item" title={item.title}>
              <span className="mt-list-id">{item.id}</span>
              <span className="mt-list-date">{item.date}</span>
              <span className="mt-list-title">{item.title}</span>
            </div>
          ))
        }
      </div>
    </div>
  );
}

function NodeInfoPanel({ node }) {
  const info = NODE_INFO[node.id] || {
    intro: `${node.name} is a working group under the ERCOT stakeholder process, responsible for technical analysis and protocol recommendations in its domain.`,
    purpose: `Develop recommendations and provide subject-matter expertise to its parent subcommittee on issues within the ${node.tag} scope.`,
    points: [
      "Meets on a standing schedule; open to ERCOT market participants and interested parties.",
      "Produces reports, white papers, and voting recommendations forwarded to the parent subcommittee.",
      "May spawn sub-task forces for time-limited issues requiring focused stakeholder engagement.",
    ],
  };
  return (
    <div className="mt-info-panel">
      <style>{`
        .mt-info-panel { margin-top: 16px; border-top: 1px dashed var(--rule-2); padding-top: 14px; }
        .mt-info-intro {
          font-size: 13px; color: var(--ink); line-height: 1.65;
          margin-bottom: 12px;
        }
        .mt-info-purpose-lbl {
          font-family: var(--mono); font-size: 10px; font-weight: 600;
          letter-spacing: .1em; text-transform: uppercase;
          padding: 2px 8px; border-radius: 5px; margin-bottom: 8px; display: inline-block;
          background: color-mix(in oklab, var(--warn), transparent 85%);
          color: var(--warn);
        }
        .mt-info-purpose {
          font-size: 12.5px; color: var(--ink-2); line-height: 1.6;
          font-style: italic; margin-bottom: 14px;
          padding-left: 10px; border-left: 2px solid var(--accent);
        }
        .mt-info-points-lbl {
          font-family: var(--mono); font-size: 10px; font-weight: 600;
          letter-spacing: .1em; text-transform: uppercase; color: var(--muted);
          margin-bottom: 8px;
        }
        .mt-info-points { display: flex; flex-direction: column; gap: 6px; }
        .mt-info-point {
          display: flex; align-items: baseline; gap: 8px;
          font-size: 12.5px; color: var(--ink-2); line-height: 1.55;
        }
        .mt-info-dot {
          width: 5px; height: 5px; border-radius: 50%;
          background: var(--accent); flex-shrink: 0; margin-top: 6px;
        }
      `}</style>
      <p className="mt-info-intro">{info.intro}</p>
      <div className="mt-info-purpose-lbl">Mission</div>
      <p className="mt-info-purpose">{info.purpose}</p>
      <div className="mt-info-points-lbl">Main Tasks</div>
      <div className="mt-info-points">
        {info.points.map((pt, i) => (
          <div key={i} className="mt-info-point">
            <span className="mt-info-dot"/>
            <span>{pt}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function SunsetGroupsPanel() {
  const [query, setQuery] = React.useState("");
  const [parentFilter, setParentFilter] = React.useState("All");

  const filtered = SUNSET_GROUPS.filter(g => {
    const matchParent = parentFilter === "All" || g.parent === parentFilter;
    const q = query.trim().toLowerCase();
    const matchQ = !q || g.tag.toLowerCase().includes(q) || g.name.toLowerCase().includes(q) || g.parent.toLowerCase().includes(q);
    return matchParent && matchQ;
  });

  return (
    <div className="mt-sunset">
      <style>{`
        .mt-sunset {
          border: 1px solid var(--rule); border-radius: var(--radius);
          background: linear-gradient(180deg, var(--panel), var(--bg-2));
          padding: 22px; box-shadow: var(--shadow-1);
          position: relative; overflow: hidden;
        }
        .mt-sunset::before {
          content: ""; position: absolute; inset: 0;
          background-image: repeating-linear-gradient(90deg, rgba(27,26,23,.03) 0 1px, transparent 1px 28px);
          pointer-events: none;
        }
        .mt-sunset-eye {
          font-family: var(--mono); font-size: 10.5px; letter-spacing: .14em;
          color: var(--muted); text-transform: uppercase;
        }
        .mt-sunset-title {
          font-family: var(--serif); font-size: 26px; line-height: 1.1;
          margin: 2px 0 4px; font-weight: 400; color: var(--ink);
        }
        .mt-sunset-sub { color: var(--ink-2); font-size: 13px; margin-bottom: 14px; }
        .mt-sunset-filters {
          display: flex; flex-wrap: wrap; gap: 5px; margin-bottom: 12px;
        }
        .mt-sunset-filter {
          padding: 4px 10px; border-radius: 6px;
          border: 1px solid var(--rule-2);
          font-family: var(--mono); font-size: 11px; font-weight: 600;
          color: var(--ink-2); background: transparent; cursor: pointer;
          transition: border-color .12s, background .12s, color .12s;
        }
        .mt-sunset-filter:hover { border-color: var(--accent); color: var(--accent); }
        .mt-sunset-filter.is-on { background: var(--ink); color: var(--bg); border-color: var(--ink); }
        .mt-sunset-search-wrap { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
        .mt-sunset-search {
          flex: 1; padding: 7px 10px; border: 1px solid var(--rule-2); border-radius: 7px;
          background: var(--bg); color: var(--ink); font-family: var(--mono); font-size: 11.5px;
          outline: none; transition: border-color .15s;
        }
        .mt-sunset-search:focus { border-color: var(--accent); }
        .mt-sunset-search::placeholder { color: var(--muted); }
        .mt-sunset-count { font-family: var(--mono); font-size: 10.5px; color: var(--muted); white-space: nowrap; }
        .mt-sunset-list { overflow-y: auto; display: flex; flex-direction: column; gap: 1px; scrollbar-width: thin; max-height: 340px; }
        .mt-sunset-item {
          display: flex; align-items: center; gap: 10px; padding: 5px 8px; border-radius: 6px;
          border: 1px solid transparent; cursor: pointer; transition: background .12s, border-color .12s;
        }
        .mt-sunset-item:hover { background: var(--accent-soft); border-color: var(--rule-2); }
        .mt-sunset-tag {
          font-family: var(--mono); font-size: 11px; font-weight: 600;
          color: var(--accent-2); min-width: 72px; flex-shrink: 0;
        }
        .mt-sunset-parent {
          font-family: var(--mono); font-size: 10px; font-weight: 600; letter-spacing: .04em;
          padding: 2px 6px; border-radius: 4px;
          background: var(--bg-2); color: var(--muted);
          flex-shrink: 0; white-space: nowrap;
        }
        .mt-sunset-name {
          font-size: 12px; color: var(--ink-2); line-height: 1.3;
          flex: 1; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }
        .mt-sunset-item:hover .mt-sunset-name { color: var(--ink); }
        .mt-sunset-empty { padding: 14px; text-align: center; font-size: 12px; color: var(--muted); }
      `}</style>

      <div className="mt-sunset-eye">Meeting Tracks</div>
      <h2 className="mt-sunset-title">Sunset Groups</h2>
      <div className="mt-sunset-sub">
        Inactive ERCOT stakeholder committees, working groups, and task forces — {SUNSET_GROUPS.length} total.
      </div>

      <div className="mt-sunset-filters">
        {SUNSET_PARENTS.map(p => (
          <button key={p}
            className={`mt-sunset-filter ${parentFilter === p ? "is-on" : ""}`}
            onClick={() => setParentFilter(p)}
          >{p}</button>
        ))}
      </div>

      <div className="mt-sunset-search-wrap">
        <input className="mt-sunset-search" type="text"
          placeholder="Search by tag, name, or parent…"
          value={query} onChange={e => setQuery(e.target.value)} spellCheck={false}
        />
        <span className="mt-sunset-count">{filtered.length} / {SUNSET_GROUPS.length}</span>
      </div>

      <div className="mt-sunset-list">
        {filtered.length === 0
          ? <div className="mt-sunset-empty">No matching groups</div>
          : filtered.map(g => (
            <div key={g.tag + g.parent} className="mt-sunset-item" title={g.name}>
              <span className="mt-sunset-tag">{g.tag}</span>
              <span className="mt-sunset-parent">{g.parent}</span>
              <span className="mt-sunset-name">{g.name}</span>
            </div>
          ))
        }
      </div>
    </div>
  );
}

function MeetingTracksOrgChart({ selected, onSelect }) {
  const [expanded, setExpanded] = React.useState({ TAC: true });
  const toggle = (id) => setExpanded(e => ({ ...e, [id]: !e[id] }));

  const selectedNode = React.useMemo(() => {
    const findNode = (n, id) => {
      if (n.id === id) return n;
      for (const c of n.children || []) { const f = findNode(c, id); if (f) return f; }
      return null;
    };
    return findNode(ERCOT_ORG, selected) || ERCOT_ORG;
  }, [selected]);

  const records = MEETING_RECORDS[selectedNode.id] || DEFAULT_RECORDS;

  const renderNode = (node, depth = 0) => {
    const isOpen = expanded[node.id];
    const hasKids = (node.children || []).length > 0;
    const isSel = node.id === selectedNode.id;
    return (
      <div key={node.id} className="mt-row-wrap">
        <div className={`mt-node depth-${depth} ${isSel ? "is-sel" : ""}`} onClick={() => onSelect(node.id)}>
          {hasKids ? (
            <button className="mt-chev" onClick={(e) => { e.stopPropagation(); toggle(node.id); }}
              aria-label={isOpen ? "Collapse" : "Expand"}>
              <svg width="10" height="10" viewBox="0 0 24 24" style={{ transform: isOpen ? "rotate(90deg)" : "none", transition: "transform .15s" }}>
                <path d="m9 6 6 6-6 6" stroke="currentColor" strokeWidth="2.2" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </button>
          ) : <span className="mt-chev-spacer"/>}
          <span className="mt-tag">{node.tag}</span>
          <span className="mt-name">{node.name}</span>
          {hasKids && <span className="mt-count">{node.children.length}</span>}
        </div>
        {isOpen && hasKids && (
          <div className="mt-children">{node.children.map(c => renderNode(c, depth + 1))}</div>
        )}
      </div>
    );
  };

  const kidCount = (selectedNode.children || []).length;
  const parentLabel = selectedNode.id === "BOD" ? "" : selectedNode.id === "TAC" ? "Board" : "TAC";

  return (
    <React.Fragment>
      <div className="pt-orgchart">
        <style>{`
          .pt-orgchart {
            border: 1px solid var(--rule);
            background:
              radial-gradient(120% 80% at 0% 0%, var(--accent-soft) 0%, transparent 55%),
              linear-gradient(180deg, var(--panel), var(--bg-2));
            border-radius: var(--radius); padding: 22px; box-shadow: var(--shadow-1);
            display: grid; grid-template-columns: 1.3fr 1fr; gap: 22px;
            position: relative; overflow: hidden; margin-bottom: 16px;
          }
          @media (max-width: 820px) { .pt-orgchart { grid-template-columns: 1fr; } }
          .pt-orgchart::before {
            content: ""; position: absolute; inset: 0;
            background-image: repeating-linear-gradient(90deg, rgba(27,26,23,.03) 0 1px, transparent 1px 28px);
            pointer-events: none;
          }
          .mt-head-eye { font-family: var(--mono); font-size: 10.5px; letter-spacing: .14em; color: var(--muted); text-transform: uppercase; }
          .mt-head-title { font-family: var(--serif); font-size: 26px; line-height: 1.1; margin: 2px 0 6px; font-weight: 400; color: var(--ink); }
          .mt-head-sub { color: var(--ink-2); font-size: 13px; margin-bottom: 14px; }
          .mt-tree { position: relative; font-size: 13px; }
          .mt-row-wrap { position: relative; }
          .mt-children { position: relative; padding-left: 14px; margin-left: 12px; border-left: 1px dashed var(--rule-2); }
          .mt-node { display: flex; align-items: center; gap: 8px; padding: 7px 10px; margin: 2px 0; border-radius: 8px; color: var(--ink-2); cursor: pointer; transition: background .12s, color .12s; }
          .mt-node:hover { background: var(--bg-2); color: var(--ink); }
          .mt-node.is-sel { background: var(--ink); color: var(--bg); }
          .mt-node.is-sel .mt-tag { background: color-mix(in oklab, var(--bg), transparent 80%); color: var(--bg); }
          .mt-node.depth-0 .mt-tag { background: var(--accent); color: #fff; }
          .mt-node.depth-1 .mt-tag { background: var(--accent-soft); color: var(--accent-2); }
          .mt-chev { width: 18px; height: 18px; border-radius: 4px; display: grid; place-items: center; color: inherit; background: transparent; }
          .mt-chev:hover { background: color-mix(in oklab, currentColor, transparent 85%); }
          .mt-chev-spacer { width: 18px; height: 18px; display: inline-block; }
          .mt-tag { font-family: var(--mono); font-size: 10.5px; font-weight: 600; padding: 2px 6px; border-radius: 4px; background: var(--bg-2); color: var(--ink-2); letter-spacing: .02em; flex: 0 0 auto; }
          .mt-name { flex: 1; font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
          .mt-count { font-family: var(--mono); font-size: 10.5px; color: var(--muted); padding: 0 6px; border-radius: 999px; border: 1px solid var(--rule-2); }
          .mt-node.is-sel .mt-count { color: var(--bg); border-color: color-mix(in oklab, var(--bg), transparent 70%); }
          .mt-detail { position: relative; border-left: 1px dashed var(--rule-2); padding-left: 22px; overflow-y: auto; max-height: 560px; scrollbar-width: thin; }
          @media (max-width: 820px) { .mt-detail { border-left: 0; padding-left: 0; border-top: 1px dashed var(--rule-2); padding-top: 16px; max-height: none; } }
          .mt-detail-tag { display: inline-block; font-family: var(--mono); font-size: 11px; font-weight: 600; padding: 3px 8px; border-radius: 6px; background: var(--accent-soft); color: var(--accent-2); }
          .mt-detail-name { font-family: var(--serif); font-size: 22px; font-weight: 400; color: var(--ink); margin: 8px 0 4px; line-height: 1.2; }
          .mt-detail-sub { font-size: 12.5px; color: var(--muted); margin-bottom: 4px; }
        `}</style>

        <div>
          <div className="mt-head-eye">Meeting Tracks</div>
          <h2 className="mt-head-title">ERCOT stakeholder process</h2>
          <div className="mt-head-sub">Click any node to inspect its meeting records.</div>
          <div className="mt-tree">{renderNode(ERCOT_ORG)}</div>
        </div>

        <div className="mt-detail">
          <span className="mt-detail-tag">{selectedNode.tag}</span>
          <div className="mt-detail-name">{selectedNode.name}</div>
          <div className="mt-detail-sub">
            {kidCount > 0 ? `${kidCount} subgroup${kidCount === 1 ? "" : "s"}` : "Working group"}
            {parentLabel ? ` · reports to ${parentLabel}` : ""}
          </div>
          <NodeInfoPanel node={selectedNode} />
        </div>
      </div>

      <SunsetGroupsPanel/>
    </React.Fragment>
  );
}

window.MeetingTracksOrgChart = MeetingTracksOrgChart;
