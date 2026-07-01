import unittest

from app.lululemon_scraper import _normalize


class LululemonScraperTests(unittest.TestCase):
    def test_normalizes_apparel_product_from_sitemap_url(self):
        product = _normalize(
            "https://shop.lululemon.com/p/men-ss-tops/"
            "Zeroed-In-Short-Sleeve-Shirt/_/prod11680098",
            "2026-06-30",
        )

        self.assertIsNotNone(product)
        self.assertEqual(product["brand"], "lululemon")
        self.assertEqual(product["audiences"], ["men"])
        self.assertEqual(product["categories"], ["Short Sleeve Shirts"])
        self.assertEqual(product["subcategories"], [])
        self.assertEqual(product["price_known"], False)

    def test_excludes_non_clothing_products(self):
        product = _normalize(
            "https://shop.lululemon.com/p/water-bottles/"
            "Insulated-Mug-20oz/_/prod11680434",
            "2026-06-30",
        )

        self.assertIsNone(product)


if __name__ == "__main__":
    unittest.main()
