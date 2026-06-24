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

        self.assertEqual(dashboard["summary"]["total_products"], 1)
        self.assertEqual(dashboard["categories"], [{"name": "Shirts", "value": 1}])
        self.assertEqual(
            dashboard["subcategories"],
            [{"name": "T-Shirts", "value": 1}],
        )
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


if __name__ == "__main__":
    unittest.main()
