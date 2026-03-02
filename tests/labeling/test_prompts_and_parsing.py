import json
import re

from data_pipeline.labeling.prompts import (
    format_sub_cluster_prompt,
    format_parent_cluster_prompt,
)
from data_pipeline.labeling.llm_client import LLMClient


def test_format_sub_cluster_prompt_basic():
    kw = "diffusion mri, tractography"
    titles = [
        "Probabilistic diffusion-tensor tractography",
        "Whole-brain structural connectome mapping",
    ]
    prompt = format_sub_cluster_prompt(kw, titles)
    assert "NOW LABEL THESE PAPERS:" in prompt
    assert "keywords: diffusion mri, tractography" in prompt
    # bullet points
    assert "• Probabilistic diffusion-tensor tractography" in prompt
    assert "<label>" in prompt


def test_format_parent_cluster_prompt_with_examples_injected():
    topics = [("Diffusion MRI Methods", 42), ("DBS Targeting", 27)]
    prompt = format_parent_cluster_prompt(topics)
    # examples block and input description
    assert "INPUTS YOU WILL RECEIVE:" in prompt
    assert "EXAMPLE 1" in prompt and "EXAMPLE 2" in prompt
    # our topics rendered
    assert " • Diffusion MRI Methods  (n=42)" in prompt
    assert "<label>" in prompt


def test_parse_sub_cluster_label_strips_tags():
    resp = "<label>Neurosurgical Imaging Methods</label>"
    label = LLMClient.parse_sub_cluster_label(resp)
    assert label == "Neurosurgical Imaging Methods"


def test_parse_parent_cluster_label_json_and_forbidden_word_block():
    resp = """
<label>
{
  "reason": "generic biomedical taxonomy",
  "label": "Biomedical"
}
"""
    reason, label = LLMClient.parse_parent_cluster_label(resp)
    # forbidden words cause fallback
    assert label == "NO VALID TITLE"
    # valid JSON path with closing tag
    good = """<label>
{
  "reason": "Emphasis on tractography and DBS imaging",
  "label": "Neurosurgical Imaging Methods"
}
</label>"""
    reason2, label2 = LLMClient.parse_parent_cluster_label(good)
    assert label2 == "Neurosurgical Imaging Methods"



