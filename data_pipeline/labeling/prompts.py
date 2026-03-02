"""Prompt templates for cluster labeling."""

SUB_CLUSTER_PROMPT_TEMPLATE = """You are an expert biomedical researcher. Your ONLY task is to provide a concise (3-5 word) topic name for the following papers.

RULES:
- Output ONLY the topic name between <label> tags
- Do NOT include explanations, steps, or reasoning
- Do NOT use generic phrases like "Gene Expression", "Machine Learning"
- Keep it specific and concise (3-5 words maximum)

Example 1:
keywords: cytokines, inflammasome, interleukin-1β
titles:
• "NLRP3 inflammasome activation in macrophages…"
• "Interleukin-1β release in sterile inflammation…"
<label>NLRP3 Inflammasome</label>

Example 2:
keywords: diffusion MRI, tractography, connectome
titles:
• "Probabilistic diffusion-tensor tractography…"
• "Whole-brain structural connectome mapping…"
<label>Diffusion MRI Methods</label>

NOW LABEL THESE PAPERS:
keywords: {keywords}
titles:
{titles}

Provide ONLY the label (no explanations):
<label>"""

PARENT_CLUSTER_PROMPT_TEMPLATE = """You are an expert biomedical taxonomist.

GOAL → Return a **JSON object** with two keys:
  • "reason" – one short sentence explaining the common theme,
  • "label"  – a SPECIFIC 3-6-word umbrella title.

INPUTS YOU WILL RECEIVE:
  • TOPIC LABELS: a list of sub-cluster labels with their sizes, one per line,
    formatted as:  "• <sub-label>  (n=<count>)"
  • Larger n means higher importance – weigh these more heavily when deciding.

STRICT RULES:
  • Weight topics with larger n more heavily.
  • ❌ NEVER use generic words: biomedical, taxonomy, keywords, miscellaneous, other, unknown, ???
  • Output JSON only – no markdown, no extra keys, no trailing commas.

EXAMPLE 1
TOPIC LABELS:
 • Diffusion MRI Methods  (n=42)
 • Connectome Tractography  (n=31)
 • Deep Brain Stimulation Targeting  (n=27)
 • Movement Disorder Imaging  (n=19)
<label>
{{
  "reason": "Sub-topics emphasize MRI tractography and DBS-related mapping with strong emphasis on imaging methods.",
  "label": "Neurosurgical Imaging Methods"
}}

EXAMPLE 2
TOPIC LABELS:
 • IL-1β Cytokine Signaling  (n=38)
 • NLRP3 Inflammasome Activation  (n=34)
 • Innate Immune Pathways  (n=21)
 • Macrophage Inflammation  (n=17)
<label>
{{
  "reason": "Sub-topics cluster around IL-1β/NLRP3-driven innate immune activation and inflammatory cascades.",
  "label": "IL-1β/NLRP3 Inflammation"
}}

NOW PRODUCE A LABEL FOR THESE TOPICS:
TOPIC LABELS:
{topics}

<label>
{{
  "reason": """

def format_sub_cluster_prompt(keywords: str, titles: list[str]) -> str:
    """Format sub-cluster labeling prompt."""
    titles_str = "\n".join(f"• {t}" for t in titles)
    return SUB_CLUSTER_PROMPT_TEMPLATE.format(keywords=keywords, titles=titles_str)


def format_parent_cluster_prompt(topics: list[tuple[str, int]]) -> str:
    """
    Format parent cluster labeling prompt.
    
    Args:
        topics: List of (label, count) tuples
    """
    topics_str = "\n".join(f" • {label}  (n={count})" for label, count in topics)
    return PARENT_CLUSTER_PROMPT_TEMPLATE.format(topics=topics_str)

