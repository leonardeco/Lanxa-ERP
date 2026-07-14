# QA Cases — Demo data seeder

Derived from the spec's success criteria (no formal user story; implicit ACs from
behavior). Given/When/Then. Test refs filled by Task 2.

| AC | Case | Given / When / Then | Test ref |
|----|------|---------------------|----------|
| AC1 volume | TC-1.1 | **Given** an empty demo DB **When** `run_demo_seed(clientes=50, ventas=200, clean=True)` **Then** clientes ≥ 50 and ventas == 200 | `tests/test_seed_demo.py::test_run_demo_seed_volume` |
| AC2 confirmed side-effects | TC-2.1 | **Given** a seeded demo DB **When** counting CONFIRMADA ventas **Then** each has a matching `CuentaPorCobrar` by `numero_factura` | `tests/test_seed_demo.py::test_confirmed_have_cxc` |
| AC2 stock safety | TC-2.2 | **Given** default demo products **When** seeding confirmed ventas **Then** no `VentaError` is raised | `tests/test_seed_demo.py::test_no_venta_error_on_confirm` |
| AC2 aging | TC-2.3 | **Given** a seeded demo DB **When** inspecting CxC **Then** ≥1 has estado PARCIAL/PAGADO and `saldo_pendiente == valor_factura - abonos` | `tests/test_seed_demo.py::test_abonos_populate_aging` |
| AC3 idempotency | TC-3.1 | **Given** a populated demo DB **When** `run_demo_seed(clean=False)` **Then** it raises `RuntimeError` (no duplication) | `tests/test_seed_demo.py::test_rerun_without_clean_refuses` |
| AC3 determinism | TC-3.2 | **Given** `seed=42` **When** running twice with `--clean` **Then** the same volume results (deterministic RNG) | covered by TC-1.1 fixed seed |
| AC4 isolation | TC-4.1 | **Given** demo_url == prod_url **When** `assert_isolated` **Then** raises `RuntimeError` | `tests/test_seed_demo.py::test_assert_isolated_rejects_prod_url` |
| AC5 CLI bounds | TC-5.1 | **Given** the arg parser **When** `--ventas 0` or `> 100000` **Then** `SystemExit` | `tests/test_seed_demo.py::test_arg_parser_defaults_and_bounds` |
| AC5 url precedence | TC-5.2 | **Given** cli/env/default urls **When** `resolve_demo_url` **Then** cli > env > default | `tests/test_seed_demo.py::test_resolve_demo_url_precedence` |

**Gaps:** none blocking. Faithful abono/recibo-de-caja simulation intentionally out of
scope (demo shortcut). Manual UI-perf observation (the ultimate purpose) is not
automatable here — run the app against `superozono_demo.db` and observe.
