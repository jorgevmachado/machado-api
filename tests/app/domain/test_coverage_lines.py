import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.domain.trainer.my_pokemon.service import MyPokemonService
from app.domain.trainer.my_pokemon.move.service import MyPokemonMoveService
from app.domain.trainer.pokedex.service import PokedexService


class TestMyPokemonServiceLines:
    """Test lines 75, 89-140 in my_pokemon/service.py"""

    @pytest.mark.asyncio
    async def test_create_line_75(self):
        """Line 75: return await self.create_owned_for_trainer(...)"""
        repository = AsyncMock()
        repository.session = AsyncMock()
        service = MyPokemonService(repository=repository)
        
        # Patch the actual method to verify it gets called
        with patch.object(
            service,
            "create_owned_for_trainer",
            new_callable=AsyncMock,
            return_value=MagicMock(),
        ) as mock_method:
            trainer = MagicMock()
            trainer.id = uuid4()
            payload = MagicMock()
            payload.pokemon_name = "test"
            payload.nickname = "test"
            
            await service.create(trainer=trainer, payload=payload)
            mock_method.assert_awaited()

    @pytest.mark.asyncio
    async def test_create_owned_exception_handler(self):
        """Lines 89-140: test exception handling in create_owned_for_trainer"""
        repository = AsyncMock()
        repository.session = AsyncMock()
        pokemon_service = AsyncMock()
        
        service = MyPokemonService(
            repository=repository,
            pokemon_service=pokemon_service,
        )
        
        # Make pokemon_service.find_detail raise exception
        pokemon_service.find_detail.side_effect = RuntimeError("Test error")
        
        trainer_id = uuid4()
        
        # With commit=True, should trigger rollback
        with pytest.raises(RuntimeError):
            await service.create_owned_for_trainer(
                trainer_id=trainer_id,
                pokemon_name="bulbasaur",
                nickname="test",
                commit=True,
            )
        
        # Verify rollback was called (line 139)
        repository.session.rollback.assert_awaited_once()


class TestMyPokemonMoveServiceLines:
    """Test lines 43-54, 57-64 in move/service.py"""

    @pytest.mark.asyncio
    async def test_sync_from_resources_main_loop(self):
        """Lines 43-54: sync_from_resources main loop"""
        repository = AsyncMock()
        service = MyPokemonMoveService(repository=repository)
        
        my_pokemon_id = uuid4()
        
        # Create mock moves
        move1 = MagicMock()
        move1.id = uuid4()
        move1.pp = 35
        
        # Mock the select_initial_moves to return moves
        with patch(
            "app.domain.trainer.my_pokemon.move.service.select_initial_moves",
            return_value=[move1],
        ):
            # Setup repository mocks
            repository.find_by.return_value = None
            created_move = MagicMock()
            repository.save.return_value = created_move
            
            result = await service.sync_from_resources(
                my_pokemon_id=my_pokemon_id,
                resources=[move1],
            )
            
            # Verify result contains the created move
            assert len(result) == 1
            assert result[0] == created_move

    @pytest.mark.asyncio
    async def test_get_or_create_find_existing(self):
        """Lines 57-62: get_or_create finds existing"""
        repository = AsyncMock()
        service = MyPokemonMoveService(repository=repository)
        
        my_pokemon_id = uuid4()
        pokemon_move_id = uuid4()
        existing = MagicMock()
        
        repository.find_by.return_value = existing
        
        result = await service.get_or_create(
            pp=35,
            max_pp=35,
            my_pokemon_id=my_pokemon_id,
            pokemon_move_id=pokemon_move_id,
        )
        
        # Verify returns existing (line 62)
        assert result == existing
        repository.save.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_get_or_create_save_new(self):
        """Lines 57-64: get_or_create creates new"""
        repository = AsyncMock()
        service = MyPokemonMoveService(repository=repository)
        
        my_pokemon_id = uuid4()
        pokemon_move_id = uuid4()
        new_move = MagicMock()
        
        repository.find_by.return_value = None
        repository.save.return_value = new_move
        
        result = await service.get_or_create(
            pp=35,
            max_pp=35,
            my_pokemon_id=my_pokemon_id,
            pokemon_move_id=pokemon_move_id,
        )
        
        # Verify returns new move (line 64)
        assert result == new_move
        repository.save.assert_awaited_once()


class TestPokedexServiceLines:
    """Test lines 55-84, 94-128, 139-156 in pokedex/service.py"""

    @pytest.mark.asyncio
    async def test_discover_main_flow(self):
        """Lines 55-84: discover method flow"""
        repository = AsyncMock()
        pokemon_service = AsyncMock()
        
        service = PokedexService(
            repository=repository,
            pokemon_service=pokemon_service,
        )
        service._invalidate_cache = AsyncMock()
        
        trainer = MagicMock()
        trainer.id = uuid4()
        
        pokedex = MagicMock()
        pokedex.discovered = False
        pokedex.id = uuid4()
        
        # Mock find_by to return pokedex twice (line 55, line 71)
        repository.find_by.side_effect = [pokedex, pokedex]
        pokemon_service.find_detail.return_value = MagicMock()
        repository.update = AsyncMock()
        
        result = await service.discover(trainer=trainer, pokemon_name="bulbasaur")
        
        # Verify update was called (line 69)
        repository.update.assert_awaited_once()
        assert result == pokedex

    @pytest.mark.asyncio
    async def test_discover_entity_not_found(self):
        """Lines 59-63: discover handles entity not found"""
        repository = AsyncMock()
        service = PokedexService(repository=repository)
        service._invalidate_cache = AsyncMock()
        
        trainer = MagicMock()
        trainer.id = uuid4()
        
        # Return None for find_by (line 55)
        repository.find_by.return_value = None
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await service.discover(trainer=trainer, pokemon_name="bulbasaur")
        
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_discover_fresh_none(self):
        """Lines 71-84: discover when fresh returns None"""
        repository = AsyncMock()
        pokemon_service = AsyncMock()
        
        service = PokedexService(
            repository=repository,
            pokemon_service=pokemon_service,
        )
        service._invalidate_cache = AsyncMock()
        
        trainer = MagicMock()
        trainer.id = uuid4()
        
        pokedex = MagicMock()
        pokedex.discovered = False
        
        repository.find_by.side_effect = [pokedex, None]
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await service.discover(trainer=trainer, pokemon_name="bulbasaur")
        
        assert exc_info.value.status_code == 500


    @pytest.mark.asyncio
    async def test_create_for_trainer_with_pokemon(self):
        """Lines 139-156: _create_for_trainer loop"""
        repository = AsyncMock()
        service = PokedexService(repository=repository)
        
        trainer_id = uuid4()
        pokemon = MagicMock()
        pokemon.id = uuid4()
        pokemon.name = "bulbasaur"
        
        pokedex = MagicMock()
        repository.save.return_value = pokedex
        
        with patch(
            "app.domain.trainer.pokedex.service.Pokedex",
        ):
            result = await service._create_for_trainer(
                trainer_id=trainer_id,
                pokemons=[pokemon],
                discovered_pokemon_name="bulbasaur",
                attributes_by_pokemon_id={pokemon.id: {}},
            )
        
        # Verify save was called (line 143)
        repository.save.assert_awaited()
        # Verify result contains saved pokedex (line 156)
        assert len(result) > 0
