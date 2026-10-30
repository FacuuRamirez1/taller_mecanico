"""Paginación uniforme de los listados (design §D2).

`ParametrosPagina` valida `page >= 1` y `size` entre 1 y 100 antes de ejecutar
el handler (FastAPI responde 422). `paginar` cuenta con los mismos filtros de
la consulta y traduce una página inexistente a un 422 propio. Con cero
resultados devuelve una página vacía con `pages = 0` (Q-20).
"""

from math import ceil
from typing import Annotated, Any, Generic, TypeVar

from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import Select, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

T = TypeVar("T")

PAGE_MINIMO = 1
SIZE_DEFECTO = 20
SIZE_MAXIMO = 100


class ParametrosPagina:
    """Dependencia de `page`/`size`; fuera de rango lo rechaza FastAPI con 422."""

    def __init__(
        self,
        page: Annotated[int, Query(ge=PAGE_MINIMO)] = 1,
        size: Annotated[int, Query(ge=1, le=SIZE_MAXIMO)] = SIZE_DEFECTO,
    ) -> None:
        self.page = page
        self.size = size


PaginacionDep = Annotated[ParametrosPagina, Depends()]


class Pagina(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int
    pages: int


def calcular_paginas(total: int, size: int) -> int:
    """Cantidad de páginas; 0 cuando no hay resultados."""
    if total <= 0:
        return 0
    return ceil(total / size)


async def paginar(
    session: AsyncSession,
    sentencia: Select[Any],
    page: int,
    size: int,
) -> Pagina[Any]:
    """Cuenta con los mismos filtros, valida la página y devuelve el envoltorio."""
    conteo = select(func.count()).select_from(sentencia.order_by(None).subquery())
    total = int(await session.scalar(conteo) or 0)
    pages = calcular_paginas(total, size)
    if total > 0 and page > pages:
        raise HTTPException(status_code=422, detail=f"La página {page} no existe: hay {pages}")
    resultado = await session.execute(sentencia.offset((page - 1) * size).limit(size))
    items = list(resultado.scalars().all())
    return Pagina(items=items, total=total, page=page, size=size, pages=pages)
