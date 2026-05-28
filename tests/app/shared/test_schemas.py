from app.shared.schemas import FilterPage


class TestFilterPage:
    @staticmethod
    def test_with_updates_keeps_existing_values_and_merges_new_fields() -> None:
        page_filter = FilterPage.build(page=1, limit=20, name="pikachu")

        updated = page_filter.with_updates(offset=40, type="electric", name=None)

        assert updated.page == 1
        assert updated.limit == 20
        assert updated.offset == 40
        assert updated.name == "pikachu"
        assert updated.type == "electric"

    @staticmethod
    def test_build_merges_existing_page_filter_and_updates() -> None:
        base = FilterPage.build(page=1, limit=12, status="INCOMPLETE")

        merged = FilterPage.build(base, limit=24, region="kanto")

        assert merged.page == 1
        assert merged.limit == 24
        assert merged.status == "INCOMPLETE"
        assert merged.region == "kanto"
