import unittest

from app.catalog import _apply_lululemon_detail_cache
from app.lululemon_scraper import (
    _apply_pdp_details,
    _apply_schema_details,
    _normalize,
)


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
        self.assertEqual(product["material_details"], [])
        self.assertEqual(product["material"], "")
        self.assertEqual(product["price_known"], False)

    def test_excludes_non_clothing_products(self):
        product = _normalize(
            "https://shop.lululemon.com/p/water-bottles/"
            "Insulated-Mug-20oz/_/prod11680434",
            "2026-06-30",
        )

        self.assertIsNone(product)

    def test_applies_pdp_details(self):
        product = _normalize(
            "https://shop.lululemon.com/p/men-ss-tops/"
            "Zeroed-In-Short-Sleeve-Shirt/_/prod11680098",
            "2026-06-30",
        )
        pdp_data = {
            "productCarousel": [
                {
                    "color": {"name": "Seafoam"},
                    "imageInfo": [
                        "https://images.lululemon.com/is/image/lululemon/LM3GFNS_0284_1"
                    ],
                }
            ],
            "colorAttributes": [
                {
                    "styleColorId": "LM3GFNS-0284",
                    "careAndContent": {
                        "sections": [
                            {
                                "attributes": [
                                    {
                                        "list": {
                                            "title": "Body",
                                            "items": ["61% Organic Cotton", "32% Polyester"],
                                        },
                                        "text": "",
                                    },
                                    {
                                        "list": {
                                            "title": "Rib",
                                            "items": ["95% Cotton", "5% Elastane"],
                                        },
                                        "text": "",
                                    }
                                ]
                            }
                        ]
                    },
                    "fabricOrBenefits": {
                        "title": "Soft Cotton-Blend Fabric",
                        "sections": [
                            {
                                "attributes": [
                                    {"text": "Four-way stretch", "list": None}
                                ]
                            }
                        ],
                    },
                }
            ],
        }

        _apply_pdp_details(product, pdp_data)

        self.assertEqual(product["style_number"], "LM3GFNS")
        self.assertEqual(product["available_colors"], ["Seafoam"])
        self.assertIn("LM3GFNS_0284_1", product["image"])
        self.assertEqual(product["material_details"], ["Body: 61% Organic Cotton, 32% Polyester"])
        self.assertEqual(
            product["innovations"],
            ["Soft Cotton-Blend Fabric", "Four-way stretch"],
        )

    def test_applies_schema_details(self):
        product = _normalize(
            "https://shop.lululemon.com/p/men-ss-tops/"
            "Zeroed-In-Short-Sleeve-Shirt/_/prod11680098",
            "2026-06-30",
        )
        schema = {
            "@type": "ProductGroup",
            "image": "https://images.lululemon.com/is/image/lululemon/LM3GFNS_0284_1",
            "hasVariant": [
                {
                    "color": "Black",
                    "image": "https://images.lululemon.com/is/image/lululemon/LM3GFNS_0001_1",
                    "offers": [
                        {
                            "price": "58.00",
                            "availability": "https://schema.org/InStock",
                        }
                    ],
                },
                {
                    "color": "Seafoam",
                    "image": "https://images.lululemon.com/is/image/lululemon/LM3GFNS_0284_1",
                    "offers": [
                        {
                            "price": "58.00",
                            "availability": "https://schema.org/OutOfStock",
                        }
                    ],
                },
            ],
        }

        _apply_schema_details(product, schema)

        self.assertEqual(product["style_number"], "LM3GFNS")
        self.assertEqual(product["available_colors"], ["Black"])
        self.assertEqual(product["unavailable_colors"], ["Seafoam"])
        self.assertEqual(len(product["color_variants"]), 2)
        self.assertIn("LM3GFNS_0284_1", product["image"])
        self.assertEqual(product["price_min"], 58)
        self.assertEqual(product["price_max"], 58)
        self.assertTrue(product["price_known"])

    def test_applies_browser_detail_cache(self):
        product = _normalize(
            "https://shop.lululemon.com/p/men-ss-tops/"
            "Zeroed-In-Short-Sleeve-Shirt/_/prod11680098",
            "2026-06-30",
        )
        details = {
            "prod11680098": {
                "color_variants": [
                    {
                        "color": "Black",
                        "image": "https://images.lululemon.com/is/image/lululemon/LM3GFNS_0001_1",
                        "url": product["url"],
                        "available": True,
                    },
                    {
                        "color": "Lavender Frost",
                        "image": "https://images.lululemon.com/is/image/lululemon/LM3GFNS_064615_1",
                        "url": product["url"],
                        "available": False,
                    },
                ],
                "available_colors": ["Black"],
                "unavailable_colors": ["Lavender Frost"],
                "material_details": [
                    "Body: 61% Organic Cotton, 32% Polyester (recycled), 7% Elastane"
                ],
                "innovations": ["Four-way stretch", "Sweat-wicking"],
            }
        }

        enriched = _apply_lululemon_detail_cache([product], details)[0]

        self.assertEqual(enriched["available_colors"], ["Black"])
        self.assertEqual(enriched["unavailable_colors"], ["Lavender Frost"])
        self.assertEqual(enriched["style_number"], "LM3GFNS")
        self.assertEqual(
            enriched["material"],
            "Body: 61% Organic Cotton, 32% Polyester (recycled), 7% Elastane",
        )
        self.assertEqual(enriched["innovations"], ["Four-way stretch", "Sweat-wicking"])


if __name__ == "__main__":
    unittest.main()
