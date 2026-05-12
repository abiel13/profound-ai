from datetime import datetime, timezone, timedelta
import uuid

DEFAULT_ORG_PROFILE = {
    "id": "org-1",
    "name": "Pro Youth Foundation",
    "country": "Namibia",
    "mission": "Pro Youth Foundation is dedicated to protecting, rescuing, and uplifting vulnerable children and mothers living in abusive, unsafe, and poverty-stricken environments. The organization removes individuals from harmful conditions and provides safe housing, education support, food assistance, clothing, and long-term support to help them rebuild their lives with dignity and stability.",
    "focus_sectors": '["Child Protection & Safe Housing", "Street Children Support & Reintegration", "Education Access", "Food Security", "Clothing Support", "Women & Mother Support", "Community Outreach"]',
    "beneficiaries": '["Vulnerable Children", "Street Children", "Orphaned Children", "Abused Women & Mothers", "Low-Income Households", "Individuals in Unsafe Conditions"]',
    "funding_needs_min": 5000,
    "funding_needs_max": 500000,
    "updated_at": datetime.now(timezone.utc).isoformat()
}

ORG_KNOWLEDGE_BASE = """
ORGANIZATION: Pro Youth Foundation
TYPE: Non-Profit Organization / Foundation
COUNTRY: Namibia

MISSION:
Pro Youth Foundation is dedicated to protecting, rescuing, and uplifting vulnerable children and mothers living in abusive, unsafe, and poverty-stricken environments. The organization removes individuals from harmful conditions and provides safe housing, education support, food assistance, clothing, and long-term support to help them rebuild their lives with dignity and stability.

CORE OBJECTIVES:
1. Rescue children and mothers from abusive and unsafe environments
2. Support street children and orphaned children living without parental care
3. Provide safe housing through hostels and affordable housing projects
4. Ensure access to education by paying school fees
5. Provide food and clothing support to vulnerable individuals
6. Restore dignity, safety, and long-term stability

PROGRAM AREAS:
1. SAFE HOUSING & SHELTER - Development of hostels for vulnerable children and mothers, affordable housing units for long-term stability, emergency shelter for those escaping abuse, safe living environments for recovery
2. STREET CHILDREN SUPPORT & REINTEGRATION - Identification of street children and orphaned children, removal from street environments, placement into safe shelters and hostels, reintegration into education, long-term support and social reintegration
3. EDUCATION SUPPORT - Payment of school fees, support for school attendance, prevention of school dropout, long-term educational development
4. FOOD SUPPORT - Monthly food hamper distribution, support for vulnerable households, reduction of hunger and poverty
5. CLOTHING SUPPORT - Provision of clothes to children and mothers, emergency clothing support, restoring dignity and wellbeing
6. PROTECTION & INTERVENTION - Identification of abuse cases, immediate rescue and relocation, safe placement into secure environments
7. COMMUNITY OUTREACH - Identification of vulnerable families, direct assistance programs, community support initiatives

TARGET BENEFICIARIES:
- Vulnerable children
- Street children
- Orphaned children
- Abused women and mothers
- Low-income households
- Individuals living in unsafe conditions

GEOGRAPHIC FOCUS: Namibia (with potential expansion into Southern Africa)

IMPACT STATEMENT:
Pro Youth Foundation transforms lives by moving children and mothers from abusive environments, street conditions, and extreme poverty into safe housing where they receive education, food, clothing, and long-term support. The organization creates a pathway from survival to stability, restoring dignity and hope.

KEY FUNDING PRIORITIES:
- Hostel construction
- Affordable housing development
- Street children rehabilitation programs
- School fee support
- Monthly food distribution programs
- Clothing support initiatives
- Emergency shelter services

MEASURABLE OUTCOMES:
- Number of children housed in safe hostels
- Number of street children removed and reintegrated
- Number of school fees paid for vulnerable children
- Number of families receiving monthly food hampers
- Number of individuals supported with clothing
- Number of mothers and children provided emergency shelter

OFFICIAL CONTACT:
Mr J Izaaks, Executive Director
Pro Youth Foundation
Email: pro-youth@africaonline.com.na
Tel: +264813243230
Website: https://proyouthfoundation.netlify.app

SIGNATURE FORMAT (use in all correspondence):
Kind regards,
Mr J Izaaks
Executive Director
Pro Youth Foundation
Email: pro-youth@africaonline.com.na
Tel: +264813243230
Website: https://proyouthfoundation.netlify.app

AI WRITING RULES:
- ALL proposals MUST include: safe housing, street children support, education (school fees), food (monthly hampers), clothing, protection from abuse
- Emphasize transition: unsafe/street life -> safe living, dignity, stability
- Connect every funding request to measurable outcomes (children housed, street children removed, fees paid, families fed)
- Include website reference: "More information about our work can be found at https://proyouthfoundation.netlify.app"
- ALL emails, letters, and proposals MUST end with the official signature block above
- Writing style: clear, strong, impact-driven. No generic NGO language. Focus on real-life transformation.
"""

DEFAULT_SOURCES = [
    {"id": str(uuid.uuid4()), "name": "UNICEF Funding", "url": "https://www.unicef.org/partnerships/funding", "type": "UN Agency", "description": "UNICEF innovation and programme funding for children and youth worldwide."},
    {"id": str(uuid.uuid4()), "name": "UNDP Funding Windows", "url": "https://www.undp.org/funding", "type": "UN Agency", "description": "UNDP development funding for sustainable development goals."},
    {"id": str(uuid.uuid4()), "name": "USAID Grants", "url": "https://www.usaid.gov/work-usaid/get-grant-or-contract", "type": "Government", "description": "US Agency for International Development funding opportunities."},
    {"id": str(uuid.uuid4()), "name": "EU International Partnerships", "url": "https://international-partnerships.ec.europa.eu/funding-and-technical-assistance_en", "type": "Government", "description": "European Union funding for international cooperation and development."},
    {"id": str(uuid.uuid4()), "name": "UK FCDO Funding", "url": "https://www.gov.uk/government/organisations/foreign-commonwealth-development-office", "type": "Government", "description": "UK Foreign, Commonwealth & Development Office funding programmes."},
    {"id": str(uuid.uuid4()), "name": "Global Fund", "url": "https://www.theglobalfund.org/en/funding-model/", "type": "International NGO", "description": "Global Fund for AIDS, TB, and Malaria community health grants."},
    {"id": str(uuid.uuid4()), "name": "Bill & Melinda Gates Foundation", "url": "https://www.gatesfoundation.org/about/how-we-work/grants", "type": "Foundation", "description": "Gates Foundation grants for global health, education, and poverty."},
    {"id": str(uuid.uuid4()), "name": "Ford Foundation", "url": "https://www.fordfoundation.org/work/our-grants/", "type": "Foundation", "description": "Ford Foundation grants for reducing inequality worldwide."},
    {"id": str(uuid.uuid4()), "name": "Mastercard Foundation", "url": "https://mastercardfdn.org/", "type": "Foundation", "description": "Mastercard Foundation Young Africa Works programme."},
    {"id": str(uuid.uuid4()), "name": "Open Society Foundations", "url": "https://www.opensocietyfoundations.org/grants", "type": "Foundation", "description": "Open Society grants for justice, democracy, and human rights."},
]

now = datetime.now(timezone.utc)

DEMO_OPPORTUNITIES = [
    {
        "id": str(uuid.uuid4()),
        "title": "Youth Innovation and Entrepreneurship Fund 2025",
        "donor_name": "UNICEF Innovation",
        "donor_type": "UN Agency",
        "donor_country": "Global",
        "region": "Global / Africa Eligible",
        "description": "UNICEF Innovation Fund invests in open-source technology solutions that have the potential to benefit children and young people globally. The fund supports early-stage, open-source technology solutions developed by companies in UNICEF programme countries. Focus areas include learning and education, youth engagement, and workforce development. Applicants must demonstrate how their solution addresses challenges faced by youth in developing countries.",
        "eligibility": "Registered organizations in UNICEF programme countries. Must focus on youth-centered solutions. Open to NGOs, social enterprises, and community-based organizations in Africa, Asia, and Latin America. Projects must be scalable and demonstrate measurable impact on youth outcomes.",
        "funding_min": 50000,
        "funding_max": 100000,
        "deadline": (now + timedelta(days=45)).strftime("%Y-%m-%d"),
        "sector": "Youth Development",
        "url": "https://www.unicef.org/innovation/venturefund",
        "africa_eligible": 1,
        "ai_summary": "",
        "ai_match_score": 0,
        "ai_fit_explanation": "",
        "created_at": (now - timedelta(days=5)).isoformat()
    },
    {
        "id": str(uuid.uuid4()),
        "title": "Sustainable Development Accelerator Programme",
        "donor_name": "UNDP",
        "donor_type": "UN Agency",
        "donor_country": "Global",
        "region": "Africa / Developing Countries",
        "description": "The UNDP Accelerator Labs programme supports community-level innovations that address sustainable development challenges. This grant cycle focuses on grassroots organizations working in education, livelihoods, and community resilience. Emphasis is placed on solutions that can be adapted across multiple African contexts and demonstrate alignment with SDG targets 1, 4, 8, and 10.",
        "eligibility": "NGOs and CBOs registered in Sub-Saharan Africa. Must have at least 2 years of operational history. Priority given to organizations serving rural and underserved communities. Must align with at least two SDG targets.",
        "funding_min": 100000,
        "funding_max": 500000,
        "deadline": (now + timedelta(days=60)).strftime("%Y-%m-%d"),
        "sector": "Community Development",
        "url": "https://www.undp.org/acceleratorlabs",
        "africa_eligible": 1,
        "ai_summary": "",
        "ai_match_score": 0,
        "ai_fit_explanation": "",
        "created_at": (now - timedelta(days=3)).isoformat()
    },
    {
        "id": str(uuid.uuid4()),
        "title": "Africa Youth Employment and Skills Initiative",
        "donor_name": "USAID",
        "donor_type": "Government",
        "donor_country": "United States",
        "region": "Sub-Saharan Africa",
        "description": "USAID's workforce development initiative targets youth unemployment across Sub-Saharan Africa. This programme funds organizations that deliver vocational training, entrepreneurship support, digital skills development, and job placement services for young people aged 15-35. Special consideration for projects that address gender gaps in employment and include rural youth populations.",
        "eligibility": "Registered NGOs and training institutions in Sub-Saharan African countries. Must have demonstrated experience in youth employment or skills training programmes. Partnerships with private sector employers are strongly encouraged.",
        "funding_min": 250000,
        "funding_max": 1000000,
        "deadline": (now + timedelta(days=30)).strftime("%Y-%m-%d"),
        "sector": "Skills Development",
        "url": "https://www.usaid.gov/africa/youth",
        "africa_eligible": 1,
        "ai_summary": "",
        "ai_match_score": 0,
        "ai_fit_explanation": "",
        "created_at": (now - timedelta(days=7)).isoformat()
    },
    {
        "id": str(uuid.uuid4()),
        "title": "Civil Society Organisations and Local Authorities Programme",
        "donor_name": "European Commission",
        "donor_type": "Government",
        "donor_country": "European Union",
        "region": "Africa, Caribbean, Pacific",
        "description": "The EU CSO-LA programme strengthens civil society organisations in partner countries, particularly in Africa. Funding supports capacity building, advocacy, community engagement, and service delivery by local NGOs. The programme emphasizes democratic governance, human rights, and inclusive development. Projects should strengthen the role of civil society in policy dialogue and public service delivery.",
        "eligibility": "Civil society organizations registered in ACP countries. Must demonstrate governance capacity and community reach. Consortium applications with at least one EU-based CSO partner are encouraged. Minimum 3 years of organizational track record.",
        "funding_min": 100000,
        "funding_max": 300000,
        "deadline": (now + timedelta(days=75)).strftime("%Y-%m-%d"),
        "sector": "Community Development",
        "url": "https://international-partnerships.ec.europa.eu",
        "africa_eligible": 1,
        "ai_summary": "",
        "ai_match_score": 0,
        "ai_fit_explanation": "",
        "created_at": (now - timedelta(days=2)).isoformat()
    },
    {
        "id": str(uuid.uuid4()),
        "title": "Education Access and Quality Improvement Grant",
        "donor_name": "Bill & Melinda Gates Foundation",
        "donor_type": "Foundation",
        "donor_country": "United States",
        "region": "Global / Africa Priority",
        "description": "The Gates Foundation Education programme funds innovative approaches to improving educational access and learning outcomes in low-income countries, with emphasis on Sub-Saharan Africa and South Asia. Priority areas include early childhood education, literacy programmes, STEM education, teacher training, and technology-enabled learning solutions for out-of-school children and youth.",
        "eligibility": "International and local NGOs with proven education programme track records. Must operate in Gates Foundation priority countries in Africa. Evidence-based approaches with clear measurement frameworks required. Co-funding or partnership with local government education departments preferred.",
        "funding_min": 200000,
        "funding_max": 2000000,
        "deadline": (now + timedelta(days=90)).strftime("%Y-%m-%d"),
        "sector": "Education",
        "url": "https://www.gatesfoundation.org/about/how-we-work/grants",
        "africa_eligible": 1,
        "ai_summary": "",
        "ai_match_score": 0,
        "ai_fit_explanation": "",
        "created_at": (now - timedelta(days=10)).isoformat()
    },
    {
        "id": str(uuid.uuid4()),
        "title": "Reducing Inequality Through Community Action",
        "donor_name": "Ford Foundation",
        "donor_type": "Foundation",
        "donor_country": "United States",
        "region": "Global / Southern Africa",
        "description": "Ford Foundation's inequality reduction programme supports organizations working to challenge structural inequality and promote inclusive economic opportunity in the Global South. Grants support community organizing, policy advocacy, economic empowerment for marginalized groups, and strengthening of grassroots movements. Special focus on youth-led organizations addressing systemic barriers to opportunity.",
        "eligibility": "Registered NGOs in Southern and East Africa. Focus on community-driven approaches to inequality reduction. Youth-led organizations strongly encouraged. Must demonstrate connection to broader social justice movements.",
        "funding_min": 100000,
        "funding_max": 500000,
        "deadline": (now + timedelta(days=55)).strftime("%Y-%m-%d"),
        "sector": "Community Development",
        "url": "https://www.fordfoundation.org/work/our-grants/",
        "africa_eligible": 1,
        "ai_summary": "",
        "ai_match_score": 0,
        "ai_fit_explanation": "",
        "created_at": (now - timedelta(days=4)).isoformat()
    },
    {
        "id": str(uuid.uuid4()),
        "title": "Community Health Systems Strengthening Grant",
        "donor_name": "The Global Fund",
        "donor_type": "International NGO",
        "donor_country": "Switzerland",
        "region": "Sub-Saharan Africa",
        "description": "The Global Fund community health grant supports organizations strengthening health systems at the community level in Sub-Saharan Africa. Funding covers community health worker training, health education campaigns, disease prevention programmes, and building resilient community health infrastructure. Priority for projects addressing HIV/AIDS, TB, malaria, and maternal/child health.",
        "eligibility": "Health-focused NGOs and CBOs in Sub-Saharan African countries. Must have health programme implementation experience. Projects should integrate with national health strategies. Community engagement and participation must be central to the approach.",
        "funding_min": 500000,
        "funding_max": 5000000,
        "deadline": (now + timedelta(days=120)).strftime("%Y-%m-%d"),
        "sector": "Health",
        "url": "https://www.theglobalfund.org/en/funding-model/",
        "africa_eligible": 1,
        "ai_summary": "",
        "ai_match_score": 0,
        "ai_fit_explanation": "",
        "created_at": (now - timedelta(days=15)).isoformat()
    },
    {
        "id": str(uuid.uuid4()),
        "title": "Africa Skills and Employability Programme",
        "donor_name": "UK FCDO",
        "donor_type": "Government",
        "donor_country": "United Kingdom",
        "region": "Sub-Saharan Africa",
        "description": "The UK Foreign, Commonwealth & Development Office funds skills development and employability programmes across Africa. This grant supports vocational training, apprenticeship schemes, digital literacy programmes, and entrepreneurship development for youth. Focus on Southern and East African countries with high youth unemployment rates. Projects must demonstrate pathways from training to sustainable employment.",
        "eligibility": "NGOs registered in eligible African countries. Must have experience in skills training or workforce development. Collaboration with UK-based development organizations or private sector partners valued. Gender-inclusive approaches required.",
        "funding_min": 150000,
        "funding_max": 750000,
        "deadline": (now + timedelta(days=40)).strftime("%Y-%m-%d"),
        "sector": "Skills Development",
        "url": "https://www.gov.uk/government/organisations/foreign-commonwealth-development-office",
        "africa_eligible": 1,
        "ai_summary": "",
        "ai_match_score": 0,
        "ai_fit_explanation": "",
        "created_at": (now - timedelta(days=6)).isoformat()
    },
    {
        "id": str(uuid.uuid4()),
        "title": "Social Protection and Safety Nets Programme",
        "donor_name": "World Bank",
        "donor_type": "International Organization",
        "donor_country": "Global",
        "region": "Developing Countries / Africa Priority",
        "description": "The World Bank Social Protection programme funds initiatives that build and strengthen social safety nets in developing countries. Grants support cash transfer programmes, social insurance schemes, labor market interventions, and community-based social protection for vulnerable populations. Priority for innovative approaches that leverage technology and community networks.",
        "eligibility": "Government agencies and large international NGOs. Must operate in IDA-eligible countries. Projects require government endorsement or partnership. Minimum organizational budget of $500K annually. Implementation capacity for large-scale social protection programmes.",
        "funding_min": 500000,
        "funding_max": 3000000,
        "deadline": (now + timedelta(days=100)).strftime("%Y-%m-%d"),
        "sector": "Community Development",
        "url": "https://www.worldbank.org/en/topic/socialprotection",
        "africa_eligible": 1,
        "ai_summary": "",
        "ai_match_score": 0,
        "ai_fit_explanation": "",
        "created_at": (now - timedelta(days=20)).isoformat()
    },
    {
        "id": str(uuid.uuid4()),
        "title": "Young Africa Works - Skills to Employment",
        "donor_name": "Mastercard Foundation",
        "donor_type": "Foundation",
        "donor_country": "Canada",
        "region": "Sub-Saharan Africa",
        "description": "The Mastercard Foundation's Young Africa Works programme aims to enable 30 million young people in Africa to access dignified and fulfilling work by 2030. This grant supports organizations delivering market-relevant skills training, digital skills, financial literacy, and entrepreneurship support. Strong emphasis on reaching young women and youth in rural areas.",
        "eligibility": "African-registered NGOs, training institutions, and social enterprises. Must focus on youth (18-35) employment outcomes. Experience in skills development required. Must demonstrate ability to track employment outcomes post-training. Gender-disaggregated reporting required.",
        "funding_min": 200000,
        "funding_max": 1000000,
        "deadline": (now + timedelta(days=50)).strftime("%Y-%m-%d"),
        "sector": "Youth Development",
        "url": "https://mastercardfdn.org/young-africa-works/",
        "africa_eligible": 1,
        "ai_summary": "",
        "ai_match_score": 0,
        "ai_fit_explanation": "",
        "created_at": (now - timedelta(days=8)).isoformat()
    },
    {
        "id": str(uuid.uuid4()),
        "title": "Capacity Building for Civil Society Programme",
        "donor_name": "SIDA (Sweden)",
        "donor_type": "Government",
        "donor_country": "Sweden",
        "region": "Sub-Saharan Africa",
        "description": "The Swedish International Development Cooperation Agency supports organizational development and capacity building for African civil society. Grants fund governance strengthening, financial management training, monitoring and evaluation systems, strategic planning, and leadership development. Priority for grassroots organizations in Southern Africa and East Africa.",
        "eligibility": "Civil society organizations in Sub-Saharan Africa. Must have at least 2 years of operational history. Focus on organizational strengthening and institutional development. Smaller organizations (annual budget under $200K) prioritized.",
        "funding_min": 50000,
        "funding_max": 300000,
        "deadline": (now + timedelta(days=65)).strftime("%Y-%m-%d"),
        "sector": "Community Development",
        "url": "https://www.sida.se/en/",
        "africa_eligible": 1,
        "ai_summary": "",
        "ai_match_score": 0,
        "ai_fit_explanation": "",
        "created_at": (now - timedelta(days=1)).isoformat()
    },
    {
        "id": str(uuid.uuid4()),
        "title": "Skills for Youth Employment Programme",
        "donor_name": "GIZ (Germany)",
        "donor_type": "Government",
        "donor_country": "Germany",
        "region": "Sub-Saharan Africa",
        "description": "The German Agency for International Cooperation (GIZ) funds vocational training and skills development programmes for African youth. Focus areas include technical and vocational education, apprenticeships, green skills, and digital economy skills. Projects should demonstrate partnerships with local training institutions and private sector employers for job placement outcomes.",
        "eligibility": "NGOs and vocational training institutions in Southern, East, and West Africa. Must have documented experience in TVET or skills training. Partnership with German development organizations valued. Projects must include practical training components alongside classroom learning.",
        "funding_min": 100000,
        "funding_max": 500000,
        "deadline": (now + timedelta(days=35)).strftime("%Y-%m-%d"),
        "sector": "Skills Development",
        "url": "https://www.giz.de/en/html/index.html",
        "africa_eligible": 1,
        "ai_summary": "",
        "ai_match_score": 0,
        "ai_fit_explanation": "",
        "created_at": (now - timedelta(days=9)).isoformat()
    },
    {
        "id": str(uuid.uuid4()),
        "title": "Community Development and Resilience Fund",
        "donor_name": "Australian Aid (DFAT)",
        "donor_type": "Government",
        "donor_country": "Australia",
        "region": "Pacific, Africa, Southeast Asia",
        "description": "Australia's Department of Foreign Affairs and Trade supports community development and resilience-building projects in developing regions including select African countries. Funding covers community infrastructure, livelihood diversification, climate adaptation, disaster preparedness, and community governance. Focus on empowering marginalized communities and building local capacity.",
        "eligibility": "Registered NGOs in eligible developing countries. Australian NGO partnership required for African applicants. Must demonstrate community-centered approach. Projects should address climate vulnerability and community resilience.",
        "funding_min": 100000,
        "funding_max": 500000,
        "deadline": (now + timedelta(days=85)).strftime("%Y-%m-%d"),
        "sector": "Community Development",
        "url": "https://www.dfat.gov.au/development",
        "africa_eligible": 1,
        "ai_summary": "",
        "ai_match_score": 0,
        "ai_fit_explanation": "",
        "created_at": (now - timedelta(days=12)).isoformat()
    },
    {
        "id": str(uuid.uuid4()),
        "title": "Youth Empowerment and Participation Fund",
        "donor_name": "Norad (Norway)",
        "donor_type": "Government",
        "donor_country": "Norway",
        "region": "Africa / Developing Countries",
        "description": "The Norwegian Agency for Development Cooperation supports youth empowerment and civic participation in developing countries with emphasis on African nations. Grants fund youth leadership programmes, civic education, political participation support, youth-led community initiatives, and peer education networks. Strong focus on gender equality and inclusion of marginalized youth.",
        "eligibility": "Youth-serving and youth-led organizations in Sub-Saharan Africa. Partnership with Norwegian civil society organizations required. Focus on democratic participation and youth empowerment. Must include youth in project design and governance.",
        "funding_min": 75000,
        "funding_max": 400000,
        "deadline": (now + timedelta(days=70)).strftime("%Y-%m-%d"),
        "sector": "Youth Development",
        "url": "https://www.norad.no/en/front/",
        "africa_eligible": 1,
        "ai_summary": "",
        "ai_match_score": 0,
        "ai_fit_explanation": "",
        "created_at": (now - timedelta(days=11)).isoformat()
    },
    {
        "id": str(uuid.uuid4()),
        "title": "Education Quality and Access Programme",
        "donor_name": "Swiss Agency for Development (SDC)",
        "donor_type": "Government",
        "donor_country": "Switzerland",
        "region": "Africa / Southern Africa",
        "description": "The Swiss Development Cooperation funds education quality improvement and access expansion projects in Southern Africa. Grants support teacher professional development, curriculum innovation, school infrastructure, inclusive education, and non-formal education for out-of-school youth. Special focus on reaching marginalized populations in rural areas.",
        "eligibility": "Education-focused NGOs in Southern African countries. Must have at least 3 years of education programme experience. Partnership with local education authorities required. Must demonstrate measurable improvements in learning outcomes.",
        "funding_min": 100000,
        "funding_max": 500000,
        "deadline": (now + timedelta(days=80)).strftime("%Y-%m-%d"),
        "sector": "Education",
        "url": "https://www.eda.admin.ch/sdc",
        "africa_eligible": 1,
        "ai_summary": "",
        "ai_match_score": 0,
        "ai_fit_explanation": "",
        "created_at": (now - timedelta(days=14)).isoformat()
    },
    {
        "id": str(uuid.uuid4()),
        "title": "Civil Society Strengthening Fund",
        "donor_name": "DANIDA (Denmark)",
        "donor_type": "Government",
        "donor_country": "Denmark",
        "region": "Africa / East Africa Priority",
        "description": "Denmark's development cooperation agency funds civil society strengthening in Africa. This programme supports advocacy capacity, governance reform engagement, community mobilization, rights-based programming, and organizational sustainability. Priority for organizations working on democratic governance, transparency, and accountability at local and national levels.",
        "eligibility": "Civil society organizations in East and Southern Africa. Danish CSO partnership or endorsement required. Must demonstrate governance-focused programming. Organizational transparency and accountability records required.",
        "funding_min": 50000,
        "funding_max": 250000,
        "deadline": (now + timedelta(days=25)).strftime("%Y-%m-%d"),
        "sector": "Community Development",
        "url": "https://um.dk/en/danida",
        "africa_eligible": 1,
        "ai_summary": "",
        "ai_match_score": 0,
        "ai_fit_explanation": "",
        "created_at": (now - timedelta(days=3)).isoformat()
    },
    {
        "id": str(uuid.uuid4()),
        "title": "Community-Based Development and Livelihoods Programme",
        "donor_name": "JICA (Japan)",
        "donor_type": "Government",
        "donor_country": "Japan",
        "region": "Africa / Asia",
        "description": "The Japan International Cooperation Agency supports community development and livelihood improvement projects across Africa. Funding covers agricultural development, community enterprise support, infrastructure improvement, water and sanitation, and skills training for rural communities. JICA emphasizes self-reliance, local ownership, and sustainable development practices.",
        "eligibility": "NGOs and community organizations in Sub-Saharan Africa. Must demonstrate community-driven development approach. Japanese technical cooperation involvement valued. Projects should promote sustainable livelihoods and local economic development.",
        "funding_min": 200000,
        "funding_max": 1000000,
        "deadline": (now + timedelta(days=95)).strftime("%Y-%m-%d"),
        "sector": "Community Development",
        "url": "https://www.jica.go.jp/english/",
        "africa_eligible": 1,
        "ai_summary": "",
        "ai_match_score": 0,
        "ai_fit_explanation": "",
        "created_at": (now - timedelta(days=18)).isoformat()
    },
    {
        "id": str(uuid.uuid4()),
        "title": "Democracy and Human Rights Programme",
        "donor_name": "Open Society Foundations",
        "donor_type": "Foundation",
        "donor_country": "United States",
        "region": "Global / Africa",
        "description": "Open Society Foundations fund organizations advancing democracy, human rights, and justice worldwide. Grants support civic space protection, freedom of expression, rule of law, anti-corruption efforts, and community-based human rights monitoring. Priority for organizations working in challenging governance environments across Africa.",
        "eligibility": "Human rights and democracy-focused NGOs globally. Strong preference for organizations in Africa. Must demonstrate commitment to open society values. Innovative approaches to civic engagement valued. Both established and emerging organizations considered.",
        "funding_min": 100000,
        "funding_max": 500000,
        "deadline": (now + timedelta(days=110)).strftime("%Y-%m-%d"),
        "sector": "Community Development",
        "url": "https://www.opensocietyfoundations.org/grants",
        "africa_eligible": 1,
        "ai_summary": "",
        "ai_match_score": 0,
        "ai_fit_explanation": "",
        "created_at": (now - timedelta(days=22)).isoformat()
    },
    {
        "id": str(uuid.uuid4()),
        "title": "Digital Inclusion and Access Initiative",
        "donor_name": "Rockefeller Foundation",
        "donor_type": "Foundation",
        "donor_country": "United States",
        "region": "Africa / Developing Countries",
        "description": "The Rockefeller Foundation funds digital inclusion projects that bridge the digital divide in Africa and other developing regions. Grants support digital literacy programmes, community technology centres, internet access expansion, digital entrepreneurship, and technology-enabled service delivery. Focus on reaching underserved populations, particularly youth and women in rural areas.",
        "eligibility": "Technology-focused and development NGOs in Africa. Must have experience in digital inclusion or technology deployment. Innovative and scalable approaches prioritized. Partnerships with technology companies encouraged. Must include digital literacy training component.",
        "funding_min": 150000,
        "funding_max": 750000,
        "deadline": (now + timedelta(days=55)).strftime("%Y-%m-%d"),
        "sector": "Education",
        "url": "https://www.rockefellerfoundation.org/grants/",
        "africa_eligible": 1,
        "ai_summary": "",
        "ai_match_score": 0,
        "ai_fit_explanation": "",
        "created_at": (now - timedelta(days=13)).isoformat()
    },
    {
        "id": str(uuid.uuid4()),
        "title": "Erasmus+ International Youth Exchange and Capacity Building",
        "donor_name": "European Commission - Erasmus+",
        "donor_type": "Government",
        "donor_country": "European Union",
        "region": "Global / Africa Eligible",
        "description": "The EU Erasmus+ programme funds international youth exchanges and capacity building for youth organizations. Grants support youth mobility, intercultural learning, organizational development, youth worker training, and policy dialogue on youth issues. African organizations can participate as partners in projects led by EU-based organizations.",
        "eligibility": "Youth organizations worldwide. African organizations must partner with EU-based lead applicant. Focus on youth (13-30) development and exchange. Must align with EU Youth Strategy objectives. Prior international cooperation experience preferred but not required.",
        "funding_min": 50000,
        "funding_max": 200000,
        "deadline": (now + timedelta(days=42)).strftime("%Y-%m-%d"),
        "sector": "Youth Development",
        "url": "https://erasmus-plus.ec.europa.eu/",
        "africa_eligible": 1,
        "ai_summary": "",
        "ai_match_score": 0,
        "ai_fit_explanation": "",
        "created_at": (now - timedelta(days=6)).isoformat()
    }
]
