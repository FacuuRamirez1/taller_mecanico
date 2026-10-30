"""Servicio de usuarios, autenticación y personal (design §D1, C-04, C-05, C-06).

Arquitectura: Router -> Service -> UoW -> Repository -> Model.
El servicio opera sobre `UsuariosUnitOfWork` y delega las transacciones a este.
El `sessionmaker` se utiliza exclusivamente para la transacción aislada de `intento_acceso` (RN-08).
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status

from app.core.config import Settings
from app.core.paginacion import Pagina
from app.core.security import crear_token_acceso, hash_password, verify_password
from app.modules.clientes.models import Cliente
from app.modules.usuarios import schemas
from app.modules.usuarios.models import (
    AsignacionRol,
    EventoSeguridad,
    IntentoAcceso,
    Usuario,
)
from app.modules.usuarios.unit_of_work import UsuariosUnitOfWork


class UsuarioService:
    def __init__(self, uow: UsuariosUnitOfWork, sessionmaker: Any) -> None:
        self.uow = uow
        self.sessionmaker = sessionmaker

    async def login(
        self,
        datos: schemas.LoginRequest,
        ip: str,
        settings: Settings,
        app_hash_ficticio: str,
    ) -> tuple[Usuario, str, list[str]]:
        # 1. Límite de intentos primero (RN-08) sin calcular ningún hash
        fallos = await self.uow.intentos.contar_fallos_recientes(
            email=datos.email, ip=ip, ventana_segundos=60
        )
        if fallos >= 5:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Demasiados intentos fallidos. Intente nuevamente más tarde",
                headers={"Retry-After": "60"},
            )

        # 2. Verificación contra hash de usuario o hash ficticio precalculado
        usuario = await self.uow.usuarios.get_by_email(datos.email)
        if usuario is not None and usuario.activo:
            password_valida = await verify_password(datos.password, usuario.password_hash)
        else:
            await verify_password(datos.password, app_hash_ficticio)
            password_valida = False

        # 3. Anotar intento_acceso en sesión y transacción propias (se confirma siempre).
        # Checklist Ej. 7 (US-034): Es la ÚNICA escritura que no comparte la transacción
        # de su petición.
        # Costo: deja filas en intento_acceso aunque la petición falle, sea rechazada
        # por credenciales inválidas (401) o por rate limit (429) (RN-08).
        async with self.sessionmaker() as ses_intento:
            intento = IntentoAcceso(
                email=datos.email,
                ip=ip,
                exito=password_valida,
            )
            ses_intento.add(intento)
            await ses_intento.commit()

        if not password_valida or usuario is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales inválidas",
            )

        # 4. Emisión del token con roles vigentes al emitir
        roles_vigentes = await self.uow.roles.listar_vigentes_por_usuario(usuario.id)  # type: ignore[arg-type]
        token = crear_token_acceso(
            usuario_id=usuario.id,
            roles=roles_vigentes,
            settings=settings,
        )
        return usuario, token, roles_vigentes

    async def registro(
        self, datos: schemas.RegistroRequest, settings: Settings
    ) -> Usuario:
        # Hash antes de abrir la transacción
        hash_pw = await hash_password(datos.password, settings.BCRYPT_COST)

        async with self.uow:
            usuario = Usuario(
                email=datos.email,
                nombre=datos.nombre,
                password_hash=hash_pw,
                activo=True,
                debe_cambiar_password=False,
            )
            await self.uow.usuarios.add(usuario)

            asignacion = AsignacionRol(
                usuario_id=usuario.id,
                rol=schemas.RolEnum.CLIENTE,
                otorgada_por=None,
            )
            await self.uow.roles.add(asignacion)

            cliente = Cliente(
                usuario_id=usuario.id,
                nombre=datos.nombre,
                documento=datos.documento,
                telefono=datos.telefono,
            )
            await self.uow.clientes.add(cliente)

            evento = EventoSeguridad(
                actor=usuario.email,
                accion="Auto-registro de cliente",
            )
            await self.uow.eventos.add(evento)

        return usuario

    async def cambiar_password(
        self,
        usuario: Usuario,
        datos: schemas.CambioPassword,
        settings: Settings,
    ) -> str:
        valida = await verify_password(datos.password_actual, usuario.password_hash)
        if not valida:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Contraseña actual incorrecta",
            )

        nuevo_hash = await hash_password(datos.password_nueva, settings.BCRYPT_COST)
        ahora = datetime.now(timezone.utc)

        async with self.uow:
            usuario.password_hash = nuevo_hash
            usuario.password_cambiada_en = ahora
            usuario.debe_cambiar_password = False
            await self.uow.usuarios.update(usuario)

            evento = EventoSeguridad(
                actor=usuario.email, accion="Cambio de contraseña"
            )
            await self.uow.eventos.add(evento)

        # Emitir el token nuevo estrictamente posterior a password_cambiada_en
        iat_nuevo = datetime.now(timezone.utc)
        if iat_nuevo <= ahora:
            iat_nuevo = ahora + timedelta(microseconds=1000)

        roles = await self.uow.roles.listar_vigentes_por_usuario(usuario.id)  # type: ignore[arg-type]
        return crear_token_acceso(
            usuario_id=usuario.id,
            roles=roles,
            settings=settings,
            iat=iat_nuevo,
        )

    async def obtener_yo(self, usuario: Usuario) -> schemas.UsuarioYoResponse:
        roles_vigentes = await self.uow.roles.listar_vigentes_por_usuario(usuario.id)  # type: ignore[arg-type]
        roles_token = getattr(usuario, "_roles_token", [])
        return schemas.UsuarioYoResponse(
            id=usuario.id,  # type: ignore[arg-type]
            email=usuario.email,
            nombre=usuario.nombre,
            activo=usuario.activo,
            debe_cambiar_password=usuario.debe_cambiar_password,
            roles=roles_vigentes,
            roles_token=roles_token,
        )

    async def crear_personal(
        self,
        datos: schemas.UsuarioPersonalCreate,
        admin_id: int,
        admin_email: str,
        settings: Settings,
    ) -> Usuario:
        """Alta de personal por parte de ADMIN."""
        hash_pw = await hash_password(datos.password, settings.BCRYPT_COST)

        async with self.uow:
            usuario = Usuario(
                email=datos.email,
                nombre=datos.nombre,
                password_hash=hash_pw,
                activo=True,
                debe_cambiar_password=True,
            )
            await self.uow.usuarios.add(usuario)

            asignacion = AsignacionRol(
                usuario_id=usuario.id,
                rol=datos.rol,
                otorgada_por=admin_id,
            )
            await self.uow.roles.add(asignacion)

            evento = EventoSeguridad(
                actor=admin_email,
                accion=f"Alta de usuario {usuario.email} con rol {datos.rol.value}",
            )
            await self.uow.eventos.add(evento)

        return usuario

    async def listar_roles_usuario(self, usuario_id: int) -> list[AsignacionRol]:
        usuario = await self.uow.usuarios.get_by_id(usuario_id)
        if usuario is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado",
            )
        return await self.uow.roles.listar_por_usuario(usuario_id)

    async def asignar_rol(
        self,
        usuario_id: int,
        datos: schemas.AsignacionRolCreate,
        admin_id: int,
        admin_email: str,
    ) -> AsignacionRol:
        usuario = await self.uow.usuarios.get_by_id(usuario_id)
        if usuario is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado",
            )

        # Verificar si ya posee el rol vigente
        asignacion_vigente = await self.uow.roles.obtener_vigente(usuario_id, datos.rol)
        if asignacion_vigente is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"El usuario ya posee el rol {datos.rol.value} vigente",
            )

        async with self.uow:
            # Si hay una fila previa que venció pero aún no tiene revocada_en, la cerramos
            asignacion_vencida = await self.uow.roles.obtener_vencida_abierta(
                usuario_id, datos.rol
            )
            if asignacion_vencida is not None:
                asignacion_vencida.revocada_en = datetime.now(timezone.utc)
                await self.uow.roles.update(asignacion_vencida)

            nueva_asignacion = AsignacionRol(
                usuario_id=usuario_id,
                rol=datos.rol,
                vence_en=datos.vence_en,
                otorgada_por=admin_id,
            )
            await self.uow.roles.add(nueva_asignacion)

            evento = EventoSeguridad(
                actor=admin_email,
                accion=f"Asignación de rol {datos.rol.value} a usuario {usuario.email}",
            )
            await self.uow.eventos.add(evento)

        return nueva_asignacion

    async def revocar_rol(
        self,
        usuario_id: int,
        rol: schemas.RolEnum,
        admin_id: int,
        admin_email: str,
    ) -> schemas.MensajeResponse:
        usuario = await self.uow.usuarios.get_by_id(usuario_id)
        if usuario is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado",
            )

        # Regla RN-05: Autoprotección del administrador
        if admin_id == usuario_id and rol == schemas.RolEnum.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Un administrador no puede revocarse su propio rol ADMIN",
            )

        if rol == schemas.RolEnum.ADMIN:
            cant_admins_vigentes = await self.uow.roles.contar_admins_vigentes()
            if cant_admins_vigentes <= 1:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="No se puede revocar el rol: el sistema no puede quedar sin administradores vigentes",
                )

        asignacion = await self.uow.roles.obtener_vigente(usuario_id, rol)
        if asignacion is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"El usuario no tiene una asignación vigente del rol {rol.value}",
            )

        async with self.uow:
            asignacion.revocada_en = datetime.now(timezone.utc)
            await self.uow.roles.update(asignacion)

            evento = EventoSeguridad(
                actor=admin_email,
                accion=f"Revocación de rol {rol.value} a usuario {usuario.email}",
            )
            await self.uow.eventos.add(evento)

        return schemas.MensajeResponse(mensaje=f"Rol {rol.value} revocado exitosamente")

    async def listar_eventos(
        self,
        page: int,
        size: int,
    ) -> Pagina[schemas.EventoSeguridadRead]:
        sentencia = self.uow.eventos.consulta_listar()
        return await self.uow.eventos.paginar(sentencia, page, size)
