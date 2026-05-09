import re
from urllib.parse import urlparse

class ScrapeValidator:
    def __init__(self, data):
        self.data = data
        self.errors = {}
    
    def validate(self):
        self._validate_url()
        return len(self.errors) == 0
    
    def _validate_url(self):
        url = self.data.get('url')
        
        if not url:
            self.errors['url'] = 'URL is required'
            return
        
        if not self._is_valid_url(url):
            self.errors['url'] = 'Invalid URL format'
            return
        
    def _is_valid_url(self, url):
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False
    
