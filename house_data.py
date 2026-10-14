import json
import pandas as pd
from playwright.sync_api import sync_playwright

url = "https://www.vivareal.com.br/venda/sp/araraquara/?onde=%2CS%C3%A3o+Paulo%2CAraraquara%2C%2C%2C%2C%2Ccity%2CBR%3ESao+Paulo%3ENULL%3EAraraquara%2C-21.774276%2C-48.17424%2C&pagina=2&precoMaximo=200000"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    print("Carregando página com Playwright...")
    page.goto(url, wait_until="domcontentloaded")

    # Extrai o conteúdo dentro da tag <script id="__NEXT_DATA__"> sem usar bs4
    script_content = page.eval_on_selector(
        "script#__NEXT_DATA__", "el => el.textContent"
    )

    data = json.loads(script_content)

    # Navega na estrutura do JSON
    results = (
        data.get("props", {})
        .get("pageProps", {})
        .get("initialState", {})
        .get("results", {})
        .get("listings", [])
    )

    imoveis = []
    for item in results:
        listing = item.get("listing", {})

        bairro = listing.get("address", {}).get("neighborhood", "N/A")
        quartos = (
            listing.get("bedrooms", [0])[0] if listing.get("bedrooms") else 0
        )
        banheiros = (
            listing.get("bathrooms", [0])[0] if listing.get("bathrooms") else 0
        )
        metragem = (
            listing.get("usableAreas", [0])[0]
            if listing.get("usableAreas")
            else 0
        )

        pricing = listing.get("pricingInfos", [{}])[0]
        valor = pricing.get("price", "N/A")

        imoveis.append({
            "Bairro": bairro,
            "Quartos": quartos,
            "Banheiros": banheiros,
            "Metragem": metragem,
            "Valor": valor,
        })

    browser.close()

    # Salva o resultado
    df = pd.DataFrame(imoveis)
    df.to_csv("imoveis_playwright.csv", index=False, encoding="utf-8-sig")
    print(f"Salvos {len(imoveis)} imóveis em 'imoveis_playwright.csv'.")