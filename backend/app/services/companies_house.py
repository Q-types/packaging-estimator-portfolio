"""
Companies House API Client

Async client for searching and retrieving company data from the UK Companies House API.
Rate limited to 600 requests per 5 minutes as per API guidelines.

API Documentation: https://developer.company-information.service.gov.uk/
"""

import asyncio
import base64
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, AsyncGenerator, Optional

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

COMPANIES_HOUSE_API_BASE = "https://api.company-information.service.gov.uk"
RATE_LIMIT_REQUESTS = 600
RATE_LIMIT_WINDOW_SECONDS = 300  # 5 minutes


# =============================================================================
# Pydantic Models for API Responses
# =============================================================================


class CompanyAddress(BaseModel):
    """Company registered address from Companies House."""

    address_line_1: Optional[str] = Field(None, alias="address_line_1")
    address_line_2: Optional[str] = Field(None, alias="address_line_2")
    locality: Optional[str] = None
    region: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None

    class Config:
        populate_by_name = True


class CompanySearchItem(BaseModel):
    """Individual company from search results."""

    company_number: str
    company_name: str = Field(alias="title")
    company_status: Optional[str] = None
    company_type: Optional[str] = None
    date_of_creation: Optional[str] = None
    date_of_cessation: Optional[str] = None
    address: Optional[CompanyAddress] = None
    sic_codes: Optional[list[str]] = Field(None, alias="sic_codes")

    class Config:
        populate_by_name = True


class CompanySearchResponse(BaseModel):
    """Response from company search endpoint."""

    items: list[CompanySearchItem] = Field(default_factory=list)
    total_results: int = 0
    items_per_page: int = 20
    start_index: int = 0
    page_number: int = 1
    kind: str = "search#companies"


class CompanyProfile(BaseModel):
    """Full company profile details."""

    company_number: str
    company_name: str
    company_status: Optional[str] = None
    company_type: Optional[str] = None
    date_of_creation: Optional[str] = None
    date_of_cessation: Optional[str] = None
    jurisdiction: Optional[str] = None
    registered_office_address: Optional[CompanyAddress] = None
    sic_codes: Optional[list[str]] = None
    has_charges: Optional[bool] = None
    has_insolvency_history: Optional[bool] = None
    has_super_secure_pscs: Optional[bool] = None
    can_file: Optional[bool] = None

    class Config:
        populate_by_name = True


class Officer(BaseModel):
    """Company officer (director, secretary, etc.)."""

    name: str
    officer_role: str
    appointed_on: Optional[str] = None
    resigned_on: Optional[str] = None
    nationality: Optional[str] = None
    occupation: Optional[str] = None

    class Config:
        populate_by_name = True


class OfficersResponse(BaseModel):
    """Response from officers endpoint."""

    items: list[Officer] = Field(default_factory=list)
    total_results: int = 0
    active_count: int = 0
    resigned_count: int = 0


class FilingHistoryItem(BaseModel):
    """Filing history item."""

    transaction_id: str
    type: str
    date: str
    description: Optional[str] = None
    category: Optional[str] = None


class FilingHistoryResponse(BaseModel):
    """Response from filing history endpoint."""

    items: list[FilingHistoryItem] = Field(default_factory=list)
    total_count: int = 0
    filing_history_status: Optional[str] = None


# =============================================================================
# Rate Limiter
# =============================================================================


@dataclass
class RateLimiter:
    """Token bucket rate limiter for API calls."""

    max_tokens: int = RATE_LIMIT_REQUESTS
    window_seconds: int = RATE_LIMIT_WINDOW_SECONDS
    _tokens: int = RATE_LIMIT_REQUESTS
    _last_refill: datetime = None
    _lock: asyncio.Lock = None

    def __post_init__(self):
        self._last_refill = datetime.utcnow()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Acquire a token, waiting if necessary."""
        async with self._lock:
            await self._refill()

            while self._tokens <= 0:
                # Wait until next refill
                wait_time = self.window_seconds / self.max_tokens
                await asyncio.sleep(wait_time)
                await self._refill()

            self._tokens -= 1

    async def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = datetime.utcnow()
        elapsed = (now - self._last_refill).total_seconds()

        if elapsed >= self.window_seconds:
            self._tokens = self.max_tokens
            self._last_refill = now
        else:
            # Proportional refill
            tokens_to_add = int((elapsed / self.window_seconds) * self.max_tokens)
            if tokens_to_add > 0:
                self._tokens = min(self.max_tokens, self._tokens + tokens_to_add)
                self._last_refill = now


# =============================================================================
# Companies House API Client
# =============================================================================


class CompaniesHouseClient:
    """
    Async client for Companies House API.

    Usage:
        async with CompaniesHouseClient(api_key="your_key") as client:
            results = await client.search_companies("packaging")
            for company in results.items:
                profile = await client.get_company(company.company_number)
    """

    def __init__(
        self,
        api_key: str,
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._client: Optional[httpx.AsyncClient] = None
        self._rate_limiter = RateLimiter()

        # Encode API key for Basic Auth (key:blank password)
        auth_string = f"{api_key}:"
        self._auth_header = base64.b64encode(auth_string.encode()).decode()

    async def __aenter__(self) -> "CompaniesHouseClient":
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            base_url=COMPANIES_HOUSE_API_BASE,
            headers={
                "Authorization": f"Basic {self._auth_header}",
                "Accept": "application/json",
            },
            timeout=self.timeout,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict] = None,
    ) -> dict[str, Any]:
        """Make a rate-limited API request with retries."""
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        await self._rate_limiter.acquire()

        last_error: Optional[Exception] = None

        for attempt in range(self.max_retries):
            try:
                response = await self._client.request(
                    method=method,
                    url=endpoint,
                    params=params,
                )

                if response.status_code == 429:
                    # Rate limited - wait and retry
                    retry_after = int(response.headers.get("Retry-After", 60))
                    logger.warning(f"Rate limited. Waiting {retry_after}s...")
                    await asyncio.sleep(retry_after)
                    continue

                if response.status_code == 404:
                    return {"error": "not_found", "status_code": 404}

                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as e:
                last_error = e
                logger.error(f"HTTP error {e.response.status_code}: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))

            except httpx.RequestError as e:
                last_error = e
                logger.error(f"Request error: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))

        raise last_error or RuntimeError("Request failed after retries")

    # =========================================================================
    # Search Endpoints
    # =========================================================================

    async def search_companies(
        self,
        query: str,
        items_per_page: int = 100,
        start_index: int = 0,
    ) -> CompanySearchResponse:
        """
        Search for companies by name or number.

        Args:
            query: Search term (company name or number)
            items_per_page: Results per page (max 100)
            start_index: Starting index for pagination

        Returns:
            CompanySearchResponse with matching companies
        """
        data = await self._request(
            "GET",
            "/search/companies",
            params={
                "q": query,
                "items_per_page": min(items_per_page, 100),
                "start_index": start_index,
            },
        )

        if "error" in data:
            return CompanySearchResponse()

        return CompanySearchResponse(**data)

    async def advanced_search(
        self,
        company_name: Optional[str] = None,
        company_status: Optional[str] = None,
        company_type: Optional[str] = None,
        sic_codes: Optional[list[str]] = None,
        location: Optional[str] = None,
        incorporated_from: Optional[str] = None,
        incorporated_to: Optional[str] = None,
        size: int = 100,
        start_index: int = 0,
    ) -> CompanySearchResponse:
        """
        Advanced company search with filters.

        Args:
            company_name: Company name filter
            company_status: active, dissolved, etc.
            company_type: ltd, plc, llp, etc.
            sic_codes: List of SIC codes to filter by
            location: Location filter (postcode area or region)
            incorporated_from: Date string YYYY-MM-DD
            incorporated_to: Date string YYYY-MM-DD
            size: Results per page
            start_index: Starting index

        Returns:
            CompanySearchResponse with matching companies
        """
        params = {
            "size": min(size, 100),
            "start_index": start_index,
        }

        if company_name:
            params["company_name_includes"] = company_name
        if company_status:
            params["company_status"] = company_status
        if company_type:
            params["company_type"] = company_type
        if sic_codes:
            params["sic_codes"] = ",".join(sic_codes)
        if location:
            params["location"] = location
        if incorporated_from:
            params["incorporated_from"] = incorporated_from
        if incorporated_to:
            params["incorporated_to"] = incorporated_to

        data = await self._request("GET", "/advanced-search/companies", params=params)

        if "error" in data:
            return CompanySearchResponse()

        return CompanySearchResponse(**data)

    # =========================================================================
    # Company Detail Endpoints
    # =========================================================================

    async def get_company(self, company_number: str) -> Optional[CompanyProfile]:
        """
        Get full company profile by company number.

        Args:
            company_number: Companies House company number

        Returns:
            CompanyProfile or None if not found
        """
        data = await self._request("GET", f"/company/{company_number}")

        if "error" in data:
            return None

        return CompanyProfile(**data)

    async def get_officers(
        self,
        company_number: str,
        register_type: str = "directors",
        items_per_page: int = 100,
        start_index: int = 0,
    ) -> OfficersResponse:
        """
        Get company officers (directors, secretaries).

        Args:
            company_number: Companies House company number
            register_type: directors, secretaries, or llp-members
            items_per_page: Results per page
            start_index: Starting index

        Returns:
            OfficersResponse with officer list
        """
        data = await self._request(
            "GET",
            f"/company/{company_number}/officers",
            params={
                "register_type": register_type,
                "items_per_page": min(items_per_page, 100),
                "start_index": start_index,
            },
        )

        if "error" in data:
            return OfficersResponse()

        # Calculate active/resigned counts
        items = data.get("items", [])
        active = sum(1 for o in items if not o.get("resigned_on"))
        resigned = len(items) - active

        return OfficersResponse(
            items=[Officer(**o) for o in items],
            total_results=data.get("total_results", len(items)),
            active_count=active,
            resigned_count=resigned,
        )

    async def get_filing_history(
        self,
        company_number: str,
        category: Optional[str] = None,
        items_per_page: int = 100,
        start_index: int = 0,
    ) -> FilingHistoryResponse:
        """
        Get company filing history.

        Args:
            company_number: Companies House company number
            category: Filter by category (accounts, confirmation-statement, etc.)
            items_per_page: Results per page
            start_index: Starting index

        Returns:
            FilingHistoryResponse with filing list
        """
        params = {
            "items_per_page": min(items_per_page, 100),
            "start_index": start_index,
        }
        if category:
            params["category"] = category

        data = await self._request(
            "GET",
            f"/company/{company_number}/filing-history",
            params=params,
        )

        if "error" in data:
            return FilingHistoryResponse()

        return FilingHistoryResponse(
            items=[FilingHistoryItem(**f) for f in data.get("items", [])],
            total_count=data.get("total_count", 0),
            filing_history_status=data.get("filing_history_status"),
        )

    async def get_charges(self, company_number: str) -> dict[str, Any]:
        """
        Get company charges (mortgages, loans).

        Args:
            company_number: Companies House company number

        Returns:
            Dict with charges information
        """
        return await self._request("GET", f"/company/{company_number}/charges")

    # =========================================================================
    # Batch Operations
    # =========================================================================

    async def search_all_pages(
        self,
        query: str,
        max_results: int = 500,
    ) -> AsyncGenerator[CompanySearchItem, None]:
        """
        Search and yield all results across pages.

        Args:
            query: Search term
            max_results: Maximum results to return

        Yields:
            CompanySearchItem for each matching company
        """
        start_index = 0
        yielded = 0

        while yielded < max_results:
            response = await self.search_companies(
                query=query,
                items_per_page=100,
                start_index=start_index,
            )

            if not response.items:
                break

            for item in response.items:
                if yielded >= max_results:
                    return
                yield item
                yielded += 1

            start_index += len(response.items)

            if start_index >= response.total_results:
                break

    async def enrich_company(self, company_number: str) -> dict[str, Any]:
        """
        Get full company data including officers and filings.

        Args:
            company_number: Companies House company number

        Returns:
            Dict with profile, officers, filings, and charges
        """
        # Fetch all data concurrently
        profile_task = self.get_company(company_number)
        officers_task = self.get_officers(company_number)
        filings_task = self.get_filing_history(company_number, items_per_page=25)
        charges_task = self.get_charges(company_number)

        profile, officers, filings, charges = await asyncio.gather(
            profile_task,
            officers_task,
            filings_task,
            charges_task,
            return_exceptions=True,
        )

        # Handle exceptions gracefully
        if isinstance(profile, Exception):
            profile = None
        if isinstance(officers, Exception):
            officers = OfficersResponse()
        if isinstance(filings, Exception):
            filings = FilingHistoryResponse()
        if isinstance(charges, Exception):
            charges = {}

        return {
            "profile": profile.model_dump() if profile else None,
            "officers": officers.model_dump(),
            "filings": filings.model_dump(),
            "charges": charges if not charges.get("error") else {},
        }
