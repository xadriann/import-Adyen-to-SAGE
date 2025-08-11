# 📊 Conversor Adyen → SAGE (con Streamlit)

Esta herramienta convierte un Excel de Adyen en un archivo de asientos compatible con SAGE y genera una comprobación de cuadre contable por batch.

---

## ✅ Requisitos

- Tener [Python 3.8+](https://www.python.org/downloads/) instalado en tu equipo.
- Tener el archivo Excel de Adyen con dos hojas:
  - `Inputs`: contiene los datos desde la fila 7.
  - `Datos`: contiene la información de cuentas por hotel.

---

## ▶️ Cómo usarlo en tu ordenador (sin saber programar)

1. **Descarga los archivos del ZIP**
2. Abre una terminal y ejecuta:

```bash
pip install -r requirements.txt
streamlit run app.py
