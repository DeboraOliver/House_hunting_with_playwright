import json
import pandas as pd
from pathlib import Path
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

URL_ALVO = "https://www.vivareal.com.br/venda/sp/araraquara/"


def fechar_popups_e_banners(page):
    """
    Localiza e fecha modais, banners de cookies (LGPD) e pop-ups promocionais do VivaReal.
    Também oculta overlays residuais via CSS.
    """
    print("Verificando a presença de pop-ups e banners...")

    seletores_fechar = [
        "#cookie-notifier-cta",
        "button:has-text('Aceitar todos os cookies')",
        "button:has-text('Aceitar')",
        "button:has-text('Entendi')",
        "button[aria-label='Fechar']",
        "button[aria-label='Close']",
        ".cookie-notifier__cta",
        ".modal__close",
        ".js-modal-close",
        "[data-type='close']"
    ]

    for seletor in seletores_fechar:
        try:
            elemento = page.locator(seletor).first
            if elemento.is_visible(timeout=1000):
                elemento.click()
                print(f"  [POPUP FECHADO] Clique realizado no seletor: '{seletor}'")
                page.wait_for_timeout(300)
        except Exception:
            pass

    try:
        page.add_style_tag(content="""
            .cookie-notifier, 
            .modal-backdrop, 
            .js-modal-overlay,
            [class*="cookie"], 
            [class*="modal"] { 
                display: none !important; 
                visibility: hidden !important; 
            }
            body { 
                overflow: auto !important; 
            }
        """)
        print("  [DOM/CSS] Overlays e modais forçadamente ocultados via CSS.")
    except Exception:
        pass


def extrair_imoveis_do_json_ld(conteudo_html):
    """Processa o HTML capturado pelo Playwright e extrai os imóveis do JSON-LD."""
    soup = BeautifulSoup(conteudo_html, "html.parser")
    scripts_json_ld = soup.find_all("script", type="application/ld+json")

    imoveis = []

    for script in scripts_json_ld:
        if not script.string:
            continue

        try:
            dados = json.loads(script.string)

            if isinstance(dados, dict) and dados.get("@type") == "ItemList":
                itens = dados.get("itemListElement", [])

                for elemento in itens:
                    produto = elemento.get("item", {})
                    if produto.get("@type") != "Product":
                        continue

                    id_imovel = produto.get("@id", "N/A")
                    nome = produto.get("name", "")
                    descricao = produto.get("description", "").strip()
                    url_anuncio = produto.get("url", "")

                    address = produto.get("address", {})
                    rua = address.get("streetAddress", "")
                    cidade = address.get("addressLocality", "")
                    uf = address.get("addressRegion", "")

                    bairro = "N/A"
                    if " em " in nome:
                        bairro = (
                            nome.split(" em ")[-1]
                            .replace(", Araraquara", "")
                            .strip()
                        )

                    quartos = produto.get("numberOfBedrooms", None)
                    banheiros = produto.get("numberOfBathroomsTotal", None)

                    floor_size = produto.get("floorSize", {})
                    area_util = (
                        floor_size.get("value", None)
                        if isinstance(floor_size, dict)
                        else None
                    )

                    offers = produto.get("offers", {})
                    preco = offers.get("price", None)

                    condominio = None
                    condo_prop = offers.get("additionalProperty", {})
                    if (
                        isinstance(condo_prop, dict)
                        and condo_prop.get("name") == "Condominium Fee"
                    ):
                        condominio = condo_prop.get("value", None)

                    imoveis.append({
                        "ID": str(id_imovel),
                        "Título": nome,
                        "Cidade": cidade,
                        "UF": uf,
                        "Rua": rua,
                        "Bairro": bairro,
                        "Preço (R$)": float(preco) if preco else None,
                        "Condomínio (R$)": (
                            float(condominio) if condominio else None
                        ),
                        "Área Útil (m²)": (
                            float(area_util) if area_util else None
                        ),
                        "Quartos": quartos,
                        "Banheiros": banheiros,
                        "URL Anúncio": url_anuncio,
                        "Descrição": descricao,
                    })
        except json.JSONDecodeError:
            continue

    return imoveis


def executar_coleta_playwright():
    print("=" * 60)
    print("INICIANDO CRAWLING COM PLAYWRIGHT E EXTRAÇÃO JSON-LD")
    print("=" * 60)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=["--start-maximized"])

        context = browser.new_context(
            no_viewport=True,
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()

        print(f"Navegando para: {URL_ALVO}")
        page.goto(URL_ALVO, wait_until="domcontentloaded")

        page.wait_for_timeout(2000)
        fechar_popups_e_banners(page)

        # CORREÇÃO AQUI: Espera a tag existir no DOM (state="attached"), sem exigir visibilidade
        page.wait_for_selector("script[type='application/ld+json']", state="attached", timeout=15000)

        # Captura o HTML completo da página renderizada
        html_pagina = page.content()

        browser.close()

    print("Processando dados estruturados do HTML...")
    imoveis_coletados = extrair_imoveis_do_json_ld(html_pagina)

    print("=" * 60)
    print(f"Total de imóveis extraídos: {len(imoveis_coletados)}")

    if imoveis_coletados:
        df = pd.DataFrame(imoveis_coletados).drop_duplicates(subset=["ID"])

        #caminho_excel = Path("imoveis_araraquara_playwright.xlsx")
        caminho_csv = Path("imoveis_araraquara_playwright.csv")

        #df.to_excel(caminho_excel, index=False, engine="openpyxl")
        df.to_csv(caminho_csv, index=False, encoding="utf-8-sig")

        #print(f"[SUCESSO] Planilha Excel salva em: '{caminho_excel}'")
        print(f"[SUCESSO] Arquivo CSV salvo em: '{caminho_csv}'")
        print("=" * 60)
        print(
            df[
                [
                    "ID",
                    "Bairro",
                    "Quartos",
                    "Banheiros",
                    "Área Útil (m²)",
                    "Preço (R$)",
                ]
            ].head()
        )
        print("=" * 60)
    else:
        print("[ERRO] Nenhum imóvel foi encontrado no HTML.")


if __name__ == "__main__":
    executar_coleta_playwright()