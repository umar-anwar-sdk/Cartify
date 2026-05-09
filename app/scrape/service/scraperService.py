from ..utils.main import scrape_product

class ScraperService:
    def scrape_product_data(self, url):
        try:
            result = scrape_product(url, render_js=False)
            
            return {
                'title': result.get('name', ''),
                'site_name': result.get('site_name', 'others'),
                'price': result.get('price', ''),
                'images': result.get('gallery_images', []),
                'description': result.get('description', '')
            }
            
        except Exception as e:
            raise Exception(f"Failed to scrape product: {str(e)}")