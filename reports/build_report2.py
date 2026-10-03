"""Builds Report 2: AgroPeace (GIS-based early warning for farmer-herder conflict)."""
import os

from docx_helpers import Report

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Report2_AgroPeace_GIS_Early_Warning.docx")

r = Report()
r.title_page("AgroPeace: A GIS-Based Early Warning and Real-Time Response Framework for Farmer-Herder "
             "Conflict Resolution in Nigeria",
             "A secure, data-driven system for prevention, alerting and mediation")

r.h1("DECLARATION")
r.p("I declare that this project report and the accompanying software were written by me as part of the "
    "requirements of CMP 468 (Computer Security). Every source used has been cited. All literature cited in "
    "this report was published between 2021 and 2026.")
r.p("Signature: ____________________          Date: ____________________")
r.page_break()

r.h1("ABSTRACT")
r.p("Violent conflict between crop farmers and pastoralists kills people, displaces communities and raises food "
    "insecurity across Nigeria's Middle Belt. Survey evidence from 401 rural households shows that both the "
    "incidence and the severity of these conflicts significantly increase household food insecurity "
    "(Nnaji et al., 2022). Existing early warning practice in pastoral areas is weakly structured, with poor "
    "coordination and slow response (Alemneh, 2025). This project designed and built AgroPeace, a GIS-based "
    "early warning and real-time response framework. It combines (1) a geodatabase of Local Government Areas "
    "(LGAs), farmland, grazing reserves, water points and stock routes, (2) incident intake through a web form, "
    "SMS and USSD for basic phones, (3) signed GPS pings from herds with geofencing for farmland encroachment "
    "and route deviation, (4) a hybrid risk engine that blends a transparent weighted index with a random forest "
    "model trained on conflict history and vegetation (NDVI) anomalies, and (5) multilingual alerts in English, "
    "Hausa and Nigerian Pidgin with a case management workflow for mediation. Because the system holds "
    "sensitive data about informants and communities, it applies computer security controls throughout: "
    "Fernet (AES-128-CBC with HMAC-SHA256) encryption of reporter phone numbers, keyed pseudonyms, HMAC-signed "
    "device messages with replay protection, role-based access, CSRF protection, rate limiting and a hash-chained "
    "audit trail. On a synthetic two-year panel of 2,376 LGA-weeks, the random forest reached an AUC of 0.659 "
    "for predicting incidents in the next seven days, against 0.611 for a naive last-month baseline. In a live "
    "simulation, the system detected three farmland encroachments and five stock route deviations in real time, "
    "and raised Guma LGA from High (54.9) to Severe (82.9) within one scoring cycle after field reports arrived.")
r.p("**Keywords:** early warning system, GIS, farmer-herder conflict, geofencing, NDVI, machine learning, "
    "data protection, Nigeria.")
r.page_break()

r.h1("TABLE OF CONTENTS")
r.toc()
r.page_break()

# ------------------------------------------------------------ chapter 1
r.h1("CHAPTER ONE: INTRODUCTION")
r.h2("1.1 Background of the Study")
r.p("Farmers and herders in Nigeria once relied on each other. Herders grazed harvested fields in the dry "
    "season and cattle manured the soil. That arrangement has broken down in many places. Recent studies trace "
    "the conflict to scarce farmland and grazing land, desertification, encroachment on grazing routes, weak "
    "governance and the political use of identity (Abdullahi, 2025; Lamidi, 2025). In Taraba State, 399 "
    "respondents ranked competition over land and the cultivation of crops along cattle routes among the top "
    "causes, and also judged media coverage to be biased and fear-inducing (Garba et al., 2025). In the "
    "Benue-Nasarawa borderland, perceptions of injustice over crop damage and cattle killings escalated "
    "disputes into violence, and the anti-open grazing law amplified those perceptions (Nwankwo, 2025).")
r.p("Climate pressure sits under these drivers. Reduced rainfall in pastoral territory pushes herds into "
    "neighbouring farm areas before harvest, and the resulting conflicts cluster in the wet season and in "
    "agricultural zones (McGuirk & Nunn, 2024). In West African rangelands the growing season is getting "
    "shorter because it starts later, which affects traditional transhumance routes (Estefania-Salazar et al., "
    "2025). Conflict also spreads across borders through pastoral mobility and uneven use of the ECOWAS "
    "Transhumance Protocol (Benjamin, 2026).")
r.p("These drivers have a location and a season. That makes the problem suitable for a Geographic Information "
    "System (GIS). A GIS can show where herds move, where crops are in the field, where vegetation is below "
    "normal, and where incidents are rising. Combined with mobile reporting and fast alerts, it can give peace "
    "committees, traditional rulers and security agencies time to act before a dispute turns violent.")

r.h2("1.2 Statement of the Problem")
r.bullets([
    "**Late information.** Incidents are often known to authorities only after casualties, through the media "
    "or social networks. Early signs such as cattle near unharvested farms, threats, or rumours are not "
    "collected in one place.",
    "**Weak warning-to-response link.** Studies of pastoral early warning describe poor coordination between "
    "those who collect information and those who decide, and a lack of timely action (Alemneh, 2025; "
    "Kamau et al., 2022).",
    "**No spatial view.** Farmland, grazing reserves and stock routes are rarely mapped together, so planners "
    "cannot see where routes cut through farms or where reserves are too small (Usman et al., 2024).",
    "**Misinformation.** False or exaggerated reports trigger reprisals. Any reporting channel must verify "
    "reports and score source credibility (Garba et al., 2025).",
    "**Danger to informants.** People who report herder or farmer movements can become targets. A system that "
    "stores their phone numbers in clear text is itself a security threat.",
])

r.h2("1.3 Aim and Objectives")
r.p("The aim is to design and implement a secure GIS-based early warning and real-time response framework "
    "for farmer-herder conflict in Nigeria. The objectives are to:")
r.bullets([
    "build a geodatabase of LGAs, farmland, grazing reserves, water points and stock routes.",
    "collect incident reports through web, SMS and USSD channels that work on basic phones.",
    "track herd positions and raise geofence alerts for farmland encroachment and route deviation.",
    "compute an explainable risk score per LGA that combines incident history, vegetation anomaly, season, "
    "herd proximity and rumours, supported by a machine learning model.",
    "send multilingual alerts to named stakeholders and manage mediation cases to resolution.",
    "protect informants and data with encryption, pseudonymisation, authentication, access control and "
    "audit logging.",
    "evaluate prediction accuracy and real-time behaviour.",
], numbered=True)

r.h2("1.4 Scope and Limitations")
r.p("The prototype covers 24 LGAs in Benue, Nasarawa, Plateau, Kaduna, Taraba, Adamawa, Niger, Oyo and Enugu "
    "States. LGA positions are approximate headquarters coordinates. Farmland polygons, the stock route and the "
    "grazing reserve outlines are illustrative, and the incident history used for training is synthetic. "
    "The system includes an importer for real ACLED event data, which requires a free ACLED account, and a "
    "Google Earth Engine procedure for real MODIS NDVI. The SMS gateway runs in demonstration mode unless an "
    "API key for a Nigerian provider such as Termii or Africa's Talking is supplied.")

r.h2("1.5 Significance of the Study")
r.p("The framework gives state emergency centres and LGA peace committees a shared, live picture. It turns "
    "scattered reports into ranked, explained warnings, so scarce security patrols go where risk is highest. "
    "The geofence warns a herder leader and a farmers' group before cattle reach a yam farm, which is the "
    "moment many clashes start. From a computer security view, it shows how to collect sensitive conflict "
    "data without exposing the people who report it, in line with the Nigeria Data Protection Act 2023.")

r.h2("1.6 Relation to the CMP 468 Course Outline")
r.table("Mapping of course topics to AgroPeace",
        ["CMP 468 topic", "Where it appears in AgroPeace"],
        [["Overview of security in computing", "Threat model covering informants, communities, devices and "
          "the server"],
         ["Characteristics of computer intrusion", "Forged GPS pings, flooding with fake reports, bots on the "
          "public form, insider look-up of informants"],
         ["Types of security breaches", "Disclosure of reporter identity, manipulation of risk scores, "
          "tampering with the trained model"],
         ["Security vulnerability", "Open public endpoints, plain-text phone numbers, unsigned devices, "
          "unsafe pickle loading"],
         ["Classes of attacks", "Spoofing, replay, CSRF, brute-force login, misinformation injection, "
          "denial of service by spam"],
         ["Methods of defence and controls", "HMAC signatures with timestamps, rate limits, honeypot field, "
          "credibility scoring, RBAC, lockout, audit chain"],
         ["Data security: encryption and decryption", "Fernet encryption of phone numbers, HMAC-SHA256 "
          "pseudonyms, PBKDF2 password hashing"],
         ["Database security", "Parameterised SQL, least-privilege roles, need-to-know reveal with audit, "
          "SHA-256 check on the model file"],
         ["Network security", "Signed device API, security headers, session cookie flags, request size limit"],
         ["Security policies and standards", "Data minimisation, retention and reveal policy aligned with "
          "NDPA 2023 and ISO/IEC 27001:2022"]],
        widths=[5, 11])
r.page_break()

# ------------------------------------------------------------ chapter 2
r.h1("CHAPTER TWO: LITERATURE REVIEW")
r.p("The review covers works published between 2021 and 2026 under five themes: causes and effects of the "
    "conflict, climate and vegetation, conflict early warning systems, prediction models, and mobile and "
    "geospatial technologies.")

r.h2("2.1 Theoretical Framework")
r.p("Three theories guide the design. Resource scarcity and political ecology explain why land, water and "
    "pasture competition produce conflict (Abdullahi, 2025; Lamidi, 2025). Relative deprivation and perceived "
    "injustice explain why some disputes escalate and others do not (Nwankwo, 2025). Conflict prevention "
    "theory, used by Kamau et al. (2022) in Samburu County, Kenya, holds that early warning only works when it "
    "is linked to a response. AgroPeace therefore measures scarcity (NDVI), tracks grievances (crop damage, "
    "rustling, threats) and ties every warning to a named responder and a case record.")

r.h2("2.2 Causes and Effects of Farmer-Herder Conflict in Nigeria")
r.p("Nnaji et al. (2022) estimated a two-stage model on 401 households and found that conflict severity raises "
    "food insecurity more than incidence does. Nnam (2025) reached a similar conclusion through media content "
    "analysis and called for modern irrigation and improved pastures. Eke et al. (2025) found that in Enugu "
    "State only collective strategies such as group farming near homesteads were sustainable, and that farmers "
    "need government help with protective infrastructure. Babatunde et al. (2024) compared Plateau State with "
    "Central Darfur and showed that state officials, traditional chiefs and security agents can intensify "
    "conflict when they distribute resources unfairly and run peace processes that favour one side. "
    "Oghuvbu et al. (2021) link the conflict to small arms proliferation and reprisal cycles, and warn of its "
    "effect on national unity. Usman et al. (2024) mapped Fadama resources in Nafada, Gombe State, and found "
    "that the two small grazing reserves and water points could not hold the cattle population and that stock "
    "routes did not connect to the reserves. These findings show that location data (routes, reserves, farms) "
    "and fairness in response are both central to any solution.")

r.h2("2.3 Climate, Vegetation and Pastoral Mobility")
r.p("McGuirk and Nunn (2024) combined ethnographic maps with rainfall and conflict data for Africa from 1989 to "
    "2018 and showed that rainfall deficits in pastoral homelands lead to conflict in neighbouring farm areas "
    "during the wet season through their effect on plant biomass. Navarro et al. (2025) found that vegetation "
    "data outperformed rainfall in predicting pastoral conflict one month ahead in the Karamoja Cluster. "
    "Estefania-Salazar et al. (2025) analysed 250-metre NDVI over 13 West African countries from 2003 to 2023 "
    "and found a shrinking growing season. Tarif (2022) reviewed the West African evidence and identified "
    "changing pastoral mobility as one of four climate-insecurity pathways, and Eboreime et al. (2025) and "
    "Lenshie et al. (2022) describe drought and desertification as threat multipliers in Nigeria and the Sahel. "
    "Schwarz et al. (2022) used Earth observation data with the Transhumance Tracking Tool to map environmental "
    "suitability for transhumance in Chad and the Central African Republic, located conflict risk areas along an "
    "agricultural belt, and proposed combining real-time herd tracking with satellite data into an early "
    "warning system. AgroPeace implements that proposal for Nigeria.")

r.h2("2.4 Conflict Early Warning Systems")
r.p("Rød et al. (2023) compared existing conflict early warning systems and found poor transparency of data "
    "and code and wide variation in key parameters, and called for open standards. Lynam et al. (2023) drew "
    "lessons from teams building warning systems in data-poor settings and stressed the difficulty of acting on "
    "rare, uncertain events. Alemneh (2025) found that early warning in Ethiopia's South Omo Zone lacked "
    "coordination and timely response. Kamau et al. (2022) reported that Samburu County combines monthly "
    "bulletins, rangeland monitoring apps and threat alerts with traditional knowledge, but lacks resources. "
    "Derbyshire et al. (2024) argue that drought early warning in Kenya should build on pastoralists' own "
    "networked knowledge rather than only external data. Rochana et al. (2024) showed that a village WhatsApp "
    "group can serve as a low-cost social conflict warning system. These works shaped three AgroPeace choices: "
    "transparent scoring with visible drivers, local channels (SMS, USSD, local languages), and a built-in "
    "response workflow.")

r.h2("2.5 Prediction Models for Conflict Risk")
r.p("Goodman et al. (2024) trained convolutional networks on Landsat imagery and ACLED data to predict conflict "
    "fatality risk in Nigeria, with an average AUC above 0.75. Sola et al. (2025) used weather and terrain data "
    "with machine learning to produce automatically updated pastoral conflict risk maps for four central African "
    "countries. Browning et al. (2024) fitted a Bayesian spatiotemporal Hawkes process to ACLED data and showed "
    "it is more stable than the historical averages used in many humanitarian dashboards. The self-exciting idea "
    "behind Hawkes models, where one attack raises the chance of reprisals, informs the recency-weighted incident "
    "feature in AgroPeace. In Nigeria, Olaide et al. (2021) trained neural networks on ACLED data, and Olayinka "
    "et al. (2024) reached 96.8% accuracy classifying terrorism incidents with REPTree. High accuracy on "
    "imbalanced event data can hide poor recall, so AgroPeace reports AUC, precision, recall and a naive "
    "baseline instead of accuracy alone.")

r.h2("2.6 Mobile Reporting, IoT and Geospatial Tracking")
r.p("WHO's EWARS Mobile tool delivered timely alerts from 158 health facilities in conflict-affected Darfur with "
    "offline reporting (Shimizu et al., 2025), and in eastern Chad it reached 81% sensitivity (Tewo et al., "
    "2025). Cicek et al. (2023) reviewed mobile crowdsensing for disaster management and noted that most "
    "solutions remain conceptual. Mirau (2022) built a low-cost human-wildlife conflict warning system in "
    "Tanzania with GPS, a Raspberry Pi and SMS alerts. Currin et al. (2022) showed that citizens' mobile safety "
    "reports can replace costly sensor networks in developing cities. For livestock, Aquilani et al. (2021) and "
    "Bailey et al. (2021) review GPS tracking and real-time alerts on rangelands, K S et al. (2024) describe "
    "IoT geofencing that triggers notifications when animals cross virtual boundaries, Parlato et al. (2024) "
    "used low-power GPS collars with GIS kernel density analysis, and Antaya et al. (2025) warn that GPS errors "
    "must be screened. Brennan et al. (2021) showed that low-cost collars can classify grazing behaviour. "
    "Wätzold et al. (2024) note that virtual fences make compliance monitoring cheap.")

r.h2("2.7 Summary of Related Works and Research Gap")
r.table("Summary of closely related works (2021 to 2026)",
        ["Author (Year)", "Approach", "Strength", "Gap addressed by AgroPeace"],
        [["Schwarz et al. (2022)", "EO suitability maps for transhumance", "Locates risk corridors",
          "Not real-time, no alerts"],
         ["Kamau et al. (2022)", "County early warning practice, Kenya", "Links state and community actors",
          "Manual, under-resourced"],
         ["Rød et al. (2023)", "Comparison of warning systems", "Calls for transparency",
          "National scale, not local"],
         ["Goodman et al. (2024)", "CNN on Landsat and ACLED, Nigeria", "AUC above 0.75",
          "No reporting or response link"],
         ["Usman et al. (2024)", "GIS overlay of Fadama resources, Gombe", "Shows route and reserve gaps",
          "Static analysis"],
         ["Sola et al. (2025)", "ML risk maps, central Africa", "Automatic updates",
          "No field reporting or herd data"],
         ["Navarro et al. (2025)", "Vegetation predicts pastoral conflict", "One month lead time",
          "Research study, no tool"],
         ["Alemneh (2025)", "Early warning in pastoral Ethiopia", "Identifies response failures",
          "No technical system"]],
        widths=[3.3, 4.3, 3.6, 4.8])
r.p("**Gap.** No reviewed system for Nigeria combines a geodatabase of farms, routes and reserves, "
    "multi-channel field reporting for basic phones, live herd geofencing, an explainable hybrid risk model, "
    "multilingual alerts, mediation case tracking and strong protection of informants. AgroPeace addresses "
    "that combination.")
r.page_break()

# ------------------------------------------------------------ chapter 3
r.h1("CHAPTER THREE: METHODOLOGY AND SYSTEM DESIGN")
r.h2("3.1 Research Methodology")
r.p("The project uses Design Science Research. The problem was defined from the literature, objectives were "
    "derived, and the artefact was built in increments: geodatabase, intake channels, geofencing, risk engine, "
    "alerting, case management and security controls. Each increment was tested before integration. The "
    "evaluation combined offline model validation with a live simulation of herd movement and field reports.")

r.h2("3.2 Analysis of the Existing System")
r.p("Today, information flows mainly by phone calls, community meetings, media reports and social media. "
    "Security agencies, LGA peace committees, traditional institutions, herders' associations and farmers' "
    "associations each hold part of the picture. There is no shared map, no record of how early signs develop, "
    "and no tracking of whether a warning led to action. Rumours on WhatsApp travel faster than verified "
    "information.")

r.h2("3.3 Stakeholders and User Roles")
r.table("Users and their permissions",
        ["Role", "Typical user", "Permissions"],
        [["Public reporter", "Farmer, herder, youth leader, teacher", "Submit reports by web, SMS or USSD. "
          "Check own LGA risk by USSD"],
         ["Responder", "LGA peace committee, DPO, NSCDC, traditional ruler", "View map and alerts, update "
          "mediation cases"],
         ["Analyst", "State emergency centre, NGO analyst", "All responder rights, plus verify or reject "
          "reports"],
         ["Admin", "System owner", "All rights, plus reveal a reporter number with a logged reason, "
          "view audit trail"],
         ["Device", "Herder phone app or GPS collar", "Send signed GPS pings only"]],
        widths=[3, 5.5, 7.5])

r.h2("3.4 System Architecture")
r.code("  Basic phone --SMS/USSD--> [Gateway: Termii / Africa's Talking] --webhook--+\n"
       "  Smartphone --web form------------------------------------------------>   |\n"
       "  GPS collar / herder app --HMAC-signed JSON------------------------------>|\n"
       "                                                                           v\n"
       "   [Intake + validation + rate limit] -> [Geodatabase: LGAs, farms, routes, reserves, NDVI]\n"
       "                 |                                   |\n"
       "        [Geofence engine]                   [Risk engine: rule index + random forest]\n"
       "                 \\________________ alerts _________/\n"
       "                                    |\n"
       "     [Multilingual SMS alerts]  [Live Leaflet map]  [Mediation cases]  [Audit chain]")
r.p("The server is a Flask application with SQLite (PostGIS is the recommended upgrade for statewide use). "
    "A background thread recomputes risk for every LGA every 30 seconds and evaluates alert rules. The map uses "
    "Leaflet, served locally so it works on a weak connection, with an offline SVG view if map tiles cannot load.")

r.h2("3.5 Geospatial Data Model")
r.table("Geodatabase layers",
        ["Layer", "Geometry", "Source in prototype", "Source for deployment"],
        [["LGAs", "Point (HQ)", "24 approximate HQ coordinates", "GRID3 or OCHA boundary shapefiles"],
         ["Farmland", "Polygon", "72 generated blocks", "Field mapping with farmers' groups, Sentinel-2 crop maps"],
         ["Grazing reserves", "Polygon", "3 illustrative outlines", "State ministries of agriculture"],
         ["Stock route", "Line", "One north-south corridor", "Gazetted routes, Transhumance Tracking Tool"],
         ["Water points", "Point", "4 points", "Community mapping"],
         ["NDVI", "Value per LGA-month", "Synthetic with drought shocks", "MODIS MOD13Q1 via Google Earth Engine"],
         ["Incidents", "Point", "Synthetic history and live reports", "ACLED import and live reports"]],
        widths=[2.8, 2.5, 4.7, 6])

r.h2("3.6 Risk Model")
r.h3("3.6.1 Features")
r.bullets([
    "**inc7:** severity-weighted incidents in the last 7 days with exponential decay (half weight after about "
    "2 days), so recent attacks count most. This reflects the self-exciting pattern modelled by Browning et al. "
    "(2024). Unverified reports count at 0.6 weight.",
    "**inc30** and **fatal30:** incident count and fatalities in the last 30 days.",
    "**ndvi_anom:** NDVI this month minus the long-term mean for the same month. Negative values mean drier than "
    "normal (McGuirk & Nunn, 2024; Navarro et al., 2025).",
    "**crop** and **transhumance:** season flags for crops in the field (April to November) and dry-season "
    "southward movement (November to April).",
    "**rumours7:** rumour and hate speech reports in the last 7 days.",
    "**baseline:** the LGA's historical level of violence.",
    "**herds_near** and **herds_inside:** herds within 3 km of, or inside, the LGA's farmland in the last 6 "
    "hours (real-time layer only).",
])
r.h3("3.6.2 Rule-based index")
r.p("Each feature is multiplied by a weight and summed to a pressure value S. The index is "
    "R = 100 × (1 − e^(−S/2.2)), which keeps scores between 0 and 100 and saturates smoothly. The "
    "contribution of each feature is stored, so the dashboard can say why an LGA is red. A hard rule applies: "
    "a herd inside farmland during crop season can never be rated Low.")
r.h3("3.6.3 Machine learning layer")
r.p("A weekly panel is built for each LGA. The label is 1 if any incident of severity 2 or more occurs in the "
    "next 7 days. Logistic regression and a random forest (300 trees, balanced class weights) are trained on "
    "the earliest 80% of weeks and tested on the latest 20%, so the model never sees the future. The model with "
    "the higher AUC is saved together with its SHA-256 hash. At start-up the hash is checked before the file is "
    "loaded, which blocks a tampered model file, since Python pickle files can execute code. The final score is "
    "the average of the rule index and the model probability × 100. Risk levels are Low (below 25), "
    "Moderate (25 to 49), High (50 to 74) and Severe (75 and above).")

r.h2("3.7 Geofencing")
r.p("Every GPS ping is tested against all farmland polygons with the ray-casting point-in-polygon algorithm. "
    "Distance to the stock route uses a local equirectangular projection, accurate to a few metres at LGA "
    "scale. An encroachment produces a High alert in crop season. A herd more than 15 km off the stock route "
    "produces a Moderate alert. Alerts are de-duplicated for 60 minutes per herd and zone.")

r.h2("3.8 Alerting and Conflict Resolution Workflow")
r.p("Each LGA has four contacts: the peace committee chair, the Ardo or herders' association representative, "
    "the farmers' association representative and the Divisional Police Officer, plus the State Emergency "
    "Operations Centre. Each contact receives the alert in their language (English, Hausa or Pidgin). A report "
    "of severity 3 or more (rustling, cattle killing, armed attack, killing, displacement) opens a mediation "
    "case automatically. Cases move through reported, verified, mediation scheduled, in mediation, resolved or "
    "escalated, with the mediator, notes and any compensation in naira recorded. This creates the "
    "warning-to-response link that Alemneh (2025) and Kamau et al. (2022) found missing.")

r.h2("3.9 Security Design")
r.table("Threats and controls",
        ["Threat", "Control implemented"],
        [["Reprisal against informants after a data leak", "Phone numbers encrypted with Fernet (AES-128-CBC + "
          "HMAC-SHA256). Anonymous option. Only admins can reveal, with a logged reason"],
         ["Linking reports by one person", "Keyed HMAC-SHA256 pseudonym instead of the phone number"],
         ["Forged or replayed GPS pings to trigger false alarms", "HMAC-SHA256 over timestamp and body, "
          "5-minute freshness window, coordinate bounds check"],
         ["Flooding with fake reports", "Per-number hourly limit, per-IP limits, hidden honeypot field, "
          "credibility score from past confirmed and rejected reports"],
         ["Misinformation driving reprisals", "Analyst verification step. Unverified reports weigh 0.6"],
         ["Password guessing", "PBKDF2-SHA256 with 310,000 iterations. Lockout after 5 failures in 5 minutes"],
         ["Cross-site request forgery", "Per-session CSRF token on every state-changing form"],
         ["SQL injection", "Parameterised queries throughout"],
         ["Tampered model file", "SHA-256 check before loading"],
         ["Insider misuse", "Role-based access and a hash-chained audit log of logins, verifications, reveals "
          "and case updates"]],
        widths=[5.5, 10.5])

r.h2("3.10 Tools")
r.table("Development tools", ["Tool", "Use"],
        [["Python 3.10+, Flask", "Server, API and web pages"],
         ["SQLite (PostGIS for scale-up)", "Geodatabase and records"],
         ["Leaflet 1.9.4, OpenStreetMap", "Interactive map"],
         ["scikit-learn", "Logistic regression and random forest"],
         ["cryptography (Fernet)", "Encryption of personal data"],
         ["Termii or Africa's Talking (optional)", "SMS and USSD gateway"]],
        widths=[6, 10])
r.page_break()

# ------------------------------------------------------------ chapter 4
r.h1("CHAPTER FOUR: IMPLEMENTATION, TESTING AND RESULTS")
r.h2("4.1 Implementation")
r.p("The system was written in Python and tested on Linux with Python 3.11. It also runs on Windows. The "
    "prototype database holds 24 LGAs, 72 farmland polygons, 3 grazing reserves, 4 water points, one stock "
    "route, 97 contacts, and synthetic NDVI for three years. A synthetic two-year incident history (1,056 "
    "events) was generated with seasonal effects, drought effects and self-excitation, so that the model has "
    "realistic, learnable patterns.")
r.figure("agropeace_map.png", "Live map: LGA risk circles, farmland blocks, the dashed stock route, herd "
         "positions and trails, and live reports, with the ranked risk table (map tiles were blocked in the "
         "test environment, so the base map is blank)")
r.figure("agropeace_side.png", "Explained risk for Guma LGA with its drivers and trend, followed by "
         "multilingual alerts sent to named stakeholders", width_cm=8)
r.figure("agropeace_report.png", "Public reporting form with anonymous option and location capture")
r.figure("agropeace_incidents.png", "Analyst view: verify or reject reports. Reporter identity is shown only "
         "as 'protected (encrypted)'")

r.h2("4.2 Model Evaluation")
r.table("Prediction of an incident in the next 7 days (time-based test set, 476 LGA-weeks)",
        ["Model", "AUC", "Precision", "Recall", "F1", "Brier score"],
        [["Naive baseline (last 30 days count)", "0.611", "-", "-", "-", "-"],
         ["Logistic regression", "0.638", "0.367", "0.333", "0.349", "0.201"],
         ["Random forest (selected)", "0.659", "0.358", "0.384", "0.371", "0.195"]],
        widths=[5.5, 1.8, 2, 1.8, 1.6, 2.3])
r.table("Random forest feature importance",
        ["Feature", "Importance"],
        [["NDVI anomaly", "0.317"], ["Recent incidents (7 days)", "0.234"], ["Incidents (30 days)", "0.165"],
         ["Historical baseline", "0.153"], ["Fatalities (30 days)", "0.063"], ["Transhumance season", "0.027"],
         ["Crop season", "0.022"], ["Rumours (7 days)", "0.018"]],
        widths=[8, 4])
r.p("The panel had 2,376 LGA-weeks, of which 548 (23.1%) were followed by an incident. The random forest beat "
    "the naive baseline by 0.048 AUC. The absolute AUC is modest, which is honest for a 7-day horizon: Goodman "
    "et al. (2024) reached an average above 0.75 for yearly fatality risk with satellite imagery, which is an "
    "easier target. The importance of NDVI agrees with Navarro et al. (2025), who found vegetation the strongest "
    "predictor. Because the history is synthetic, these figures validate the pipeline, not the real-world skill. "
    "Retraining on imported ACLED data and real NDVI is the next step.")

r.h2("4.3 Real-Time Simulation")
r.p("The simulator moved five herds south along the stock route for 30 steps. One herd was programmed to "
    "leave the route towards a farm in Guma, and another to drift east. Six SMS reports and one USSD report "
    "were sent from field numbers.")
r.table("Real-time events observed", ["Event", "Result"],
        [["Farmland encroachment alerts", "3 (Lafia twice, Guma once), each sent within the same request"],
         ["Stock route deviation alerts", "5 (deviations of 15.3 to 30.0 km)"],
         ["SMS reports accepted", "6 of 6 in the first run. In a later run the sixth was blocked by the "
          "per-number hourly limit, as designed"],
         ["USSD report", "Accepted through a 3-step menu ('END Report #... received')"],
         ["Guma LGA risk", "Rose from High 54.9 to Severe 82.9 at the next scoring cycle (under 30 s)"],
         ["Mediation cases", "Opened automatically for cattle rustling and the armed attack report"],
         ["Recipients per LGA alert", "4 LGA contacts plus the State Emergency Operations Centre, in "
          "English, Hausa or Pidgin"]],
        widths=[5, 11])

r.h2("4.4 Security Testing")
r.table("Security test cases",
        ["#", "Test", "Expected", "Observed", "Status"],
        [["1", "GPS ping without a valid signature", "Rejected", "HTTP 401", "Pass"],
         ["2", "Open the map without logging in", "Redirect to login", "HTTP 302", "Pass"],
         ["3", "Public form submitted with the honeypot field filled", "Rejected", "HTTP 400", "Pass"],
         ["4", "Responder opens the analyst incident page", "Forbidden", "HTTP 403", "Pass"],
         ["5", "Reporter phone stored in database", "Ciphertext only", "Fernet token 'gAAAAA...'", "Pass"],
         ["6", "Admin reveals reporter number", "Shown and logged", "Number shown, audit entry written", "Pass"],
         ["7", "Malformed SMS", "Help text, no record", "Format instructions returned", "Pass"],
         ["8", "Audit chain after all tests", "Intact", "Intact", "Pass"]],
        widths=[0.7, 6, 3, 4.6, 1.3])

r.h2("4.5 Discussion")
r.p("The prototype meets its objectives. The geofence gave warnings at the moment cattle entered farmland, "
    "which is earlier than any report a farmer could send after the damage. The hybrid score ranked LGAs with "
    "both structural risk and live pressure at the top, and the dashboard showed the drivers, which supports "
    "the transparency that Rød et al. (2023) found lacking. The security controls answer a risk that general "
    "conflict tools often ignore: the informant. Encrypting phone numbers and logging every reveal means a "
    "stolen database does not become a target list.")
r.p("The main limitations are synthetic training data, approximate geography, and the need for herders to "
    "accept tracking. Tracking must be voluntary and should bring benefits to herders too, such as route "
    "information, water point status and protection from false accusations. The system must also avoid "
    "stigmatising any ethnic group, so reports describe events, never identities, and verification is "
    "required before escalation.")
r.page_break()

# ------------------------------------------------------------ chapter 5
r.h1("CHAPTER FIVE: SUMMARY, CONCLUSION AND RECOMMENDATIONS")
r.h2("5.1 Summary")
r.p("AgroPeace is a GIS-based early warning and response framework for farmer-herder conflict. It maps farms, "
    "routes and reserves, gathers reports from any phone, tracks herds with signed GPS pings, scores risk per "
    "LGA with an explainable hybrid model, alerts local stakeholders in their languages, and tracks mediation "
    "cases. It protects informants with encryption and pseudonyms and records all sensitive actions in a "
    "tamper-evident log.")
r.h2("5.2 Conclusion")
r.p("Early warning fails when it is late, unexplained or disconnected from response. Joining geospatial data, "
    "mobile reporting, vegetation monitoring and a mediation workflow in one secure system addresses all three "
    "failures. The prototype shows that this is possible with free software and modest hardware, and that "
    "security engineering is essential when the data concerns people in conflict zones.")
r.h2("5.3 Recommendations")
r.bullets([
    "Pilot the system in two neighbouring LGAs, for example Guma (Benue) and Keana (Nasarawa), with the state "
    "emergency management agencies.",
    "Map farmland and stock routes with farmers' and herders' associations together, so both groups trust the "
    "map.",
    "Retrain the model on ACLED data and MODIS NDVI each quarter and publish its performance.",
    "Set up a short code with a Nigerian SMS provider and publicise the USSD menu through community radio in "
    "Hausa, Tiv, Fulfulde and English.",
    "Adopt a data protection policy under the NDPA 2023: data minimisation, 12-month retention for raw reports, "
    "and two-person approval for revealing an informant.",
    "Fund the rehabilitation of grazing reserves and water points flagged on the map, as Usman et al. (2024) "
    "and Nnam (2025) recommend.",
])
r.h2("5.4 Contribution to Knowledge")
r.bullets([
    "An integrated design that links GIS, field reporting, herd geofencing, explainable risk scoring and "
    "mediation tracking for Nigeria.",
    "A security model for conflict early warning that protects informants by design.",
    "An open, reproducible evaluation pipeline with a time-based split and a naive baseline.",
])
r.h2("5.5 Suggestions for Further Work")
r.bullets([
    "Natural language processing of SMS text in Hausa and Pidgin to classify reports automatically.",
    "Sentinel-2 crop maps to replace hand-drawn farmland.",
    "A spatiotemporal Hawkes model following Browning et al. (2024).",
    "An offline Android app that queues reports when there is no network.",
])
r.page_break()

r.h1("REFERENCES")
r.references([
    "Abdullahi, A. (2025). Herders-crop farmers conflicts in Nigeria: Issues, challenges and prospects. *Journal of Innovative Social Science and Humanities Research*.",
    "Alemneh, A. S. (2025). Conflict early-warning system in the Hammer, Nyangatom, and Dassanech pastoralist and agro-pastoralist community of South Omo Zone, Ethiopia. *Kashf Journal of Multidisciplinary Research*.",
    "Antaya, A., et al. (2025). Challenges and opportunities to leverage virtual fence data for rangeland management. *Rangelands*.",
    "Aquilani, C., et al. (2021). Review: Precision livestock farming technologies in pasture-based livestock systems. *Animal*.",
    "Babatunde, A., et al. (2024). The dynamics of herder-farmer conflicts in Plateau State, Nigeria, and Central Darfur State, Sudan. *African Studies Review*.",
    "Bailey, D., et al. (2021). Opportunities to apply precision livestock management on rangelands. *Frontiers in Sustainable Food Systems*.",
    "Benjamin, E. O. (2026). Climate change, resource scarcity, and cross-border conflict: The international dimensions of farmer-herder violence in West Africa. *INOSR Arts and Management*.",
    "Brennan, J., et al. (2021). Classifying season long livestock grazing behavior with the use of a low-cost GPS and accelerometer. *Computers and Electronics in Agriculture*.",
    "Browning, R., et al. (2024). Bayesian spatiotemporal modelling of political violence and conflict events using discrete-time Hawkes processes. *Journal of the Royal Statistical Society Series A: Statistics in Society*.",
    "Cicek, D., et al. (2023). Use of mobile crowdsensing in disaster management: A systematic review, challenges, and open issues. *Sensors*.",
    "Currin, A., et al. (2022). A smart city qualitative data analysis model: Participatory crowdsourcing of public safety reports in South Africa. *The Electronic Journal of Information Systems in Developing Countries*.",
    "Derbyshire, S., et al. (2024). Uncertainty, pastoral knowledge and early warning: A review of drought management in the drylands, with insights from northern Kenya. *Pastoralism: Research, Policy and Practice*.",
    "Eboreime, E., et al. (2025). From drought to displacement: Assessing the impacts of climate change on conflict and forced migration in West Africa's Sahel region. *The Journal of Climate Change and Health*.",
    "Eke, O. G., et al. (2025). Climate-driven conflicts in Nigeria: Farmers' strategies for coping with herders' incursion on crop lands. *Sustainability*.",
    "Estefania-Salazar, E., et al. (2025). Assessing vegetation phenology dynamics in West African rangelands: Implications for livestock sustainability and transhumance. *Ecological Informatics*.",
    "Garba, M., et al. (2025). Causes of farmer-herder conflict in Taraba State, Nigeria. *Journal of Agricultural Extension*.",
    "Goodman, S., et al. (2024). Spatiotemporal prediction of conflict fatality risk using convolutional neural networks and satellite imagery. *Remote Sensing*.",
    "K S, et al. (2024). Integration of IoT for precision livestock monitoring through geofencing. *2024 5th International Conference on Electronics and Sustainable Communication Systems (ICESC)*. IEEE.",
    "Kamau, C. W., et al. (2022). Early warning system and preventive diplomacy in land-based conflicts among pastoralist communities in Samburu County. *International Journal of Professional Practice*.",
    "Lamidi, K. (2025). Farmers-herders' conflict in Nigeria: Causes, consequences and resolution mechanisms. *Journal of Cultural Analysis and Social Change*.",
    "Lenshie, N. E., et al. (2022). Geopolitics of climate change-induced conflict and population displacement in West Africa. *Local Environment*.",
    "Lynam, T., et al. (2023). Early warning and predictive analytic systems in conflict contexts: Insights from the field. *Civil Wars*.",
    "McGuirk, E., & Nunn, N. (2024). Transhumant pastoralism, climate change, and conflict in Africa. *SSRN Electronic Journal* (working paper).",
    "Mirau, S. (2022). Human-wildlife conflict early warning system using the Internet of Things and short message service. *Engineering, Technology & Applied Science Research*.",
    "Navarro, R., et al. (2025). Pastoral conflict on the greener grass? Exploring the climate-conflict nexus in the Karamoja Cluster. *International Journal of Disaster Risk Reduction*.",
    "Nnaji, A., et al. (2022). Farmer-herder conflicts and food insecurity: Evidence from rural Nigeria. *Agricultural and Resource Economics Review*.",
    "Nnam, M. U. (2025). Violent herder-farmer conflicts and human security in Nigeria: A focus on food security. *Development in Practice*.",
    "Nwankwo, C. F. (2025). Perceptions of injustices in the struggle for scarce critical lands: Farmer-herder conflict and violence escalation in the Benue-Nasarawa borderland. *World Development*.",
    "Oghuvbu, E. A., et al. (2021). Farmer-herders conflict as a challenge to national unity in Nigeria. *Africa and the Formation of the New System of International Relations*.",
    "Olaide, O. B., et al. (2021). A model for conflicts' prediction using deep neural network. *International Journal of Computer Applications*.",
    "Olayinka, T., et al. (2024). Patterns of terror: A comparative predictive model. *2024 IEEE 5th International Conference on Electro-Computing Technologies for Humanity (NIGERCON)*. IEEE.",
    "Parlato, M., et al. (2024). GIS-based methodology for tracking the grazing cattle site use. *Heliyon*.",
    "Rochana, E., et al. (2024). The urgency of an early warning system for social conflict by using WhatsApp. *International Journal of Innovative Research and Scientific Studies*.",
    "Rød, E., et al. (2023). A review and comparison of conflict early warning systems. *International Journal of Forecasting*.",
    "Schwarz, M., et al. (2022). Assessing the environmental suitability for transhumance in support of conflict prevention in the Sahel. *Remote Sensing*.",
    "Shimizu, K., et al. (2025). Piloting a mobile early warning alert and response system for East and Central Darfur, Sudan. *International Health*.",
    "Sola, L., et al. (2025). Quantifying the risk of pastoral conflict in 4 central African countries. *EPJ Data Science*.",
    "Tarif, K. (2022). *Climate change and violent conflict in West Africa: Assessing the evidence* (SIPRI Insights on Peace and Security). Stockholm International Peace Research Institute.",
    "Tewo, S., et al. (2025). Evaluation of the implementation of the EWARS Mobile epidemiological surveillance tool in Sudanese refugee camps in Eastern Chad. *Frontiers in Epidemiology*.",
    "Usman, S., et al. (2024). Identification and mapping of Fadama resources exposed to pastoralist-farmer conflicts in Nafada town, Gombe State, Nigeria. *Zbornik radova Departmana za geografiju, turizam i hotelijerstvo*.",
    "Wätzold, F., et al. (2024). Harnessing virtual fencing for more effective and adaptive agri-environment schemes to conserve grassland biodiversity. *Biological Conservation*.",
])
r.h2("Standards and Legal Instruments Consulted")
r.references([
    "Federal Republic of Nigeria. (2023). *Nigeria Data Protection Act, 2023*. Nigeria Data Protection Commission.",
    "International Organization for Standardization. (2022). *ISO/IEC 27001:2022 Information security, cybersecurity and privacy protection: Information security management systems: Requirements*. ISO.",
])
r.page_break()

r.h1("APPENDIX A: SOURCE CODE STRUCTURE")
r.table("AgroPeace source files", ["File", "Purpose"],
        [["core.py", "Database, encryption, pseudonyms, geometry, features, risk engine, alerts, geofence"],
         ["geodata.py", "LGAs, generated farmland, grazing reserves, water points and stock route"],
         ["manage.py", "Key generation, initialisation, synthetic history, ACLED import, training, risk ranking"],
         ["app.py", "Flask web app, SMS, USSD and GPS endpoints, case management, scheduler"],
         ["simulate.py", "Live demo: moving herds, SMS and USSD reports"],
         ["templates/", "Map dashboard, report form, incidents, cases, audit pages"]],
        widths=[3.5, 12.5])
r.p("The full source code and the step-by-step implementation guide are in the project folder "
    "project2-agropeace (README.md).")

r.save(OUT)
print("wrote", OUT)
