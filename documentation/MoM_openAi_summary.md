


# 🧠 Council Meeting Summary via OpenAI API – Workflow Memo

This document describes the workflow for processing individual council meeting minutes using GPT models via the OpenAI API, resulting in a structured JSON per meeting.

---

## ✅ Why This Workflow Is Recommended

| Feature                         | Benefit                                         |
|----------------------------------|--------------------------------------------------|
| One file per meeting             | Easy to version, inspect, and re-process         |
| Self-contained structure         | All relevant motions + metadata travel together |
| Compatible with streaming / GPT | Optimised for summarisation and chunking        |
| Easy to split later              | You can populate `motions.jsonl` and `meetings_metadata.jsonl` in one step |

---

## 🧾 Workflow Overview

1. **Scrape or extract PDF**  
   Clean text is extracted from meeting minutes using PDF parsers (e.g. `pdfplumber` or `PyMuPDF`).

2. **Send to OpenAI API**  
   Cleaned text is sent to OpenAI’s GPT model with a system prompt requesting structured output in a specific schema.

3. **Receive structured JSON per meeting**  
   Example:
   ```json
   {
     "meeting_id": "2024-11-03_kent_cc__planning",
     "committee": "Planning Committee",
     "meeting_date": "2024-11-03",
     "location": "Council Chamber, Maidstone",
     "chair": "Mr G Cooke",
     "attendance": {
       "present": [...],
       "absent": [...],
       "virtual": []
     },
     "motions": [
       {
         "title": "Motion to Approve Housing Development",
         "proposed_by": "Mr J Meade",
         "seconded_by": "Mrs C Bell",
         "text": "That the application be approved subject to conditions.",
         "vote": { "for": 8, "against": 2, "abstain": 1 },
         "status": "passed"
       }
     ],
     "summary": "The committee reviewed several planning applications..."
   }
   ```

4. **Save the file**  
   File is saved as:
   ```
   data/events/by_meeting/2024-11-03_kent_cc__planning.json
   ```

5. **Split into downstream structures**  
   A script parses these files and:
   - Adds meeting-level metadata to `meetings_metadata.jsonl`
   - Appends motions to `motions.jsonl`

---

## 📍 Output Location

- Raw OpenAI summary: `data/events/by_meeting/<meeting_id>.json`
- Structured stores:
  - `data/events/meetings_metadata.jsonl`
  - `data/events/motions.jsonl`

---

## 📦 Next Steps

Consider building a Python script:
- To scan `by_meeting/` folder
- To extract + append to official registries
- To verify `motion_id` uniqueness

#### Recommended models

Model                 Context Window        Notes
GPT-4-turbo (128k)    ~300 pages            Ideal for entire meetings + structured prompts
Claude 3 Opus         200k tokens           Even larger context, great for summarisation
Gemini 1.5 Pro        1M tokens             Largest context (but check JSON reliability)
GPT-3.5-turbo-16k     16k tokens            Might work for shorter meetings only
GPT-4o                128k tokens           Fast and good balance of cost/performance


## 💰 Cost Estimate for Processing Meeting Minutes (batch processing prices)

### Token Estimate per Meeting

- Prompt: ~1,200–1,500 tokens
- Meeting Text: ~3,000–10,000 tokens
- ✅ Safe average per call: **~7,000 tokens**

### Cost to Process 100 Meetings (700,000 tokens total)

| Model            | Input Price/M | Output Price/M | Est. Total Cost |
|------------------|----------------|----------------|------------------|
| **GPT-4o**       | $1.25          | $5.00          | **~$4.38**       |
| GPT-4o-mini      | $0.075         | $0.30          | ~$0.26           |
| GPT-4-turbo      | $5.00          | $15.00         | ~$14.00          |
| GPT-3.5-turbo    | $0.25          | $0.75          | ~$0.70           |
| Claude 3 Opus    | ~$15.00 est.   | ~$15.00 est.   | ~$21–25 est.     |

> ✅ **Recommended:** Use **GPT-4o** for the best balance of accuracy, speed, context, and price.

### Best Practices

- Use `temperature = 0.2` for consistent structured output.
- Validate outputs using `pydantic` or JSON schema.
- Process entire meeting in one call if model supports 128k+ context.
