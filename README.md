# LATAM Intelligence MCP

Latin America business intelligence, compliance tools, and economic data for AI agents.

**No API key required.** Data from official government sources: Receita Federal Brazil, Banco Central do Brasil, Argentina datos.gob.ar.

## Tools

- **lookup_brazil_company** — Full company profile by CNPJ: name, status, address, partners, activity codes (Receita Federal)
- **lookup_brazil_address** — Brazilian address lookup by CEP (postal code)
- **validate_latam_tax_id** — Validate and verify tax ID checksum for Brazil (CNPJ/CPF), Mexico (RFC), Argentina (CUIT/CUIL), Peru (RUC)
- **get_brazil_exchange_rate** — Official BRL exchange rates from Banco Central do Brasil (PTAX)
- **get_argentina_economic_data** — Argentine economic indicators: dollar rate, inflation, GDP, policy rate, reserves

## Example queries

- "Look up Brazilian company with CNPJ 33.000.167/0001-01"
- "Who are the partners of Brazilian company 11.222.333/0001-81?"
- "Is this Mexican RFC number PEMX820810NH6 valid?"
- "Validate Argentine CUIT 30-50001036-0"
- "What is the current BRL/USD exchange rate?"
- "What is the Argentine monthly inflation for the last 6 months?"
- "Find the address for Brazilian postal code 01310-100"
- "Check if CNPJ 12.345.678/0001-95 is a valid Brazilian company"

## Coverage

### Brazil (Receita Federal + BrasilAPI + BCB)
- 50M+ registered companies (active and inactive)
- Full company profiles: legal name, trade name, CNAE activity codes
- Partners and shareholders with roles
- Address with CEP postal code lookup
- Official BRL exchange rates (PTAX) for USD, EUR, GBP, JPY, ARS, and more

### Argentina (datos.gob.ar)
- Official dollar exchange rate (historical series)
- Monthly and annual inflation (CPI)
- GDP growth
- Central bank policy rate
- Foreign reserves

### Tax ID Validation (4 countries, no API call needed)
| Country | ID Type | Format |
|---|---|---|
| Brazil 🇧🇷 | CNPJ | 14-digit company tax ID |
| Brazil 🇧🇷 | CPF | 11-digit individual tax ID |
| Mexico 🇲🇽 | RFC | 12-13 char alphanumeric |
| Argentina 🇦🇷 | CUIT/CUIL | 11-digit tax/social ID |
| Peru 🇵🇪 | RUC | 11-digit tax registry |

## Use cases

- KYC/AML compliance for companies with LATAM counterparties
- Due diligence on Brazilian companies
- FX risk monitoring (BRL/USD rates)
- Argentina economic monitoring for investment decisions
- Validating tax IDs before processing payments or contracts
- Legal and accounting firms with LATAM clients

## Data sources & legal

- **BrasilAPI** (`brasilapi.com.br`) — Open source community API wrapping Receita Federal data. Public domain.
- **Banco Central do Brasil** (`olinda.bcb.gov.br`) — Official Brazilian central bank open data API.
- **datos.gob.ar** (`apis.datos.gob.ar`) — Official Argentine government open data platform. Licensed under Creative Commons.
- Tax ID validation is purely algorithmic (no external API calls).

---
## Install & Access
**Smithery** — works with Claude, Cursor, Windsurf, and all MCP clients:
```bash
npx -y @smithery/cli install @fzth-ia-it/latam-intelligence-mcp --client claude
```
[![Smithery](https://smithery.ai/badge/@fzth-ia-it/latam-intelligence-mcp)](https://smithery.ai/server/@fzth-ia-it/latam-intelligence-mcp)

**MCPize** — hosted, managed access with Free / PRO / ULTRA tiers:  
[mcpize.com](https://mcpize.com) → search `LATAM Intelligence MCP`
