import os
import re
import httpx
import datetime
from mcp.server.fastmcp import FastMCP

_port_env = os.getenv("PORT")
HTTP_PORT = int(_port_env) if _port_env else int(os.getenv("MCP_HTTP_PORT", "8096"))
_default_path = "/mcp" if _port_env else os.getenv("MCP_HTTP_PATH", "/mcp/latam")

mcp = FastMCP(
    "LATAM Intelligence",
    stateless_http=True,
    host="0.0.0.0",
    port=HTTP_PORT,
    streamable_http_path=_default_path,
)

BRASIL_API = "https://brasilapi.com.br/api"
BCB_API = "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata"
ARG_API = "https://apis.datos.gob.ar/series/api/series"

HEADERS = {"Accept": "application/json", "User-Agent": "LATAMIntelligenceMCP/1.0"}

ARG_SERIES = {
    "dolar": "168.1_T_CAMBIOR_D_0_0_26",
    "inflacion_mensual": "103.1_I2NG_2016_M_19",
    "pib": "134.2_PBI_PCHA_0_0_44",
    "tasa_politica": "7.2_TPNP_0_0_5",
    "reservas": "53.4_RRFR_0_0_43",
    "inflacion_anual": "103.1_I2NG_2016_A_19",
}


# ─── Brazil ─────────────────────────────────────────────────────────────────

def _cnpj_validate(cnpj: str) -> bool:
    digits = re.sub(r"\D", "", cnpj)
    if len(digits) != 14 or len(set(digits)) == 1:
        return False
    def _calc(d, weights):
        s = sum(int(d[i]) * weights[i] for i in range(len(weights)))
        r = s % 11
        return 0 if r < 2 else 11 - r
    w1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    w2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    return _calc(digits[:12], w1) == int(digits[12]) and _calc(digits[:13], w2) == int(digits[13])


@mcp.tool()
async def lookup_brazil_company(cnpj: str) -> dict:
    """Look up a Brazilian company by CNPJ (tax registration number).

    Returns company name, address, status, partners, activity codes and more.

    Args:
        cnpj: Brazilian CNPJ number (14 digits, with or without formatting)
    """
    digits = re.sub(r"\D", "", cnpj)
    if len(digits) != 14:
        return {"error": "CNPJ must have 14 digits"}
    if not _cnpj_validate(digits):
        return {"error": f"Invalid CNPJ checksum: {cnpj}"}

    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(f"{BRASIL_API}/cnpj/v1/{digits}", headers=HEADERS)
        if r.status_code == 404:
            return {"error": f"CNPJ {cnpj} not found in Receita Federal"}
        r.raise_for_status()
        d = r.json()

    partners = [
        {
            "name": p.get("nome_socio"),
            "role": p.get("qualificacao_socio"),
            "age_range": p.get("faixa_etaria"),
            "entry_date": p.get("data_entrada_sociedade"),
        }
        for p in d.get("qsa", [])
    ]

    activities = []
    if d.get("cnae_fiscal_descricao"):
        activities.append({"code": d.get("cnae_fiscal"), "description": d.get("cnae_fiscal_descricao"), "primary": True})
    for a in d.get("cnaes_secundarios", []):
        activities.append({"code": a.get("codigo"), "description": a.get("descricao"), "primary": False})

    return {
        "cnpj": d.get("cnpj"),
        "legal_name": d.get("razao_social"),
        "trade_name": d.get("nome_fantasia") or None,
        "status": d.get("descricao_situacao_cadastral"),
        "legal_type": d.get("descricao_natureza_juridica"),
        "founded": d.get("data_inicio_atividade"),
        "employees_range": d.get("descricao_porte"),
        "address": {
            "street": f"{d.get('tipo_logradouro', '')} {d.get('logradouro', '')} {d.get('numero', '')}".strip(),
            "complement": d.get("complemento"),
            "neighborhood": d.get("bairro"),
            "city": d.get("municipio"),
            "state": d.get("uf"),
            "zip": d.get("cep"),
        },
        "phone": d.get("ddd_telefone_1"),
        "email": d.get("email"),
        "capital": d.get("capital_social"),
        "activities": activities,
        "partners": partners,
    }


@mcp.tool()
async def lookup_brazil_address(cep: str) -> dict:
    """Look up a Brazilian address by CEP (postal code / ZIP code).

    Args:
        cep: Brazilian CEP (8 digits, with or without dash)
    """
    digits = re.sub(r"\D", "", cep)
    if len(digits) != 8:
        return {"error": "CEP must have 8 digits"}

    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(f"{BRASIL_API}/cep/v2/{digits}", headers=HEADERS)
        if r.status_code == 404:
            return {"error": f"CEP {cep} not found"}
        r.raise_for_status()
        d = r.json()

    return {
        "cep": d.get("cep"),
        "street": d.get("street"),
        "neighborhood": d.get("neighborhood"),
        "city": d.get("city"),
        "state": d.get("state"),
        "state_code": d.get("state"),
        "coordinates": d.get("location", {}).get("coordinates") if d.get("location") else None,
    }


# ─── Argentina ──────────────────────────────────────────────────────────────

@mcp.tool()
async def get_argentina_economic_data(indicator: str, limit: int = 12) -> dict:
    """Get Argentine economic indicators from the official datos.gob.ar API.

    Available indicators: dolar, inflacion_mensual, inflacion_anual, pib,
    tasa_politica, reservas

    Args:
        indicator: One of: dolar, inflacion_mensual, inflacion_anual, pib, tasa_politica, reservas
        limit: Number of recent data points to return (default 12)
    """
    indicator = indicator.lower().strip()
    if indicator not in ARG_SERIES:
        return {
            "error": f"Unknown indicator: {indicator}",
            "available": list(ARG_SERIES.keys()),
        }

    series_id = ARG_SERIES[indicator]
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(
            ARG_API,
            headers=HEADERS,
            params={"ids": series_id, "limit": limit, "sort": "desc"},
        )
        r.raise_for_status()
        d = r.json()

    series_meta = d.get("meta", [{}])[0] if d.get("meta") else {}
    data_points = [{"date": row[0], "value": row[1]} for row in d.get("data", [])]

    return {
        "indicator": indicator,
        "description": series_meta.get("title") or indicator,
        "frequency": series_meta.get("frequency"),
        "unit": series_meta.get("units"),
        "data": data_points,
    }


# ─── Exchange rates ──────────────────────────────────────────────────────────

@mcp.tool()
async def get_brazil_exchange_rate(currency: str = "USD", date: str = None) -> dict:
    """Get the official BRL exchange rate from Banco Central do Brasil (BCB PTAX).

    Args:
        currency: Target currency code (USD, EUR, GBP, JPY, ARS, etc.)
        date: Date in YYYY-MM-DD format (default: today or last business day)
    """
    currency = currency.upper()
    if date:
        try:
            dt = datetime.datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            return {"error": "Date must be in YYYY-MM-DD format"}
        bcb_date = dt.strftime("%m-%d-%Y")
    else:
        today = datetime.date.today()
        bcb_date = today.strftime("%m-%d-%Y")

    # BCB PTAX endpoint
    url = f"{BCB_API}/CotacaoMoedaDia(moeda=@moeda,dataCotacao=@dataCotacao)"
    params = {
        "@moeda": f"'{currency}'",
        "@dataCotacao": f"'{bcb_date}'",
        "$format": "json",
    }

    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(url, headers=HEADERS, params=params)
        r.raise_for_status()
        d = r.json()

    values = d.get("value", [])
    if not values:
        # Try USD as fallback to show BRL/USD
        if currency != "USD":
            return {"error": f"No PTAX rate found for {currency} on {bcb_date}. Try 'USD', 'EUR', 'GBP'."}
        return {"error": f"No PTAX rate found for {bcb_date} — may be a non-business day"}

    latest = values[-1]
    return {
        "currency_pair": f"BRL/{currency}",
        "date": latest.get("dataHoraCotacao", bcb_date)[:10],
        "buy": latest.get("cotacaoCompra"),
        "sell": latest.get("cotacaoVenda"),
        "source": "Banco Central do Brasil (PTAX)",
    }


# ─── Tax ID validation ───────────────────────────────────────────────────────

def _validate_cnpj(digits: str) -> tuple[bool, str]:
    if len(digits) != 14:
        return False, "CNPJ must have 14 digits"
    if not _cnpj_validate(digits):
        return False, "Invalid checksum digits"
    return True, f"Valid CNPJ: {digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"


def _validate_cpf(digits: str) -> tuple[bool, str]:
    if len(digits) != 11 or len(set(digits)) == 1:
        return False, "Invalid CPF"
    def _check(d, n):
        s = sum(int(d[i]) * (n - i) for i in range(n - 1))
        r = (s * 10) % 11
        return 0 if r == 10 else r
    if _check(digits, 10) != int(digits[9]) or _check(digits, 11) != int(digits[10]):
        return False, "Invalid CPF checksum"
    return True, f"Valid CPF: {digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"


def _validate_rfc(rfc: str) -> tuple[bool, str]:
    rfc = rfc.upper().strip()
    pattern_person = r"^[A-Z]{4}\d{6}[A-Z0-9]{3}$"
    pattern_company = r"^[A-Z]{3}\d{6}[A-Z0-9]{3}$"
    if re.match(pattern_person, rfc) or re.match(pattern_company, rfc):
        return True, f"Valid RFC format: {rfc}"
    return False, f"Invalid RFC format: must be 12 chars (company) or 13 chars (person) with letters+date+homoclave"


def _validate_cuit(digits: str) -> tuple[bool, str]:
    if len(digits) != 11:
        return False, "CUIT/CUIL must have 11 digits"
    weights = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    s = sum(int(digits[i]) * weights[i] for i in range(10))
    check = 11 - (s % 11)
    if check == 11:
        check = 0
    if check == 10:
        return False, "Invalid CUIT/CUIL checksum (result 10)"
    if check != int(digits[10]):
        return False, "Invalid CUIT/CUIL checksum"
    return True, f"Valid CUIT/CUIL: {digits[:2]}-{digits[2:10]}-{digits[10]}"


def _validate_ruc_peru(digits: str) -> tuple[bool, str]:
    if len(digits) != 11:
        return False, "Peru RUC must have 11 digits"
    if digits[:2] not in ("10", "15", "16", "17", "20"):
        return False, f"Peru RUC must start with 10, 15, 16, 17, or 20 (got {digits[:2]})"
    weights = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    s = sum(int(digits[i]) * weights[i] for i in range(10))
    check = 11 - (s % 11)
    if check >= 10:
        check -= 10
    if check != int(digits[10]):
        return False, "Invalid RUC checksum"
    return True, f"Valid Peru RUC: {digits}"


@mcp.tool()
def validate_latam_tax_id(tax_id: str, country: str) -> dict:
    """Validate the format and checksum of a Latin American tax ID number.

    Supported countries and ID types:
    - Brazil: CNPJ (company, 14 digits) or CPF (individual, 11 digits)
    - Mexico: RFC (12 chars for companies, 13 for individuals)
    - Argentina: CUIT/CUIL (11 digits)
    - Peru: RUC (11 digits)

    Args:
        tax_id: The tax ID to validate (numbers only, or with formatting)
        country: Country code: BR, MX, AR, PE
    """
    country = country.upper().strip()
    digits = re.sub(r"\W", "", tax_id)

    if country == "BR":
        if len(digits) == 14:
            ok, msg = _validate_cnpj(digits)
            id_type = "CNPJ (company)"
        elif len(digits) == 11:
            ok, msg = _validate_cpf(digits)
            id_type = "CPF (individual)"
        else:
            return {"valid": False, "error": "Brazilian IDs must be 11 digits (CPF) or 14 digits (CNPJ)"}
    elif country == "MX":
        ok, msg = _validate_rfc(tax_id)
        id_type = "RFC"
        digits = tax_id.upper().strip()
    elif country == "AR":
        ok, msg = _validate_cuit(digits)
        id_type = "CUIT/CUIL"
    elif country == "PE":
        ok, msg = _validate_ruc_peru(digits)
        id_type = "RUC"
    else:
        return {
            "valid": False,
            "error": f"Unsupported country: {country}",
            "supported": {"BR": "Brazil (CNPJ/CPF)", "MX": "Mexico (RFC)", "AR": "Argentina (CUIT/CUIL)", "PE": "Peru (RUC)"},
        }

    return {
        "valid": ok,
        "tax_id": tax_id,
        "country": country,
        "id_type": id_type,
        "message": msg,
    }


if __name__ == "__main__":
    transport = os.getenv("MCP_TRANSPORT", "streamable-http")
    if transport == "streamable-http":
        mcp.run(transport="streamable-http")
    else:
        mcp.run(transport="stdio")
