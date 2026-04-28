def ensure_external_image(order: int | None) -> str:
    if not order:
        return ''
    formatted_order = str(order).zfill(3)
    return f'https://www.pokemon.com/static-assets/content-assets/cms2/img/pokedex/detail/{formatted_order}.png'
