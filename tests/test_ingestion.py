"""
Tests unitarios para el módulo ingestion/.

Todos los tests mockean las llamadas HTTP (sin depender de la API real).
Se pueden ejecutar en modo offline, sin credenciales ni conexión a Primary.

Ejecutar:
    uv run pytest tests/test_ingestion.py -v
"""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import polars as pl
import pytest

from ingestion.auth import AuthError, AuthManager
from ingestion.base import BaseConnector
from ingestion.instruments import (
    RFX20_TICKERS,
    instrument_id_to_ticker,
    ticker_to_instrument_id,
)
from ingestion.pipeline import IngestionPipeline
from ingestion.primary_rest import OHLCV_COLUMNS, PrimaryRESTConnector, _empty_ohlcv_df


# ------------------------------------------------------------------ #
# Fixtures                                                             #
# ------------------------------------------------------------------ #

@pytest.fixture
def mock_auth_manager() -> MagicMock:
    """AuthManager completamente mockeado (sin HTTP real)."""
    auth = MagicMock(spec=AuthManager)
    mock_client = MagicMock()
    auth.get_client.return_value = mock_client
    return auth


@pytest.fixture
def mock_ohlcv_response_dict() -> MagicMock:
    """Respuesta HTTP 200 con OHLCV en el formato real confirmado de la API."""
    response = MagicMock()
    response.status_code = 200
    response.is_success = True
    response.is_server_error = False
    response.json.return_value = {
        "nextTime": "2024-01-01T00:00:00Z",
        "noData": False,
        "series": [
            {
                "c": 1030.0,
                "d": "2024-01-02T00:00:00Z",
                "h": 1050.0,
                "l": 990.0,
                "o": 1000.0,
                "r": "D",
                "sid": "bm_MERV_GGAL_24hs",
                "v": 5000.0,
            },
            {
                "c": 1060.0,
                "d": "2024-01-03T00:00:00Z",
                "h": 1080.0,
                "l": 1020.0,
                "o": 1030.0,
                "r": "D",
                "sid": "bm_MERV_GGAL_24hs",
                "v": 6200.0,
            },
        ],
    }
    return response


@pytest.fixture
def mock_empty_response() -> MagicMock:
    """Respuesta HTTP 200 con serie vacía (sin datos en el período)."""
    response = MagicMock()
    response.status_code = 200
    response.is_success = True
    response.is_server_error = False
    response.json.return_value = {
        "nextTime": None,
        "noData": False,
        "series": [],
    }
    return response


# ------------------------------------------------------------------ #
# Tests: instruments.py                                                #
# ------------------------------------------------------------------ #

class TestInstruments:

    def test_ticker_to_instrument_id(self):
        """ALUA debe convertirse a bm_MERV_ALUA_24hs."""
        assert ticker_to_instrument_id("ALUA") == "bm_MERV_ALUA_24hs"

    def test_ticker_to_instrument_id_various(self):
        """La conversión debe funcionar para cualquier ticker del RFX20."""
        assert ticker_to_instrument_id("GGAL") == "bm_MERV_GGAL_24hs"
        assert ticker_to_instrument_id("YPFD") == "bm_MERV_YPFD_24hs"
        assert ticker_to_instrument_id("TECO2") == "bm_MERV_TECO2_24hs"

    def test_instrument_id_to_ticker(self):
        """bm_MERV_ALUA_24hs debe convertirse a ALUA."""
        assert instrument_id_to_ticker("bm_MERV_ALUA_24hs") == "ALUA"

    def test_instrument_id_to_ticker_roundtrip(self):
        """La conversión debe ser reversible para todos los tickers del RFX20."""
        for ticker in RFX20_TICKERS:
            instrument_id = ticker_to_instrument_id(ticker)
            recovered = instrument_id_to_ticker(instrument_id)
            assert recovered == ticker, f"Roundtrip falló para {ticker!r}"

    def test_instrument_id_to_ticker_invalid_format(self):
        """instrument_id_to_ticker debe lanzar ValueError ante formato inválido."""
        with pytest.raises(ValueError, match="Formato de instrument_id inválido"):
            instrument_id_to_ticker("ALUA")  # Falta el prefijo/sufijo

    def test_rfx20_tickers_count(self):
        """RFX20_TICKERS debe contener exactamente 20 tickers."""
        assert len(RFX20_TICKERS) == 20

    def test_rfx20_tickers_no_duplicates(self):
        """RFX20_TICKERS no debe tener duplicados."""
        assert len(set(RFX20_TICKERS)) == len(RFX20_TICKERS)


# ------------------------------------------------------------------ #
# Tests: AuthManager                                                   #
# ------------------------------------------------------------------ #

class TestAuthManager:

    def test_auth_manager_login_csrf_flow(self):
        """Verifica el flujo completo: GET /api/v2/profile (CSRF) → POST /auth/login."""
        with patch("ingestion.auth.httpx.Client") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            # Mock GET /api/v2/profile → devuelve csrfToken
            profile_response = MagicMock()
            profile_response.json.return_value = {"csrfToken": "csrf-token-abc123"}
            profile_response.raise_for_status = MagicMock()

            # Mock POST /auth/login → éxito
            login_response = MagicMock()
            login_response.status_code = 200
            login_response.is_success = True

            mock_client.get.return_value = profile_response
            mock_client.post.return_value = login_response

            with patch("ingestion.auth.settings") as mock_settings:
                mock_settings.PRIMARY_BASE_URL = "https://test.api.com"
                mock_settings.PRIMARY_USER = "testuser"
                mock_settings.PRIMARY_PASS = "testpass"
                mock_settings.PRIMARY_TIMEOUT = 30

                auth = AuthManager()
                auth.login()

            # Verificar que se hizo GET /api/v2/profile
            mock_client.get.assert_called_once_with("https://test.api.com/api/v2/profile")

            # Verificar POST /auth/login con CSRF header correcto
            mock_client.post.assert_called_once()
            post_call = mock_client.post.call_args
            assert post_call.kwargs["headers"]["x-csrf-token"] == "csrf-token-abc123"
            assert post_call.kwargs["json"]["username"] == "testuser"
            assert post_call.kwargs["json"]["password"] == "testpass"

            assert auth._is_authenticated is True

    def test_auth_manager_credentials_not_stored_after_login(self):
        """Las credenciales no deben quedar almacenadas en atributos de instancia."""
        with patch("ingestion.auth.httpx.Client") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            profile_response = MagicMock()
            profile_response.json.return_value = {"csrfToken": "tok"}
            profile_response.raise_for_status = MagicMock()

            login_response = MagicMock()
            login_response.status_code = 200
            login_response.is_success = True

            mock_client.get.return_value = profile_response
            mock_client.post.return_value = login_response

            with patch("ingestion.auth.settings") as mock_settings:
                mock_settings.PRIMARY_BASE_URL = "https://test.api.com"
                mock_settings.PRIMARY_USER = "secretuser"
                mock_settings.PRIMARY_PASS = "secretpass"
                mock_settings.PRIMARY_TIMEOUT = 30

                auth = AuthManager()
                auth.login()

        # Las credenciales NO deben estar almacenadas en el objeto
        assert not hasattr(auth, "_username") or getattr(auth, "_username", None) is None
        assert not hasattr(auth, "_password") or getattr(auth, "_password", None) is None

    def test_auth_manager_login_raises_on_invalid_credentials(self):
        """Login con credenciales inválidas (401) debe lanzar AuthError."""
        with patch("ingestion.auth.httpx.Client") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            profile_response = MagicMock()
            profile_response.json.return_value = {"csrfToken": "tok"}
            profile_response.raise_for_status = MagicMock()

            login_response = MagicMock()
            login_response.status_code = 401
            login_response.is_success = False

            mock_client.get.return_value = profile_response
            mock_client.post.return_value = login_response

            with patch("ingestion.auth.settings") as mock_settings:
                mock_settings.PRIMARY_BASE_URL = "https://test.api.com"
                mock_settings.PRIMARY_USER = "bad"
                mock_settings.PRIMARY_PASS = "wrong"
                mock_settings.PRIMARY_TIMEOUT = 30

                auth = AuthManager()
                with pytest.raises(AuthError, match="401"):
                    auth.login()

    def test_auth_manager_login_raises_on_missing_csrf_token(self):
        """Si /profile no devuelve csrfToken, debe lanzar AuthError."""
        with patch("ingestion.auth.httpx.Client") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            profile_response = MagicMock()
            profile_response.json.return_value = {"otherField": "value"}  # Sin csrfToken
            profile_response.raise_for_status = MagicMock()

            mock_client.get.return_value = profile_response

            with patch("ingestion.auth.settings") as mock_settings:
                mock_settings.PRIMARY_BASE_URL = "https://test.api.com"
                mock_settings.PRIMARY_USER = "user"
                mock_settings.PRIMARY_PASS = "pass"
                mock_settings.PRIMARY_TIMEOUT = 30

                auth = AuthManager()
                with pytest.raises(AuthError, match="csrfToken"):
                    auth.login()

    def test_get_client_calls_login_when_not_authenticated(self):
        """get_client() debe llamar a login() si no hay sesión activa."""
        with patch("ingestion.auth.httpx.Client") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            with patch("ingestion.auth.settings") as mock_settings:
                mock_settings.PRIMARY_BASE_URL = "https://test.api.com"
                mock_settings.PRIMARY_USER = "u"
                mock_settings.PRIMARY_PASS = "p"
                mock_settings.PRIMARY_TIMEOUT = 30

                auth = AuthManager()

            with patch.object(auth, "login") as mock_login:
                auth._is_authenticated = False
                auth.get_client()
                mock_login.assert_called_once()

    def test_get_client_skips_login_when_authenticated(self):
        """get_client() no debe llamar a login() si ya hay sesión activa."""
        with patch("ingestion.auth.httpx.Client") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            with patch("ingestion.auth.settings") as mock_settings:
                mock_settings.PRIMARY_BASE_URL = "https://test.api.com"
                mock_settings.PRIMARY_TIMEOUT = 30

                auth = AuthManager()
                auth._is_authenticated = True

            with patch.object(auth, "login") as mock_login:
                client = auth.get_client()
                mock_login.assert_not_called()
                assert client is mock_client

    def test_reauth_resets_client_and_logs_in(self):
        """reauth() debe crear un nuevo cliente y volver a hacer login."""
        with patch("ingestion.auth.httpx.Client") as MockClient:
            mock_client_1 = MagicMock()
            mock_client_2 = MagicMock()
            MockClient.side_effect = [mock_client_1, mock_client_2]

            with patch("ingestion.auth.settings") as mock_settings:
                mock_settings.PRIMARY_BASE_URL = "https://test.api.com"
                mock_settings.PRIMARY_TIMEOUT = 30

                auth = AuthManager()
                auth._is_authenticated = True

            assert auth._client is mock_client_1

            with patch.object(auth, "login") as mock_login:
                auth.reauth()
                mock_login.assert_called_once()

            assert auth._client is mock_client_2
            assert auth._is_authenticated is False  # login() lo pondrá en True

    def test_validate_config_raises_on_missing_settings(self):
        """_validate_config debe lanzar ValueError si faltan settings."""
        with patch("ingestion.auth.httpx.Client"):
            with patch("ingestion.auth.settings") as mock_settings:
                mock_settings.PRIMARY_BASE_URL = ""
                mock_settings.PRIMARY_USER = ""
                mock_settings.PRIMARY_PASS = ""
                mock_settings.PRIMARY_TIMEOUT = 30

                auth = AuthManager()
                with pytest.raises(ValueError, match="PRIMARY_BASE_URL"):
                    auth._validate_config()


# ------------------------------------------------------------------ #
# Tests: PrimaryRESTConnector                                          #
# ------------------------------------------------------------------ #

class TestPrimaryRESTConnector:

    def test_fetch_converts_ticker_to_instrument_id(self, mock_auth_manager, mock_empty_response):
        """fetch() debe construir la URL usando el instrument_id correcto."""
        mock_auth_manager.get_client.return_value.get.return_value = mock_empty_response

        connector = PrimaryRESTConnector(
            auth_manager=mock_auth_manager,
            base_url="https://test.api.com",
        )
        connector.fetch("ALUA", date(2024, 1, 1), date(2024, 1, 31))

        call_args = mock_auth_manager.get_client.return_value.get.call_args
        assert "bm_MERV_ALUA_24hs" in call_args.args[0]

    def test_fetch_returns_standard_columns(self, mock_auth_manager, mock_ohlcv_response_dict):
        """fetch() debe retornar un DataFrame con las columnas OHLCV estándar."""
        mock_auth_manager.get_client.return_value.get.return_value = mock_ohlcv_response_dict

        connector = PrimaryRESTConnector(
            auth_manager=mock_auth_manager,
            base_url="https://test.api.com",
        )
        df = connector.fetch("GGAL", date(2024, 1, 2), date(2024, 1, 3))

        assert isinstance(df, pl.DataFrame)
        for col in OHLCV_COLUMNS:
            assert col in df.columns, f"Columna faltante: {col!r}"

    def test_fetch_adds_ticker_column(self, mock_auth_manager, mock_ohlcv_response_dict):
        """El DataFrame debe incluir la columna ticker con el valor correcto."""
        mock_auth_manager.get_client.return_value.get.return_value = mock_ohlcv_response_dict

        connector = PrimaryRESTConnector(
            auth_manager=mock_auth_manager,
            base_url="https://test.api.com",
        )
        df = connector.fetch("GGAL", date(2024, 1, 2), date(2024, 1, 3))

        assert df["ticker"].unique().to_list() == ["GGAL"]

    def test_fetch_correct_row_count(self, mock_auth_manager, mock_ohlcv_response_dict):
        """El número de filas debe coincidir con los registros de la respuesta mock."""
        mock_auth_manager.get_client.return_value.get.return_value = mock_ohlcv_response_dict

        connector = PrimaryRESTConnector(
            auth_manager=mock_auth_manager,
            base_url="https://test.api.com",
        )
        df = connector.fetch("GGAL", date(2024, 1, 2), date(2024, 1, 3))

        assert len(df) == 2

    def test_fetch_handles_401_calls_reauth_and_retries(self, mock_auth_manager, mock_ohlcv_response_dict):
        """Ante 401: debe llamar reauth() y reintentar una vez."""
        response_401 = MagicMock()
        response_401.status_code = 401
        response_401.is_success = False
        response_401.is_server_error = False

        # Primera llamada → client con 401; segunda llamada (post-reauth) → client con 200
        mock_client_401 = MagicMock()
        mock_client_401.get.return_value = response_401

        mock_client_ok = MagicMock()
        mock_client_ok.get.return_value = mock_ohlcv_response_dict

        # get_client() devuelve clientes distintos antes y después del reauth
        mock_auth_manager.get_client.side_effect = [mock_client_401, mock_client_ok]

        connector = PrimaryRESTConnector(
            auth_manager=mock_auth_manager,
            base_url="https://test.api.com",
        )
        df = connector.fetch("ALUA", date(2024, 1, 1), date(2024, 1, 31))

        mock_auth_manager.reauth.assert_called_once()
        assert isinstance(df, pl.DataFrame)

    def test_fetch_handles_403_calls_reauth(self, mock_auth_manager, mock_empty_response):
        """Ante 403 (Forbidden): también debe llamar reauth() y reintentar."""
        response_403 = MagicMock()
        response_403.status_code = 403
        response_403.is_success = False
        response_403.is_server_error = False

        mock_client_403 = MagicMock()
        mock_client_403.get.return_value = response_403

        mock_client_ok = MagicMock()
        mock_client_ok.get.return_value = mock_empty_response

        mock_auth_manager.get_client.side_effect = [mock_client_403, mock_client_ok]

        connector = PrimaryRESTConnector(
            auth_manager=mock_auth_manager,
            base_url="https://test.api.com",
        )
        connector.fetch("ALUA", date(2024, 1, 1), date(2024, 1, 31))

        mock_auth_manager.reauth.assert_called_once()

    def test_fetch_raises_auth_error_if_reauth_fails(self, mock_auth_manager):
        """Si después del reauth la API sigue devolviendo 401, debe lanzar AuthError."""
        response_401 = MagicMock()
        response_401.status_code = 401
        response_401.is_success = False
        response_401.is_server_error = False

        # Ambas llamadas devuelven 401 (reauth no resuelve el problema)
        mock_client = MagicMock()
        mock_client.get.return_value = response_401
        mock_auth_manager.get_client.return_value = mock_client

        connector = PrimaryRESTConnector(
            auth_manager=mock_auth_manager,
            base_url="https://test.api.com",
        )
        with pytest.raises(AuthError, match="reauth"):
            connector.fetch("ALUA", date(2024, 1, 1), date(2024, 1, 31))

    def test_validate_response_accepts_valid_structure(self, mock_auth_manager):
        """validate_response debe aceptar el formato real de la API."""
        connector = PrimaryRESTConnector(auth_manager=mock_auth_manager)
        payload = {"nextTime": "2024-01-01T00:00:00Z", "noData": False, "series": []}
        assert connector.validate_response(payload) is True

    def test_validate_response_accepts_series_with_records(self, mock_auth_manager):
        """validate_response debe aceptar cuando series tiene registros."""
        connector = PrimaryRESTConnector(auth_manager=mock_auth_manager)
        payload = {
            "nextTime": "2024-01-01T00:00:00Z",
            "noData": False,
            "series": [{"c": 100.0, "d": "2024-01-02T00:00:00Z"}],
        }
        assert connector.validate_response(payload) is True

    def test_validate_response_rejects_no_data_true(self, mock_auth_manager):
        """validate_response debe rechazar cuando noData es True."""
        connector = PrimaryRESTConnector(auth_manager=mock_auth_manager)
        payload = {"nextTime": None, "noData": True, "series": []}
        assert connector.validate_response(payload) is False

    def test_validate_response_rejects_missing_series_key(self, mock_auth_manager):
        """validate_response debe rechazar si falta la clave 'series'."""
        connector = PrimaryRESTConnector(auth_manager=mock_auth_manager)
        assert connector.validate_response({"noData": False}) is False

    def test_validate_response_rejects_none(self, mock_auth_manager):
        """validate_response debe rechazar None."""
        connector = PrimaryRESTConnector(auth_manager=mock_auth_manager)
        assert connector.validate_response(None) is False

    def test_validate_response_rejects_list(self, mock_auth_manager):
        """validate_response debe rechazar una lista directa (no es el formato de la API)."""
        connector = PrimaryRESTConnector(auth_manager=mock_auth_manager)
        assert connector.validate_response([{"c": 100.0}]) is False

    def test_empty_ohlcv_df_has_correct_schema(self):
        """_empty_ohlcv_df debe retornar un DataFrame vacío con el schema canónico."""
        df = _empty_ohlcv_df("TEST")
        assert len(df) == 0
        for col in OHLCV_COLUMNS:
            assert col in df.columns, f"Columna faltante en df vacío: {col!r}"

    def test_fetch_sends_resolution_param(self, mock_auth_manager, mock_empty_response):
        """fetch() debe incluir el parámetro resolution=D en el request."""
        mock_auth_manager.get_client.return_value.get.return_value = mock_empty_response

        connector = PrimaryRESTConnector(
            auth_manager=mock_auth_manager,
            base_url="https://test.api.com",
        )
        connector.fetch("GGAL", date(2024, 1, 1), date(2024, 1, 31))

        call_kwargs = mock_auth_manager.get_client.return_value.get.call_args.kwargs
        params = call_kwargs.get("params", {})
        assert params.get("resolution") == "D"


# ------------------------------------------------------------------ #
# Tests: BaseConnector                                                 #
# ------------------------------------------------------------------ #

class TestBaseConnector:

    def test_cannot_instantiate_abstract_class(self):
        """BaseConnector es abstracta y no debe instanciarse directamente."""
        with pytest.raises(TypeError):
            BaseConnector()  # type: ignore[abstract]

    def test_partial_subclass_cannot_be_instantiated(self):
        """Una subclase sin todos los métodos abstractos implementados falla."""

        class IncompleteConnector(BaseConnector):
            @property
            def source_name(self) -> str:
                return "test"
            # fetch y validate_response no implementados

        with pytest.raises(TypeError):
            IncompleteConnector()  # type: ignore[abstract]


# ------------------------------------------------------------------ #
# Tests: IngestionPipeline                                             #
# ------------------------------------------------------------------ #

class TestIngestionPipeline:

    def _make_pipeline(self, connector: MagicMock) -> IngestionPipeline:
        """Crea un pipeline con store mock y el conector dado."""
        store = MagicMock()
        return IngestionPipeline(store=store, connector=connector)

    def test_pipeline_continues_on_ticker_failure(self):
        """Un ticker fallido no debe detener el procesamiento de los demás."""
        mock_connector = MagicMock()

        success_df = pl.DataFrame(
            {
                "date": [date(2024, 1, 2)],
                "open": [100.0],
                "high": [110.0],
                "low": [90.0],
                "close": [105.0],
                "volume": [1000.0],
                "ticker": ["GGAL"],
            }
        )

        # ALUA falla, GGAL tiene éxito
        mock_connector.fetch.side_effect = [
            Exception("Simulated connection error"),
            success_df,
        ]

        pipeline = self._make_pipeline(mock_connector)
        results = pipeline.run(["ALUA", "GGAL"], date(2024, 1, 1), date(2024, 1, 31))

        assert results == {"ALUA": False, "GGAL": True}
        assert mock_connector.fetch.call_count == 2

    def test_run_returns_dict_with_all_tickers(self):
        """run() debe retornar un dict con entrada para cada ticker solicitado."""
        mock_connector = MagicMock()
        success_df = pl.DataFrame(
            {
                "date": [date(2024, 1, 2)],
                "open": [100.0],
                "high": [110.0],
                "low": [90.0],
                "close": [105.0],
                "volume": [1000.0],
                "ticker": ["X"],
            }
        )
        mock_connector.fetch.return_value = success_df

        pipeline = self._make_pipeline(mock_connector)
        results = pipeline.run(
            ["ALUA", "GGAL", "YPFD"], date(2024, 1, 1), date(2024, 1, 31)
        )

        assert set(results.keys()) == {"ALUA", "GGAL", "YPFD"}
        assert all(isinstance(v, bool) for v in results.values())

    def test_run_all_success(self):
        """Cuando todos los tickers tienen éxito, el dict debe tener todos True."""
        mock_connector = MagicMock()
        success_df = pl.DataFrame(
            {
                "date": [date(2024, 1, 2)],
                "open": [100.0],
                "high": [110.0],
                "low": [90.0],
                "close": [105.0],
                "volume": [1000.0],
                "ticker": ["X"],
            }
        )
        mock_connector.fetch.return_value = success_df

        pipeline = self._make_pipeline(mock_connector)
        results = pipeline.run(["ALUA", "GGAL"], date(2024, 1, 1), date(2024, 1, 31))

        assert results == {"ALUA": True, "GGAL": True}

    def test_run_raises_on_empty_tickers(self):
        """run() debe lanzar ValueError si la lista de tickers está vacía."""
        pipeline = self._make_pipeline(MagicMock())
        with pytest.raises(ValueError, match="vacía"):
            pipeline.run([], date(2024, 1, 1), date(2024, 1, 31))

    def test_run_raises_on_invalid_date_range(self):
        """run() debe lanzar ValueError si date_from > date_to."""
        pipeline = self._make_pipeline(MagicMock())
        with pytest.raises(ValueError, match="anterior"):
            pipeline.run(["ALUA"], date(2024, 12, 31), date(2024, 1, 1))

    def test_run_rfx20_uses_all_rfx20_tickers(self):
        """run_rfx20() debe llamar run() con los 20 tickers del índice."""
        mock_connector = MagicMock()
        success_df = pl.DataFrame(
            {
                "date": pl.Series([], dtype=pl.Date),
                "open": pl.Series([], dtype=pl.Float64),
                "high": pl.Series([], dtype=pl.Float64),
                "low": pl.Series([], dtype=pl.Float64),
                "close": pl.Series([], dtype=pl.Float64),
                "volume": pl.Series([], dtype=pl.Float64),
                "ticker": pl.Series([], dtype=pl.Utf8),
            }
        )
        mock_connector.fetch.return_value = success_df

        pipeline = self._make_pipeline(mock_connector)

        with patch.object(pipeline, "run", wraps=pipeline.run) as mock_run:
            pipeline.run_rfx20(date(2024, 1, 1), date(2024, 1, 31))
            called_tickers = mock_run.call_args.args[0]

        assert set(called_tickers) == set(RFX20_TICKERS)
        assert len(called_tickers) == 20

    def test_run_macro_raises_not_implemented(self):
        """run_macro() debe lanzar NotImplementedError."""
        pipeline = self._make_pipeline(MagicMock())
        with pytest.raises(NotImplementedError):
            pipeline.run_macro()

    def test_auth_error_is_caught_per_ticker(self):
        """Un AuthError en un ticker individual se registra como fallo (no propaga)."""
        mock_connector = MagicMock()
        mock_connector.fetch.side_effect = AuthError("Sesión expirada")

        pipeline = self._make_pipeline(mock_connector)
        results = pipeline.run(["ALUA"], date(2024, 1, 1), date(2024, 1, 31))

        assert results == {"ALUA": False}
