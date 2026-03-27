from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional


@dataclass
class NewsItem:
    title: str
    source_url: str
    summary_paragraphs: List[str]
    signal: Optional[str] = None  # "So what" takeaway for the reader


@dataclass
class SocialItem:
    platform: str
    handle: str
    post_url: str
    commentary: str  # Should open with a fitting emoji


@dataclass
class WorkflowOfWeek:
    id: str
    title: str
    who_for: str
    domain: str
    problem: str
    tools: str
    steps_codeblock: str


@dataclass
class PromptOfWeek:
    id: str
    title: str
    cadence: str
    intro: str  # 1-sentence setup line before the prompt block
    description: str
    prompt_text: str  # Must open with "You are my [character]..."


@dataclass
class WeeklyRead:
    title: str
    url: str
    source: Optional[str] = None
    source_domain: Optional[str] = None  # e.g. "techcrunch.com"
    description: Optional[str] = None    # 1-2 sentence summary


@dataclass
class IssueDraft:
    issue_number: Optional[int]
    issue_date: date
    subtitle: str
    ai_in_the_news: List[NewsItem] = field(default_factory=list)
    trending_on_social: List[SocialItem] = field(default_factory=list)
    workflow_of_week: Optional[WorkflowOfWeek] = None
    try_this_prompt: Optional[PromptOfWeek] = None
    weekly_reads: List[WeeklyRead] = field(default_factory=list)
