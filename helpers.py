import base64
import io
import sqlite3
import pandas as pd


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


def parse_contents(contents, filename):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    try:
        df = pd.read_excel(io.BytesIO(decoded), sheet_name="data", engine="openpyxl")
        for col in ["broadcasting_time", "visibility", "apt", "program_duration",
                    "start_time_program", "end_time_program", "start_time_item"]:
            if col in df.columns and pd.api.types.is_timedelta64_dtype(df[col]):
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
    else:
        if_exists_option = "append"
    df.to_sql("data", conn, if_exists=if_exists_option, index=False)
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
