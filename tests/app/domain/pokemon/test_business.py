from app.domain.pokemon.business import collect_evolution_names, stats_by_name


class TestPokemonBusiness:
    @staticmethod
    def test_stats_by_name_normalizes_keys() -> None:
        payload = {
            "stats": [
                {"base_stat": 45, "stat": {"name": "hp"}},
                {"base_stat": 49, "stat": {"name": "special-attack"}},
            ]
        }

        result = stats_by_name(payload)

        assert result == {"hp": 45, "special_attack": 49}

    @staticmethod
    def test_collect_evolution_names_handles_none() -> None:
        assert collect_evolution_names(None) == set()

    @staticmethod
    def test_collect_evolution_names_collects_nested_chain() -> None:
        chain = {
            "species": {"name": "bulbasaur"},
            "evolves_to": [
                {
                    "species": {"name": "ivysaur"},
                    "evolves_to": [{"species": {"name": "venusaur"}, "evolves_to": []}],
                }
            ],
        }

        result = collect_evolution_names(chain)

        assert result == {"bulbasaur", "ivysaur", "venusaur"}
