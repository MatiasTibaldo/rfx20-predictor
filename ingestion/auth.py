"""
Gestión de autenticación para la API de Primary S.A. (Matriz xoms).

Flujo de autenticación (cookie-based, NO bearer token):
    1. GET /api/v2/profile           → respuesta JSON contiene campo ``csrfToken``
    2. POST /auth/login            → header ``x-csrf-token: {csrfToken}``
                                body JSON ``{username, password}``
                                → la API setea la cookie ``_mtz_web_key``
    3. Requests subsiguientes → httpx.Client reenvía la cookie automáticamente

Decisiones de diseño:
- Se usa un único httpx.Client persistente (con cookie jar automático) en lugar
  de crear un nuevo cliente por request. Esto es lo que permite que las cookies
  de sesión se propaguen a los requests subsiguientes.
- Las credenciales se leen de settings en el momento del login y NO se almacenan
  en atributos de instancia. Para re-autenticar se vuelve a leer de settings.
- Los logs nunca exponen credenciales ni tokens (ni siquiera a nivel DEBUG).
"""

from __future__ import annotations

import httpx
from loguru import logger

from config.settings import settings


class AuthError(Exception):
    """Falla irrecuperable de autenticación (credenciales inválidas, servicio caído)."""


class AuthManager:
    """Gestiona el ciclo de vida de la sesión cookie para la API de Primary.

    El login se realiza mediante el flujo CSRF descrito en el módulo docstring.
    La cookie de sesión la gestiona httpx.Client automáticamente; no es necesario
    manipularla explícitamente.

    Args:
        base_url: URL base de la API. Si se omite, se lee de ``settings.PRIMARY_BASE_URL``.

    Example:
        >>> auth = AuthManager()
        >>> client = auth.get_client()   # dispara login si no hay sesión activa
        >>> response = client.get("/api/v2/series/securities/bm_MERV_GGAL_24hs")
    """

    _PROFILE_ENDPOINT = "/api/v2/profile"
    _LOGIN_ENDPOINT = "/auth/login"

    def __init__(self, base_url: str | None = None) -> None:
        self._base_url: str = (base_url or settings.PRIMARY_BASE_URL).rstrip("/")
        # Cliente único con cookie jar automático. Se recrea en reauth().
        self._client: httpx.Client = httpx.Client(timeout=settings.PRIMARY_TIMEOUT)
        self._is_authenticated: bool = False

    # ------------------------------------------------------------------ #
    # Interfaz pública                                                     #
    # ------------------------------------------------------------------ #

    def login(self) -> None:
        """Realiza el flujo CSRF → login y activa la cookie de sesión.

        Las credenciales se leen de settings como variables locales y NO se
        almacenan en ningún atributo de instancia después de este método.

        Raises:
            ValueError: Si PRIMARY_BASE_URL, PRIMARY_USER o PRIMARY_PASS están vacíos.
            AuthError: Si el CSRF fetch o el login fallan (red o credenciales).
        """
        self._validate_config()

        # Leer credenciales desde settings solo durante el login.
        # Son variables locales: se descartan al salir del método.
        username = settings.PRIMARY_USER
        password = settings.PRIMARY_PASS

        logger.info(f"[Auth] Iniciando login (usuario={username!r})")

        # Paso 1: obtener CSRF token.
        csrf_token = self._get_csrf_token()

        # Paso 2: POST /auth/login con CSRF header y credenciales.
        url = f"{self._base_url}{self._LOGIN_ENDPOINT}"
        try:
            response = self._client.post(
                url,
                headers={"x-csrf-token": csrf_token},
                json={"username": username, "password": password},
            )
        except httpx.RequestError as exc:
            raise AuthError(f"No se pudo conectar al servidor de login: {exc}") from exc

        if response.status_code == 401:
            raise AuthError(
                "Credenciales inválidas (401). Verificar PRIMARY_USER y PRIMARY_PASS."
            )
        if not response.is_success:
            raise AuthError(
                f"Login fallido: HTTP {response.status_code} — {response.text[:200]}"
            )

        # La cookie _mtz_web_key ya fue guardada en el cookie jar de self._client.
        self._is_authenticated = True
        logger.info("[Auth] Login exitoso — sesión activa.")

        # Descarte explícito de credenciales (las variables locales se liberan
        # igual al salir del scope, pero esto documenta la intención de seguridad).
        del username, password, csrf_token

    def get_client(self) -> httpx.Client:
        """Devuelve el cliente httpx con la sesión activa.

        Login lazy: solo se autentica la primera vez (``_is_authenticated=False``).
        Entre requests del mismo run, si la sesión sigue activa, retorna el
        cliente existente sin ninguna llamada HTTP adicional.
        ``reauth()`` solo se llama externamente ante un 401 real (ver
        ``PrimaryRESTConnector._fetch_with_auth_retry``).

        Returns:
            httpx.Client con la cookie de sesión configurada.
        """
        if not self._is_authenticated:
            logger.debug("[Auth] Sin sesión activa — realizando login.")
            self.login()
        return self._client

    def reauth(self) -> None:
        """Resetea el cliente y realiza un nuevo login.

        Debe llamarse cuando un request devuelve 401/403 inesperado
        (sesión expirada). Crea un nuevo httpx.Client para limpiar las
        cookies expiradas antes de re-loguear.
        """
        logger.info("[Auth] Re-autenticando — reseteando sesión.")
        try:
            self._client.close()
        except Exception:
            pass  # Ignorar errores al cerrar un cliente ya cerrado
        self._client = httpx.Client(timeout=settings.PRIMARY_TIMEOUT)
        self._is_authenticated = False
        self.login()

    # ------------------------------------------------------------------ #
    # Helpers privados                                                     #
    # ------------------------------------------------------------------ #

    def _get_csrf_token(self) -> str:
        """GET /profile y parsea el campo csrfToken del JSON de respuesta.

        Returns:
            CSRF token como string.

        Raises:
            AuthError: Si el request falla o el campo csrfToken no está presente.
        """
        url = f"{self._base_url}{self._PROFILE_ENDPOINT}"
        logger.debug("[Auth] GET /profile (obteniendo CSRF token)")

        try:
            response = self._client.get(url)
            logger.debug(f"[Auth] GET /profile response: {url}")
            response.raise_for_status()
        except httpx.RequestError as exc:
            raise AuthError(
                f"No se pudo conectar a /profile para obtener CSRF token: {exc}"
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise AuthError(
                f"Error al obtener CSRF token: HTTP {exc.response.status_code}"
            ) from exc

        data = response.json()
        csrf_token = data.get("csrfToken")
        if not csrf_token:
            raise AuthError(
                f"Campo 'csrfToken' no encontrado en respuesta de /profile. "
            )

        logger.debug("[Auth] CSRF token obtenido correctamente.")
        return str(csrf_token)

    def _validate_config(self) -> None:
        """Verifica que las variables de configuración necesarias no estén vacías."""
        missing = []
        if not self._base_url:
            missing.append("PRIMARY_BASE_URL")
        if not settings.PRIMARY_USER:
            missing.append("PRIMARY_USER")
        if not settings.PRIMARY_PASS:
            missing.append("PRIMARY_PASS")
        if missing:
            raise ValueError(
                f"Configuración de Primary incompleta. Faltan: {', '.join(missing)}. "
                "Verificar settings o archivo .env."
            )
