"""
Super Ozono Global — Seeder de datos base
Carga inicial del PUC, Centros de Costo, Períodos, Parámetros, Productos y Clientes
Basado en: SuperOzono_Carga_Inicial_Contable.xlsx
"""

import asyncio
import structlog
from decimal import Decimal
from sqlalchemy import select
from app.core.database import engine, async_session, Base
from app.modules.contabilidad.models import (
    PlanCuentas, CentroCosto, PeriodoContable,
    ParametroTributario, ParametroNomina,
    NaturalezaCuenta, ClaseCuenta, NivelCuenta,
    TipoCentroCosto, EstadoPeriodo,
)
from app.modules.ventas.models import (
    Producto, Cliente,
    UnidadMedida, CategoriaProducto,
)
from app.modules.usuarios.models import Usuario
from app.core.security import get_password_hash
from app.core.config import get_settings

logger = structlog.get_logger()
settings = get_settings()

# Password de fábrica: si sigue en uso, avisamos para que se cambie en producción.
_DEFAULT_ADMIN_PASSWORD = "Admin2026!"


# ══════════════════════════════════════════════════════════
# DATOS BASE DEL EXCEL
# ══════════════════════════════════════════════════════════

PLAN_CUENTAS_DATA = [
    # (código, nombre, clase, naturaleza, nivel, req_tercero, req_cc)
    ("1105", "Caja", "Activo", "Débito", "Auxiliar", False, True),
    ("1110", "Bancos", "Activo", "Débito", "Auxiliar", True, True),
    ("1305", "Clientes", "Activo", "Débito", "Auxiliar", True, False),
    ("1355", "Anticipo de impuestos y contribuciones", "Activo", "Débito", "Auxiliar", False, True),
    ("1435", "Mercancías no fabricadas por la empresa", "Activo", "Débito", "Auxiliar", False, True),
    ("1455", "Materias primas", "Activo", "Débito", "Auxiliar", False, True),
    ("1524", "Equipo de oficina", "Activo", "Débito", "Auxiliar", False, True),
    ("1528", "Equipo de cómputo y comunicación", "Activo", "Débito", "Auxiliar", False, True),
    ("2205", "Proveedores nacionales", "Pasivo", "Crédito", "Auxiliar", True, True),
    ("2335", "Costos y gastos por pagar", "Pasivo", "Crédito", "Auxiliar", True, True),
    ("2365", "Retención en la fuente", "Pasivo", "Crédito", "Auxiliar", False, True),
    ("2367", "Impuesto a las ventas retenido", "Pasivo", "Crédito", "Auxiliar", False, True),
    ("2368", "Impuesto de industria y comercio retenido", "Pasivo", "Crédito", "Auxiliar", False, True),
    ("2370", "Retenciones y aportes de nómina", "Pasivo", "Crédito", "Auxiliar", False, False),
    ("2380", "Acreedores varios", "Pasivo", "Crédito", "Auxiliar", True, False),
    ("2404", "IVA por pagar (generado)", "Pasivo", "Crédito", "Auxiliar", False, False),
    ("2408", "IVA descontable (compras)", "Pasivo", "Crédito", "Auxiliar", False, False),
    ("2412", "ICA por pagar", "Pasivo", "Crédito", "Auxiliar", False, False),
    ("3105", "Capital suscrito y pagado", "Patrimonio", "Crédito", "Auxiliar", False, False),
    ("3115", "Aportes sociales", "Patrimonio", "Crédito", "Auxiliar", False, False),
    ("3605", "Utilidad del ejercicio", "Patrimonio", "Crédito", "Auxiliar", False, False),
    ("3705", "Pérdidas acumuladas", "Patrimonio", "Débito", "Auxiliar", False, False),
    ("4135", "Comercio al por mayor y al por menor", "Ingreso", "Crédito", "Auxiliar", False, True),
    ("4175", "Devoluciones en ventas (DB)", "Ingreso", "Débito", "Auxiliar", False, True),
    ("5105", "Gastos de personal", "Gasto", "Débito", "Auxiliar", False, True),
    ("5110", "Honorarios", "Gasto", "Débito", "Auxiliar", True, True),
    ("5115", "Impuestos", "Gasto", "Débito", "Auxiliar", False, False),
    ("5120", "Arrendamientos", "Gasto", "Débito", "Auxiliar", True, True),
    ("5135", "Servicios", "Gasto", "Débito", "Auxiliar", False, True),
    ("5195", "Diversos", "Gasto", "Débito", "Auxiliar", False, True),
    ("5199", "Provisiones", "Gasto", "Débito", "Auxiliar", False, False),
    ("6135", "Comercio al por mayor y al por menor (costo)", "Costo", "Débito", "Auxiliar", False, True),
    ("6205", "Compras de mercancías", "Costo", "Débito", "Auxiliar", True, True),
    ("6225", "Devoluciones en compras (CR)", "Costo", "Crédito", "Auxiliar", True, True),
]

CENTROS_COSTO_DATA = [
    # (código, nombre, tipo, marca_asociada, activo, notas)
    ("CC-01", "Superozono", "Marca", "Superozono", True, None),
    ("CC-02", "Biozono", "Marca", "Biozono", True, "⚠️ Pendiente confirmar con la empresa"),
    ("CC-03", "Ecoozono", "Marca", "Ecoozono", True, None),
    ("CC-04", "Agroking", "Marca", "Agroking", True, None),
    ("CC-05", "Ozono Evolution", "Marca", "Ozono Evolution", True, None),
    ("CC-06", "Agro Vital", "Marca", "Agro Vital", True, None),
    ("CC-07", "Agro Fusion", "Marca", "Agro Fusion", True, None),
    ("CC-08", "Hiper Ozono", "Marca", "Hiper Ozono", True, None),
    ("CC-09", "Ozono Pro", "Marca", "Ozono Pro", True, None),
    ("CC-10", "Ozomax", "Marca", "Ozomax", True, None),
    ("CC-ADM", "Administración", "Área", None, True, None),
    ("CC-LOG", "Logística y bodega", "Área", None, True, None),
]

PERIODOS_DATA = [
    (2026, i, f"2026-{i:02d}", "Abierto") for i in range(1, 13)
]

PARAMETROS_TRIBUTARIOS_DATA = [
    # (concepto, tarifa, base_aplica, cuenta_puc, notas)
    ("IVA general", Decimal("0.19000"), "Ventas gravadas", "2408", "Tarifa general vigente"),
    ("IVA tarifa reducida", Decimal("0.05000"), "Productos tarifa 5%", "2408", "Confirmar productos aplicables"),
    ("Retención en la fuente - compras", Decimal("0.02500"), "Compras a declarantes", "2365", "Confirmar tarifa por concepto"),
    ("Retención en la fuente - servicios", Decimal("0.04000"), "Servicios", "2365", "Confirmar tarifa por concepto"),
    ("Retención en la fuente - honorarios", Decimal("0.11000"), "Honorarios", "2365", "Confirmar tarifa por concepto"),
    ("ReteIVA", Decimal("0.15000"), "% del IVA en compras", "2367", "Sobre el valor del IVA"),
    ("ReteICA", None, "Según municipio (por mil)", "2368", "⚠️ Depende del municipio - completar"),
    ("ICA (industria y comercio)", None, "Tarifa municipal (por mil)", "2412", "⚠️ Tarifa de Armenia/Quindío - completar"),
]

PARAMETROS_NOMINA_DATA = [
    # (concepto, valor, tipo, notas)
    ("Salario / Honorarios", None, "$", "Pago por prestación de servicios"),
    ("Auxilio de transporte", Decimal("0.00000"), "%", "No aplica (Prestación de servicios)"),
    ("Tope auxilio transporte", Decimal("0.00000"), "%", "No aplica (Prestación de servicios)"),
    ("Salud - aporte empleado", None, "%", "El contratista aporta como independiente"),
    ("Pensión - aporte empleado", Decimal("0.00000"), "%", "No aplica (Prestación de servicios)"),
    ("Salud - aporte empresa", Decimal("0.00000"), "%", "No aplica (Prestación de servicios)"),
    ("Pensión - aporte empresa", Decimal("0.00000"), "%", "No aplica (Prestación de servicios)"),
    ("ARL", None, "%", "Según nivel de riesgo acordado"),
    ("Caja de compensación", Decimal("0.00000"), "%", "No aplica (Prestación de servicios)"),
    ("SENA", Decimal("0.00000"), "%", "No aplica (Prestación de servicios)"),
    ("ICBF", Decimal("0.00000"), "%", "No aplica (Prestación de servicios)"),
    ("Cesantías", Decimal("0.00000"), "%", "No aplica (Prestación de servicios)"),
    ("Intereses sobre cesantías", Decimal("0.00000"), "%", "No aplica (Prestación de servicios)"),
    ("Prima de servicios", Decimal("0.00000"), "%", "No aplica (Prestación de servicios)"),
    ("Vacaciones", Decimal("0.00000"), "%", "No aplica (Prestación de servicios)"),
]


# ══════════════════════════════════════════════════════════
# DATOS DE VENTAS — Productos y Clientes
# ══════════════════════════════════════════════════════════

PRODUCTOS_DATA = [
    # (sku, nombre, desc, categoria, marca, unidad, contenido, precio_venta, precio_costo, iva%, stock, stock_min, registro_ica)
    ("SOZ-001", "Superozono Biocida Concentrado 1L", "Biocida orgánico de ozono concentrado para cultivos extensivos", "Biocida", "Superozono", "Litro", "1L", Decimal("85000.00"), Decimal("32000.00"), Decimal("19.00"), 120, 20, "ICA-2024-001"),
    ("SOZ-002", "Superozono Biocida Concentrado 20L", "Presentación industrial caneca 20 litros", "Biocida", "Superozono", "Caneca", "20L", Decimal("1350000.00"), Decimal("520000.00"), Decimal("19.00"), 45, 10, "ICA-2024-001"),
    ("ECO-001", "Ecoozono Desinfectante Agrícola 1L", "Desinfectante ecológico para riego y fumigación", "Desinfectante", "Ecoozono", "Litro", "1L", Decimal("65000.00"), Decimal("25000.00"), Decimal("19.00"), 200, 30, "ICA-2024-003"),
    ("ECO-002", "Ecoozono Desinfectante Agrícola 5L", "Desinfectante ecológico presentación 5 litros", "Desinfectante", "Ecoozono", "Galón", "5L", Decimal("280000.00"), Decimal("105000.00"), Decimal("19.00"), 85, 15, "ICA-2024-003"),
    ("AGK-001", "Agroking Fertilizante Ozonizado 1L", "Fertilizante foliar potenciado con ozono", "Fertilizante", "Agroking", "Litro", "1L", Decimal("72000.00"), Decimal("28000.00"), Decimal("5.00"), 150, 25, "ICA-2024-005"),
    ("AGK-002", "Agroking Fertilizante Ozonizado 20L", "Presentación para cultivos extensivos", "Fertilizante", "Agroking", "Caneca", "20L", Decimal("1150000.00"), Decimal("450000.00"), Decimal("5.00"), 30, 8, "ICA-2024-005"),
    ("OZE-001", "Ozono Evolution Coadyuvante 1L", "Coadyuvante agrícola de nueva generación", "Coadyuvante", "Ozono Evolution", "Litro", "1L", Decimal("55000.00"), Decimal("20000.00"), Decimal("19.00"), 180, 30, "ICA-2024-007"),
    ("AVT-001", "Agro Vital Bioestimulante 1L", "Bioestimulante orgánico para floración y fructificación", "Fertilizante", "Agro Vital", "Litro", "1L", Decimal("68000.00"), Decimal("26000.00"), Decimal("5.00"), 140, 20, "ICA-2024-009"),
    ("AFU-001", "Agro Fusion Mix Integral 1L", "Mezcla integral de nutrientes ozonizados", "Fertilizante", "Agro Fusion", "Litro", "1L", Decimal("78000.00"), Decimal("30000.00"), Decimal("5.00"), 100, 15, "ICA-2024-011"),
    ("HPO-001", "Hiper Ozono Potente 1L", "Biocida de alta concentración para plagas resistentes", "Biocida", "Hiper Ozono", "Litro", "1L", Decimal("95000.00"), Decimal("38000.00"), Decimal("19.00"), 90, 15, "ICA-2024-013"),
    ("OZP-001", "Ozono Pro Profesional 1L", "Línea profesional para cultivos tecnificados", "Biocida", "Ozono Pro", "Litro", "1L", Decimal("110000.00"), Decimal("45000.00"), Decimal("19.00"), 60, 10, "ICA-2024-015"),
    ("OZM-001", "Ozomax Ultra Concentrado 1L", "Máxima concentración de ozono activo", "Biocida", "Ozomax", "Litro", "1L", Decimal("125000.00"), Decimal("50000.00"), Decimal("19.00"), 40, 8, "ICA-2024-017"),
    ("BIO-001", "Biozono Natural 1L", "Biocida 100% natural para agricultura orgánica", "Biocida", "Biozono", "Litro", "1L", Decimal("75000.00"), Decimal("29000.00"), Decimal("19.00"), 110, 20, "ICA-2024-019"),
    ("SOZ-003", "Superozono Kit Starter", "Kit de inicio: 3 productos Superozono + dosificador", "Otro", "Superozono", "Caja", "Kit", Decimal("220000.00"), Decimal("85000.00"), Decimal("19.00"), 25, 5, None),
    ("ECO-003", "Ecoozono Pack Cafetero", "Pack especial para cultivos de café", "Biocida", "Ecoozono", "Caja", "Pack", Decimal("185000.00"), Decimal("72000.00"), Decimal("19.00"), 35, 8, "ICA-2024-003"),
]

CLIENTES_DATA = [
    # (nit, dv, razon_social, nombre_comercial, tipo_persona, regimen, direccion, ciudad, depto, tel, cel, email, contacto, cargo, lista, cupo, dias)
    ("900123456", "7", "AGROINSUMOS DEL EJE CAFETERO S.A.S.", "Agroinsumos Eje Cafetero", "Jurídica", "Responsable", "Cra 14 #23-45 Centro", "Armenia", "Quindío", "6067312200", "3154567890", "compras@agroinsumos.co", "Carlos Martínez", "Director de Compras", "Distribuidor", Decimal("50000000.00"), 30),
    ("800987654", "1", "DISTRIBUIDORA AGROPECUARIA VALLE VERDE LTDA", "Valle Verde", "Jurídica", "Responsable", "Av 6N #35-20 Centenario", "Cali", "Valle del Cauca", "6025551234", "3209876543", "pedidos@valleverde.com", "María Fernanda Ríos", "Gerente Comercial", "Mayorista", Decimal("80000000.00"), 45),
    ("901555888", "3", "AGROCENTRO TOLIMA S.A.S.", "Agrocentro Tolima", "Jurídica", "Responsable", "Calle 42 #5-28 La Estación", "Ibagué", "Tolima", "6082654321", "3171234567", "gerencia@agrocentro.co", "Pedro Alejandro Gómez", "Gerente General", "General", Decimal("30000000.00"), 30),
    ("1098765432", None, "FINCA EL PORVENIR - JUAN PABLO HERRERA", "Finca El Porvenir", "Natural", "No responsable", "Vereda La Esperanza Km 5", "Pereira", "Risaralda", None, "3187654321", "jpherrera@gmail.com", "Juan Pablo Herrera", "Propietario", "General", Decimal("10000000.00"), 15),
    ("860444777", "5", "COOPERATIVA DE CAFICULTORES DEL HUILA", "Coocafih", "Jurídica", "Responsable", "Cra 5 #10-42 Centro", "Neiva", "Huila", "6088753210", "3145678901", "logistica@coocafih.coop", "Andrés Felipe Rojas", "Jefe de Logística", "Distribuidor", Decimal("100000000.00"), 60),
    ("900777333", "9", "INVERSIONES AGRÍCOLAS SANTANDER S.A.", "InverAgro", "Jurídica", "Gran contribuyente", "Cl 36 #27-40 Cabecera", "Bucaramanga", "Santander", "6076543210", "3201112233", "compras@inveragro.com.co", "Lucía Mendoza", "Coordinadora de Suministros", "Mayorista", Decimal("150000000.00"), 45),
]


# ══════════════════════════════════════════════════════════
# FUNCIONES DE CARGA
# ══════════════════════════════════════════════════════════

async def seed_plan_cuentas(session):
    """Carga el Plan Único de Cuentas (PUC) base."""
    existing = await session.scalar(select(PlanCuentas.id).limit(1))
    if existing:
        logger.info("[SKIP]  PUC ya tiene datos, omitiendo seed")
        return

    for codigo, nombre, clase, naturaleza, nivel, req_tercero, req_cc in PLAN_CUENTAS_DATA:
        cuenta = PlanCuentas(
            codigo_puc=codigo,
            nombre=nombre,
            clase=ClaseCuenta(clase),
            naturaleza=NaturalezaCuenta(naturaleza),
            nivel=NivelCuenta(nivel),
            requiere_tercero=req_tercero,
            requiere_centro_costo=req_cc,
        )
        session.add(cuenta)

    await session.commit()
    logger.info(f"[OK] PUC: {len(PLAN_CUENTAS_DATA)} cuentas cargadas")


async def seed_centros_costo(session):
    """Carga los centros de costo (10 marcas + 2 áreas)."""
    existing = await session.scalar(select(CentroCosto.id).limit(1))
    if existing:
        logger.info("[SKIP] Centros de costo ya tienen datos, omitiendo seed")
        return

    for codigo, nombre, tipo, marca, activo, notas in CENTROS_COSTO_DATA:
        cc = CentroCosto(
            codigo=codigo,
            nombre=nombre,
            tipo=TipoCentroCosto(tipo),
            marca_asociada=marca,
            activo=activo,
            notas=notas,
        )
        session.add(cc)

    await session.commit()
    logger.info(f"[OK] Centros de costo: {len(CENTROS_COSTO_DATA)} centros cargados")


async def seed_periodos(session):
    """Carga los 12 períodos contables de 2026."""
    existing = await session.scalar(select(PeriodoContable.id).limit(1))
    if existing:
        logger.info("[SKIP] Periodos ya tienen datos, omitiendo seed")
        return

    for anio, mes, periodo, estado in PERIODOS_DATA:
        p = PeriodoContable(
            anio=anio,
            mes=mes,
            periodo=periodo,
            estado=EstadoPeriodo(estado),
        )
        session.add(p)

    await session.commit()
    logger.info(f"[OK] Periodos: {len(PERIODOS_DATA)} periodos cargados")


async def seed_parametros_tributarios(session):
    """Carga los parámetros tributarios base."""
    existing = await session.scalar(select(ParametroTributario.id).limit(1))
    if existing:
        logger.info("[SKIP] Parametros tributarios ya tienen datos, omitiendo seed")
        return

    for concepto, tarifa, base_aplica, cuenta, notas in PARAMETROS_TRIBUTARIOS_DATA:
        pt = ParametroTributario(
            concepto=concepto,
            tarifa_valor=tarifa,
            base_aplica=base_aplica,
            cuenta_puc=cuenta,
            notas=notas,
        )
        session.add(pt)

    await session.commit()
    logger.info(f"[OK] Parametros tributarios: {len(PARAMETROS_TRIBUTARIOS_DATA)} registros cargados")


async def seed_parametros_nomina(session):
    """Carga los parámetros de nómina con valores de ley."""
    existing = await session.scalar(select(ParametroNomina.id).limit(1))
    if existing:
        logger.info("[SKIP] Parametros de nomina ya tienen datos, omitiendo seed")
        return

    for concepto, valor, tipo, notas in PARAMETROS_NOMINA_DATA:
        pn = ParametroNomina(
            concepto=concepto,
            valor_porcentaje=valor,
            tipo=tipo,
            notas=notas,
        )
        session.add(pn)

    await session.commit()
    logger.info(f"[OK] Parametros de nomina: {len(PARAMETROS_NOMINA_DATA)} registros cargados")


async def seed_usuarios(session):
    """Carga el usuario administrador por defecto."""
    existing = await session.scalar(select(Usuario.id).limit(1))
    if existing:
        logger.info("[SKIP] Usuarios ya tienen datos, omitiendo seed")
        return

    if settings.SEED_ADMIN_PASSWORD == _DEFAULT_ADMIN_PASSWORD:
        logger.warning(
            "[SEC] El admin se está creando con la contraseña de fábrica. "
            "Configura SEED_ADMIN_PASSWORD en el .env y cámbiala tras el primer login."
        )

    admin = Usuario(
        email=settings.SEED_ADMIN_EMAIL,
        nombre_completo="Administrador del Sistema",
        hashed_password=get_password_hash(settings.SEED_ADMIN_PASSWORD),
        rol="Admin",
        is_active=True
    )
    session.add(admin)
    await session.commit()
    logger.info(f"[OK] Usuario administrador creado ({settings.SEED_ADMIN_EMAIL})")


async def seed_productos(session):
    """Carga el catálogo de productos de ejemplo."""
    existing = await session.scalar(select(Producto.id).limit(1))
    if existing:
        logger.info("[SKIP] Productos ya tienen datos, omitiendo seed")
        return

    for sku, nombre, desc, cat, marca, unidad, contenido, pv, pc, iva, stock, smin, reg in PRODUCTOS_DATA:
        producto = Producto(
            sku=sku,
            nombre=nombre,
            descripcion=desc,
            categoria=CategoriaProducto(cat),
            marca=marca,
            unidad_medida=UnidadMedida(unidad),
            contenido_neto=contenido,
            precio_venta=pv,
            precio_costo=pc,
            tarifa_iva=iva,
            stock_actual=stock,
            stock_minimo=smin,
            registro_ica=reg,
        )
        session.add(producto)

    await session.commit()
    logger.info(f"[OK] Productos: {len(PRODUCTOS_DATA)} productos cargados")


async def seed_clientes(session):
    """Carga los clientes de ejemplo (distribuidores B2B)."""
    existing = await session.scalar(select(Cliente.id).limit(1))
    if existing:
        logger.info("[SKIP] Clientes ya tienen datos, omitiendo seed")
        return

    for nit, dv, razon, comercial, tipo, regimen, dir_, ciudad, depto, tel, cel, email, contacto, cargo, lista, cupo, dias in CLIENTES_DATA:
        cliente = Cliente(
            nit_cc=nit,
            dv=dv,
            razon_social=razon,
            nombre_comercial=comercial,
            tipo_persona=tipo,
            regimen_iva=regimen,
            direccion=dir_,
            ciudad=ciudad,
            departamento=depto,
            telefono=tel,
            celular=cel,
            email=email,
            contacto_nombre=contacto,
            contacto_cargo=cargo,
            lista_precios=lista,
            cupo_credito=cupo,
            dias_credito=dias,
        )
        session.add(cliente)

    await session.commit()
    logger.info(f"[OK] Clientes: {len(CLIENTES_DATA)} clientes cargados")


# ══════════════════════════════════════════════════════════
# RUNNER PRINCIPAL
# ══════════════════════════════════════════════════════════

async def run_seeds():
    """Ejecuta todos los seeders en orden."""
    logger.info("[SEED] Iniciando carga de datos base -- Super Ozono Global ERP")

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("[DB] Tablas creadas correctamente")

    # Run seeders
    async with async_session() as session:
        await seed_plan_cuentas(session)
        await seed_centros_costo(session)
        await seed_periodos(session)
        await seed_parametros_tributarios(session)
        await seed_parametros_nomina(session)
        await seed_usuarios(session)
        await seed_productos(session)
        await seed_clientes(session)

    logger.info("[DONE] Carga de datos base completada exitosamente")


if __name__ == "__main__":
    asyncio.run(run_seeds())
