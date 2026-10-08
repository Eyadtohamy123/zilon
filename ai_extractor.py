"""
Web Scraper 4.0 — AI Extraction Module (Ollama)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Sends scraped HTML/text to a local LLM (Llama 3.2 via Ollama) for
intelligent structured extraction. Falls back gracefully to CSS parsing
if Ollama is unreachable or AI mode is disabled.
"""
import json
import time
import logging
import re

logger = logging.getLogger("WebScraper3.0")

# Default AI extraction prompt
DEFAULT_AI_PROMPT = """You are a data extraction AI. Analyze the following web page content and extract ALL relevant structured information.

Return your response as a valid JSON object with these keys (include only keys that have data):
- "summary": A 2-3 sentence summary of what this page is about.
- "key_entities": A list of important names, organizations, or products mentioned.
- "key_facts": A list of important facts, statistics, or data points found.
- "sentiment": Overall sentiment of the page content (positive/negative/neutral).
- "category": The category/topic of this page (e.g., "technology", "health", "e-commerce").

IMPORTANT: Return ONLY the JSON object, no markdown, no code fences, no explanation.

Page URL: {url}
Page Content:
{content}"""


class AIExtractor:
    """
    AI-powered data extraction using a local Ollama LLM.
    
    Usage:
        extractor = AIExtractor(model="llama3.2", prompt="...")
        result = extractor.extract(url, page_text)
    """

    def __init__(self, model: str = "llama3.2", prompt: str = "", 
                 ollama_host: str = "http://localhost:11434", timeout: float = 60.0):
        self.model = model
        self.prompt = prompt or DEFAULT_AI_PROMPT
        self.ollama_host = ollama_host.rstrip("/")
        self.timeout = timeout
        self._available = None  # Cached availability check

    def is_available(self) -> bool:
        """Check if Ollama is running and the model is available."""
        if self._available is not None:
            return self._available
        try:
            import ollama as ollama_lib
            models = ollama_lib.list()
            model_names = [m.model for m in models.models] if hasattr(models, 'models') else []
            # Check if any model name starts with our model name (handles tags like :latest)
            self._available = any(
                name.startswith(self.model) for name in model_names
            )
            if not self._available:
                logger.warning(f"  ⚠ AI model '{self.model}' not found in Ollama. "
                             f"Available: {model_names}. Run: ollama pull {self.model}")
            return self._available
        except Exception as e:
            logger.warning(f"  ⚠ Ollama not reachable: {e}. AI extraction disabled.")
            self._available = False
            return False

    def extract(self, url: str, page_text: str, max_content_chars: int = 6000) -> dict | None:
        """
        Send page content to Ollama and parse the AI's structured response.
        
        Args:
            url: The page URL (for context in the prompt).
            page_text: Cleaned page text content.
            max_content_chars: Max characters to send to avoid context overflow.
            
        Returns:
            Dict with AI-extracted data, or None on failure.
        """
        if not self.is_available():
            return None

        if not page_text or len(page_text.strip()) < 50:
            return None  # Too little content to analyze

        # Truncate content to fit context window
        content = page_text[:max_content_chars]

        # Build the prompt
        filled_prompt = self.prompt.replace("{url}", url).replace("{content}", content)

        start_time = time.time()
        try:
            import ollama as ollama_lib
            response = ollama_lib.generate(
                model=self.model,
                prompt=filled_prompt,
                options={"temperature": 0.1, "num_predict": 1024},
            )
            
            elapsed_ms = (time.time() - start_time) * 1000
            raw_response = response.get("response", "") if isinstance(response, dict) else str(response.response)

            # Try to parse JSON from the response
            parsed = self._parse_json_response(raw_response)

            result = {
                "url": url,
                "ai_model": self.model,
                "prompt_used": self.prompt[:200] + "..." if len(self.prompt) > 200 else self.prompt,
                "ai_response": json.dumps(parsed) if parsed else raw_response[:2000],
                "extraction_time_ms": round(elapsed_ms, 1),
            }
            return result

        except Exception as e:
            logger.error(f"  ✗ AI extraction failed for {url}: {e}")
            return None

    def _parse_json_response(self, text: str) -> dict | None:
        """Attempt to parse JSON from AI response, handling common formatting issues."""
        if not text:
            return None

        # Try direct JSON parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try to extract JSON from markdown code fences
        json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try to find JSON object in the text
        brace_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass

        return None


class AIExtractorDisabled:
    """Null-object pattern: used when AI extraction is disabled. All methods are no-ops."""

    def is_available(self) -> bool:
        return False

    def extract(self, url: str, page_text: str, **kwargs) -> None:
        return None
