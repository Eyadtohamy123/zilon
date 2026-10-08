"""
Web Scraper 4.0 — Pydantic v2 Validation Schemas
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Every extracted record is validated through these models before storage.
Invalid records are logged and skipped — no junk data reaches the output.
"""
from __future__ import annotations
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional
from datetime import datetime


class PageMetadata(BaseModel):
    """Validated schema for page metadata & SEO data."""
    url: str
    title: str = ""
    description: str = ""
    keywords: str = ""
    author: str = ""
    og_title: str = ""
    og_description: str = ""
    og_image: str = ""
    canonical_url: str = ""
    language: str = ""
    scraped_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    @field_validator("url")
    @classmethod
    def url_must_be_nonempty(cls, v):
        if not v or not v.strip():
            raise ValueError("URL cannot be empty")
        return v.strip()


class PageText(BaseModel):
    """Validated schema for full page text extraction."""
    url: str
    full_text: str = ""
    character_count: int = 0
    word_count: int = 0
    scraped_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    emails_found: Optional[str] = None
    phones_found: Optional[str] = None

    @field_validator("character_count", "word_count")
    @classmethod
    def counts_must_be_nonneg(cls, v):
        return max(0, v)


class HeadingRecord(BaseModel):
    """Validated schema for heading extraction."""
    url: str
    level: str   # h1, h2, h3, etc.
    text: str

    @field_validator("level")
    @classmethod
    def level_must_be_valid(cls, v):
        if v not in ("h1", "h2", "h3", "h4", "h5", "h6"):
            raise ValueError(f"Invalid heading level: {v}")
        return v

    @field_validator("text")
    @classmethod
    def text_must_be_nonempty(cls, v):
        if not v or not v.strip():
            raise ValueError("Heading text cannot be empty")
        return v.strip()


class ImageRecord(BaseModel):
    """Validated schema for image extraction."""
    url: str
    image_src: str
    alt_text: str = ""
    width: str = ""
    height: str = ""
    loading: str = ""
    local_path: Optional[str] = None

    @field_validator("image_src")
    @classmethod
    def src_must_be_nonempty(cls, v):
        if not v or not v.strip():
            raise ValueError("Image src cannot be empty")
        return v.strip()


class LinkRecord(BaseModel):
    """Validated schema for link extraction."""
    source_url: str
    link_url: str
    link_text: str = "[No Text]"
    type: str = "internal"  # internal | external
    rel: str = ""

    @field_validator("link_url")
    @classmethod
    def link_url_must_be_nonempty(cls, v):
        if not v or not v.strip():
            raise ValueError("Link URL cannot be empty")
        return v.strip()


class TableRow(BaseModel, extra="allow"):
    """Validated schema for table data. Uses extra='allow' for dynamic columns."""
    url: str
    table_number: int = 1
    row_number: int = 1


class EcommerceProduct(BaseModel):
    """Validated schema for e-commerce product extraction."""
    url: str
    product_name: str = ""
    price: str = ""
    currency: str = ""
    availability: str = ""
    brand: str = ""
    sku_asin: str = ""
    rating: str = ""
    review_count: str = ""
    main_image: str = ""
    description: str = ""

    @model_validator(mode="after")
    def must_have_name_or_price(self):
        if not self.product_name and not self.price:
            raise ValueError("E-commerce product must have at least a name or price")
        return self


class AIInsight(BaseModel):
    """Validated schema for AI-extracted insights."""
    url: str
    ai_model: str = ""
    prompt_used: str = ""
    ai_response: str = ""
    extraction_time_ms: float = 0
    scraped_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class CrawlLogEntry(BaseModel):
    """Validated schema for crawl log entries."""
    url: str
    status_code: str | int = ""
    content_length: int = 0
    depth: int = 0
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    error: Optional[str] = None
    content_hash: Optional[str] = None


# ── Schema Registry ─────────────────────────────────────────
# Maps dataset name → Pydantic model for validation
SCHEMA_MAP = {
    "metadata": PageMetadata,
    "text": PageText,
    "headings": HeadingRecord,
    "images": ImageRecord,
    "links": LinkRecord,
    "tables": TableRow,
    "ecommerce": EcommerceProduct,
    "ai_insights": AIInsight,
    "crawl_log": CrawlLogEntry,
}


def validate_record(dataset_name: str, data: dict) -> BaseModel | None:
    """
    Validate a single record against its schema.
    Returns the validated model instance, or None if validation fails.
    """
    model = SCHEMA_MAP.get(dataset_name)
    if not model:
        return None
    try:
        return model(**data)
    except Exception:
        return None


def validate_batch(dataset_name: str, records: list[dict]) -> list[dict]:
    """
    Validate a batch of records. Returns only valid records as dicts.
    Invalid records are silently dropped.
    """
    model = SCHEMA_MAP.get(dataset_name)
    if not model:
        return records  # No schema defined, pass through

    valid = []
    for record in records:
        try:
            validated = model(**record)
            valid.append(validated.model_dump())
        except Exception:
            continue
    return valid
