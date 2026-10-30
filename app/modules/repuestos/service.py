"""Servicio de repuestos (design §D6).

Deuda declarada de C-03: el servicio usa `AsyncSession` directa y confirma al
final. C-06 mueve las consultas a repositorios y el `commit` al UnitOfWork sin
cambiar las firmas públicas ni los schemas.
"""

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.errores import traducir_integrity_error
from app.core.paginacion import Pagina, paginar
from app.modules.repuestos.models import (
    HistorialPrecioRepuesto,
    MovimientoStock,
    Repuesto,
)
from app.modules.repuestos.schemas import RepuestoCreate, RepuestoUpdate
from app.modules.usuarios.models import AsignacionRol, Usuario

# TODO C-06: mover consultas a repositorios y `commit` al UnitOfWork (firmas estables).

EMAIL_ACTOR_INTERNO = "admin@example.com"


class RepuestoService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _actor(self) -> Usuario:
        # TODO C-05: reemplazar el actor interno por el usuario autenticado.
        usuario = await self.session.scalar(
            select(Usuario).where(Usuario.email == EMAIL_ACTOR_INTERNO)
        )
        if usuario is None:
            usuario = await self.session.scalar(
                select(Usuario)
                .join(AsignacionRol, AsignacionRol.usuario_id == Usuario.id)
                .where(
                    AsignacionRol.rol == "ADMIN",
                    AsignacionRol.revocada_en.is_(None),
                    Usuario.activo.is_(True),
                )
                .order_by(Usuario.id)
            )
        if usuario is None:
            raise HTTPException(
                status_code=409,
                detail="No hay un usuario administrador para registrar la operación",
            )
        return usuario

    async def _obtener_vigente(self, repuesto_id: int) -> Repuesto:
        repuesto = await self.session.scalar(
            select(Repuesto).where(
                Repuesto.id == repuesto_id,
                Repuesto.borrado_en.is_(None),
            )
        )
        if repuesto is None:
            raise HTTPException(status_code=404, detail="Repuesto no encontrado")
        return repuesto

    async def listar(self, q: str | None, page: int, size: int) -> Pagina[Repuesto]:
        sentencia = select(Repuesto).where(Repuesto.borrado_en.is_(None))
        if q:
            sentencia = sentencia.where(Repuesto.descripcion.ilike(f"%{q}%"))
        sentencia = sentencia.order_by(Repuesto.id.desc())
        return await paginar(self.session, sentencia, page, size)

    async def obtener(self, repuesto_id: int) -> Repuesto:
        return await self._obtener_vigente(repuesto_id)

    async def crear(self, datos: RepuestoCreate) -> Repuesto:
        actor = await self._actor()
        repuesto = Repuesto(
            codigo=datos.codigo,
            descripcion=datos.descripcion,
            precio=datos.precio,
            stock=datos.stock_inicial,
        )
        self.session.add(repuesto)
        try:
            await self.session.flush()
            if datos.stock_inicial > 0:
                self.session.add(
                    MovimientoStock(
                        repuesto_id=repuesto.id,
                        orden_id=None,
                        usuario_id=actor.id,
                        cantidad=datos.stock_inicial,
                        motivo="Stock inicial",
                    )
                )
                await self.session.flush()
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise traducir_integrity_error(exc) from None
        return repuesto

    async def actualizar(self, repuesto_id: int, datos: RepuestoUpdate) -> Repuesto:
        repuesto = await self._obtener_vigente(repuesto_id)
        cambios = datos.model_dump(exclude_unset=True)

        precio_nuevo: Decimal | None = cambios.get("precio")
        if precio_nuevo is not None and precio_nuevo != repuesto.precio:
            if precio_nuevo < repuesto.precio:
                raise HTTPException(
                    status_code=422,
                    detail="El precio no puede ser menor que el actual",
                )
            actor = await self._actor()
            self.session.add(
                HistorialPrecioRepuesto(
                    repuesto_id=repuesto.id,
                    usuario_id=actor.id,
                    precio_anterior=repuesto.precio,
                    precio_nuevo=precio_nuevo,
                )
            )
            repuesto.precio = precio_nuevo

        descripcion = cambios.get("descripcion")
        if descripcion is not None:
            repuesto.descripcion = descripcion

        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise traducir_integrity_error(exc) from None
        return repuesto

    async def dar_baja(self, repuesto_id: int) -> None:
        repuesto = await self._obtener_vigente(repuesto_id)
        repuesto.borrado_en = datetime.now(timezone.utc)
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise traducir_integrity_error(exc) from None

    async def reponer(self, repuesto_id: int, cantidad: int) -> Repuesto:
        repuesto = await self._obtener_vigente(repuesto_id)
        actor = await self._actor()
        repuesto.stock += cantidad
        self.session.add(
            MovimientoStock(
                repuesto_id=repuesto.id,
                orden_id=None,
                usuario_id=actor.id,
                cantidad=cantidad,
                motivo="Reposición",
            )
        )
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise traducir_integrity_error(exc) from None
        return repuesto

    async def movimientos(self, repuesto_id: int) -> list[MovimientoStock]:
        await self._obtener_vigente(repuesto_id)
        resultado = await self.session.execute(
            select(MovimientoStock)
            .where(MovimientoStock.repuesto_id == repuesto_id)
            .order_by(MovimientoStock.cuando.desc(), MovimientoStock.id.desc())
        )
        return list(resultado.scalars().all())

    async def precios(self, repuesto_id: int) -> list[HistorialPrecioRepuesto]:
        await self._obtener_vigente(repuesto_id)
        resultado = await self.session.execute(
            select(HistorialPrecioRepuesto)
            .where(HistorialPrecioRepuesto.repuesto_id == repuesto_id)
            .order_by(
                HistorialPrecioRepuesto.cuando.desc(),
                HistorialPrecioRepuesto.id.desc(),
            )
        )
        return list(resultado.scalars().all())
