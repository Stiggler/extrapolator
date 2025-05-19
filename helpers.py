import base64
import io
import sqlite3
import pandas as pd
import datetime
from openpyxl import load_workbook

def read_time_column_with_openpyxl(path_or_buffer, column_name):
    wb = load_workbook(path_or_buffer, data_only=True)
    ws = wb["data"]
    header = [cell.value for cell in next(ws.iter_rows(min_row=1, max_row=1))]
    target_index = None
    for i, name in enumerate(header):
        if name and str(name).strip().lower() == column_name.strip().lower():
            target_index = i
            break
    values = []
    if target_index is not None:
        for row in ws.iter_rows(min_row=2):
            val = row[target_index].value
            if isinstance(val, datetime.timedelta):
                values.append(val)
            elif isinstance(val, (int, float)):
                values.append(pd.to_timedelta(val, unit="D"))
            elif isinstance(val, str):
                try:
                    values.append(pd.to_timedelta(val))
                except:
                    values.append(pd.NaT)
            elif hasattr(val, "hour") and hasattr(val, "minute") and hasattr(val, "second"):
                try:
                    values.append(pd.to_timedelta(f"{val.hour}:{val.minute}:{val.second}"))
                except:
                    values.append(pd.NaT)
            else:
                values.append(pd.NaT)
    return pd.Series(values)


def convert_timedelta_to_decimal(td):
    if pd.isnull(td):
        return None
    return td.total_seconds() / 86400


def decimal_to_hms(decimal_val):
    if pd.isnull(decimal_val):
        return ""
    total_seconds = decimal_val * 86400
    total_seconds = int(round(total_seconds))
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

def time_to_timedelta(val):
    if pd.isna(val):
        return pd.NaT
    if isinstance(val, pd.Timedelta):
        return val
    if isinstance(val, (int, float)):
        # Excel-Zeitwert als Bruchteil eines Tages
        return pd.to_timedelta(val, unit="D")
    if isinstance(val, str):
        try:
            return pd.to_timedelta(val)
        except:
            return pd.NaT
    if hasattr(val, "hour") and hasattr(val, "minute") and hasattr(val, "second"):
        try:
            return pd.to_timedelta(f"{val.hour}:{val.minute}:{val.second}")
        except:
            return pd.NaT
    return pd.NaT





def parse_contents(contents, filename):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    try:
        excel_io = io.BytesIO(decoded)
        df = pd.read_excel(excel_io, sheet_name="data", engine="openpyxl")

        # Sichtbarkeiten & Sendezeiten robust auslesen
        df["visibility"] = read_time_column_with_openpyxl(excel_io, "visibility").apply(convert_timedelta_to_decimal)
        df["broadcasting_time"] = read_time_column_with_openpyxl(excel_io, "broadcasting_time").apply(convert_timedelta_to_decimal)

        # Weitere Zeitspalten normal verarbeiten
        for col in ["apt", "program_duration", "start_time_program", "end_time_program", "start_time_item"]:
            if col in df.columns:
                df[col] = df[col].apply(time_to_timedelta)
                df[col] = df[col].apply(convert_timedelta_to_decimal)

        return df
    except Exception as e:
        print(f"Fehler beim Einlesen von {filename}: {e}")
        return None



def update_database(df, mode, first_file):
    db_path = 'data.db'
    conn = sqlite3.connect(db_path)

    if first_file:
        if_exists_option = "replace" if mode == "replace" else "append"
        df.to_sql("data", conn, if_exists=if_exists_option, index=False)
    else:
        # 👉 Spaltenstruktur aus existierender Tabelle lesen
        existing_cols = pd.read_sql("SELECT * FROM data LIMIT 1", conn).columns.tolist()

        # 👉 Nur gemeinsame Spalten behalten (Überschüssige entfernen)
        df = df[[col for col in df.columns if col in existing_cols]]

        # 👉 Fehlende Spalten ergänzen mit NaN
        for col in existing_cols:
            if col not in df.columns:
                df[col] = pd.NA
        df = df[existing_cols]

        df.to_sql("data", conn, if_exists="append", index=False)

    conn.close()



def get_aggregated_data():
    db_path = 'data.db'
    conn = sqlite3.connect(db_path)
    query = """
    SELECT 
        TRIM(hr_basis) AS hr_basis,
        COUNT(DISTINCT bid) AS distinct_bid,
        SUM(visibility) AS sum_visibility,
        SUM(CASE WHEN tool IS NULL OR tool = '' THEN broadcasting_time ELSE 0 END) AS sum_broadcasting_time
    FROM data
    WHERE (media = 'TV/OTT' OR (media = 'Social Media' AND post_type IN ('Video')))
    GROUP BY TRIM(hr_basis);
    """
    df = pd.read_sql(query, conn)
    conn.close()
    if not df.empty:
        df['sum_visibility'] = df['sum_visibility'].apply(decimal_to_hms)
        df['sum_broadcasting_time'] = df['sum_broadcasting_time'].apply(decimal_to_hms)
    return df


def get_aggregated_data_opposite():
    db_path = 'data.db'
    conn = sqlite3.connect(db_path)
    query = """
    SELECT 
        TRIM(hr_basis) AS hr_basis,
        COUNT(DISTINCT bid) AS distinct_bid,
        SUM(mentions) AS sum_mentions
    FROM data
    WHERE media IN ('Print', 'Online', 'Social Media')
      AND (post_type IS NULL OR post_type = '' OR post_type NOT IN ('Video'))
    GROUP BY TRIM(hr_basis);
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df
