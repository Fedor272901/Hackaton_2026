"""
Page Data Service for fetching data from internal API.

This module provides a service layer that isolates business logic from direct
database access by making HTTP requests to the internal API endpoints. It ensures
proper separation of concerns and allows for centralized error handling, logging,
and potential future enhancements like caching or rate limiting.
"""

import logging
from typing import Any, Dict, List, Optional, Union

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class ServiceAPIError(Exception):
    """
    Custom exception for API service errors.

    Raised when an error occurs during API communication, including timeout,
    connection errors, or server-side errors (5xx status codes).
    """

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        original_exception: Optional[Exception] = None,
    ):
        """
        Initialize ServiceAPIError.

        Args:
            message: Human-readable error message describing what went wrong.
            status_code: HTTP status code if available (e.g., 500, 502, 503).
            original_exception: The original exception that caused this error, if any.
        """
        self.message = message
        self.status_code = status_code
        self.original_exception = original_exception
        super().__init__(self.message)


async def fetch_api_data(
    method: str,
    url: str,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Fetch data from an internal API endpoint with comprehensive error handling.

    This function serves as a universal wrapper for all HTTP requests made by the
    PageDataService. It handles various types of errors that can occur during
    HTTP communication and provides standardized error responses or exceptions.

    The function uses httpx.AsyncClient for non-blocking HTTP requests, which is
    essential for maintaining high concurrency in the FastAPI application.

    Args:
        method: HTTP method to use (GET, POST, PUT, PATCH, DELETE).
        url: Full URL or path to the API endpoint. If it's a path (starts with /),
             it will be prefixed with the base API URL from settings.
        **kwargs: Additional keyword arguments passed to httpx.request(), such as:
            - params: Query parameters (dict)
            - json: JSON payload for POST/PUT/PATCH requests (dict)
            - headers: Custom HTTP headers (dict)
            - timeout: Request timeout in seconds (float)
            - cookies: Cookies to send with the request (dict)

    Returns:
        Dict[str, Any]: Parsed JSON response from the API. For successful requests,
                        this contains the data returned by the endpoint.

    Raises:
        ServiceAPIError: Raised in the following cases:
            - TimeoutException: When the request takes longer than the specified
              timeout (default 10 seconds). This prevents hanging requests from
              blocking the application.
            - ConnectError: When unable to establish a connection to the API server.
              This could indicate the API service is down or network issues.
            - RequestError: For other request-related errors (invalid URLs, SSL
              errors, etc.).
            - HTTPStatusError: When the API returns a 5xx server error. These are
              logged and re-raised as ServiceAPIError for proper handling upstream.
            - For 4xx client errors, the function assumes these are expected
              (e.g., 404 for not found) and returns the error response as-is.

    Note:
        The function distinguishes between different error types to provide
        appropriate error messages and handling strategies:

        - TimeoutException: Handled separately because timeouts are common in
          production and should be treated as transient failures that might
          succeed on retry. The application can implement retry logic specifically
          for timeouts.

        - ConnectError: Indicates infrastructure issues (network problems, API
          service down). These errors require immediate attention and should be
          logged with high priority.

        - RequestError: Catches miscellaneous request errors like invalid URLs,
          SSL certificate issues, or malformed requests. These are typically
          configuration or code issues that need to be fixed.

        - 5xx Status Codes: Server errors indicate problems with the API itself
          (bugs, overload, database issues). These are logged and converted to
          ServiceAPIError so the calling code can decide how to respond
          (e.g., show a user-friendly error message).

        - 4xx Status Codes: Client errors (400, 401, 403, 404) are considered
          expected behavior in many cases (e.g., resource not found, unauthorized).
          These are returned as-is so the calling code can handle them appropriately.
    """
    # Build full URL if only path is provided
    if url.startswith("/"):
        # Use API_BASE_URL from config
        # For internal requests, we assume the API is on the same host
        base_url = settings.INTERNAL_API_BASE_URL or "http://localhost:8000"
        full_url = f"{base_url}{url}"
    else:
        full_url = url

    # Set default timeout if not specified
    if "timeout" not in kwargs:
        kwargs["timeout"] = 10.0  # Default 10 second timeout

    try:
        async with httpx.AsyncClient() as client:
            response = await client.request(method=method, url=full_url, **kwargs)

            # Handle 5xx server errors - these indicate API problems
            if response.status_code >= 500:
                logger.error(
                    f"API server error: {response.status_code} for {method} {url}. "
                    f"Response: {response.text[:200]}"
                )
                raise ServiceAPIError(
                    message=f"API server returned error: {response.status_code}",
                    status_code=response.status_code,
                )

            # For 4xx errors, return the response as-is
            # These are often expected (e.g., 404 Not Found, 401 Unauthorized)
            # and should be handled by the calling code
            if response.status_code >= 400:
                logger.warning(
                    f"API client error: {response.status_code} for {method} {url}. "
                    f"Response: {response.text[:200]}"
                )
                try:
                    return response.json()
                except Exception:
                    return {"error": response.text, "status_code": response.status_code}

            # Successful response - parse and return JSON
            try:
                return response.json()
            except Exception as e:
                logger.error(f"Failed to parse JSON response from {method} {url}: {e}")
                raise ServiceAPIError(
                    message="Invalid JSON response from API",
                    original_exception=e,
                )

    except httpx.TimeoutException as e:
        # TimeoutException: Request took too long
        # This is a transient error that might succeed on retry
        # Common causes: API overload, slow database queries, network latency
        logger.error(f"Request timeout for {method} {url}: {e}")
        raise ServiceAPIError(
            message=f"Request timed out after {kwargs.get('timeout', 10)} seconds",
            original_exception=e,
        )

    except httpx.ConnectError as e:
        # ConnectError: Unable to establish connection to API server
        # This indicates infrastructure issues: API down, network problems,
        # firewall blocking, or incorrect host/port configuration
        # Requires immediate attention and monitoring alert
        logger.error(f"Connection error for {method} {url}: {e}")
        raise ServiceAPIError(
            message="Unable to connect to API service",
            original_exception=e,
        )

    except httpx.RequestError as e:
        # RequestError: Other request-related errors
        # This includes: invalid URLs, SSL certificate errors, DNS resolution failures,
        # malformed requests, or protocol errors
        # Typically indicates configuration or code issues that need fixing
        logger.error(f"Request error for {method} {url}: {e}")
        raise ServiceAPIError(
            message=f"Request failed: {str(e)}",
            original_exception=e,
        )


class PageDataService:
    """
    Service for fetching page-related data from the internal API.

    This class provides methods to retrieve data needed for rendering web pages.
    All methods delegate to the internal API endpoints, ensuring that business
    logic remains in the API layer and is not duplicated in the presentation layer.

    The service promotes:
    - Separation of concerns: Pages don't directly access the database
    - Centralized error handling: All API errors are handled consistently
    - Testability: The service can be easily mocked in tests
    - Maintainability: Changes to API endpoints only require updates here
    """

    def __init__(self, api_base_url: Optional[str] = None):
        """
        Initialize PageDataService.

        Args:
            api_base_url: Optional base URL for the API. If not provided,
                         uses the default from config.
        """
        self.api_base_url = api_base_url or settings.INTERNAL_API_BASE_URL or "http://localhost:8000"

    async def get_districts(
        self,
        skip: int = 0,
        limit: int = 100,
        active_only: bool = True,
    ) -> Dict[str, Any]:
        """
        Fetch list of districts from the API.

        Calls internal endpoint: GET /api/v1/districts/

        Expected response format:
        {
            "items": [
                {
                    "id": 1,
                    "name": "District Name",
                    "description": "Description",
                    "is_active": true,
                    ...
                },
                ...
            ],
            "total": 10,
            "skip": 0,
            "limit": 100
        }

        Args:
            skip: Number of records to skip for pagination. Defaults to 0.
            limit: Maximum number of records to return. Defaults to 100.
            active_only: If True, only return active districts. Defaults to True.

        Returns:
            Dict[str, Any]: Dictionary containing 'items' list and pagination metadata.
                           Returns empty dict if API call fails.

        Raises:
            ServiceAPIError: If the API request fails due to timeout, connection
                            error, or server error.
        """
        params = {"skip": skip, "limit": limit}
        if active_only:
            params["active_only"] = "true"

        try:
            result = await fetch_api_data(
                method="GET",
                url="/api/v1/districts/",
                params=params,
            )
            return result if result else {"items": [], "total": 0}
        except ServiceAPIError:
            # Re-raise to let caller handle
            raise
        except Exception as e:
            logger.error(f"Unexpected error in get_districts: {e}")
            raise ServiceAPIError(
                message="Failed to fetch districts",
                original_exception=e,
            )

    async def get_deputies(
        self,
        district_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """
        Fetch list of deputies from the API.

        Calls internal endpoint: GET /api/v1/deputies/

        Expected response format:
        {
            "items": [
                {
                    "id": 1,
                    "user_id": 5,
                    "district_id": 2,
                    "user": {
                        "first_name": "John",
                        "last_name": "Doe",
                        "email": "john@example.com"
                    },
                    "district": {
                        "id": 2,
                        "name": "District Name"
                    },
                    ...
                },
                ...
            ],
            "total": 5,
            "skip": 0,
            "limit": 100
        }

        Args:
            district_id: Optional filter by district ID. If provided, only returns
                        deputies from that district. Defaults to None (all deputies).
            skip: Number of records to skip for pagination. Defaults to 0.
            limit: Maximum number of records to return. Defaults to 100.

        Returns:
            Dict[str, Any]: Dictionary containing 'items' list and pagination metadata.
                           Returns empty dict if API call fails.

        Raises:
            ServiceAPIError: If the API request fails due to timeout, connection
                            error, or server error.
        """
        params = {"skip": skip, "limit": limit}
        if district_id is not None:
            params["district_id"] = district_id

        try:
            result = await fetch_api_data(
                method="GET",
                url="/api/v1/deputies/",
                params=params,
            )
            return result if result else {"items": [], "total": 0}
        except ServiceAPIError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in get_deputies: {e}")
            raise ServiceAPIError(
                message="Failed to fetch deputies",
                original_exception=e,
            )

    async def get_deputy_by_district(self, district_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetch a single deputy by their district ID.

        Calls internal endpoint: GET /api/v1/deputies/?district_id={district_id}

        This is a convenience method that fetches deputies filtered by district
        and returns the first one (assuming one deputy per district).

        Expected response format (single item from items list):
        {
            "id": 1,
            "user_id": 5,
            "district_id": 2,
            "user": {
                "first_name": "John",
                "last_name": "Doe",
                "email": "john@example.com"
            },
            "district": {
                "id": 2,
                "name": "District Name"
            },
            ...
        }

        Args:
            district_id: The ID of the district to find the deputy for.

        Returns:
            Optional[Dict[str, Any]]: Deputy data dictionary if found, None otherwise.
                                     Returns None if API call fails or no deputy found.

        Raises:
            ServiceAPIError: If the API request fails due to timeout, connection
                            error, or server error.
        """
        try:
            result = await self.get_deputies(district_id=district_id, limit=1)
            items = result.get("items", [])
            return items[0] if items else None
        except ServiceAPIError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in get_deputy_by_district: {e}")
            return None

    async def get_requests(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Fetch list of requests (appeals) from the API.

        Calls internal endpoint: GET /api/v1/requests/

        Expected response format:
        {
            "items": [
                {
                    "id": 1,
                    "title": "Request Title",
                    "description": "Description",
                    "status": {
                        "id": 1,
                        "code": "new",
                        "name": "Новое"
                    },
                    "category": {
                        "id": 1,
                        "name": "Category Name"
                    },
                    "district": {
                        "id": 1,
                        "name": "District Name"
                    },
                    "user": {
                        "first_name": "John",
                        "last_name": "Doe"
                    },
                    "created_at": "2024-01-01T10:00:00",
                    ...
                },
                ...
            ],
            "total": 50,
            "skip": 0,
            "limit": 100
        }

        Args:
            skip: Number of records to skip for pagination. Defaults to 0.
            limit: Maximum number of records to return. Defaults to 100.
            filters: Optional dictionary of filter parameters to pass to the API.
                    Supported filters may include:
                    - status_id: Filter by status ID
                    - category_id: Filter by category ID
                    - district_id: Filter by district ID
                    - assigned_deputy_id: Filter by assigned deputy ID
                    - search: Search term for title/description

        Returns:
            Dict[str, Any]: Dictionary containing 'items' list and pagination metadata.
                           Returns empty dict if API call fails.

        Raises:
            ServiceAPIError: If the API request fails due to timeout, connection
                            error, or server error.
        """
        params = {"skip": skip, "limit": limit}
        if filters:
            params.update(filters)

        try:
            result = await fetch_api_data(
                method="GET",
                url="/api/v1/requests/",
                params=params,
            )
            return result if result else {"items": [], "total": 0}
        except ServiceAPIError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in get_requests: {e}")
            raise ServiceAPIError(
                message="Failed to fetch requests",
                original_exception=e,
            )

    async def get_categories(self) -> List[Dict[str, Any]]:
        """
        Fetch list of request categories from the API.

        Calls internal endpoint: GET /api/v1/categories/

        Expected response format:
        {
            "items": [
                {
                    "id": 1,
                    "name": "Category Name",
                    "description": "Category description",
                    "code": "category_code"
                },
                ...
            ]
        }

        Returns:
            List[Dict[str, Any]]: List of category dictionaries.
                                 Returns empty list if API call fails.

        Raises:
            ServiceAPIError: If the API request fails due to timeout, connection
                            error, or server error.
        """
        try:
            result = await fetch_api_data(
                method="GET",
                url="/api/v1/categories/",
            )
            if result and isinstance(result, dict):
                return result.get("items", [])
            elif isinstance(result, list):
                return result
            return []
        except ServiceAPIError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in get_categories: {e}")
            return []

    async def get_statuses(self) -> List[Dict[str, Any]]:
        """
        Fetch list of request statuses from the API.

        Calls internal endpoint: GET /api/v1/statuses/

        Expected response format:
        {
            "items": [
                {
                    "id": 1,
                    "code": "new",
                    "name": "Новое"
                },
                ...
            ]
        }

        Returns:
            List[Dict[str, Any]]: List of status dictionaries.
                                 Returns empty list if API call fails.

        Raises:
            ServiceAPIError: If the API request fails due to timeout, connection
                            error, or server error.
        """
        try:
            result = await fetch_api_data(
                method="GET",
                url="/api/v1/statuses/",
            )
            if result and isinstance(result, dict):
                return result.get("items", [])
            elif isinstance(result, list):
                return result
            return []
        except ServiceAPIError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in get_statuses: {e}")
            return []

    async def get_district_by_id(self, district_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetch a single district by its ID.

        Calls internal endpoint: GET /api/v1/districts/{district_id}

        Expected response format:
        {
            "id": 1,
            "name": "District Name",
            "description": "Description",
            "is_active": true,
            "geometry": {...},
            ...
        }

        Args:
            district_id: The ID of the district to fetch.

        Returns:
            Optional[Dict[str, Any]]: District data dictionary if found, None otherwise.
                                     Returns None if API call fails or district not found.

        Raises:
            ServiceAPIError: If the API request fails due to timeout, connection
                            error, or server error.
        """
        try:
            result = await fetch_api_data(
                method="GET",
                url=f"/api/v1/districts/{district_id}",
            )
            # Check if result is an error response (contains 'error' key)
            if result and isinstance(result, dict) and "error" in result:
                return None
            return result if result else None
        except ServiceAPIError as e:
            # 404 errors will be caught here, return None for not found
            if e.status_code == 404:
                return None
            raise
        except Exception as e:
            logger.error(f"Unexpected error in get_district_by_id: {e}")
            return None

    async def get_request_by_id(self, request_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetch a single request (appeal) by its ID.

        Calls internal endpoint: GET /api/v1/requests/{request_id}

        Expected response format:
        {
            "id": 1,
            "title": "Request Title",
            "description": "Description",
            "status": {
                "id": 1,
                "code": "new",
                "name": "Новое"
            },
            "category": {
                "id": 1,
                "name": "Category Name"
            },
            "district": {
                "id": 1,
                "name": "District Name"
            },
            "user": {
                "first_name": "John",
                "last_name": "Doe"
            },
            "created_at": "2024-01-01T10:00:00",
            ...
        }

        Args:
            request_id: The ID of the request to fetch.

        Returns:
            Optional[Dict[str, Any]]: Request data dictionary if found, None otherwise.
                                     Returns None if API call fails or request not found.

        Raises:
            ServiceAPIError: If the API request fails due to timeout, connection
                            error, or server error.
        """
        try:
            result = await fetch_api_data(
                method="GET",
                url=f"/api/v1/requests/{request_id}",
            )
            # Check if result is an error response (contains 'error' key)
            if result and isinstance(result, dict) and "error" in result:
                return None
            return result if result else None
        except ServiceAPIError as e:
            # 404 errors will be caught here, return None for not found
            if e.status_code == 404:
                return None
            raise
        except Exception as e:
            logger.error(f"Unexpected error in get_request_by_id: {e}")
            return None

    async def get_request_messages(
        self,
        request_id: int,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Fetch messages for a specific request from the API.

        Calls internal endpoint: GET /api/v1/requests/{request_id}/messages/

        Expected response format:
        {
            "items": [
                {
                    "id": 1,
                    "text": "Message text",
                    "sender": {
                        "id": 5,
                        "first_name": "John",
                        "last_name": "Doe"
                    },
                    "created_at": "2024-01-01T10:00:00",
                    ...
                },
                ...
            ],
            "total": 10,
            "skip": 0,
            "limit": 50
        }

        Args:
            request_id: The ID of the request to fetch messages for.
            skip: Number of records to skip for pagination. Defaults to 0.
            limit: Maximum number of records to return. Defaults to 50.

        Returns:
            List[Dict[str, Any]]: List of message dictionaries.
                                 Returns empty list if API call fails.

        Raises:
            ServiceAPIError: If the API request fails due to timeout, connection
                            error, or server error.
        """
        params = {"skip": skip, "limit": limit}
        try:
            result = await fetch_api_data(
                method="GET",
                url=f"/api/v1/requests/{request_id}/messages/",
                params=params,
            )
            if result and isinstance(result, dict):
                return result.get("items", [])
            elif isinstance(result, list):
                return result
            return []
        except ServiceAPIError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in get_request_messages: {e}")
            return []

    async def get_request_status_history(
        self,
        request_id: int,
    ) -> List[Dict[str, Any]]:
        """
        Fetch status history for a specific request from the API.

        Calls internal endpoint: GET /api/v1/requests/{request_id}/status-history

        Expected response format:
        [
            {
                "id": 1,
                "status": {
                    "id": 1,
                    "code": "new",
                    "name": "Новое"
                },
                "changed_at": "2024-01-01T10:00:00",
                "changed_by": {
                    "id": 5,
                    "first_name": "John",
                    "last_name": "Doe"
                },
                ...
            },
            ...
        ]

        Args:
            request_id: The ID of the request to fetch status history for.

        Returns:
            List[Dict[str, Any]]: List of status history entries.
                                 Returns empty list if API call fails.

        Raises:
            ServiceAPIError: If the API request fails due to timeout, connection
                            error, or server error.
        """
        try:
            result = await fetch_api_data(
                method="GET",
                url=f"/api/v1/requests/{request_id}/status-history",
            )
            if result and isinstance(result, list):
                return result
            elif result and isinstance(result, dict):
                return result.get("items", [])
            return []
        except ServiceAPIError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in get_request_status_history: {e}")
            return []