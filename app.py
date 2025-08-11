import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO

# ============ FUNCIONES AUXILIARES ============

def limpiar_hotel(nombre):
    return nombre.replace("Travelodge", "").replace("POS", "").strip()

def generar_asientos(df, hoteles, asiento_inicial):
    df["Merchant Account"] = df["Merchant Account"].str.strip()
    hoteles["Merchant Account"] = hoteles["Merchant Account"].str.strip()

    df = df.merge(hoteles, on="Merchant Account", how="left")

    for col in ["Gross Credit (GC)", "Gross Debit (GC)", "Net Debit (NC)", "Bank/Card Commission (NC)"]:
        df[col] = df[col].astype(str).str.replace(",", ".").astype(float, errors="ignore")

    df["Batch Closed Date"] = pd.to_datetime(df["Batch Closed Date"], dayfirst=True)

    asientos = []

    # 1. CTA CLIENTE
    cliente_group = df.groupby(["Batch Number", "Merchant Account", "Hotel", "CTA CLIENTE", "CANAL", "Batch Closed Date"]).apply(
        lambda x: x["Gross Credit (GC)"].sum() - x["Gross Debit (GC)"].sum() - x.loc[x["Journal Type"] == "DepositCorrection", "Net Debit (NC)"].sum()
    ).reset_index(name="Importe")

    for _, row in cliente_group.iterrows():
        hotel_limpio = limpiar_hotel(row["Hotel"])
        asientos.append({
            "CodigoCuenta": int(row["CTA CLIENTE"]),
            "CargoAbono": "H",
            "FechaAsiento": row["Batch Closed Date"].strftime("%Y-%m-%d"),
            "ejercicio": row["Batch Closed Date"].year,
            "numeroperiodo": row["Batch Closed Date"].month,
            "Comentario": f"INGRESO ADYEN Batch {row['Batch Number']} {hotel_limpio}",
            "ImporteAsiento": round(row["Importe"], 2),
            "Codigocanal": row["CANAL"],
            "Codigodepartamento": "",
            "N. Documento": row["Batch Number"],
            "Batch number": row["Batch Number"]
        })

    # 2. CTA COMIS
    comis_group = df.groupby(["Batch Number", "Merchant Account", "Hotel", "CTA COMIS", "CANAL", "Batch Closed Date"]).apply(
        lambda x: x.loc[x["Journal Type"] == "Settled", "Bank/Card Commission (NC)"].sum()
        + x.loc[x["Journal Type"] == "Chargeback", "Bank/Card Commission (NC)"].sum()
        + x.loc[x["Journal Type"] == "Fee", "Net Debit (NC)"].sum()
    ).reset_index(name="Importe")

    for _, row in comis_group.iterrows():
        if row["Importe"] > 0:
            hotel_limpio = limpiar_hotel(row["Hotel"])
            asientos.append({
                "CodigoCuenta": int(row["CTA COMIS"]),
                "CargoAbono": "D",
                "FechaAsiento": row["Batch Closed Date"].strftime("%Y-%m-%d"),
                "ejercicio": row["Batch Closed Date"].year,
                "numeroperiodo": row["Batch Closed Date"].month,
                "Comentario": f"INGRESO ADYEN Batch {row['Batch Number']} {hotel_limpio}",
                "ImporteAsiento": round(row["Importe"], 2),
                "Codigocanal": row["CANAL"],
                "Codigodepartamento": "",
                "N. Documento": row["Batch Number"],
                "Batch number": row["Batch Number"]
            })

    # 3. CTA BANCO
    banco_group = df[df["Journal Type"] == "MerchantPayout"].groupby(
        ["Batch Number", "Merchant Account", "Hotel", "CTA BANCO", "CANAL", "Batch Closed Date"]
    )["Net Debit (NC)"].sum().reset_index(name="Importe")

    for _, row in banco_group.iterrows():
        hotel_limpio = limpiar_hotel(row["Hotel"])
        asientos.append({
            "CodigoCuenta": int(row["CTA BANCO"]),
            "CargoAbono": "D",
            "FechaAsiento": row["Batch Closed Date"].strftime("%Y-%m-%d"),
            "ejercicio": row["Batch Closed Date"].year,
            "numeroperiodo": row["Batch Closed Date"].month,
            "Comentario": f"INGRESO ADYEN Batch {row['Batch Number']} {hotel_limpio}",
            "ImporteAsiento": round(row["Importe"], 2),
            "Codigocanal": row["CANAL"],
            "Codigodepartamento": "",
            "N. Documento": row["Batch Number"],
            "Batch number": row["Batch Number"]
        })

    # 4. CTA INVOICE
    invoice_group = df[df["Journal Type"] == "InvoiceDeduction"].groupby(
        ["Batch Number", "Merchant Account", "Hotel", "CTA INVOICE", "CANAL", "Batch Closed Date"]
    )["Net Debit (NC)"].sum().reset_index(name="Importe")

    for _, row in invoice_group.iterrows():
        hotel_limpio = limpiar_hotel(row["Hotel"])
        asientos.append({
            "CodigoCuenta": int(row["CTA INVOICE"]),
            "CargoAbono": "D",
            "FechaAsiento": row["Batch Closed Date"].strftime("%Y-%m-%d"),
            "ejercicio": row["Batch Closed Date"].year,
            "numeroperiodo": row["Batch Closed Date"].month,
            "Comentario": f"INGRESO ADYEN Batch {row['Batch Number']} {hotel_limpio}",
            "ImporteAsiento": round(row["Importe"], 2),
            "Codigocanal": row["CANAL"],
            "Codigodepartamento": "",
            "N. Documento": row["Batch Number"],
            "Batch number": row["Batch Number"]
        })

    df_final = pd.DataFrame(asientos)
    df_final["Asiento"] = range(asiento_inicial, asiento_inicial + len(df_final))

    cols = [
        "Asiento", "CodigoCuenta", "CargoAbono", "FechaAsiento", "ejercicio",
        "numeroperiodo", "Comentario", "ImporteAsiento", "Codigocanal",
        "Codigodepartamento", "N. Documento", "Batch number"
    ]
    return df_final[cols]

def comprobar_cuadre(df):
    resultados = []
    for batch in df["Batch number"].unique():
        datos_batch = df[df["Batch number"] == batch]
        suma_haber = datos_batch[datos_batch["CargoAbono"] == "H"]["ImporteAsiento"].sum()
        suma_debe = datos_batch[datos_batch["CargoAbono"] == "D"]["ImporteAsiento"].sum()
        diferencia = suma_haber - suma_debe
        hotel = datos_batch.iloc[0]["Comentario"].split("Batch")[1].split()[1]
        resultados.append({
            "Batch Number": batch,
            "Hotel": hotel,
            "Suma Haber (H)": suma_haber,
            "Suma Debe (D)": suma_debe,
            "Diferencia (H-D)": diferencia,
            "Cuadra": "SÍ" if abs(diferencia) < 0.01 else "NO"
        })
    return pd.DataFrame(resultados)

# ============ INTERFAZ STREAMLIT ============

st.title("📊 Conversor de Adyen a SAGE con comprobación contable")

archivo = st.file_uploader("Sube el archivo Excel de Adyen con las hojas 'Inputs' y 'Datos'", type=["xlsx"])

asiento_inicial = st.number_input("Asiento inicial", min_value=1, value=1, step=1)

if archivo and st.button("Generar asientos y comprobar cuadre"):
    with st.spinner("Procesando..."):
        xls = pd.ExcelFile(archivo)
        df_inputs = pd.read_excel(xls, sheet_name="Inputs", skiprows=6)
        df_hoteles = pd.read_excel(xls, sheet_name="Datos")
        
        df_sage = generar_asientos(df_inputs, df_hoteles, asiento_inicial)
        df_cuadre = comprobar_cuadre(df_sage)

        # Mostrar resumen
        st.success("✅ Asientos generados y comprobación realizada.")
        st.subheader("📋 Resultado del cuadre contable por Batch")
        st.dataframe(df_cuadre)

        # Descarga del archivo Sage
        buffer_sage = BytesIO()
        with pd.ExcelWriter(buffer_sage, engine="openpyxl") as writer:
            df_sage.to_excel(writer, sheet_name="Datos", index=False)
        # Obtener el nombre del archivo sin extensión
        nombre_archivo = archivo.name.rsplit('.', 1)[0]
        nombre_sage = f"SAGE_import_{nombre_archivo}.xlsx"
        st.download_button("⬇️ Descargar archivo para Sage", buffer_sage.getvalue(), file_name=nombre_sage)

        # Descarga del archivo de comprobación
        buffer_cuadre = BytesIO()
        with pd.ExcelWriter(buffer_cuadre, engine="openpyxl") as writer:
            df_cuadre.to_excel(writer, sheet_name="Cuadre_por_Batch", index=False)
        st.download_button("⬇️ Descargar comprobación de cuadre", buffer_cuadre.getvalue(), file_name="Comprobacion_Cuadre.xlsx")
