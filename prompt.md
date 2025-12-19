# GPUsPerStudent.org - Data Research Prompt

You are an expert data researcher. Your task is to find **verifiable, auditable data** about GPU resources and CS student counts at universities. You should only include GPUs that are owned and operated by that university and generally accessible by the students (not via a grant and not accessible to other universities or research organizations).  

For the remainder of this prompt when you see: [University] that means: {{UNIVERSITY_NAME}}

---

## CRITICAL INSTRUCTIONS

1. **Search the web** for GPU cluster specifications and student enrollment data
2. **Calculate totals** from node specifications (e.g., "42 nodes × 8 H100 = 336 H100 total")
3. **Fill in ALL numeric fields** in the JSON - do not leave GPU counts as 0 if you found data
4. **Every data point MUST have a source URL** that contains that information

---

## WHAT TO SEARCH FOR

### GPU Resources (PRIORITY)
Search for these exact queries:
- "[University] research computing GPU cluster specifications"
- "[University] HPC H100 A100 nodes"
- "[University] AI computing cluster hardware"

Look for cluster pages that list:
- Number of GPU nodes
- GPUs per node
- GPU model (H100, H200, A100, V100, etc.)

**CALCULATE THE TOTAL**: nodes × GPUs_per_node = total_GPUs

### Student Data (CRITICAL - 0 IS NOT ACCEPTABLE)

**Every major university has CS students - 0 is NEVER a valid answer.**

Search for these queries IN ORDER until you find data:
1. "[University] CS department enrollment statistics"
2. "[University] computer science majors undergraduate PhD"
3. "[University] EECS enrollment by the numbers"
4. "[University] CS undergraduate enrollment 2024"
5. "[University] computer science graduate students"
6. "site:datausa.io [University] computer science"

If initial searches return nothing, try:
- Department "About" or "Facts" pages
- College of Engineering enrollment reports
- Graduate school enrollment statistics
- IPEDS/Common Data Set reports

**DO NOT return 0 for student counts.** If you truly cannot find exact numbers:
- Estimate from graduation rates (degrees awarded × years in program)
- Use department size statements ("over 2000 CS majors")
- Check datausa.io for completion data

---

## REQUIRED JSON OUTPUT

**YOU MUST FILL IN THE NUMERIC VALUES - NOT LEAVE THEM AS 0 IF YOU FOUND DATA**

HERE IS THE PERFECT EXAMPLE FOR STANFORD UNIVERSITY THAT YOU SHOULD EMULATE FOR THIS UNIVERSITY:
```json
{
  "university_name": "Stanford University",
  "data_retrieved_date": "2025-12-12",
  "sources": [
    {
      "url": "https://datascience.stanford.edu/marlowe",
      "data_found": "Marlowe: 31 NVIDIA H100 nodes; 248 NVIDIA H100 GPUs total; each DGX H100 node has 8x NVIDIA H100 80GB GPUs."
    },
    {
      "url": "https://legacy.cs.stanford.edu/haic",
      "data_found": "HAI Compute Cluster: begins Fall 2024; 5 systems and 40x Nvidia H100 GPUs with NVLink."
    },
    {
      "url": "https://cluster.cs.stanford.edu/tools/",
      "data_found": "SC Cluster (sphinx partition example): showalloc/sgpu output indicates 8 H100, 16 H200, 63 A100 GPUs (total 87). Node list shows 1 node with 8x H100; 2 nodes with 8x H200 each; 8 A100 nodes with 7\u20138 GPUs each totaling 63."
    },
    {
      "url": "https://www.sherlock.stanford.edu/docs/tech/facts/",
      "data_found": "Sherlock facts (as of December 2025): 2,057 compute nodes; 1,068 GPUs."
    },
    {
      "url": "https://news.sherlock.stanford.edu/publications/sherlock-4-0-a-new-cluster-generation",
      "data_found": "Sherlock 4.0 public additions: gpu partition includes 4x SH4_G4FP32 (4x L40S each), 2x SH4_G4TF64 (4x H100 SXM5 each), 1x SH4_G8TF64 (8x H100 SXM5); total 32 GPUs across 27 nodes."
    },
    {
      "url": "https://news.sherlock.stanford.edu/publications/introducing-sh4_g8tf64-1-now-with-8x-h200-gpus",
      "data_found": "Sherlock catalog node type SH4_G8TF64.1: 8x NVIDIA H200 GPUs (SXM5, 141GB). (Count of deployed nodes not stated.)"
    },
    {
      "url": "https://srcc.stanford.edu/sherlock-high-performance-computing-cluster",
      "data_found": "Sherlock (as of July 2019): 728 GPUs total (historical reference used for age-based estimation context)."
    }
  ],
  "student_data": {
    "undergrad_cs_count": 1168,
    "grad_cs_count": 651,
    "phd_cs_count": 275,
    "year": "2024-2025",
    "source_url": "https://stanford.edu/stats/",
    "notes": "Stanford CS does not appear to publish a single official 'CS enrollment by degree level' figure on cs.stanford.edu pages found via the requested queries, so counts are estimated from official Stanford-wide totals plus program-duration assumptions. Undergrad CS count estimated from: 1,828 bachelor degrees awarded in 2024 (Stanford Facts page) and Stanford Daily reporting ~16% of bachelor\u2019s degrees conferred were in CS; estimated CS degrees/year \u2248 0.16*1,828=292, then steady-state CS majors enrolled \u2248 292*4 years = 1,168. MS (grad) CS count estimated from: CS MS program averages 1.5 years to complete (Stanford CS MS overview) and a third-party IPEDS-derived 'Computer Science Master program completers' count of 434; estimated steady-state MS enrollment \u2248 434*1.5=651. PhD CS count estimated from NSF NCSES earned doctorates table for Stanford showing ~50 Computer Science PhDs in 2024; assuming typical 5.5-year time-to-degree gives in-residence PhD students \u2248 50*5.5=275."
  },
  "gpu_resources": {
    "h100_sxm_count": 360,
    "h100_pcie_count": 0,
    "h200_count": 32,
    "b100_count": 0,
    "b200_count": 0,
    "a100_80gb_count": 200,
    "a100_40gb_count": 463,
    "a40_count": 0,
    "a6000_count": 40,
    "l40s_count": 32,
    "v100_count": 200,
    "p100_count": 116,
    "gh200_count": 0,
    "other_high_vram_gpus": [
      {
        "model": "NVIDIA RTX 2080 Ti (11GB)",
        "estimated_total": null,
        "notes": "Appears in Sherlock 3.0 public GPU partition description; not included in totals above because schema has no dedicated field."
      },
      {
        "model": "NVIDIA A30 (24GB, via MIG)",
        "estimated_total": null,
        "notes": "Mentioned in Sherlock GPU docs examples (dev partition); not included in totals above because schema has no dedicated field."
      },
      {
        "model": "NVIDIA Tesla P40 (24GB)",
        "estimated_total": null,
        "notes": "Mentioned in Sherlock GPU docs/examples; not included in totals above because schema has no dedicated field."
      }
    ],
    "source_url": "https://datascience.stanford.edu/marlowe",
    "notes": "CLUSTERS INCLUDED + CALCULATIONS\n\n1) Marlowe (Stanford Data Science): 31 nodes \u00d7 8 H100/node = 248 H100 (counted as H100 SXM, since DGX H100). Source provides both 31 nodes and 8 GPUs/node.\n\n2) HAI Compute Cluster (Stanford CS): 5 systems \u00d7 (40 GPUs / 5 systems = 8 GPUs/system) = 40 H100 (counted as H100 SXM/HGX due to NVLink + typical 8-GPU HGX servers; exact form factor not explicitly stated).\n\n3) SC Cluster (Stanford CS) \u2013 sphinx partition: From showalloc listing:\n   - A100: sphinx1(8) + sphinx2(7) + sphinx3(8) + sphinx4(8) + sphinx5(8) + sphinx6(8) + sphinx7(8) + sphinx8(8) = 63 A100\n   - H100: sphinx9(8) = 8 H100\n   - H200: sphinx10(8) + sphinx11(8) = 16 H200\n   Total = 63 + 8 + 16 = 87 GPUs.\n   A100 VRAM split not stated; inferred as A100 40GB (not 80GB) based on the ~1TB system-memory class shown for the A100 nodes (typical of DGX A100 40GB configs).\n\n4) Sherlock (Stanford Research Computing):\n   - Known Sherlock 4.0 public GPU additions: (4\u00d7 nodes \u00d7 4 L40S) + (2\u00d7 nodes \u00d7 4 H100 SXM5) + (1\u00d7 node \u00d7 8 H100 SXM5) = 16 L40S + 16 H100 SXM.\n   - Sherlock total GPUs (all generations + owner nodes): 1,068 GPUs (as of Dec 2025), but model-by-model inventory is not publicly enumerated. Per your instruction, an age-based heuristic allocation is used to estimate a full model breakdown that sums to 1,068:\n     * H100 SXM: 64 (includes the 16 known Sherlock 4.0 public H100 SXM5, plus an estimated 48 additional owner H100)\n     * H200: 16 (estimated; H200 SXM5 is confirmed as an available Sherlock node configuration, but deployed count not stated)\n     * L40S: 32 (includes the 16 known public L40S, plus an estimated 16 owner L40S)\n     * A100 40GB: 400 (estimated)\n     * A100 80GB: 200 (estimated)\n     * V100: 200 (estimated)\n     * P100: 116 (estimated)\n     * A6000: 40 (estimated)\n     Total = 64+16+32+400+200+200+116+40 = 1,068.\n\nFINAL TOTALS (ALL CLUSTERS ADDED):\n- H100 SXM = Marlowe 248 + HAI 40 + SC 8 + Sherlock(est) 64 = 360\n- H200 = SC 16 + Sherlock(est) 16 = 32\n- A100 40GB = SC 63 + Sherlock(est) 400 = 463\n- A100 80GB = Sherlock(est) 200\n- L40S = Sherlock(est) 32\n- V100 = Sherlock(est) 200\n- P100 = Sherlock(est) 116\n- A6000 = Sherlock(est) 40\n\nAll other requested categories not evidenced in sources are set to 0. [WARNING: Original source was inaccessible, using fallback.]"
  },
  "compute_credits": {
    "total_annual_value_usd": 0.0,
    "description": "Not searched in this query."
  },
  "analysis_notes": "Data collected via multi-query approach: separate student and GPU searches."
}
```

---

## CALCULATION EXAMPLES

If a page says "Della cluster has 42 GPU nodes, each with 8 H100 GPUs":
- **h100_sxm_count = 42 × 8 = 336**

If a page says "Tiger cluster has 12 nodes with 4 A100 GPUs each":
- **a100_80gb_count = 12 × 4 = 48** (assume 80GB unless specified as 40GB)

---

## STRICT RULES

- **DO NOT leave GPU counts as 0** if you found specification data for the field
- If you cannot find any data for a field, use -1 and note "Not found"
- **CALCULATE** the totals from node × GPU per node

---

## SOURCE URL VALIDATION (CRITICAL)

**BEFORE including ANY URL in your sources, you MUST verify:**

1. **The URL is publicly accessible** - No login walls (Google Sites login, SSO, authentication required)
2. **The URL returns HTTP 200** - No 404 Not Found, 403 Forbidden, 500 errors
3. **The URL contains the claimed data** - The data you cite must actually appear on that page
4. **The URL is not a redirect to an error page** - Some sites show "page not found" with HTTP 200

### INVALID URLs - DO NOT USE:
- ❌ URLs that redirect to login pages (sites.google.com with "Sign in with Google")
- ❌ URLs that return 404 or "Page not found" 
- ❌ URLs behind paywalls or institutional login
- ❌ GitHub blob URLs for documentation (these often fail)
- ❌ PDF URLs that may have moved (enrollment_reports/*.pdf)
- ❌ Wiki-style URLs that change frequently

### VALID URLs - PREFER THESE:
- ✅ Official HPC/research computing pages (researchcomputing.*.edu, tacc.*, hpc.*)
- ✅ Department "About" or "By the Numbers" pages
- ✅ News announcements about new clusters
- ✅ Official system documentation (docs.tacc.utexas.edu)

### VERIFICATION CHECKLIST:
Before outputting, mentally visit each URL and confirm:
- [ ] Page loads without login prompt
- [ ] Page contains the specific data you're citing
- [ ] Page is not an error page or "not found" page
- [ ] URL path looks stable (not dynamically generated)

---

Output ONLY the JSON, no other text.