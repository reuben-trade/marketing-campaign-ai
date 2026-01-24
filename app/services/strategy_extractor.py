"""Strategy extraction service using AI."""

import json
import logging
from io import BytesIO

from openai import AsyncOpenAI
from pypdf import PdfReader

from app.config import get_settings
from app.schemas.business_strategy import (
    BrandVoice,
    BusinessStrategyCreate,
    TargetAudience,
)
from app.utils.prompts import STRATEGY_EXTRACTION_PROMPT
from app.utils.supabase_storage import SupabaseStorage

logger = logging.getLogger(__name__)


class StrategyExtractionError(Exception):
    """Exception raised when strategy extraction fails."""

    pass


class StrategyExtractor:
    """Extracts business strategy from PDF documents using AI."""

    def __init__(self) -> None:
        """Initialize the strategy extractor."""
        settings = get_settings()
        self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.storage = SupabaseStorage()

    def _extract_text_from_pdf(self, pdf_content: bytes) -> str:
        """Extract text content from a PDF file."""
        try:
            reader = PdfReader(BytesIO(pdf_content))
            text_parts = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
            return "\n\n".join(text_parts)
        except Exception as e:
            raise StrategyExtractionError(f"Failed to extract text from PDF: {e}") from e

    async def extract_from_pdf(
        self,
        pdf_content: bytes,
    ) -> tuple[BusinessStrategyCreate, float, list[str]]:
        """
        Extract business strategy from PDF content.

        Args:
            pdf_content: PDF file content as bytes

        Returns:
            Tuple of (BusinessStrategyCreate, confidence score, missing fields)
        """
        document_text = self._extract_text_from_pdf(pdf_content)

        if not document_text.strip():
            raise StrategyExtractionError("PDF appears to be empty or contains no extractable text")

        prompt = STRATEGY_EXTRACTION_PROMPT.format(document_content=document_text[:15000])

        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at extracting structured business information from documents. Always respond with valid JSON only.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=4000,
            )

            result_text = response.choices[0].message.content
            if not result_text:
                raise StrategyExtractionError("Empty response from AI")

            result_text = result_text.strip()
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.startswith("```"):
                result_text = result_text[3:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]

            result = json.loads(result_text.strip())

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response: {e}")
            raise StrategyExtractionError(f"Failed to parse AI response: {e}") from e
        except Exception as e:
            logger.error(f"AI extraction failed: {e}")
            raise StrategyExtractionError(f"AI extraction failed: {e}") from e

        target_audience = None
        if result.get("target_audience"):
            ta = result["target_audience"]
            target_audience = TargetAudience(
                demographics=ta.get("demographics", ""),
                psychographics=ta.get("psychographics", ""),
                pain_points=ta.get("pain_points", []),
            )

        brand_voice = None
        if result.get("brand_voice"):
            bv = result["brand_voice"]
            brand_voice = BrandVoice(
                tone=bv.get("tone", ""),
                personality_traits=bv.get("personality_traits", []),
                messaging_guidelines=bv.get("messaging_guidelines", ""),
            )

        strategy = BusinessStrategyCreate(
            business_name=result.get("business_name", "Unknown Business"),
            business_description=result.get("business_description"),
            industry=result.get("industry"),
            target_audience=target_audience,
            brand_voice=brand_voice,
            market_position=result.get("market_position"),
            price_point=result.get("price_point"),
            business_life_stage=result.get("business_life_stage"),
            unique_selling_points=result.get("unique_selling_points"),
            competitive_advantages=result.get("competitive_advantages"),
            marketing_objectives=result.get("marketing_objectives"),
        )

        confidence = result.get("extraction_confidence", 0.7)
        missing_fields = result.get("missing_fields", [])

        return strategy, confidence, missing_fields

    async def extract_from_storage(
        self,
        storage_path: str,
    ) -> tuple[BusinessStrategyCreate, float, list[str]]:
        """
        Extract business strategy from a PDF in Supabase Storage.

        Args:
            storage_path: Path to the PDF in storage

        Returns:
            Tuple of (BusinessStrategyCreate, confidence score, missing fields)
        """
        pdf_content = await self.storage.download_file(
            storage_path, bucket=self.storage.strategy_documents_bucket
        )
        return await self.extract_from_pdf(pdf_content)
