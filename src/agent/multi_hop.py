# ABOUTME: Multi-hop clinical reasoning for expanded code searches.
# ABOUTME: Maps conditions to related diagnoses, labs, and medications.

from typing import Any

import httpx

from src.agent.state import AgentState


# Clinical relationships for common conditions
# Each condition maps to related diagnoses, labs, and medications
CLINICAL_RELATIONSHIPS: dict[str, dict[str, list[str]]] = {
    # Metabolic conditions
    "diabetes": {
        "related_diagnoses": [
            "diabetic neuropathy",
            "diabetic retinopathy",
            "diabetic nephropathy",
            "diabetic foot",
            "hypoglycemia",
        ],
        "related_labs": [
            "hemoglobin A1c",
            "fasting glucose",
            "glucose tolerance test",
            "fructosamine",
            "C-peptide",
        ],
        "related_medications": [
            "metformin",
            "insulin",
            "glipizide",
            "sitagliptin",
            "empagliflozin",
        ],
    },
    "hyperlipidemia": {
        "related_diagnoses": ["atherosclerosis", "coronary artery disease", "xanthoma"],
        "related_labs": ["lipid panel", "LDL cholesterol", "HDL cholesterol", "triglycerides"],
        "related_medications": ["atorvastatin", "simvastatin", "rosuvastatin", "ezetimibe"],
    },
    "obesity": {
        "related_diagnoses": ["metabolic syndrome", "sleep apnea", "fatty liver"],
        "related_labs": ["fasting glucose", "lipid panel", "liver function tests"],
        "related_medications": ["orlistat", "liraglutide", "semaglutide"],
    },
    "thyroid": {
        "related_diagnoses": ["hypothyroidism", "hyperthyroidism", "thyroiditis", "goiter"],
        "related_labs": ["TSH", "free T4", "free T3", "thyroid antibodies"],
        "related_medications": ["levothyroxine", "methimazole", "propylthiouracil"],
    },
    # Cardiovascular conditions
    "hypertension": {
        "related_diagnoses": [
            "hypertensive heart disease",
            "hypertensive nephropathy",
            "left ventricular hypertrophy",
        ],
        "related_labs": [
            "basic metabolic panel",
            "lipid panel",
            "urinalysis",
            "creatinine",
        ],
        "related_medications": [
            "lisinopril",
            "amlodipine",
            "hydrochlorothiazide",
            "losartan",
            "metoprolol",
        ],
    },
    "heart failure": {
        "related_diagnoses": [
            "cardiomyopathy",
            "pulmonary edema",
            "cardiac arrhythmia",
        ],
        "related_labs": ["BNP", "NT-proBNP", "troponin", "basic metabolic panel"],
        "related_medications": [
            "furosemide",
            "carvedilol",
            "spironolactone",
            "sacubitril",
            "digoxin",
        ],
    },
    "atrial fibrillation": {
        "related_diagnoses": ["stroke", "heart failure", "thromboembolism"],
        "related_labs": ["INR", "PT", "complete blood count", "thyroid function"],
        "related_medications": ["warfarin", "apixaban", "rivaroxaban", "metoprolol", "diltiazem"],
    },
    "coronary artery disease": {
        "related_diagnoses": ["angina", "myocardial infarction", "heart failure"],
        "related_labs": ["troponin", "lipid panel", "BNP", "CRP"],
        "related_medications": ["aspirin", "clopidogrel", "atorvastatin", "metoprolol", "nitroglycerin"],
    },
    "deep vein thrombosis": {
        "related_diagnoses": ["pulmonary embolism", "post-thrombotic syndrome"],
        "related_labs": ["D-dimer", "PT", "INR", "factor V Leiden"],
        "related_medications": ["heparin", "enoxaparin", "warfarin", "rivaroxaban"],
    },
    # Respiratory conditions
    "asthma": {
        "related_diagnoses": ["allergic rhinitis", "eczema", "COPD"],
        "related_labs": ["IgE", "pulmonary function test", "peak flow"],
        "related_medications": [
            "albuterol",
            "fluticasone",
            "montelukast",
            "budesonide",
            "ipratropium",
        ],
    },
    "copd": {
        "related_diagnoses": ["chronic bronchitis", "emphysema", "pneumonia"],
        "related_labs": ["pulmonary function test", "arterial blood gas", "chest x-ray"],
        "related_medications": ["tiotropium", "fluticasone", "salmeterol", "prednisone", "azithromycin"],
    },
    "pneumonia": {
        "related_diagnoses": ["respiratory failure", "sepsis", "pleural effusion"],
        "related_labs": ["chest x-ray", "sputum culture", "complete blood count", "procalcitonin"],
        "related_medications": ["azithromycin", "amoxicillin", "levofloxacin", "ceftriaxone"],
    },
    # Gastrointestinal conditions
    "gerd": {
        "related_diagnoses": ["esophagitis", "Barrett's esophagus", "hiatal hernia"],
        "related_labs": ["upper endoscopy", "pH monitoring"],
        "related_medications": ["omeprazole", "pantoprazole", "famotidine", "sucralfate"],
    },
    "peptic ulcer": {
        "related_diagnoses": ["gastritis", "H. pylori infection", "GI bleeding"],
        "related_labs": ["H. pylori test", "hemoglobin", "stool guaiac"],
        "related_medications": ["omeprazole", "clarithromycin", "amoxicillin", "bismuth"],
    },
    "inflammatory bowel disease": {
        "related_diagnoses": ["Crohn's disease", "ulcerative colitis", "malnutrition"],
        "related_labs": ["CRP", "ESR", "fecal calprotectin", "colonoscopy"],
        "related_medications": ["mesalamine", "prednisone", "azathioprine", "infliximab"],
    },
    "cirrhosis": {
        "related_diagnoses": ["hepatic encephalopathy", "ascites", "esophageal varices"],
        "related_labs": ["liver function tests", "albumin", "INR", "ammonia"],
        "related_medications": ["lactulose", "spironolactone", "propranolol", "rifaximin"],
    },
    # Renal conditions
    "chronic kidney disease": {
        "related_diagnoses": ["anemia", "hyperkalemia", "metabolic acidosis"],
        "related_labs": ["creatinine", "BUN", "GFR", "urinalysis", "phosphorus"],
        "related_medications": ["lisinopril", "furosemide", "erythropoietin", "calcitriol"],
    },
    "nephrotic syndrome": {
        "related_diagnoses": ["edema", "hyperlipidemia", "thrombosis"],
        "related_labs": ["urinalysis", "24-hour urine protein", "albumin", "lipid panel"],
        "related_medications": ["prednisone", "lisinopril", "furosemide", "atorvastatin"],
    },
    "urinary tract infection": {
        "related_diagnoses": ["pyelonephritis", "cystitis", "sepsis"],
        "related_labs": ["urinalysis", "urine culture", "complete blood count"],
        "related_medications": ["ciprofloxacin", "nitrofurantoin", "trimethoprim", "cephalexin"],
    },
    # Neurological conditions
    "stroke": {
        "related_diagnoses": ["transient ischemic attack", "atrial fibrillation", "carotid stenosis"],
        "related_labs": ["CT scan", "MRI", "carotid ultrasound", "echocardiogram"],
        "related_medications": ["aspirin", "clopidogrel", "alteplase", "atorvastatin"],
    },
    "epilepsy": {
        "related_diagnoses": ["seizure disorder", "status epilepticus"],
        "related_labs": ["EEG", "MRI brain", "drug levels"],
        "related_medications": ["levetiracetam", "phenytoin", "valproic acid", "lamotrigine"],
    },
    "parkinson": {
        "related_diagnoses": ["tremor", "bradykinesia", "dementia"],
        "related_labs": ["DaTscan", "MRI brain"],
        "related_medications": ["levodopa", "carbidopa", "pramipexole", "rasagiline"],
    },
    "migraine": {
        "related_diagnoses": ["tension headache", "cluster headache", "aura"],
        "related_labs": ["MRI brain", "CT scan"],
        "related_medications": ["sumatriptan", "topiramate", "propranolol", "amitriptyline"],
    },
    "dementia": {
        "related_diagnoses": ["Alzheimer's disease", "vascular dementia", "Lewy body dementia"],
        "related_labs": ["cognitive testing", "MRI brain", "vitamin B12"],
        "related_medications": ["donepezil", "memantine", "rivastigmine", "galantamine"],
    },
    # Musculoskeletal conditions
    "osteoarthritis": {
        "related_diagnoses": ["joint pain", "joint stiffness", "bone spur"],
        "related_labs": ["X-ray", "MRI joint"],
        "related_medications": ["acetaminophen", "ibuprofen", "celecoxib", "duloxetine"],
    },
    "rheumatoid arthritis": {
        "related_diagnoses": ["joint swelling", "joint deformity", "rheumatoid nodule"],
        "related_labs": ["rheumatoid factor", "anti-CCP", "ESR", "CRP"],
        "related_medications": ["methotrexate", "hydroxychloroquine", "adalimumab", "prednisone"],
    },
    "osteoporosis": {
        "related_diagnoses": ["fracture", "kyphosis", "bone loss"],
        "related_labs": ["DEXA scan", "calcium", "vitamin D"],
        "related_medications": ["alendronate", "risedronate", "denosumab", "teriparatide"],
    },
    "gout": {
        "related_diagnoses": ["hyperuricemia", "tophus", "nephrolithiasis"],
        "related_labs": ["uric acid", "joint fluid analysis", "renal function"],
        "related_medications": ["colchicine", "allopurinol", "febuxostat", "indomethacin"],
    },
    "back pain": {
        "related_diagnoses": ["herniated disc", "spinal stenosis", "sciatica"],
        "related_labs": ["MRI spine", "X-ray spine"],
        "related_medications": ["ibuprofen", "cyclobenzaprine", "gabapentin", "lidocaine patch"],
    },
    # Infectious diseases
    "sepsis": {
        "related_diagnoses": ["septic shock", "bacteremia", "multi-organ failure"],
        "related_labs": ["blood culture", "lactate", "procalcitonin", "complete blood count"],
        "related_medications": ["vancomycin", "piperacillin-tazobactam", "ceftriaxone", "norepinephrine"],
    },
    "cellulitis": {
        "related_diagnoses": ["abscess", "lymphangitis", "necrotizing fasciitis"],
        "related_labs": ["complete blood count", "blood culture", "wound culture"],
        "related_medications": ["cephalexin", "clindamycin", "vancomycin", "doxycycline"],
    },
    "hepatitis": {
        "related_diagnoses": ["cirrhosis", "hepatocellular carcinoma", "liver failure"],
        "related_labs": ["hepatitis panel", "liver function tests", "viral load"],
        "related_medications": ["entecavir", "tenofovir", "sofosbuvir", "ledipasvir"],
    },
    "hiv": {
        "related_diagnoses": ["AIDS", "opportunistic infection", "Kaposi sarcoma"],
        "related_labs": ["CD4 count", "viral load", "HIV genotype"],
        "related_medications": ["emtricitabine", "tenofovir", "dolutegravir", "bictegravir"],
    },
    # Psychiatric conditions
    "depression": {
        "related_diagnoses": ["major depressive disorder", "dysthymia", "suicidal ideation"],
        "related_labs": ["thyroid function", "vitamin B12", "folate"],
        "related_medications": ["sertraline", "fluoxetine", "bupropion", "venlafaxine"],
    },
    "anxiety": {
        "related_diagnoses": ["generalized anxiety disorder", "panic disorder", "social anxiety"],
        "related_labs": ["thyroid function", "drug screen"],
        "related_medications": ["sertraline", "buspirone", "lorazepam", "gabapentin"],
    },
    "bipolar": {
        "related_diagnoses": ["mania", "hypomania", "psychosis"],
        "related_labs": ["lithium level", "thyroid function", "renal function"],
        "related_medications": ["lithium", "valproic acid", "lamotrigine", "quetiapine"],
    },
    "schizophrenia": {
        "related_diagnoses": ["psychosis", "hallucination", "delusion"],
        "related_labs": ["drug screen", "metabolic panel", "prolactin"],
        "related_medications": ["risperidone", "olanzapine", "aripiprazole", "clozapine"],
    },
    # Dermatological conditions
    "psoriasis": {
        "related_diagnoses": ["psoriatic arthritis", "plaque psoriasis"],
        "related_labs": ["skin biopsy", "rheumatoid factor"],
        "related_medications": ["methotrexate", "adalimumab", "ustekinumab", "apremilast"],
    },
    "eczema": {
        "related_diagnoses": ["atopic dermatitis", "contact dermatitis"],
        "related_labs": ["IgE", "allergy testing", "skin biopsy"],
        "related_medications": ["hydrocortisone", "tacrolimus", "dupilumab", "crisaborole"],
    },
    # Oncology conditions
    "breast cancer": {
        "related_diagnoses": ["ductal carcinoma", "lobular carcinoma", "metastasis"],
        "related_labs": ["mammogram", "biopsy", "ER/PR/HER2", "tumor markers"],
        "related_medications": ["tamoxifen", "anastrozole", "trastuzumab", "paclitaxel"],
    },
    "lung cancer": {
        "related_diagnoses": ["non-small cell lung cancer", "small cell lung cancer", "metastasis"],
        "related_labs": ["CT chest", "PET scan", "biopsy", "EGFR mutation"],
        "related_medications": ["cisplatin", "carboplatin", "pembrolizumab", "osimertinib"],
    },
    "colon cancer": {
        "related_diagnoses": ["colorectal cancer", "adenocarcinoma", "metastasis"],
        "related_labs": ["colonoscopy", "CEA", "CT scan", "biopsy"],
        "related_medications": ["fluorouracil", "oxaliplatin", "bevacizumab", "cetuximab"],
    },
    "prostate cancer": {
        "related_diagnoses": ["adenocarcinoma", "metastatic prostate cancer"],
        "related_labs": ["PSA", "prostate biopsy", "bone scan", "CT scan"],
        "related_medications": ["leuprolide", "enzalutamide", "abiraterone", "docetaxel"],
    },
    # Hematological conditions
    "anemia": {
        "related_diagnoses": ["iron deficiency anemia", "B12 deficiency", "hemolytic anemia"],
        "related_labs": ["complete blood count", "iron studies", "reticulocyte count", "vitamin B12"],
        "related_medications": ["ferrous sulfate", "cyanocobalamin", "epoetin alfa", "folic acid"],
    },
    "leukemia": {
        "related_diagnoses": ["acute lymphoblastic leukemia", "chronic myeloid leukemia"],
        "related_labs": ["complete blood count", "bone marrow biopsy", "flow cytometry"],
        "related_medications": ["imatinib", "dasatinib", "vincristine", "daunorubicin"],
    },
    # Endocrine conditions
    "cushing": {
        "related_diagnoses": ["Cushing syndrome", "adrenal adenoma", "pituitary adenoma"],
        "related_labs": ["cortisol", "ACTH", "dexamethasone suppression test"],
        "related_medications": ["ketoconazole", "metyrapone", "pasireotide"],
    },
    "addison": {
        "related_diagnoses": ["adrenal insufficiency", "hypocortisolism"],
        "related_labs": ["cortisol", "ACTH", "ACTH stimulation test"],
        "related_medications": ["hydrocortisone", "fludrocortisone", "prednisone"],
    },
    # Autoimmune conditions
    "lupus": {
        "related_diagnoses": ["systemic lupus erythematosus", "lupus nephritis", "antiphospholipid syndrome"],
        "related_labs": ["ANA", "anti-dsDNA", "complement levels", "urinalysis"],
        "related_medications": ["hydroxychloroquine", "prednisone", "mycophenolate", "belimumab"],
    },
    "multiple sclerosis": {
        "related_diagnoses": ["optic neuritis", "transverse myelitis", "demyelination"],
        "related_labs": ["MRI brain", "MRI spine", "lumbar puncture", "evoked potentials"],
        "related_medications": ["interferon beta", "glatiramer", "dimethyl fumarate", "ocrelizumab"],
    },
}


async def get_related_terms(
    query: str, selected_systems: list[str], max_terms: int = 5
) -> list[str]:
    """
    Get clinically related search terms based on the query and selected systems.

    Uses LLM-driven expansion when enabled, with static fallback.

    Args:
        query: Original search query
        selected_systems: List of coding systems being searched
        max_terms: Maximum number of additional terms to return

    Returns:
        List of related search terms
    """
    from src.services.expansion import get_expansion_service

    service = await get_expansion_service()
    expansion = await service.expand(query, selected_systems, max_per_category=max_terms)

    # Flatten all categories into a single list
    additional_terms: list[str] = []

    # Add terms based on selected systems
    if "ICD-10-CM" in selected_systems or "HPO" in selected_systems:
        additional_terms.extend(expansion.get("diagnoses", []))
    if "LOINC" in selected_systems or "UCUM" in selected_systems:
        additional_terms.extend(expansion.get("labs", []))
    if "RxTerms" in selected_systems:
        additional_terms.extend(expansion.get("medications", []))

    # Deduplicate and limit
    query_lower = query.lower()
    seen = set()
    unique_terms = []
    for term in additional_terms:
        if term.lower() not in seen and term.lower() != query_lower:
            seen.add(term.lower())
            unique_terms.append(term)

    return unique_terms[:max_terms]


def get_related_terms_sync(
    query: str, selected_systems: list[str], max_terms: int = 5
) -> list[str]:
    """
    Synchronous version using static fallback only.

    For backwards compatibility with non-async code.
    """
    query_lower = query.lower()
    additional_terms: list[str] = []

    for condition, relations in CLINICAL_RELATIONSHIPS.items():
        if condition in query_lower:
            if "ICD-10-CM" in selected_systems or "HPO" in selected_systems:
                additional_terms.extend(relations.get("related_diagnoses", []))
            if "LOINC" in selected_systems or "UCUM" in selected_systems:
                additional_terms.extend(relations.get("related_labs", []))
            if "RxTerms" in selected_systems:
                additional_terms.extend(relations.get("related_medications", []))

    # Deduplicate and limit
    seen = set()
    unique_terms = []
    for term in additional_terms:
        if term.lower() not in seen and term.lower() != query_lower:
            seen.add(term.lower())
            unique_terms.append(term)

    return unique_terms[:max_terms]


async def multi_hop_node(state: AgentState) -> dict[str, Any]:
    """
    LangGraph node: Expand search with clinically related terms.

    Only runs if multi_hop_enabled is True in state.

    Returns updates with additional search terms.
    """
    if not state.get("multi_hop_enabled", False):
        return {}

    query = state["query"]
    selected_systems = state.get("selected_systems", [])

    related_terms = await get_related_terms(query, selected_systems)

    if not related_terms:
        return {"reasoning_trace": ["Multi-hop: No clinical relationships found"]}

    return {
        "related_terms": related_terms,
        "search_terms": state.get("search_terms", []) + related_terms,
        "reasoning_trace": [f"Multi-hop: Added {len(related_terms)} related terms: {', '.join(related_terms[:3])}..."],
    }


async def fetch_hierarchy(code: str, system: str) -> dict[str, str]:
    """
    Fetch parent code information for a given code.

    Currently supports ICD-10-CM hierarchy based on code structure.

    Args:
        code: The code to look up
        system: The coding system

    Returns:
        Dict with parent_code and parent_display (if found)
    """
    if system != "ICD-10-CM":
        return {}

    # ICD-10 hierarchy is encoded in the code structure
    # E.g., E11.65 (diabetes with hyperglycemia) has parent E11 (type 2 diabetes)
    parts = code.split(".")
    if len(parts) != 2:
        return {}

    parent_code = parts[0]

    # Fetch parent info from API
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                "https://clinicaltables.nlm.nih.gov/api/icd10cm/v3/search",
                params={"terms": parent_code, "maxList": 1, "sf": "code,name"},
            )
            if resp.status_code != 200:
                return {}

            data = resp.json()
            # Response format: [total, codes, null, [[code, name], ...]]
            if data[3] and len(data[3]) > 0:
                result = data[3][0]
                if len(result) >= 2:
                    return {
                        "parent_code": result[0],
                        "parent_display": result[1],
                    }
    except Exception:
        pass

    return {}


async def fetch_hierarchies_for_results(
    results: list, max_codes: int = 10
) -> dict[str, dict]:
    """
    Fetch hierarchy info for top results.

    Args:
        results: List of CodeResult objects
        max_codes: Maximum number of codes to fetch hierarchy for

    Returns:
        Dict mapping code -> {parent_code, parent_display}
    """
    import asyncio

    hierarchies: dict[str, dict] = {}
    tasks = []

    for result in results[:max_codes]:
        if result.system == "ICD-10-CM":
            tasks.append((result.code, fetch_hierarchy(result.code, result.system)))

    if not tasks:
        return {}

    # Run fetches in parallel
    codes = [t[0] for t in tasks]
    coros = [t[1] for t in tasks]
    results_list = await asyncio.gather(*coros, return_exceptions=True)

    for code, result in zip(codes, results_list):
        if isinstance(result, dict) and result:
            hierarchies[code] = result

    return hierarchies
