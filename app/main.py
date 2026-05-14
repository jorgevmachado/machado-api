from http import HTTPStatus

from fastapi import FastAPI
from fastapi_pagination import add_pagination


from app.core.logging import configure_logging
from app.shared.schemas import Message

from app.domain.auth.route import router as auth_router
from app.domain.my_pokemon.route import router as my_pokemon_router
from app.domain.pokemon.route import router as pokemon_router
from app.domain.trainer.route import router as trainer_router


configure_logging()
app = FastAPI()

add_pagination(app)

app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(my_pokemon_router)
app.include_router(pokemon_router)
app.include_router(trainer_router)


@app.get("/", status_code=HTTPStatus.OK, response_model=Message)
def read_root():
    return {"message": "Hello World!"}
