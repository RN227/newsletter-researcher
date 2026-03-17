from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional


@dataclass
class NewsItem:
    title: str
    source_url: str
    summary_paragraphs: List[str]


@dataclass
class SocialItem:
    platform: str
    handle: str
    post_url: str
    commentary: str


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
    description: str
    prompt_text: str


@dataclass
class WeeklyRead:
    title: str
    url: str
    source: Optional[str] = None


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

