import pandas as pd

# abrir 
df = pd.read_csv(
    "imoveis_araraquara_playwright.csv",
    converters={"Bairro": lambda value: value or float("nan")},
)

df.head(3)

# Da URL, coletar o bairro entre "quartos-" e "-bairros-araraquara" e trocar "-" por espaços.
mask = df["Bairro"].eq("N/A")
df.loc[mask, "Bairro"] = (
    df.loc[mask, "URL Anúncio"]
    .str.extract(r"quartos-(.*?)-bairros-araraquara", expand=False)
    .str.replace("-", " ", regex=False)
)

df.to_csv("imoveis_playwright.csv", index=False, encoding="utf-8-sig")