"""
Translation module for Google Trends data.
Supports both free translation (deep-translator) and GPT-5-nano.
"""

import logging
import os
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Union
from functools import lru_cache
import asyncio
import json

from deep_translator import GoogleTranslator
import httpx

from models import TranslationProvider


logger = logging.getLogger(__name__)


class TranslatorBase(ABC):
    """Abstract base class for translation providers."""
    
    def __init__(self, target_language: str = "zh"):
        self.target_language = target_language
        self._cache = {}
    
    @abstractmethod
    async def translate(self, text: str, source_lang: str = "auto") -> str:
        """Translate a single text."""
        pass
    
    @abstractmethod
    async def translate_batch(self, texts: List[str], source_lang: str = "auto") -> List[str]:
        """Translate multiple texts efficiently."""
        pass
    
    def _get_cache_key(self, text: str, source_lang: str) -> str:
        """Generate cache key for translation."""
        return f"{source_lang}:{self.target_language}:{text}"
    
    def _get_from_cache(self, text: str, source_lang: str) -> Optional[str]:
        """Get translation from cache if exists."""
        key = self._get_cache_key(text, source_lang)
        return self._cache.get(key)
    
    def _add_to_cache(self, text: str, translation: str, source_lang: str):
        """Add translation to cache."""
        key = self._get_cache_key(text, source_lang)
        self._cache[key] = translation


class FreeTranslator(TranslatorBase):
    """Free translation using deep-translator (Google Translate)."""
    
    def __init__(self, target_language: str = "zh"):
        super().__init__(target_language)
        self.translator = None
        self._init_translator()
    
    def _init_translator(self):
        """Initialize the translator instance."""
        try:
            # Convert common language codes to deep-translator format
            target_lang = self._convert_language_code(self.target_language)
            
            self.translator = GoogleTranslator(
                source='auto',
                target=target_lang
            )
        except Exception as e:
            logger.error(f"Failed to initialize GoogleTranslator: {e}")
            raise
    
    def _convert_language_code(self, lang_code: str) -> str:
        """Convert common language codes to deep-translator format."""
        # Common conversions for deep-translator compatibility
        conversions = {
            'zh': 'zh-CN',  # Default Chinese to Simplified Chinese
            'zh-cn': 'zh-CN',
            'zh-tw': 'zh-TW',
            'he': 'iw',  # Hebrew
            'jw': 'jv',  # Javanese
        }
        
        return conversions.get(lang_code.lower(), lang_code.lower())
    
    async def translate(self, text: str, source_lang: str = "auto") -> str:
        """Translate a single text using free Google Translate."""
        if not text or not text.strip():
            return text
        
        # Check cache first
        cached = self._get_from_cache(text, source_lang)
        if cached is not None:
            return cached
        
        try:
            # deep-translator is synchronous, so we run it in executor
            loop = asyncio.get_event_loop()
            translation = await loop.run_in_executor(
                None,
                self._translate_sync,
                text,
                source_lang
            )
            
            # Cache the result
            self._add_to_cache(text, translation, source_lang)
            return translation
            
        except Exception as e:
            logger.error(f"Free translation failed for '{text}': {e}")
            return text  # Return original text if translation fails
    
    def _translate_sync(self, text: str, source_lang: str) -> str:
        """Synchronous translation method."""
        if source_lang != "auto":
            # Create new translator with specific source language
            target_lang = self._convert_language_code(self.target_language)
            source_lang_converted = self._convert_language_code(source_lang)
            translator = GoogleTranslator(
                source=source_lang_converted,
                target=target_lang
            )
            return translator.translate(text)
        else:
            return self.translator.translate(text)
    
    async def translate_batch(self, texts: List[str], source_lang: str = "auto") -> List[str]:
        """Translate multiple texts efficiently."""
        if not texts:
            return []
        
        # Filter out empty texts and check cache
        translations = []
        texts_to_translate = []
        indices_to_translate = []
        
        for i, text in enumerate(texts):
            if not text or not text.strip():
                translations.append(text)
            else:
                cached = self._get_from_cache(text, source_lang)
                if cached is not None:
                    translations.append(cached)
                else:
                    translations.append(None)  # Placeholder
                    texts_to_translate.append(text)
                    indices_to_translate.append(i)
        
        # Translate uncached texts
        if texts_to_translate:
            try:
                # deep-translator supports batch translation
                loop = asyncio.get_event_loop()
                batch_translations = await loop.run_in_executor(
                    None,
                    self._translate_batch_sync,
                    texts_to_translate,
                    source_lang
                )
                
                # Fill in the translations and cache them
                for idx, translation in zip(indices_to_translate, batch_translations):
                    translations[idx] = translation
                    self._add_to_cache(texts[idx], translation, source_lang)
                    
            except Exception as e:
                logger.error(f"Batch translation failed: {e}")
                # Fill failed translations with original text
                for idx in indices_to_translate:
                    translations[idx] = texts[idx]
        
        return translations
    
    def _translate_batch_sync(self, texts: List[str], source_lang: str) -> List[str]:
        """Synchronous batch translation."""
        if source_lang != "auto":
            target_lang = self._convert_language_code(self.target_language)
            source_lang_converted = self._convert_language_code(source_lang)
            translator = GoogleTranslator(
                source=source_lang_converted,
                target=target_lang
            )
        else:
            translator = self.translator
        
        # deep-translator can handle batch translation
        return translator.translate_batch(texts)


class GPTTranslator(TranslatorBase):
    """Translation using GPT-5-nano model."""
    
    def __init__(self, target_language: str = "zh", api_key: Optional[str] = None):
        super().__init__(target_language)
        # Try multiple environment variable names for flexibility
        self.api_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("GPT_NANO_API_KEY")
        if not self.api_key:
            raise ValueError("API key is required. Set OPENAI_API_KEY in .env file or pass via --gpt-api-key")
        
        # GPT-5-nano endpoint
        self.api_url = "https://api.openai.com/v1/chat/completions"
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def translate(self, text: str, source_lang: str = "auto") -> str:
        """Translate using GPT-5-nano."""
        if not text or not text.strip():
            return text
        
        # Check cache first
        cached = self._get_from_cache(text, source_lang)
        if cached is not None:
            return cached
        
        try:
            # Prepare the request
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Create translation prompt
            prompt = self._create_translation_prompt(text, source_lang)
            
            payload = {
                "model": "gpt-4o-mini",  # Using available OpenAI model
                "messages": [
                    {"role": "system", "content": "You are a professional translator. Translate the given text accurately while preserving the original meaning and context. Only return the translation, nothing else."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 500
            }
            
            response = await self.client.post(
                self.api_url,
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            translation = result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            
            if translation:
                self._add_to_cache(text, translation, source_lang)
                return translation
            else:
                logger.warning(f"Empty translation response for '{text}'")
                return text
                
        except Exception as e:
            logger.error(f"GPT translation failed for '{text}': {e}")
            return text
    
    def _create_translation_prompt(self, text: str, source_lang: str) -> str:
        """Create translation prompt for GPT."""
        target_lang_name = self._get_language_name(self.target_language)
        
        if source_lang == "auto":
            prompt = f"Translate the following text to {target_lang_name}. Only provide the translation, nothing else:\n\n{text}"
        else:
            source_lang_name = self._get_language_name(source_lang)
            prompt = f"Translate the following {source_lang_name} text to {target_lang_name}. Only provide the translation, nothing else:\n\n{text}"
        
        return prompt
    
    def _get_language_name(self, lang_code: str) -> str:
        """Convert language code to full name."""
        lang_map = {
            "zh": "Chinese",
            "en": "English", 
            "es": "Spanish",
            "fr": "French",
            "de": "German",
            "ja": "Japanese",
            "ko": "Korean",
            "pt": "Portuguese",
            "ru": "Russian",
            "ar": "Arabic",
            "hi": "Hindi"
        }
        return lang_map.get(lang_code, lang_code)
    
    def _get_country_context(self, geo: str) -> str:
        """Get cultural and linguistic context for the country/region."""
        geo_lower = geo.lower()
        
        context_map = {
            "japan": "Japanese culture emphasizes politeness and formality. Sports include baseball, sumo, soccer. Major cities: Tokyo, Osaka. Language context: Japanese to Chinese translation.",
            "south korea": "Korean culture values respect and technology. K-pop, K-dramas are major exports. Sports include soccer, baseball, esports. Major cities: Seoul, Busan. Language: Korean to Chinese.",
            "korea": "Korean culture values respect and technology. K-pop, K-dramas are major exports. Sports include soccer, baseball, esports. Major cities: Seoul, Busan. Language: Korean to Chinese.",
            "united states": "American culture emphasizes individualism and entertainment. Major sports: NFL, NBA, MLB, NHL. Tech hub: Silicon Valley. Language: English to Chinese.",
            "china": "Chinese culture with rich history. Major sports: basketball, soccer, table tennis. Tech companies: Alibaba, Tencent. Language: Chinese (may need regional dialect considerations).",
            "taiwan": "Traditional Chinese culture with modern technology. Popular sports: baseball, basketball. Language: Traditional Chinese, may need conversion to Simplified.",
            "france": "French culture emphasizes art and cuisine. Sports: soccer, rugby, tennis. Fashion capital. Language: French to Chinese.",
            "germany": "German culture values precision and engineering. Sports: soccer (football), Formula 1. Major tech and automotive industry. Language: German to Chinese.",
            "united kingdom": "British culture with royal traditions. Sports: soccer, cricket, rugby. Financial center: London. Language: English to Chinese.",
            "canada": "Canadian culture with multiculturalism. Sports: hockey, soccer, basketball. Bilingual country. Language: English/French to Chinese.",
            "australia": "Australian culture with outdoor lifestyle. Sports: cricket, rugby, Australian football. Language: English to Chinese.",
            "brazil": "Brazilian culture famous for soccer and carnival. Major sports: soccer, volleyball, Formula 1. Language: Portuguese to Chinese.",
            "india": "Indian culture with diverse languages and Bollywood. Sports: cricket, kabaddi, soccer. Tech hub: Bangalore. Language: Hindi/English to Chinese.",
            "russia": "Russian culture with rich literature and arts. Sports: hockey, soccer, figure skating. Language: Russian to Chinese.",
            "vietnam": "Vietnamese culture with French colonial influence and strong national identity. Popular sports: soccer, badminton, martial arts. Major cities: Ho Chi Minh City, Hanoi. Language: Vietnamese to Chinese.",
        }
        
        for country, context in context_map.items():
            if country in geo_lower:
                return context
        
        return f"International trends from {geo}. Consider local culture, popular sports, entertainment, and current events when translating."
    
    async def translate_batch(self, texts: List[str], source_lang: str = "auto") -> List[str]:
        """Translate multiple texts using GPT in a single optimized call."""
        if not texts:
            return []
        
        # Check cache first
        translations = []
        texts_to_translate = []
        indices_to_translate = []
        
        for i, text in enumerate(texts):
            if not text or not text.strip():
                translations.append(text)
            else:
                cached = self._get_from_cache(text, source_lang)
                if cached is not None:
                    translations.append(cached)
                else:
                    translations.append(None)
                    texts_to_translate.append(text)
                    indices_to_translate.append(i)
        
        if texts_to_translate:
            try:
                # Use optimized trending topics translation
                batch_translations = await self._translate_trending_topics_batch(texts_to_translate, source_lang)
                
                # Fill in translations and cache
                for idx, translation in zip(indices_to_translate, batch_translations):
                    translations[idx] = translation
                    self._add_to_cache(texts[idx], translation, source_lang)
                    
            except Exception as e:
                logger.error(f"GPT batch translation failed: {e}")
                # Fallback to original text
                for idx in indices_to_translate:
                    translations[idx] = texts[idx]
        
        return translations

    async def _translate_trending_topics_batch(self, texts: List[str], source_lang: str = "auto", geo: str = "Unknown", categories: List[str] = None, breakdown_contexts: List[dict] = None) -> List[str]:
        """Optimized batch translation for trending topics with context awareness."""
        target_lang_name = self._get_language_name(self.target_language)
        
        # Get country/region context
        country_context = self._get_country_context(geo)
        
        # Create numbered list of topics with rich context
        numbered_list = ""
        for i, text in enumerate(texts, 1):
            category = categories[i-1] if categories and i-1 < len(categories) else "General"
            
            # Add breakdown context if available
            context_info = ""
            if breakdown_contexts and i-1 < len(breakdown_contexts):
                breakdown = breakdown_contexts[i-1]
                if breakdown:
                    if breakdown.get('trend_context'):
                        context_info += f" | Context: {breakdown['trend_context']}"
                    if breakdown.get('breakdown_description'):
                        context_info += f" | Description: {breakdown['breakdown_description']}"
                    if breakdown.get('query_variants'):
                        variants = breakdown['query_variants'][:3]  # Top 3 variants
                        context_info += f" | Variants: {', '.join(variants)}"
            
            numbered_list += f"{i}. {text} [Category: {category}]{context_info}\n"
        
        # Enhanced context-aware prompt
        system_prompt = f"""You are an expert translator specializing in trending topics and current events from {geo}. 

CONTEXT UNDERSTANDING:
- These are popular search terms from Google Trends in {geo}
- {country_context}
- Each topic includes its category to help you understand the context
- Sports topics often refer to team matchups (e.g., "Team A vs Team B" means a game/match)
- Entertainment topics may include celebrity names, movies, TV shows
- Technology topics include product launches, company news
- News topics cover current events and breaking news

TRANSLATION REQUIREMENTS:
- Translate to {target_lang_name} (Simplified Chinese if Chinese)
- Use the rich context information (Category, Context, Description, Variants) to provide accurate translations
- Add brief contextual explanation in parentheses when helpful for understanding
- For sports matchups, clarify it's a game/match: "球队A对球队B (体育比赛)"
- For celebrity names, keep original name + Chinese if commonly known: "Name (中文名/职业)"
- For products/brands, keep English name + brief Chinese description: "Product (产品类型/公司)"
- Consider cultural context, recent events, and trending topic context from {geo}
- Use breakdown variants and context to ensure translation accuracy

ENHANCED EXAMPLES:
- "Lakers vs Warriors [Category: Sports] | Context: NBA basketball matchup" → "湖人队对勇士队 (NBA篮球比赛)"
- "iPhone 15 [Category: Technology] | Context: Apple smartphone release" → "iPhone 15 (苹果新款智能手机)"
- "Taylor Swift [Category: Entertainment] | Variants: Taylor Swift concert, Taylor Swift tour" → "Taylor Swift (泰勒·斯威夫特, 美国歌手巡演)"
- "Breaking news [Category: News] | Context: Current events coverage" → "突发新闻 (最新时事报道)"

Use the context and variants to provide the most accurate and culturally appropriate translation."""

        user_prompt = f"""Translate the following trending Google search topics from {geo} to {target_lang_name}. Return ONLY the translations with contextual notes in the same order, separated by ||| delimiter.

{numbered_list.strip()}"""

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "max_tokens": min(len(texts) * 50 + 500, 4000)  # Dynamic token limit
        }
        
        response = await self.client.post(
            self.api_url,
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        
        result = response.json()
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        
        # Parse the response
        translations = content.split("|||")
        translations = [t.strip() for t in translations if t.strip()]
        
        # Ensure we have the right number of translations
        if len(translations) != len(texts):
            logger.warning(f"Expected {len(texts)} translations, got {len(translations)}")
            # Pad with original text if needed
            while len(translations) < len(texts):
                translations.append(texts[len(translations)])
            translations = translations[:len(texts)]
        
        return translations
    
    def _create_batch_translation_prompt(self, texts: List[str], source_lang: str) -> str:
        """Create batch translation prompt."""
        target_lang_name = self._get_language_name(self.target_language)
        
        prompt = f"Translate the following texts to {target_lang_name}. "
        prompt += "Return ONLY the translations in the same order, separated by ||| delimiter:\n\n"
        
        for i, text in enumerate(texts, 1):
            prompt += f"{i}. {text}\n"
        
        return prompt
    
    def _parse_batch_response(self, response: str, expected_count: int) -> List[str]:
        """Parse batch translation response."""
        translations = response.strip().split("|||")
        translations = [t.strip() for t in translations if t.strip()]
        
        # Ensure we have the right number of translations
        if len(translations) != expected_count:
            logger.warning(f"Expected {expected_count} translations, got {len(translations)}")
            # Pad with empty strings or truncate as needed
            if len(translations) < expected_count:
                translations.extend([""] * (expected_count - len(translations)))
            else:
                translations = translations[:expected_count]
        
        return translations
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.aclose()


def create_translator(
    provider: TranslationProvider,
    target_language: str = "zh",
    api_key: Optional[str] = None
) -> TranslatorBase:
    """
    Factory function to create appropriate translator.
    
    Args:
        provider: Translation provider type
        target_language: Target language code
        api_key: API key for GPT translator (optional)
    
    Returns:
        Translator instance
    """
    if provider == TranslationProvider.FREE:
        return FreeTranslator(target_language)
    elif provider == TranslationProvider.GPT_NANO:
        return GPTTranslator(target_language, api_key)
    else:
        raise ValueError(f"Unknown translation provider: {provider}")


async def translate_trend_items(
    trends: List,
    translator: TranslatorBase,
    source_lang: str = "auto",
    geo: str = "Unknown"
) -> None:
    """
    Translate trend items in place with enhanced context.
    
    Args:
        trends: List of TrendItem objects
        translator: Translator instance
        source_lang: Source language code
        geo: Geographic region for context
    """
    if not trends:
        return
    
    # Check if translator supports enhanced batch translation
    if isinstance(translator, GPTTranslator):
        await _translate_trends_with_context(trends, translator, source_lang, geo)
    else:
        # Fallback to basic translation for free translator
        await _translate_trends_basic(trends, translator, source_lang)


async def _translate_trends_with_context(
    trends: List,
    translator: GPTTranslator,
    source_lang: str,
    geo: str
) -> None:
    """Enhanced translation with category and geo context for GPT translator."""
    
    # Collect titles with categories and breakdown context
    titles = [trend.title for trend in trends]
    categories = [getattr(trend, 'trend_category', 'General') for trend in trends]
    
    # Collect breakdown context information
    breakdown_contexts = []
    for trend in trends:
        breakdown = {
            'trend_context': getattr(trend, 'trend_context', None),
            'breakdown_description': getattr(trend, 'breakdown_description', None),
            'query_variants': getattr(trend, 'query_variants', None)
        }
        breakdown_contexts.append(breakdown)
    
    # Collect related queries
    all_related = []
    related_indices = []
    related_categories = []
    related_breakdowns = []
    
    for i, trend in enumerate(trends):
        if trend.top_related:
            all_related.extend(trend.top_related)
            related_indices.append((i, len(trend.top_related)))
            # Use same category and breakdown for related queries
            category = getattr(trend, 'trend_category', 'General')
            breakdown = breakdown_contexts[i]
            related_categories.extend([category] * len(trend.top_related))
            related_breakdowns.extend([breakdown] * len(trend.top_related))
    
    # Translate titles with enhanced context
    logger.info(f"Translating {len(titles)} trend titles with rich context...")
    translated_titles = await translator._translate_trending_topics_batch(
        titles, source_lang, geo, categories, breakdown_contexts
    )
    
    # Translate related queries with context
    translated_related = []
    if all_related:
        logger.info(f"Translating {len(all_related)} related queries with context...")
        translated_related = await translator._translate_trending_topics_batch(
            all_related, source_lang, geo, related_categories, related_breakdowns
        )
    
    # Apply translations to trends
    for i, trend in enumerate(trends):
        trend.title_translated = translated_titles[i]
    
    # Apply related translations
    if translated_related:
        related_idx = 0
        for trend_idx, count in related_indices:
            trend = trends[trend_idx]
            trend.related_translated = translated_related[related_idx:related_idx + count]
            related_idx += count


async def _translate_trends_basic(
    trends: List,
    translator: TranslatorBase,
    source_lang: str
) -> None:
    """Basic translation for free translator."""
    
    # Collect all texts to translate
    titles = [trend.title for trend in trends]
    all_related = []
    related_indices = []
    
    for i, trend in enumerate(trends):
        if trend.top_related:
            all_related.extend(trend.top_related)
            related_indices.append((i, len(trend.top_related)))
    
    # Translate titles
    logger.info(f"Translating {len(titles)} trend titles...")
    translated_titles = await translator.translate_batch(titles, source_lang)
    
    # Translate related queries if any
    translated_related = []
    if all_related:
        logger.info(f"Translating {len(all_related)} related queries...")
        translated_related = await translator.translate_batch(all_related, source_lang)
    
    # Apply translations to trends
    for i, trend in enumerate(trends):
        trend.title_translated = translated_titles[i]
    
    # Apply related translations
    if translated_related:
        related_idx = 0
        for trend_idx, count in related_indices:
            trend = trends[trend_idx]
            trend.related_translated = translated_related[related_idx:related_idx + count]
            related_idx += count