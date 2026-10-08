"""Client for the MyPT dedicated media server.

This module provides the MyPTMediaClient class for communicating with the
dedicated diagram/media server. The media server handles diagram content
(images and additional text) separately from the main MyPT database.

The API key is a server-to-server secret. It is never sent to the browser, the
mobile app or the student - only from the MyPT backend to this service.
"""

import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class MyPTMediaClient:
    """Client for communicating with the MyPT dedicated media server."""
    
    def __init__(self, base_url=None, api_key=None, api_header='X-API-Key', timeout=30):
        """Initialize the media client.
        
        Args:
            base_url: Base URL of the media server (defaults to settings)
            api_key: API key for authentication (defaults to settings)
            api_header: Header name for API key (default: X-API-Key)
            timeout: Request timeout in seconds (default: 30)
        """
        self.base_url = (base_url or settings.MYPT_MEDIA_API_URL).rstrip('/')
        self.api_key = api_key or settings.MYPT_MEDIA_API_KEY
        self.headers = {api_header: self.api_key} if self.api_key else {}
        self.timeout = timeout or getattr(settings, 'MYPT_MEDIA_TIMEOUT', 5)
        
        # Simple in-memory cache for diagram data during export generation
        self._cache = {}
        
    def _url(self, *parts):
        """Build URL from path parts."""
        parts = tuple(str(p).strip('/') for p in parts if str(p).strip('/'))
        path = '/'.join(parts)
        return self.base_url + '/api/' + path + '/'
    
    def get_document(self, report_reference):
        """GET /api/diagrams/<reference>/ ; always returns a payload.
        
        Args:
            report_reference: The MyPT report reference (e.g., weekly_report.id)
            
        Returns:
            dict: Diagram document data or empty payload if not exists
            
        Raises:
            requests.RequestException: If the request fails
        """
        # Check cache first
        cache_key = f'document_{report_reference}'
        if cache_key in self._cache:
            logger.debug(f"Cache hit for document {report_reference}")
            return self._cache[cache_key]
        
        if not self.base_url:
            logger.warning("MYPT_MEDIA_API_URL not configured, returning empty document")
            return self._empty_document_payload(report_reference)
        
        try:
            response = requests.get(
                self._url('diagrams', report_reference, ''),
                headers=self.headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            
            # Cache the result
            self._cache[cache_key] = data
            logger.info(f"Successfully retrieved diagram document for {report_reference}")
            return data
            
        except requests.RequestException as e:
            logger.error(f"Failed to retrieve diagram document for {report_reference}: {e}")
            return self._empty_document_payload(report_reference)
    
    def _empty_document_payload(self, report_reference):
        """Return empty document payload when diagram doesn't exist or server unavailable."""
        return {
            'exists': False,
            'report_reference': report_reference,
            'uuid': None,
            'text': '',
            'image': None,
            'images': [],
            'created_at': None,
            'updated_at': None,
        }
    
    def create_document(self, report_reference, text=''):
        """POST /api/diagrams/ - create content for a report reference.
        
        Args:
            report_reference: The MyPT report reference (e.g., weekly_report.id)
            text: Optional additional text for the diagram
            
        Returns:
            dict: Created diagram document data
            
        Raises:
            requests.RequestException: If the request fails
        """
        if not self.base_url:
            logger.warning("MYPT_MEDIA_API_URL not configured, returning empty document")
            return self._empty_document_payload(report_reference)
        
        try:
            response = requests.post(
                self._url('diagrams/'),
                json={'report_reference': report_reference, 'text': text},
                headers=self.headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            
            # Cache the result
            cache_key = f'document_{report_reference}'
            self._cache[cache_key] = data
            logger.info(f"Successfully created diagram document for {report_reference}")
            return data
            
        except requests.RequestException as e:
            logger.error(f"Failed to create diagram document for {report_reference}: {e}")
            raise

    def save_text(self, report_reference, text):
        """PUT /api/diagrams/<reference>/ - replace the stored additional text (upsert).
        
        Args:
            report_reference: The MyPT report reference (e.g., weekly_report.id)
            text: Text content to save
            
        Returns:
            dict: Updated diagram document data
            
        Raises:
            requests.RequestException: If the request fails
        """
        if not self.base_url:
            logger.warning("MYPT_MEDIA_API_URL not configured, returning empty document")
            return self._empty_document_payload(report_reference)
        
        try:
            response = requests.put(
                self._url('diagrams', report_reference, ''),
                json={'text': text},
                headers=self.headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            
            # Update cache
            cache_key = f'document_{report_reference}'
            self._cache[cache_key] = data
            logger.info(f"Successfully saved text for diagram {report_reference}")
            return data
            
        except requests.RequestException as e:
            logger.error(f"Failed to save text for diagram {report_reference}: {e}")
            raise

    def set_image(self, report_reference, image_path_or_file):
        """POST /api/diagrams/<reference>/image/ - set the main illustration.
        
        Args:
            report_reference: The MyPT report reference (e.g., weekly_report.id)
            image_path_or_file: Path to image file or file-like object
            
        Returns:
            dict: Response with image and document data
            
        Raises:
            requests.RequestException: If the request fails
        """
        if not self.base_url:
            logger.warning("MYPT_MEDIA_API_URL not configured")
            raise ValueError("MYPT_MEDIA_API_URL not configured")
        
        try:
            with open(image_path_or_file, 'rb') as fh:
                response = requests.post(
                    self._url('diagrams', report_reference, 'image/'),
                    files={'image': fh},
                    headers=self.headers,
                    timeout=self.timeout,
                )
            response.raise_for_status()
            data = response.json()
            
            # Clear cache for this document since image changed
            cache_key = f'document_{report_reference}'
            if cache_key in self._cache:
                del self._cache[cache_key]
            
            logger.info(f"Successfully set image for diagram {report_reference}")
            return data
            
        except requests.RequestException as e:
            logger.error(f"Failed to set image for diagram {report_reference}: {e}")
            raise

    def delete_image(self, report_reference, image_id=None):
        """DELETE /api/diagrams/<reference>/image/ - remove image(s).
        
        Args:
            report_reference: The MyPT report reference (e.g., weekly_report.id)
            image_id: Optional specific image ID to delete, otherwise deletes all
            
        Returns:
            dict: Response with deletion confirmation and document data
            
        Raises:
            requests.RequestException: If the request fails
        """
        if not self.base_url:
            logger.warning("MYPT_MEDIA_API_URL not configured")
            raise ValueError("MYPT_MEDIA_API_URL not configured")
        
        try:
            query = f'?image_id={image_id}' if image_id else ''
            response = requests.delete(
                self._url('diagrams', report_reference, 'image/') + query,
                headers=self.headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            
            # Clear cache for this document since image changed
            cache_key = f'document_{report_reference}'
            if cache_key in self._cache:
                del self._cache[cache_key]
            
            logger.info(f"Successfully deleted image for diagram {report_reference}")
            return data
            
        except requests.RequestException as e:
            logger.error(f"Failed to delete image for diagram {report_reference}: {e}")
            raise

    def delete_document(self, report_reference):
        """DELETE /api/diagrams/<reference>/ - delete content + all its images.
        
        Args:
            report_reference: The MyPT report reference (e.g., weekly_report.id)
            
        Raises:
            requests.RequestException: If the request fails
        """
        if not self.base_url:
            logger.warning("MYPT_MEDIA_API_URL not configured")
            raise ValueError("MYPT_MEDIA_API_URL not configured")
        
        try:
            response = requests.delete(
                self._url('diagrams', report_reference, ''),
                headers=self.headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            
            # Clear cache for this document
            cache_key = f'document_{report_reference}'
            if cache_key in self._cache:
                del self._cache[cache_key]
            
            logger.info(f"Successfully deleted diagram document {report_reference}")
            
        except requests.RequestException as e:
            logger.error(f"Failed to delete diagram document {report_reference}: {e}")
            raise

    def clear_cache(self):
        """Clear the in-memory cache."""
        self._cache.clear()
        logger.debug("Diagram client cache cleared")