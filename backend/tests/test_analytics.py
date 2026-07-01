import unittest

from app.analytics import build_dashboard


class StraussVariantAggregationTests(unittest.TestCase):
    def test_strauss_colors_are_merged_into_one_product(self):
        products = [
            {
                "id": "strauss:variant-1",
                "source_id": "variant-1",
                "product_id": "product-1",
                "brand": "strauss",
                "brand_label": "Strauss",
                "title": "Artwork T-Shirt",
                "categories": ["Shirts"],
                "subcategories": ["T-Shirts"],
                "audiences": ["men"],
                "audience_labels": ["Men"],
                "collections": ["e.s.e:pic"],
                "available_colors": ["black"],
                "unavailable_colors": [],
                "color": "black",
                "image": "https://example.com/black.jpg",
                "url": "https://example.com/product?variant=1",
                "available": True,
                "price_min": 25,
                "price_max": 25,
                "variant_count": 5,
            },
            {
                "id": "strauss:variant-2",
                "source_id": "variant-2",
                "product_id": "product-1",
                "brand": "strauss",
                "brand_label": "Strauss",
                "title": "Artwork T-Shirt",
                "categories": ["Shirts"],
                "subcategories": ["T-Shirts"],
                "audiences": ["men"],
                "audience_labels": ["Men"],
                "collections": ["e.s.e:pic"],
                "available_colors": ["almondbrown"],
                "unavailable_colors": [],
                "color": "almondbrown",
                "image": "https://example.com/almondbrown.jpg",
                "url": "https://example.com/product?variant=2",
                "available": True,
                "price_min": 25,
                "price_max": 25,
                "variant_count": 4,
            },
        ]

        dashboard = build_dashboard(products, "test", "2026-06-24")
        product = dashboard["products"][0]

        self.assertEqual(dashboard["summary"]["total_products"], 2)
        self.assertEqual(dashboard["categories"], [{"name": "Shirts", "value": 2}])
        self.assertEqual(
            dashboard["subcategories"],
            [{"name": "T-Shirts", "value": 2}],
        )
        self.assertEqual(len(dashboard["products"]), 1)
        self.assertEqual(product["available_colors"], ["black", "almondbrown"])
        self.assertEqual(len(product["color_variants"]), 2)
        self.assertEqual(product["variant_count"], 9)

    def test_other_brands_keep_individual_rows(self):
        products = [
            {
                "id": "arcteryx:1",
                "product_id": "same-product",
                "brand": "arcteryx",
                "brand_label": "Arc'teryx",
                "title": "Product one",
                "categories": ["Shirts and Tops"],
                "price_min": 100,
                "price_max": 100,
                "available": True,
            },
            {
                "id": "arcteryx:2",
                "product_id": "same-product",
                "brand": "arcteryx",
                "brand_label": "Arc'teryx",
                "title": "Product two",
                "categories": ["Shirts and Tops"],
                "price_min": 120,
                "price_max": 120,
                "available": True,
            },
        ]

        dashboard = build_dashboard(products, "test", "2026-06-24")

        self.assertEqual(dashboard["summary"]["total_products"], 2)
        self.assertEqual(len(dashboard["products"]), 2)

    def test_lululemon_styles_are_grouped_for_table_only(self):
        products = [
            {
                "id": "lululemon:one",
                "product_id": "prod-one",
                "style_number": "LM123",
                "brand": "lululemon",
                "brand_label": "lululemon",
                "title": "Zeroed In Shirt",
                "categories": ["T-Shirts"],
                "audiences": ["men"],
                "audience_labels": ["Men"],
                "available_colors": ["Black"],
                "color": "Black",
                "image": "https://example.com/black.jpg",
                "color_variants": [
                    {
                        "color": "Black",
                        "image": "https://example.com/black.jpg",
                        "url": "https://example.com/black",
                        "available": True,
                    }
                ],
                "material_details": ["Body: 61% Organic Cotton"],
                "innovations": ["Four-way stretch"],
                "price_min": 0,
                "price_max": 0,
                "price_known": False,
                "available": True,
            },
            {
                "id": "lululemon:two",
                "product_id": "prod-two",
                "style_number": "LM123",
                "brand": "lululemon",
                "brand_label": "lululemon",
                "title": "Zeroed In Shirt",
                "categories": ["T-Shirts"],
                "audiences": ["men"],
                "audience_labels": ["Men"],
                "available_colors": ["Seafoam"],
                "color": "Seafoam",
                "image": "https://example.com/seafoam.jpg",
                "color_variants": [
                    {
                        "color": "Seafoam",
                        "image": "https://example.com/seafoam.jpg",
                        "url": "https://example.com/seafoam",
                        "available": True,
                    }
                ],
                "material_details": ["Body: 61% Organic Cotton"],
                "innovations": ["Sweat-wicking"],
                "price_min": 0,
                "price_max": 0,
                "price_known": False,
                "available": True,
            },
        ]

        dashboard = build_dashboard(products, "test", "2026-07-01")
        product = dashboard["products"][0]

        self.assertEqual(dashboard["summary"]["total_products"], 2)
        self.assertEqual(dashboard["categories"], [{"name": "T-Shirts", "value": 2}])
        self.assertEqual(len(dashboard["products"]), 1)
        self.assertEqual(product["available_colors"], ["Black", "Seafoam"])
        self.assertEqual(len(product["color_variants"]), 2)
        self.assertEqual(product["innovations"], ["Four-way stretch", "Sweat-wicking"])


if __name__ == "__main__":
    unittest.main()
